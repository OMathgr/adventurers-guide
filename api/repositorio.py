"""Converte entre o motor (Personagem) e as tabelas do banco.

Carregar = refazer o personagem pelo motor: criação, cada subida de nível
em ordem (revalidando tudo) e o estado atual por cima. Assim o banco nunca
guarda uma ficha que o motor não aceitaria.
"""

import uuid
from functools import lru_cache

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from motor import Biblioteca, Criacao, Personagem, SubidaDeNivel

from .tabelas import PersonagemTabela, SubidaTabela

_CRIACAO = TypeAdapter(Criacao)
_SUBIDA = TypeAdapter(SubidaDeNivel)


class NaoEncontrado(Exception):
    pass


@lru_cache
def biblioteca() -> Biblioteca:
    """O SRD é lido uma vez só e compartilhado (é só leitura)."""
    return Biblioteca()


def para_json(criacao_ou_subida) -> dict:
    adaptador = _CRIACAO if isinstance(criacao_ou_subida, Criacao) else _SUBIDA
    return adaptador.dump_python(criacao_ou_subida, mode="json")


def criar(banco: Session, criacao: Criacao) -> tuple[str, Personagem]:
    personagem = Personagem(biblioteca(), criacao)   # valida a criação
    linha = PersonagemTabela(id=str(uuid.uuid4()), nome=criacao.nome,
                             criacao=para_json(criacao), **personagem.estado())
    banco.add(linha)
    banco.commit()
    return linha.id, personagem


def carregar(banco: Session, personagem_id: str) -> Personagem:
    linha = _linha(banco, personagem_id)
    personagem = Personagem(biblioteca(), _CRIACAO.validate_python(linha.criacao))
    for subida in linha.subidas:
        personagem.subir_de_nivel(_SUBIDA.validate_python(subida.dados))
    personagem.restaurar_estado({"equipamento": linha.equipamento, "cofre": linha.cofre,
                                 "sessao": linha.sessao})
    return personagem


def salvar(banco: Session, personagem_id: str, personagem: Personagem):
    """Grava o estado atual e sincroniza as subidas de nível com o histórico."""
    linha = _linha(banco, personagem_id)
    estado = personagem.estado()
    linha.equipamento, linha.cofre, linha.sessao = (
        estado["equipamento"], estado["cofre"], estado["sessao"])
    salvas = {s.nivel: s for s in linha.subidas}
    no_historico = {s.nivel for s in personagem.historico}
    for nivel, subida in salvas.items():
        if nivel not in no_historico:          # nível desfeito
            linha.subidas.remove(subida)
    for subida in personagem.historico:
        dados = para_json(subida)
        if subida.nivel not in salvas:          # nível novo
            linha.subidas.append(SubidaTabela(nivel=subida.nivel, dados=dados))
        elif salvas[subida.nivel].dados != dados:   # desfeito e refeito com outras escolhas
            salvas[subida.nivel].dados = dados
    banco.commit()


def listar(banco: Session) -> list[PersonagemTabela]:
    return list(banco.scalars(select(PersonagemTabela).order_by(PersonagemTabela.criado_em)))


def apagar(banco: Session, personagem_id: str):
    banco.delete(_linha(banco, personagem_id))
    banco.commit()


def _linha(banco: Session, personagem_id: str) -> PersonagemTabela:
    linha = banco.get(PersonagemTabela, personagem_id)
    if linha is None:
        raise NaoEncontrado(f"Personagem {personagem_id} não encontrado.")
    return linha
