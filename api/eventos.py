"""Atualização ao vivo: avisos de "isto mudou" para as telas abertas.

Os avisos NÃO levam dados, só o que mudou (`{"tipo": "mesa", "id": ...}` ou
`{"tipo": "personagem", "id": ...}`); cada tela busca de novo pela API, com as
próprias permissões. Assim nada chega a quem não poderia ler.

Quem gera os avisos é um gancho no banco (`before_flush`/`after_commit` da
sessão do SQLAlchemy): ele vê o que cada commit tocou (mesa, membro, inimigo,
NPC, sessão, encontro, loja, personagem, nível) e avisa os membros daquela mesa e o
dono do personagem. Rotas novas ficam cobertas sem precisar lembrar de avisar.

Limite: a central vive na memória de UM processo. Com vários servidores,
trocar por um Redis (pub/sub) mantendo a mesma interface.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from itertools import chain

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from .tabelas import (EncontroTabela, InimigoTabela, LojaTabela, MembroTabela, ParticipacaoTabela, RepousoTabela,
                      MesaTabela, NpcTabela, PersonagemTabela, RolagemTabela, SessaoTabela, SubidaTabela)

Evento = dict
Ouvinte = Callable[[Evento], None]


class Central:
    """Quem está conectado (por usuário) e a entrega dos avisos."""

    def __init__(self):
        self._ouvintes: dict[str, list[Ouvinte]] = defaultdict(list)
        self._trava = threading.Lock()

    def assinar(self, usuario_id: str, ouvinte: Ouvinte) -> Callable[[], None]:
        with self._trava:
            self._ouvintes[usuario_id].append(ouvinte)

        def cancelar():
            with self._trava:
                lista = self._ouvintes.get(usuario_id, [])
                if ouvinte in lista:
                    lista.remove(ouvinte)
                if not lista:
                    self._ouvintes.pop(usuario_id, None)
        return cancelar

    def online(self, usuario_id: str) -> bool:
        return bool(self._ouvintes.get(usuario_id))

    def alguem_ouvindo(self) -> bool:
        return bool(self._ouvintes)

    def enviar(self, usuarios, evento: Evento):
        with self._trava:
            alvos = [o for u in set(usuarios) for o in self._ouvintes.get(u, [])]
        for ouvinte in alvos:
            try:
                ouvinte(evento)
            except Exception:   # uma tela fechada não pode derrubar o commit dos outros
                pass


central = Central()


# --- Gancho no banco ----------------------------------------------------------------------

_POR_MESA = (InimigoTabela, NpcTabela, SessaoTabela, EncontroTabela, LojaTabela, RepousoTabela, RolagemTabela)


def _pendentes(sessao: Session) -> dict:
    return sessao.info.setdefault("avisos", {"mesas": set(), "personagens": set(), "usuarios": defaultdict(set)})


@event.listens_for(Session, "before_flush")
def _anotar(sessao: Session, _contexto, _instancias):
    """Anota o que este flush vai mudar (antes, porque um apagar em cascata
    some com os membros que precisam ser avisados)."""
    if not central.alguem_ouvindo():
        return
    p = _pendentes(sessao)
    with sessao.no_autoflush:
        for obj in chain(sessao.new, sessao.dirty, sessao.deleted):
            if isinstance(obj, MesaTabela):
                p["mesas"].add(obj.id)
                if obj in sessao.deleted:   # a mesa vai sumir: avisa quem era membro
                    p["usuarios"][obj.id].update(m.usuario_id for m in obj.membros)
            elif isinstance(obj, MembroTabela):
                p["mesas"].add(obj.mesa_id)
                p["usuarios"][obj.mesa_id].add(obj.usuario_id)   # quem entrou ou saiu também
            elif isinstance(obj, _POR_MESA):
                p["mesas"].add(obj.mesa_id)
            elif isinstance(obj, PersonagemTabela):
                p["personagens"].add(obj.id)
                anteriores = inspect(obj).attrs.mesa_id.history.deleted or ()
                p["mesas"].update(m for m in (obj.mesa_id, *anteriores) if m)
            elif isinstance(obj, SubidaTabela) and obj.personagem_id:
                p["personagens"].add(obj.personagem_id)
            elif isinstance(obj, ParticipacaoTabela):   # marcas de jogo: a ficha e a vista da sessão
                p["mesas"].add(obj.mesa_id)
                p["personagens"].add(obj.personagem_id)


@event.listens_for(Session, "after_commit")
def _avisar(sessao: Session):
    p = sessao.info.pop("avisos", None)
    if not p or not (p["mesas"] or p["personagens"]):
        return
    # numa sessão nova: depois do commit a original não deve mais ir ao banco
    with Session(bind=sessao.get_bind()) as s:
        donos = dict(s.execute(select(PersonagemTabela.id, PersonagemTabela.dono_id)
                               .where(PersonagemTabela.id.in_(p["personagens"]))).all()) if p["personagens"] else {}
        mesas_dos_personagens = dict(s.execute(select(PersonagemTabela.id, PersonagemTabela.mesa_id)
                                              .where(PersonagemTabela.id.in_(p["personagens"]))).all()) \
            if p["personagens"] else {}
        todas = p["mesas"] | {m for m in mesas_dos_personagens.values() if m}
        membros: dict[str, set[str]] = defaultdict(set)
        if todas:
            for mesa_id, usuario_id in s.execute(select(MembroTabela.mesa_id, MembroTabela.usuario_id)
                                                 .where(MembroTabela.mesa_id.in_(todas))):
                membros[mesa_id].add(usuario_id)
    for mesa_id in p["mesas"]:
        central.enviar(membros[mesa_id] | p["usuarios"].get(mesa_id, set()), {"tipo": "mesa", "id": mesa_id})
    for pid in p["personagens"]:
        mesa_id = mesas_dos_personagens.get(pid)
        alvo = ({donos[pid]} if pid in donos else set()) | (membros[mesa_id] if mesa_id else set())
        central.enviar(alvo, {"tipo": "personagem", "id": pid, "mesa_id": mesa_id})


@event.listens_for(Session, "after_rollback")
def _descartar(sessao: Session):
    sessao.info.pop("avisos", None)


def avisar_presenca(sessao: Session, usuario_id: str):
    """Alguém conectou ou desconectou: as mesas dele atualizam quem está online."""
    mesas = [m for (m,) in sessao.execute(select(MembroTabela.mesa_id).where(MembroTabela.usuario_id == usuario_id))]
    if not mesas:
        return
    for mesa_id, membro_id in sessao.execute(select(MembroTabela.mesa_id, MembroTabela.usuario_id)
                                             .where(MembroTabela.mesa_id.in_(mesas))):
        central.enviar({membro_id}, {"tipo": "mesa", "id": mesa_id})
