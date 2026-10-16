"""A sessão de jogo do lado dos jogadores: entrar com um personagem, a vista
da sessão (Medo, quem está jogando, o que o mestre revelou, lojas) e a ficha
de cada participante nela.

Mesa = o grupo; sessão = um dia de jogo, com um mestre (o responsável). Quando
ela está em andamento, os membros entram com um personagem seu da mesa; as
marcas de jogo daquele personagem passam a ser desta sessão (ver
`api/repositorio.py`). Encerrada, a sessão fica para consulta: como cada um
terminou e o Medo final.

Visibilidade: qualquer membro vê sessões em andamento e encerradas; as
planejadas só o mestre responsável (e quem ele compartilhou), como antes.
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from motor import RegraViolada

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..esquemas import FichaSaida, ficha_saida
from ..mesas import Permissao, SemPermissao, membro, pode
from ..repositorio import NaoEncontrado
from ..sessoes import pode_ver
from ..tabelas import ParticipacaoTabela, PersonagemTabela, SessaoTabela
from .mesas import FichaResumida, resumo_de
from .revelado import EncontroVisivel, LojaVisivel, NpcConhecido, combate_visivel, lojas_visiveis, npcs_conhecidos

rotas = APIRouter(prefix="/mesas/{mesa_id}/sessoes/{sessao_id}", tags=["Jogo"])

JOGAVEIS = ("em_andamento", "encerrada")


class ParticipanteDaSessao(BaseModel):
    personagem_id: str
    dono_id: str
    resumo: FichaResumida


class VistaDaSessao(BaseModel):
    id: str
    titulo: str
    status: str
    mestre: str
    responsavel_id: str
    sou_responsavel: bool
    posso_gerir: bool                 # vê o lado do mestre (responsável ou compartilhada)
    medo: int
    participantes: list[ParticipanteDaSessao]
    meus: list[str]                   # meus personagens jogando esta sessão
    combate: list[EncontroVisivel]
    npcs: list[NpcConhecido]
    lojas: list[LojaVisivel]


class Entrar(BaseModel):
    personagem_id: str


def _sessao(a: Acesso, mesa_id: str, sessao_id: str) -> SessaoTabela:
    """Sessão que o membro pode ver: em andamento/encerrada, ou dele (planejada)."""
    membro(a.banco, mesa_id, a.usuario_id)
    s = a.banco.get(SessaoTabela, sessao_id)
    if s is None or s.mesa_id != mesa_id or (s.status not in JOGAVEIS and not pode_ver(s, a.usuario_id)):
        raise NaoEncontrado("Sessão não encontrada.")
    return s


def _participacoes(a: Acesso, sessao_id: str) -> list[ParticipacaoTabela]:
    return (a.banco.query(ParticipacaoTabela).filter_by(sessao_id=sessao_id)
            .order_by(ParticipacaoTabela.entrou_em).all())


def _participacao(a: Acesso, sessao_id: str, personagem_id: str) -> ParticipacaoTabela:
    p = a.banco.query(ParticipacaoTabela).filter_by(sessao_id=sessao_id, personagem_id=personagem_id).first()
    if p is None:
        raise NaoEncontrado("Este personagem não está nesta sessão.")
    return p


def _vista(a: Acesso, s: SessaoTabela) -> VistaDaSessao:
    participantes = []
    for p in _participacoes(a, s.id):
        linha = p.personagem
        f = repositorio.montar(linha, participacao=p).ficha()
        participantes.append(ParticipanteDaSessao(personagem_id=linha.id, dono_id=linha.dono_id, resumo=resumo_de(linha, f)))
    em_jogo = s.status == "em_andamento"
    return VistaDaSessao(
        id=s.id, titulo=s.titulo, status=s.status, mestre=s.responsavel.nome, responsavel_id=s.responsavel_id,
        sou_responsavel=s.responsavel_id == a.usuario_id, posso_gerir=pode_ver(s, a.usuario_id), medo=s.medo,
        participantes=participantes, meus=[p.personagem_id for p in participantes if p.dono_id == a.usuario_id],
        # o que o mestre mostra só vale enquanto a sessão está em andamento
        combate=combate_visivel(a, s.mesa_id, s.id) if em_jogo else [],
        npcs=npcs_conhecidos(a, s.mesa_id, s.id),   # os vinculados a esta sessão (e exibidos para todos)
        lojas=lojas_visiveis(a, s.mesa_id, s.id) if em_jogo else [])


@rotas.get("/jogo", response_model=VistaDaSessao)
def vista(mesa_id: str, sessao_id: str, a: Acesso = Depends(acesso)):
    return _vista(a, _sessao(a, mesa_id, sessao_id))


@rotas.post("/participantes", response_model=VistaDaSessao)
def entrar(mesa_id: str, sessao_id: str, pedido: Entrar, a: Acesso = Depends(acesso)):
    """Entra na sessão em andamento com um personagem seu desta mesa. Ele
    começa limpo (PV, Fadiga, armadura, condições) e com a Esperança inicial."""
    s = _sessao(a, mesa_id, sessao_id)
    if s.status != "em_andamento":
        raise RegraViolada("Só dá para entrar numa sessão em andamento.")
    linha = a.banco.get(PersonagemTabela, pedido.personagem_id)
    if linha is None or linha.dono_id != a.usuario_id or linha.mesa_id != mesa_id:
        raise NaoEncontrado("Escolha um personagem seu desta mesa.")
    if linha.dono_id == s.responsavel_id:
        raise RegraViolada("Quem mestra a sessão não joga nela com um personagem.")
    if (linha.sessao or {}).get("morto"):
        raise RegraViolada(f"{linha.nome or 'Este personagem'} atravessou o véu e não joga mais.")
    ativa = repositorio.participacao_ativa(a.banco, linha.id)
    if ativa is not None:
        if ativa.sessao_id == s.id:
            return _vista(a, s)   # já está: entrar de novo não muda nada
        raise RegraViolada(f"{linha.nome or 'Este personagem'} já está jogando outra sessão em andamento.")
    a.banco.add(ParticipacaoTabela(id=str(uuid.uuid4()), mesa_id=mesa_id, sessao_id=s.id,
                                   personagem_id=linha.id, estado={}))
    a.banco.commit()
    return _vista(a, s)


@rotas.delete("/participantes/{personagem_id}", response_model=VistaDaSessao)
def sair(mesa_id: str, sessao_id: str, personagem_id: str, a: Acesso = Depends(acesso)):
    """Tira o personagem da sessão em andamento (entrou com o personagem
    errado, ou foi embora mais cedo). O dono ou o mestre responsável. As marcas
    desta sessão são descartadas."""
    s = _sessao(a, mesa_id, sessao_id)
    if s.status != "em_andamento":
        raise RegraViolada("A sessão já foi encerrada: o que aconteceu nela fica registrado.")
    p = _participacao(a, s.id, personagem_id)
    if a.usuario_id not in (p.personagem.dono_id, s.responsavel_id):
        raise SemPermissao("Só o dono do personagem (ou o mestre da sessão) pode tirá-lo.")
    a.banco.delete(p)
    a.banco.commit()
    return _vista(a, s)


@rotas.get("/participantes/{personagem_id}", response_model=FichaSaida)
def ficha_na_sessao(mesa_id: str, sessao_id: str, personagem_id: str, a: Acesso = Depends(acesso)):
    """A ficha completa do personagem nesta sessão (em andamento: agora;
    encerrada: como terminou). Para o dono e para mestres com 'ver_fichas'."""
    s = _sessao(a, mesa_id, sessao_id)
    p = _participacao(a, s.id, personagem_id)
    if p.personagem.dono_id != a.usuario_id and not pode(membro(a.banco, mesa_id, a.usuario_id), Permissao.VER_FICHAS):
        raise SemPermissao("Você vê a ficha resumida dos outros personagens; a completa é do dono e do mestre.")
    return ficha_saida(repositorio.montar(p.personagem, participacao=p).ficha())
