"""Repouso do grupo: o mestre responsável pela sessão abre um descanso curto ou
longo; cada jogador escolhe os movimentos do seu personagem (podem ser num
aliado); o mestre encerra e o motor aplica tudo de uma vez (motor/repouso.py).
Ao encerrar, o mestre ganha Medo: 1d4 no curto, 1d4 + o número de personagens
no longo.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, TypeAdapter

from motor import RegraViolada
from motor.encontro import ajustar_medo
from motor.repouso import EscolhaDeRepouso, ResultadoDoRepouso, TipoDeRepouso, concluir, validar_escolha
from motor.sessao import Movimento

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..mesas import SemPermissao, membro
from ..repositorio import NaoEncontrado
from ..sessoes import sessao_do_mestre
from ..tabelas import MesaTabela, PersonagemTabela, RepousoTabela, SessaoTabela

rotas = APIRouter(prefix="/mesas/{mesa_id}", tags=["Repouso"])
_ESCOLHA = TypeAdapter(EscolhaDeRepouso)
_RESULTADO = TypeAdapter(ResultadoDoRepouso)
MOSTRAR_RESULTADO_POR = timedelta(minutes=30)   # depois de encerrado, o resultado fica à vista um tempo


class MovimentoEntrada(BaseModel):
    movimento: Movimento
    alvo: str | None = None                      # id de um aliado no repouso
    rolagem: int | None = Field(None, ge=1, le=4)   # d4 da mesa (no curto); sem ela, o app rola


class EscolhaEntrada(BaseModel):
    movimentos: list[MovimentoEntrada]
    movimento_longo: int | None = None           # Efficient (Clank)


class NovoRepouso(BaseModel):
    tipo: TipoDeRepouso
    participantes: list[str] | None = None       # ids; sem a lista, todos os personagens vivos dos jogadores


class Encerrar(BaseModel):
    interrompido: bool = False                   # longo interrompido vale como curto
    rolagem_medo: int | None = Field(None, ge=1, le=4)


class Participante(BaseModel):
    id: str
    nome: str
    jogador: str
    dono_id: str
    pronto: bool
    escolha: EscolhaEntrada | None


class RepousoSaida(BaseModel):
    id: str
    sessao_id: str
    tipo: TipoDeRepouso
    status: str                                  # aberto, concluido, cancelado
    mestre: str
    sou_responsavel: bool
    participantes: list[Participante]
    resultado: ResultadoDoRepouso | None = None
    medo_ganho: int | None = None


def _saida(a: Acesso, r: RepousoTabela) -> RepousoSaida:
    sessao = a.banco.get(SessaoTabela, r.sessao_id)
    linhas = {p.id: p for p in a.banco.query(PersonagemTabela).filter(PersonagemTabela.id.in_(r.participantes))}
    participantes = []
    for pid in r.participantes:
        p = linhas.get(pid)
        if p is None:
            continue
        escolha = r.escolhas.get(pid)
        participantes.append(Participante(id=pid, nome=p.nome or "Sem nome", jogador=p.dono.nome, dono_id=p.dono_id,
                                          pronto=escolha is not None,
                                          escolha=EscolhaEntrada.model_validate(escolha) if escolha else None))
    resultado = r.resultado or {}
    return RepousoSaida(
        id=r.id, sessao_id=r.sessao_id, tipo=TipoDeRepouso(r.tipo), status=r.status, mestre=sessao.responsavel.nome,
        sou_responsavel=sessao.responsavel_id == a.usuario_id, participantes=participantes,
        resultado=_RESULTADO.validate_python(resultado["repouso"]) if "repouso" in resultado else None,
        medo_ganho=resultado.get("medo"))


def _repouso(a: Acesso, mesa_id: str, repouso_id: str) -> RepousoTabela:
    r = a.banco.get(RepousoTabela, repouso_id)
    if r is None or r.mesa_id != mesa_id:
        raise NaoEncontrado("Repouso não encontrado.")
    return r


def _aberto(r: RepousoTabela):
    if r.status != "aberto":
        raise RegraViolada("Este repouso já foi encerrado.")


@rotas.get("/repouso", response_model=RepousoSaida | None)
def repouso_atual(mesa_id: str, a: Acesso = Depends(acesso)):
    """O repouso aberto da mesa (ou o último encerrado, por meia hora, para todos
    verem o resultado). Qualquer membro."""
    membro(a.banco, mesa_id, a.usuario_id)
    r = (a.banco.query(RepousoTabela).filter_by(mesa_id=mesa_id)
         .order_by(RepousoTabela.criado_em.desc()).first())
    if r is None:
        return None
    if r.status != "aberto":
        fim = r.atualizado_em if r.atualizado_em.tzinfo else r.atualizado_em.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fim > MOSTRAR_RESULTADO_POR:
            return None
    return _saida(a, r)


@rotas.post("/sessoes/{sessao_id}/repouso", status_code=201, response_model=RepousoSaida)
def abrir(mesa_id: str, sessao_id: str, pedido: NovoRepouso, a: Acesso = Depends(acesso)):
    """O mestre responsável abre o repouso: os jogadores escolhem os movimentos."""
    sessao = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    if a.banco.query(RepousoTabela).filter_by(mesa_id=mesa_id, status="aberto").first():
        raise RegraViolada("Já há um repouso aberto nesta mesa: encerre ou cancele antes.")
    mesa = a.banco.get(MesaTabela, mesa_id)
    vivos = {p.id: p for p in mesa.personagens if not (p.sessao or {}).get("morto")}
    if pedido.participantes is None:
        participantes = [i for i, p in vivos.items() if p.dono_id != sessao.responsavel_id]
    else:
        participantes = list(dict.fromkeys(pedido.participantes))
        fora = [i for i in participantes if i not in vivos]
        if fora:
            raise RegraViolada("Só personagens vivos desta mesa podem descansar.")
    if not participantes:
        raise RegraViolada("Nenhum personagem para descansar.")
    r = RepousoTabela(id=str(uuid.uuid4()), mesa_id=mesa_id, sessao_id=sessao_id, tipo=pedido.tipo.value,
                      participantes=participantes, escolhas={})
    a.banco.add(r)
    a.banco.commit()
    return _saida(a, r)


@rotas.put("/repouso/{repouso_id}/escolhas/{personagem_id}", response_model=RepousoSaida)
def escolher(mesa_id: str, repouso_id: str, personagem_id: str, pedido: EscolhaEntrada,
             a: Acesso = Depends(acesso)):
    """O dono do personagem (ou o mestre responsável) escolhe os movimentos. A
    escolha é conferida já; aplicar, só quando o mestre encerrar."""
    membro(a.banco, mesa_id, a.usuario_id)
    r = _repouso(a, mesa_id, repouso_id)
    _aberto(r)
    if personagem_id not in r.participantes:
        raise NaoEncontrado("Este personagem não está no repouso.")
    linha = repositorio.linha_na_mesa(a.banco, mesa_id, personagem_id)
    responsavel = a.banco.get(SessaoTabela, r.sessao_id).responsavel_id
    if a.usuario_id not in (linha.dono_id, responsavel):
        raise SemPermissao("Só o dono do personagem (ou o mestre da sessão) escolhe os movimentos dele.")
    escolha = _ESCOLHA.validate_python(pedido.model_dump())
    validar_escolha(r.tipo, personagem_id, repositorio.montar(linha), escolha, set(r.participantes))
    r.escolhas = {**r.escolhas, personagem_id: pedido.model_dump(mode="json")}
    a.banco.commit()
    return _saida(a, r)


@rotas.post("/sessoes/{sessao_id}/repouso/{repouso_id}/encerrar", response_model=RepousoSaida)
def encerrar(mesa_id: str, sessao_id: str, repouso_id: str, pedido: Encerrar, a: Acesso = Depends(acesso)):
    """Aplica os movimentos de todos de uma vez e dá o Medo ao mestre. Se alguma
    escolha não valer mais, nada muda."""
    sessao = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    r = _repouso(a, mesa_id, repouso_id)
    _aberto(r)
    linhas = {pid: repositorio.linha_na_mesa(a.banco, mesa_id, pid) for pid in r.participantes}
    personagens = {pid: repositorio.montar(linha) for pid, linha in linhas.items()}
    escolhas = {pid: _ESCOLHA.validate_python(e) for pid, e in r.escolhas.items() if pid in personagens}
    resultado = concluir(r.tipo, personagens, escolhas, pedido.interrompido)
    d4 = pedido.rolagem_medo or random.randint(1, 4)
    vivos = sum(1 for p in personagens.values() if not p.sessao.morto)
    medo = d4 + (vivos if resultado.tipo is TipoDeRepouso.LONGO else 0)
    sessao.medo = ajustar_medo(sessao.medo, medo)
    for pid, linha in linhas.items():
        repositorio.gravar(a.banco, linha, personagens[pid], commit=False)
    r.status = "concluido"
    r.resultado = {"repouso": _RESULTADO.dump_python(resultado, mode="json"), "medo": medo}
    a.banco.commit()   # tudo junto: personagens, Medo e o repouso
    return _saida(a, r)


@rotas.post("/sessoes/{sessao_id}/repouso/{repouso_id}/cancelar", response_model=RepousoSaida)
def cancelar(mesa_id: str, sessao_id: str, repouso_id: str, a: Acesso = Depends(acesso)):
    """Repouso que não aconteceu (ou descanso curto interrompido): ninguém ganha nada."""
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    r = _repouso(a, mesa_id, repouso_id)
    _aberto(r)
    r.status = "cancelado"
    a.banco.commit()
    return _saida(a, r)
