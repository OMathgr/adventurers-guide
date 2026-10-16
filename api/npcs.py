"""Quem vê cada NPC da mesa.

Todo NPC tem um dono (quem criou) e uma visibilidade:
- "privado": só o dono;
- "mestres": todos os mestres da mesa veem (inclusive notas) e podem usar
  (vincular à sessão deles, pôr num encontro); editar continua com o dono;
- "todos": além dos mestres, os jogadores veem nome, foto e descrição, mas só
  na página da sessão em que o mestre vinculou o NPC (`SessaoTabela.npcs`).

Se o dono saiu da mesa, quem criou a mesa passa a ser o dono (ninguém perde o NPC).
"""

from sqlalchemy.orm import Session

from .mesas import MESTRE, eh_criador
from .tabelas import MembroTabela, MesaTabela, NpcTabela

PRIVADO, MESTRES, TODOS = "privado", "mestres", "todos"
VISIBILIDADES = (PRIVADO, MESTRES, TODOS)


def dono(banco: Session, npc: NpcTabela) -> str:
    """Id do dono efetivo (quem criou; se saiu da mesa, quem criou a mesa)."""
    if npc.dono_id and banco.get(MembroTabela, (npc.mesa_id, npc.dono_id)) is not None:
        return npc.dono_id
    return banco.get(MesaTabela, npc.mesa_id).criador_id


def e_mestre(m: MembroTabela) -> bool:
    return eh_criador(m) or m.papel == MESTRE


def mestre_ve(banco: Session, npc: NpcTabela, usuario_id: str) -> bool:
    """O NPC aparece na biblioteca deste mestre (e ele pode usá-lo)."""
    return npc.visibilidade in (MESTRES, TODOS) or dono(banco, npc) == usuario_id


def pode_editar(banco: Session, npc: NpcTabela, usuario_id: str) -> bool:
    return dono(banco, npc) == usuario_id


def visivel_para(banco: Session, npc: NpcTabela, m: MembroTabela) -> bool:
    """Para qualquer membro: o mestre que pode ver, ou o jogador se é para todos."""
    if e_mestre(m):
        return mestre_ve(banco, npc, m.usuario_id)
    return npc.visibilidade == TODOS
