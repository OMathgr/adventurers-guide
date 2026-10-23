"""Rolagem de dados na sessão de jogo: o servidor rola (motor/rolagem.py) e
guarda no registro da sessão, que todos os membros veem ao vivo.

- Com personagem (o seu, jogando esta sessão): teste de atributo, ataque,
  conjuração, reação e dano (da arma ou de carta da mão), com os efeitos do
  catálogo (automáticos, opções com custo) e o resultado aplicado na ficha;
  "com Medo" dá Medo ao mestre da sessão.
- Livre (qualquer membro): uma expressão. O mestre responsável pode rolar oculto.
- Reações (depois do resultado): o personagem que reage paga o custo; a
  rolagem é desfeita e refeita na ficha do dono, e a versão nova entra no
  registro no lugar da anterior (que fica marcada como substituída).
"""

import random
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, TypeAdapter

from motor import OpcaoDeRolagem, OpcaoEscolhida, Personagem, RegraViolada, ResultadoRolagem, Traco
from motor.encontro import MEDO_MAXIMO
from motor.rolagem import rolar_expressao

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..mesas import SemPermissao, membro
from ..repositorio import NaoEncontrado
from ..tabelas import ParticipacaoTabela, PersonagemTabela, RolagemTabela, SessaoTabela

rotas = APIRouter(prefix="/mesas/{mesa_id}/sessoes/{sessao_id}", tags=["Rolagens"])
_RESULTADO = TypeAdapter(ResultadoRolagem)
LIMITE_REGISTRO = 60


class PedidoDeRolagem(BaseModel):
    tipo: Literal["atributo", "ataque", "conjuracao", "dano", "livre"]
    personagem_id: str | None = None
    traco: Traco | None = None                # atributo
    ataque: int | None = None                 # índice em ficha.ataques (ataque e dano)
    conjuracao: int = 0                       # índice em ficha.conjuracoes
    carta: str | None = None                  # dano de carta da mão
    formula: int = 0                          # qual rolagem da carta
    experiencias: list[str] = []
    vantagem: bool = False
    desvantagem: bool = False
    dificuldade: int | None = Field(None, ge=1, le=60)
    reacao: bool = False
    critico: bool = False                     # dano crítico
    extra: str = Field("", max_length=60)     # dano: dados/números a mais
    somar: str = Field("", max_length=60)     # teste: dados de fora (Inspiração, Oração...)
    expressao: str = Field("", max_length=80)  # livre
    opcoes: list[OpcaoEscolhida] = []
    oculta: bool = False                      # só o mestre responsável


class PedidoDeReacao(BaseModel):
    personagem_id: str                        # quem reage (o seu personagem nesta sessão)
    efeito: str
    escolha: str | None = None


class RolagemSaida(BaseModel):
    id: str
    autor: str
    usuario_id: str
    personagem_id: str | None
    personagem: str | None
    oculta: bool
    substituida: bool
    criado_em: str
    resultado: ResultadoRolagem
    reacoes: list[OpcaoDeRolagem] = []       # o que VOCÊ pode fazer nesta rolagem agora
    cartas: list[str] = []                   # cartas da SUA mão que esta rolagem dispara (usar com rolagem_id)


def _sessao(a: Acesso, mesa_id: str, sessao_id: str, rolar: bool = False) -> SessaoTabela:
    membro(a.banco, mesa_id, a.usuario_id)
    s = a.banco.get(SessaoTabela, sessao_id)
    if s is None or s.mesa_id != mesa_id or s.status not in ("em_andamento", "encerrada") and \
            s.responsavel_id != a.usuario_id:
        raise NaoEncontrado("Sessão não encontrada.")
    if rolar and s.status != "em_andamento":
        raise RegraViolada("Só dá para rolar numa sessão em andamento.")
    return s


def _meu_personagem(a: Acesso, s: SessaoTabela, personagem_id: str) -> tuple[PersonagemTabela, Personagem]:
    """O seu personagem, jogando esta sessão (as marcas são as dela)."""
    linha = a.banco.get(PersonagemTabela, personagem_id)
    if linha is None or linha.dono_id != a.usuario_id:
        raise NaoEncontrado("Personagem não encontrado.")
    ativa = repositorio.participacao_ativa(a.banco, linha.id)
    if ativa is None or ativa.sessao_id != s.id:
        raise RegraViolada("Entre nesta sessão com o personagem para rolar com ele.")
    return linha, repositorio.montar(linha)


def _saida(a: Acesso, linha: RolagemTabela, reacoes: list[OpcaoDeRolagem] | None = None,
           cartas: list[str] | None = None) -> RolagemSaida:
    return RolagemSaida(
        id=linha.id, autor=linha.usuario.nome, usuario_id=linha.usuario_id, personagem_id=linha.personagem_id,
        personagem=(linha.personagem.nome or "Sem nome") if linha.personagem else None, oculta=linha.oculta,
        substituida=linha.substituida_por is not None, criado_em=linha.criado_em.isoformat(),
        resultado=_RESULTADO.validate_python(linha.resultado), reacoes=reacoes or [], cartas=cartas or [])


def _somar_medo(s: SessaoTabela, delta: int):
    """Medo do mestre (0 a 12). Desfazer um "com Medo" numa reação não falha se
    o mestre já gastou aquele Medo: só não fica negativo."""
    s.medo = max(0, min(MEDO_MAXIMO, s.medo + delta))


def _registrar(a: Acesso, s: SessaoTabela, r: ResultadoRolagem, personagem_id: str | None,
               oculta: bool = False) -> RolagemTabela:
    linha = RolagemTabela(id=str(uuid.uuid4()), mesa_id=s.mesa_id, sessao_id=s.id, usuario_id=a.usuario_id,
                          personagem_id=personagem_id, oculta=oculta, resultado=_RESULTADO.dump_python(r, mode="json"))
    a.banco.add(linha)
    return linha


@rotas.get("/rolagens", response_model=list[RolagemSaida])
def registro(mesa_id: str, sessao_id: str, personagem_id: str | None = None, a: Acesso = Depends(acesso)):
    """As últimas rolagens da sessão (as ocultas, só para quem rolou). Com
    `personagem_id` (o seu, nesta sessão), cada uma traz as reações que ele pode usar."""
    s = _sessao(a, mesa_id, sessao_id)
    linhas = (a.banco.query(RolagemTabela).filter_by(sessao_id=s.id).order_by(RolagemTabela.criado_em.desc())
              .limit(LIMITE_REGISTRO).all())
    linhas = [x for x in linhas if not x.oculta or x.usuario_id == a.usuario_id]
    eu = None
    if personagem_id and s.status == "em_andamento":
        try:
            _, eu = _meu_personagem(a, s, personagem_id)
        except (NaoEncontrado, RegraViolada):
            eu = None
    saida = []
    for x in linhas:
        reacoes, cartas = [], []
        if eu is not None and x.personagem_id and x.substituida_por is None:
            r = _RESULTADO.validate_python(x.resultado)
            proprio = x.personagem_id == personagem_id
            reacoes = [o for o in eu.opcoes_de_rolagem(r.tipo, r.traco, r.ataque if proprio else None,
                                                        r.carta if proprio else None)
                       if o.momento == "depois" and (o.alvo == "qualquer" or (o.alvo == "aliado") != proprio)]
            if r.tipo != "carta":
                cartas = eu.cartas_para_rolagem(r, proprio)
        saida.append(_saida(a, x, reacoes, cartas))
    return saida


@rotas.get("/rolagens/opcoes", response_model=list[OpcaoDeRolagem])
def opcoes(mesa_id: str, sessao_id: str, personagem_id: str, tipo: str, traco: str | None = None,
           ataque: int | None = None, carta: str | None = None, a: Acesso = Depends(acesso)):
    """Os efeitos do catálogo para esta rolagem: automáticos e opções (com custo e se dá para usar agora)."""
    s = _sessao(a, mesa_id, sessao_id, rolar=True)
    _, p = _meu_personagem(a, s, personagem_id)
    return [o for o in p.opcoes_de_rolagem(tipo, traco, ataque, carta) if o.momento != "depois"]


@rotas.post("/rolagens", response_model=RolagemSaida, status_code=201)
def rolar(mesa_id: str, sessao_id: str, pedido: PedidoDeRolagem, a: Acesso = Depends(acesso)):
    s = _sessao(a, mesa_id, sessao_id, rolar=True)
    if pedido.oculta and s.responsavel_id != a.usuario_id:
        raise SemPermissao("Só o mestre da sessão rola oculto.")
    if pedido.tipo == "livre":
        if pedido.personagem_id:
            _meu_personagem(a, s, pedido.personagem_id)   # só com o seu personagem desta sessão
        r = rolar_expressao(pedido.expressao, random.Random(), "Rolagem livre")
        linha = _registrar(a, s, r, pedido.personagem_id or None, pedido.oculta)
        a.banco.commit()
        return _saida(a, linha)
    if not pedido.personagem_id:
        raise RegraViolada("Escolha o personagem que rola.")
    linha_p, p = _meu_personagem(a, s, pedido.personagem_id)
    if pedido.tipo == "dano":
        r = p.rolar_dano(ataque=pedido.ataque, carta=pedido.carta, formula=pedido.formula, critico=pedido.critico,
                         extra=pedido.extra, opcoes=pedido.opcoes)
    else:
        alvo = {"atributo": pedido.traco.value if pedido.traco else None, "ataque": pedido.ataque,
                "conjuracao": pedido.conjuracao}[pedido.tipo]
        r = p.rolar_teste(pedido.tipo, alvo, pedido.experiencias, pedido.vantagem, pedido.desvantagem,
                          pedido.dificuldade, pedido.reacao, pedido.opcoes, pedido.somar)
    if r.medo_gerado:
        _somar_medo(s, r.medo_gerado)
    repositorio.gravar(a.banco, linha_p, p, commit=False)
    linha = _registrar(a, s, r, linha_p.id, pedido.oculta)
    a.banco.commit()
    return _saida(a, linha)


@rotas.post("/rolagens/{rolagem_id}/reacao", response_model=RolagemSaida, status_code=201)
def reagir(mesa_id: str, sessao_id: str, rolagem_id: str, pedido: PedidoDeReacao, a: Acesso = Depends(acesso)):
    s = _sessao(a, mesa_id, sessao_id, rolar=True)
    original = a.banco.get(RolagemTabela, rolagem_id)
    if original is None or original.sessao_id != s.id or original.personagem_id is None:
        raise NaoEncontrado("Rolagem não encontrada.")
    if original.substituida_por is not None:
        raise RegraViolada("Essa rolagem já foi refeita: reaja à versão nova.")
    linha_eu, eu = _meu_personagem(a, s, pedido.personagem_id)
    if original.personagem_id == linha_eu.id:
        linha_dono, dono = linha_eu, eu
    else:
        linha_dono = a.banco.get(PersonagemTabela, original.personagem_id)
        participa = a.banco.query(ParticipacaoTabela).filter_by(sessao_id=s.id, personagem_id=linha_dono.id).first()
        if participa is None:
            raise RegraViolada("Esse personagem não está mais nesta sessão.")
        dono = repositorio.montar(linha_dono)
    antigo = _RESULTADO.validate_python(original.resultado)
    novo = eu.reagir(antigo, pedido.efeito, pedido.escolha, dono=dono)
    if novo.medo_gerado != antigo.medo_gerado:
        _somar_medo(s, novo.medo_gerado - antigo.medo_gerado)
    repositorio.gravar(a.banco, linha_eu, eu, commit=False)
    if dono is not eu:
        repositorio.gravar(a.banco, linha_dono, dono, commit=False)
    linha = _registrar(a, s, novo, linha_dono.id, original.oculta)
    original.substituida_por = linha.id
    a.banco.commit()
    return _saida(a, linha)
