"""Regras de acesso das mesas.

Papéis: o **criador** (dono da mesa, também mestre, administra tudo), os
**mestres** e os **jogadores**. O criador escolhe quem é mestre e quais
permissões TODOS os mestres têm (as mesmas para todos). Mestre só lê fichas
e age em jogo (dano, condições); não edita o resto do personagem.

Quem não é membro não "vê" a mesa: recebe 404, como se ela não existisse.
Membro sem permissão recebe 403 (ele já sabe que a mesa existe).
"""

import secrets
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from .repositorio import NaoEncontrado
from .tabelas import MembroTabela, MesaTabela

JOGADOR, MESTRE = "jogador", "mestre"


class Permissao(str, Enum):
    VER_FICHAS = "ver_fichas"
    APLICAR_DANO = "aplicar_dano"
    APLICAR_CONDICOES = "aplicar_condicoes"


PERMISSOES_PADRAO = {p.value: True for p in Permissao}

# sem 0/O e 1/I/L, para ler e digitar sem confusão
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
TAMANHO_CODIGO = 8


class SemPermissao(Exception):
    pass


def gerar_codigo(banco: Session) -> str:
    while True:
        codigo = "".join(secrets.choice(_ALFABETO) for _ in range(TAMANHO_CODIGO))
        if not banco.scalar(select(MesaTabela.id).where(MesaTabela.codigo_convite == codigo)):
            return codigo


def membro(banco: Session, mesa_id: str, usuario_id: str) -> MembroTabela:
    m = banco.get(MembroTabela, (mesa_id, usuario_id))
    if m is None:
        raise NaoEncontrado(f"Mesa {mesa_id} não encontrada.")
    return m


def eh_criador(m: MembroTabela) -> bool:
    return m.mesa.criador_id == m.usuario_id


def exigir_criador(m: MembroTabela):
    if not eh_criador(m):
        raise SemPermissao("Só quem criou a mesa pode fazer isso.")


def pode(m: MembroTabela, permissao: Permissao) -> bool:
    if eh_criador(m):
        return True
    return m.papel == MESTRE and bool(m.mesa.permissoes_mestres.get(permissao.value))


def exigir(m: MembroTabela, permissao: Permissao):
    if not pode(m, permissao):
        raise SemPermissao(f"Você não tem a permissão '{permissao.value}' nesta mesa.")
