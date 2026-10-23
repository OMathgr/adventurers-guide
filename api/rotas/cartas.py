"""Usar uma carta de domínio na sessão de jogo (motor/usos_de_cartas.py).

O jogador usa uma carta da mão do seu personagem (jogando esta sessão): paga
o custo e aplica os efeitos nele e nos aliados escolhidos, que também estão
jogando a sessão (todos são salvos juntos). O uso entra no registro ao vivo,
como uma rolagem, para o mestre ver; Medo tirado pela carta sai do Medo da sessão.

Com `rolagem_id`, a carta foi disparada por uma rolagem do registro (gatilho:
crítico, falha, dano...): vale uma vez por rolagem, e as que mudam a rolagem
(Fane of the Wilds, Stealth Expertise, Wild Surge) a refazem como uma reação,
na ficha de quem rolou (a versão nova substitui a antiga no registro).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from motor import RegraViolada, ResultadoRolagem

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..esquemas import FichaSaida, ficha_saida
from ..repositorio import NaoEncontrado
from ..tabelas import ParticipacaoTabela, PersonagemTabela, RolagemTabela
from .rolagens import _RESULTADO, RolagemSaida, _meu_personagem, _registrar, _saida, _sessao, _somar_medo

rotas = APIRouter(prefix="/mesas/{mesa_id}/sessoes/{sessao_id}", tags=["Cartas"])


class UsoEntrada(BaseModel):
    personagem_id: str = Field(description="O seu personagem, jogando esta sessão")
    carta: str
    alvos: list[str] = Field(default_factory=list,
                             description="Aliados da sessão (ids de personagem). Vazio em \"todos os aliados\": todos.")
    opcao: str | None = None
    quantidade: int | None = Field(None, ge=0)
    rolagem_id: str | None = Field(None, description="A rolagem do registro que disparou a carta (RolagemSaida.cartas)")


class UsoDeCartaSaida(BaseModel):
    notas: list[str]
    teste: str              # o que rolar agora, se a carta pede
    ficha: FichaSaida
    registro: RolagemSaida


def _tipo_de_alvo(p, pedido: UsoEntrada) -> str | None:
    carta = p.bib.cartas.get(pedido.carta)
    if carta is None or carta.uso is None:
        return None
    opcao = next((o for o in carta.uso.opcoes if o.id == pedido.opcao), None)
    return opcao.alvo if opcao and opcao.alvo else carta.uso.alvo


@rotas.post("/cartas/usar", response_model=UsoDeCartaSaida)
def usar(mesa_id: str, sessao_id: str, pedido: UsoEntrada, a: Acesso = Depends(acesso)):
    s = _sessao(a, mesa_id, sessao_id, rolar=True)
    linha, p = _meu_personagem(a, s, pedido.personagem_id)
    aliados = []
    for alvo_id in dict.fromkeys(pedido.alvos):
        if alvo_id == linha.id:
            continue
        alvo = a.banco.get(PersonagemTabela, alvo_id)
        ativa = repositorio.participacao_ativa(a.banco, alvo_id) if alvo else None
        if ativa is None or ativa.sessao_id != s.id:
            raise NaoEncontrado("O aliado precisa estar jogando esta sessão.")
        aliados.append((alvo, repositorio.montar(alvo)))
    if not pedido.alvos and _tipo_de_alvo(p, pedido) in ("aliados", "grupo"):
        # "todos os aliados": quem está jogando a sessão, menos você
        participantes = a.banco.query(ParticipacaoTabela).filter_by(sessao_id=s.id)
        aliados = [(x.personagem, repositorio.montar(x.personagem)) for x in participantes
                   if x.personagem_id != linha.id]
    rolagem, original, dono_linha, dono = None, None, None, None
    if pedido.rolagem_id:
        original = a.banco.get(RolagemTabela, pedido.rolagem_id)
        if original is None or original.sessao_id != s.id or original.personagem_id is None:
            raise NaoEncontrado("Rolagem não encontrada.")
        if original.substituida_por is not None:
            raise RegraViolada("Essa rolagem já foi refeita: use a carta na versão nova.")
        rolagem = _RESULTADO.validate_python(original.resultado)
        if original.personagem_id != linha.id:   # rolagem de um aliado (Stealth Expertise, Encore)
            dono_linha, dono = next(((x, y) for x, y in aliados if x.id == original.personagem_id), (None, None))
            if dono is None:
                dono_linha = a.banco.get(PersonagemTabela, original.personagem_id)
                participa = a.banco.query(ParticipacaoTabela).filter_by(sessao_id=s.id, personagem_id=dono_linha.id).first()
                if participa is None:
                    raise RegraViolada("Esse personagem não está mais nesta sessão.")
                dono = repositorio.montar(dono_linha)
    r = p.usar_carta(pedido.carta, [x for _, x in aliados], pedido.opcao, pedido.quantidade,
                     rolagem=rolagem, dono_da_rolagem=dono)
    if r.medo:
        _somar_medo(s, -r.medo)
    repositorio.gravar(a.banco, linha, p, commit=False)
    for alvo_linha, alvo in aliados:
        repositorio.gravar(a.banco, alvo_linha, alvo, commit=False)
    if dono is not None and all(dono is not y for _, y in aliados):
        repositorio.gravar(a.banco, dono_linha, dono, commit=False)
    if original is not None:
        original.resultado = _RESULTADO.dump_python(rolagem, mode="json")   # a carta foi usada nesta rolagem
        if r.rolagem is not None:   # a carta mudou a rolagem: a versão nova a substitui
            novo = r.rolagem
            if novo.medo_gerado != rolagem.medo_gerado:
                _somar_medo(s, novo.medo_gerado - rolagem.medo_gerado)
            nova = _registrar(a, s, novo, original.personagem_id, original.oculta)
            original.substituida_por = nova.id
    nome = p.bib.cartas[pedido.carta].nome
    registro = _registrar(a, s, ResultadoRolagem(titulo=f"Carta: {nome}", dados=[], bonus=[], total=0, tipo="carta",
                                                 efeitos=r.notas + ([f"Teste: {r.teste}"] if r.teste else []),
                                                 carta=pedido.carta), linha.id)
    a.banco.commit()
    return UsoDeCartaSaida(notas=r.notas, teste=r.teste, ficha=ficha_saida(p.ficha()), registro=_saida(a, registro))
