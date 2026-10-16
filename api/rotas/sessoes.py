"""Sessões de jogo: planejamento e condução por UM mestre (o responsável).

Criar exige ser mestre com a permissão `preparar`; quem cria é o responsável.
Ver, mudar, compartilhar e conduzir seguem `api/sessoes.py`. O Medo é de cada
sessão e começa no número de personagens da mesa que não são do mestre
responsável (máximo 12).
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import object_session

from motor import RegraViolada
from motor.encontro import MEDO_MAXIMO, ajustar_medo, definir_medo

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..concorrencia import conferir, versao_de
from ..mesas import MESTRE, Permissao, eh_criador, exigir, exigir_mestre, membro
from ..sessoes import STATUS, pode_ver, sessao_do_mestre
from .. import npcs
from ..repositorio import NaoEncontrado
from ..tabelas import MembroTabela, NpcTabela, ParticipacaoTabela, SessaoTabela
from .encontros import EncontroResumo, resumos

rotas = APIRouter(prefix="/mesas/{mesa_id}/sessoes", tags=["Sessões"])


class SessaoResumo(BaseModel):
    id: str
    titulo: str
    data: date | None
    status: str
    medo: int
    responsavel_id: str
    responsavel: str
    sou_responsavel: bool
    posso_gerir: bool = False          # vê o lado do mestre (responsável ou compartilhada)
    participantes: int = 0             # personagens que entraram


class Sessao(SessaoResumo):
    resumo: str
    notas: str                         # privadas do mestre
    compartilhada_com: list[str]       # ids de mestres que podem ver (só leitura)
    npcs: list[str]                    # NPCs da mesa que devem aparecer
    inimigos: list[str]                # inimigos da mesa que devem aparecer
    encontros: list[EncontroResumo]
    versao: str                        # do planejamento: mande de volta ao salvar (api/concorrencia.py)


class NovaSessao(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    data: date | None = None


class DadosDaSessao(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    data: date | None = None
    resumo: str = Field("", max_length=4000)
    notas: str = Field("", max_length=8000)
    npcs: list[str] = []
    inimigos: list[str] = []


class StatusDaSessao(BaseModel):
    status: str = Field(pattern="^(" + "|".join(STATUS) + ")$")


class Compartilhar(BaseModel):
    mestres: list[str] = Field(description="Ids dos mestres da mesa que podem ver a sessão")


class AjusteMedo(BaseModel):
    delta: int = Field(description="Positivo ganha (até 12), negativo gasta")


class ValorMedo(BaseModel):
    valor: int


def _resumo(s: SessaoTabela, usuario_id: str) -> SessaoResumo:
    return SessaoResumo(id=s.id, titulo=s.titulo, data=s.data, status=s.status, medo=s.medo,
                        responsavel_id=s.responsavel_id, responsavel=s.responsavel.nome,
                        sou_responsavel=s.responsavel_id == usuario_id, posso_gerir=pode_ver(s, usuario_id),
                        participantes=object_session(s).query(ParticipacaoTabela).filter_by(sessao_id=s.id).count())


def _versao_conteudo(s: SessaoTabela) -> tuple:
    return s.titulo, s.data, s.resumo, s.notas, list(s.npcs or []), list(s.inimigos or [])


def _versao_planejamento(s: SessaoTabela) -> str:
    return versao_de(*_versao_conteudo(s))


def _saida(a: Acesso, s: SessaoTabela) -> Sessao:
    return Sessao(**_resumo(s, a.usuario_id).model_dump(), resumo=s.resumo, notas=s.notas,
                  compartilhada_com=list(s.compartilhada_com or []), npcs=list(s.npcs or []),
                  inimigos=list(s.inimigos or []), encontros=resumos(a, s.id), versao=_versao_planejamento(s))


@rotas.get("", response_model=list[SessaoResumo])
def listar(mesa_id: str, a: Acesso = Depends(acesso)):
    """Para qualquer membro: as em andamento (para entrar) e as encerradas (para
    consultar). As planejadas, só as suas e as compartilhadas com você."""
    membro(a.banco, mesa_id, a.usuario_id)
    linhas = a.banco.query(SessaoTabela).filter_by(mesa_id=mesa_id).order_by(SessaoTabela.criado_em)
    return [_resumo(s, a.usuario_id) for s in linhas
            if pode_ver(s, a.usuario_id) or s.status in ("em_andamento", "encerrada")]


@rotas.post("", status_code=201, response_model=Sessao)
def criar(mesa_id: str, dados: NovaSessao, a: Acesso = Depends(acesso)):
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir_mestre(m)
    exigir(m, Permissao.PREPARAR)
    # o Medo começa no número de personagens em jogo (como o da campanha, no livro).
    # Quem mestra uma sessão pode ser jogador em outra: o personagem do próprio
    # mestre não joga a sessão dele, então não conta (com 1 personagem dele: N − 1).
    em_jogo = [p for p in m.mesa.personagens
               if p.dono_id != a.usuario_id and not (p.sessao or {}).get("morto")]   # quem morreu não joga
    medo = min(MEDO_MAXIMO, len(em_jogo))
    s = SessaoTabela(id=str(uuid.uuid4()), mesa_id=mesa_id, responsavel_id=a.usuario_id,
                     titulo=dados.titulo.strip(), data=dados.data, medo=medo,
                     resumo="", notas="", status="planejada", compartilhada_com=[], npcs=[], inimigos=[])
    a.banco.add(s)
    a.banco.commit()
    return _saida(a, s)


@rotas.get("/{sessao_id}", response_model=Sessao)
def ver(mesa_id: str, sessao_id: str, a: Acesso = Depends(acesso)):
    return _saida(a, sessao_do_mestre(a, mesa_id, sessao_id))


@rotas.put("/{sessao_id}", response_model=Sessao)
def editar(mesa_id: str, sessao_id: str, dados: DadosDaSessao, versao: str | None = None,
           a: Acesso = Depends(acesso)):
    s = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    conferir(versao, *_versao_conteudo(s))
    for npc_id in dados.npcs:   # vincular: só NPCs desta mesa que você vê
        n = a.banco.get(NpcTabela, npc_id)
        if n is None or n.mesa_id != mesa_id or not npcs.mestre_ve(a.banco, n, a.usuario_id):
            raise NaoEncontrado("NPC não encontrado.")
    s.titulo, s.data, s.resumo, s.notas = dados.titulo.strip(), dados.data, dados.resumo, dados.notas
    s.npcs, s.inimigos = list(dict.fromkeys(dados.npcs)), list(dict.fromkeys(dados.inimigos))
    a.banco.commit()
    return _saida(a, s)


@rotas.put("/{sessao_id}/status", response_model=Sessao)
def mudar_status(mesa_id: str, sessao_id: str, pedido: StatusDaSessao, a: Acesso = Depends(acesso)):
    s = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    if pedido.status == "em_andamento" and s.status != "em_andamento":
        # reabrir: quem jogou esta sessão não pode estar jogando outra agora
        for p in a.banco.query(ParticipacaoTabela).filter_by(sessao_id=s.id):
            outra = repositorio.participacao_ativa(a.banco, p.personagem_id)
            if outra is not None and outra.sessao_id != s.id:
                raise RegraViolada(f"{p.personagem.nome or 'Um personagem'} desta sessão está jogando outra "
                                   "em andamento: encerre aquela antes de reabrir esta.")
    s.status = pedido.status
    a.banco.commit()
    return _saida(a, s)


@rotas.put("/{sessao_id}/compartilhar", response_model=Sessao)
def compartilhar(mesa_id: str, sessao_id: str, pedido: Compartilhar, a: Acesso = Depends(acesso)):
    """Com quais mestres da mesa a sessão é compartilhada (eles só veem)."""
    s = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    mestres = {x.usuario_id for x in a.banco.query(MembroTabela).filter_by(mesa_id=mesa_id)
               if x.papel == MESTRE or eh_criador(x)}
    invalidos = [u for u in pedido.mestres if u not in mestres or u == s.responsavel_id]
    if invalidos:
        raise RegraViolada("Só dá para compartilhar com outros mestres desta mesa.")
    s.compartilhada_com = list(dict.fromkeys(pedido.mestres))
    a.banco.commit()
    return _saida(a, s)


@rotas.delete("/{sessao_id}", status_code=204)
def apagar(mesa_id: str, sessao_id: str, a: Acesso = Depends(acesso)):
    """Apaga a sessão e os encontros dela."""
    a.banco.delete(sessao_do_mestre(a, mesa_id, sessao_id, editar=True))
    a.banco.commit()
    return Response(status_code=204)


@rotas.post("/{sessao_id}/medo", response_model=Sessao)
def mudar_medo(mesa_id: str, sessao_id: str, pedido: AjusteMedo, a: Acesso = Depends(acesso)):
    s = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    s.medo = ajustar_medo(s.medo, pedido.delta)
    a.banco.commit()
    return _saida(a, s)


@rotas.put("/{sessao_id}/medo", response_model=Sessao)
def definir(mesa_id: str, sessao_id: str, pedido: ValorMedo, a: Acesso = Depends(acesso)):
    s = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    s.medo = definir_medo(pedido.valor)
    a.banco.commit()
    return _saida(a, s)

