"""Converte entre o motor (Personagem) e as tabelas do banco.

Carregar = refazer o personagem pelo motor: criação, cada subida de nível
em ordem (revalidando tudo) e o estado atual por cima. Assim o banco nunca
guarda uma ficha que o motor não aceitaria.

Toda função recebe o `dono_id`: personagem de outro usuário se comporta como
inexistente (NaoEncontrado), para não revelar que ele existe.

Marcas de jogo (PV, Fadiga, Esperança, armadura, condições...) são de cada
sessão de jogo: ficam na participação (`ParticipacaoTabela`) da sessão em
andamento em que o personagem entrou. Fora dela, o personagem aparece limpo
(Esperança inicial). Morte e cicatrizes seguem no personagem (`linha.sessao`).
"""

import uuid
from functools import lru_cache

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from motor import Biblioteca, Criacao, Personagem, RegraViolada, SubidaDeNivel
from motor.sessao import Sessao

from .tabelas import ParticipacaoTabela, PersonagemTabela, SessaoTabela, SubidaTabela

_CRIACAO = TypeAdapter(Criacao)
_SUBIDA = TypeAdapter(SubidaDeNivel)


class NaoEncontrado(Exception):
    pass


ATIVA = object()   # montar(): usar a participação da sessão em andamento, se houver


def participacao_ativa(banco: Session, personagem_id: str) -> ParticipacaoTabela | None:
    """A participação do personagem numa sessão em andamento (no máximo uma)."""
    return (banco.query(ParticipacaoTabela)
            .join(SessaoTabela, ParticipacaoTabela.sessao_id == SessaoTabela.id)
            .filter(ParticipacaoTabela.personagem_id == personagem_id, SessaoTabela.status == "em_andamento")
            .first())


def exigir_em_jogo(banco: Session, personagem_id: str, dono_id: str | None = None):
    """Marcas de jogo só se mexem dentro de uma sessão em andamento. Com
    `dono_id`, confere antes o dono (personagem de outro continua "inexistente")."""
    if dono_id is not None:
        _linha(banco, dono_id, personagem_id)
    if participacao_ativa(banco, personagem_id) is None:
        raise RegraViolada("Para marcar PV, Fadiga, Esperança ou condições, o personagem precisa "
                           "entrar numa sessão em andamento (aba Sessões da mesa).")


def _colunas(personagem: Personagem) -> dict:
    """Estado atual nas colunas do personagem (as marcas da sessão não vão)."""
    estado = personagem.estado()
    return {"equipamento": estado["equipamento"], "cofre": estado["cofre"],
            "sessao": personagem.sessao.estado_permanente(), "inventario": estado["inventario"]}


@lru_cache
def biblioteca() -> Biblioteca:
    """O SRD é lido uma vez só e compartilhado (é só leitura). Nomes e
    textos em português; as regras continuam lendo o inglês do SRD."""
    return Biblioteca(idioma="pt-BR")


def para_json(criacao_ou_subida) -> dict:
    adaptador = _CRIACAO if isinstance(criacao_ou_subida, Criacao) else _SUBIDA
    return adaptador.dump_python(criacao_ou_subida, mode="json")


def criar(banco: Session, dono_id: str, criacao: Criacao) -> tuple[str, Personagem]:
    personagem = Personagem(biblioteca(), criacao)   # valida a criação
    linha = PersonagemTabela(id=str(uuid.uuid4()), dono_id=dono_id, nome=criacao.nome,
                             criacao=para_json(criacao), **_colunas(personagem))
    banco.add(linha)
    banco.commit()
    return linha.id, personagem


def criar_copia(banco: Session, original: PersonagemTabela, mesa_id: str, nivel_maximo: int) -> tuple[str, Personagem]:
    """Cópia do personagem presa à mesa `mesa_id`: níveis acima do limite viram plano."""
    copia = montar(original).copia(nivel_maximo)
    linha = PersonagemTabela(id=str(uuid.uuid4()), dono_id=original.dono_id, mesa_id=mesa_id,
                             nome=original.nome, criacao=dict(original.criacao), foto=original.foto,
                             **_colunas(copia))
    banco.add(linha)
    gravar(banco, linha, copia)   # subidas e plano
    return linha.id, copia


def carregar(banco: Session, dono_id: str, personagem_id: str) -> Personagem:
    return montar(_linha(banco, dono_id, personagem_id))


def montar(linha: PersonagemTabela, participacao=ATIVA) -> Personagem:
    """Refaz o personagem de uma linha já autorizada (pelo dono ou pela mesa).

    As marcas vêm da participação: por padrão a da sessão em andamento; passe
    uma (ex.: de sessão encerrada, para consulta) ou None (personagem limpo)."""
    if participacao is ATIVA:
        banco = object_session(linha)
        participacao = participacao_ativa(banco, linha.id) if banco else None
        if banco is not None:
            # guarda a participação lida para o gravar() usar a MESMA (com a versão
            # que foi lida): o mapa de identidade do SQLAlchemy só tem referência
            # fraca, e reler no gravar perderia uma gravação simultânea sem conflito
            banco.info.setdefault("participacoes", {})[linha.id] = participacao
    personagem = Personagem(biblioteca(), _CRIACAO.validate_python(linha.criacao))
    personagem.refazer_historico([_SUBIDA.validate_python(subida.dados) for subida in linha.subidas])
    permanente = {k: v for k, v in (linha.sessao or {}).items() if k in Sessao.CAMPOS_PERMANENTES}
    da_sessao = participacao.estado if participacao is not None else {}
    personagem.restaurar_estado({"equipamento": linha.equipamento, "cofre": linha.cofre,
                                 "sessao": {**da_sessao, **permanente}, "inventario": linha.inventario})
    personagem.plano = [_SUBIDA.validate_python(s) for s in linha.plano or []]
    # o limite vem depois do histórico: baixar o nível da mesa não impede carregar
    personagem.nivel_limite = linha.mesa.nivel_maximo if linha.mesa else None
    personagem.moedas_da_mesa = linha.mesa.usar_moedas if linha.mesa else None
    return personagem


def salvar(banco: Session, dono_id: str, personagem_id: str, personagem: Personagem):
    gravar(banco, _linha(banco, dono_id, personagem_id), personagem)


def gravar(banco: Session, linha: PersonagemTabela, personagem: Personagem, commit: bool = True):
    """Grava o estado atual e sincroniza as subidas de nível com o histórico.
    `commit=False`: para gravar vários personagens juntos (ex.: o repouso do grupo)."""
    colunas = _colunas(personagem)
    linha.equipamento, linha.cofre, linha.sessao, linha.inventario = (
        colunas["equipamento"], colunas["cofre"], colunas["sessao"], colunas["inventario"])
    lidas = banco.info.get("participacoes", {})
    participacao = lidas[linha.id] if linha.id in lidas else participacao_ativa(banco, linha.id)
    if participacao is not None:
        participacao.estado = personagem.sessao.estado_da_sessao()
    linha.plano = [para_json(s) for s in personagem.plano]
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
    if commit:
        banco.commit()


def listar(banco: Session, dono_id: str) -> list[PersonagemTabela]:
    consulta = (select(PersonagemTabela).where(PersonagemTabela.dono_id == dono_id)
                .order_by(PersonagemTabela.criado_em))
    return list(banco.scalars(consulta))


def apagar(banco: Session, dono_id: str, personagem_id: str):
    banco.delete(_linha(banco, dono_id, personagem_id))
    banco.commit()


def linha_do_dono(banco: Session, dono_id: str, personagem_id: str) -> PersonagemTabela:
    return _linha(banco, dono_id, personagem_id)


def linha_na_mesa(banco: Session, mesa_id: str, personagem_id: str) -> PersonagemTabela:
    """Para o mestre: o personagem precisa estar vinculado a esta mesa."""
    linha = banco.get(PersonagemTabela, personagem_id)
    if linha is None or linha.mesa_id != mesa_id:
        raise NaoEncontrado(f"Personagem {personagem_id} não está nesta mesa.")
    return linha


def _linha(banco: Session, dono_id: str, personagem_id: str) -> PersonagemTabela:
    linha = banco.get(PersonagemTabela, personagem_id)
    if linha is None or linha.dono_id != dono_id:
        raise NaoEncontrado(f"Personagem {personagem_id} não encontrado.")
    return linha
