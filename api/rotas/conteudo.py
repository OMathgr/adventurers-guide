"""Conteúdo do mestre numa mesa: inimigos e NPCs.

Tudo aqui é privado dos mestres (jogador recebe 404, como se não existisse).
Ver exige ser mestre; criar, editar e apagar exige a permissão `preparar`
(o criador da mesa pode sempre).
"""

import copy
import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, TypeAdapter

from motor import Adversario
from motor.adversarios import validar

from ..autenticacao import Acesso, acesso
from ..mesas import Permissao, exigir, exigir_mestre, membro
from ..repositorio import NaoEncontrado, biblioteca
from ..tabelas import InimigoTabela, NpcTabela
from .imagens import imagem_valida

rotas = APIRouter(prefix="/mesas/{mesa_id}", tags=["Conteúdo do mestre"])
_ADVERSARIO = TypeAdapter(Adversario)


def _mestre(a: Acesso, mesa_id: str, editar: bool = False):
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir_mestre(m)
    if editar:
        exigir(m, Permissao.PREPARAR)
    return m


def _salvavel(adv: Adversario, id_: str) -> dict:
    validar(adv)
    adv = copy.deepcopy(adv)
    adv.id = id_
    return _ADVERSARIO.dump_python(adv, mode="json")


# --- Inimigos -------------------------------------------------------------------------

class InimigoResumo(BaseModel):
    id: str
    nome: str
    patamar: int
    tipo: str
    base_id: str | None


def _resumo(linha: InimigoTabela) -> InimigoResumo:
    d = linha.dados
    return InimigoResumo(id=linha.id, nome=d["nome"], patamar=d["patamar"], tipo=d["tipo"],
                         base_id=d.get("base_id"))


def _inimigo(a: Acesso, mesa_id: str, inimigo_id: str) -> InimigoTabela:
    linha = a.banco.get(InimigoTabela, inimigo_id)
    if linha is None or linha.mesa_id != mesa_id:
        raise NaoEncontrado("Inimigo não encontrado.")
    return linha


@rotas.get("/inimigos", response_model=list[InimigoResumo])
def listar_inimigos(mesa_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id)
    linhas = a.banco.query(InimigoTabela).filter_by(mesa_id=mesa_id).order_by(InimigoTabela.criado_em)
    return [_resumo(x) for x in linhas]


@rotas.post("/inimigos", status_code=201, response_model=Adversario)
def criar_inimigo(mesa_id: str, inimigo: Adversario, a: Acesso = Depends(acesso)):
    """Inimigo criado do zero (mesmo formato dos adversários do SRD)."""
    _mestre(a, mesa_id, editar=True)
    imagem_valida(a, inimigo.foto)
    novo_id = str(uuid.uuid4())
    linha = InimigoTabela(id=novo_id, mesa_id=mesa_id, dados=_salvavel(inimigo, novo_id))
    a.banco.add(linha)
    a.banco.commit()
    return linha.dados


@rotas.post("/inimigos/do-srd/{adversario_id}", status_code=201, response_model=Adversario)
def copiar_do_srd(mesa_id: str, adversario_id: str, a: Acesso = Depends(acesso)):
    """Copia um adversário do SRD para a mesa, onde pode ser ajustado à vontade."""
    _mestre(a, mesa_id, editar=True)
    base = biblioteca().adversarios.get(adversario_id)
    if base is None:
        raise NaoEncontrado(f"Adversário {adversario_id} não encontrado.")
    copia = copy.deepcopy(base)
    copia.base_id = base.id
    novo_id = str(uuid.uuid4())
    linha = InimigoTabela(id=novo_id, mesa_id=mesa_id, dados=_salvavel(copia, novo_id))
    a.banco.add(linha)
    a.banco.commit()
    return linha.dados


@rotas.get("/inimigos/{inimigo_id}", response_model=Adversario)
def ver_inimigo(mesa_id: str, inimigo_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id)
    return _inimigo(a, mesa_id, inimigo_id).dados


@rotas.put("/inimigos/{inimigo_id}", response_model=Adversario)
def editar_inimigo(mesa_id: str, inimigo_id: str, inimigo: Adversario, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id, editar=True)
    linha = _inimigo(a, mesa_id, inimigo_id)
    imagem_valida(a, inimigo.foto)
    inimigo.base_id = linha.dados.get("base_id")   # a origem não muda ao editar
    linha.dados = _salvavel(inimigo, inimigo_id)
    a.banco.commit()
    return linha.dados


@rotas.delete("/inimigos/{inimigo_id}", status_code=204)
def apagar_inimigo(mesa_id: str, inimigo_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id, editar=True)
    a.banco.delete(_inimigo(a, mesa_id, inimigo_id))
    a.banco.commit()
    return Response(status_code=204)


# --- NPCs ---------------------------------------------------------------------------------

class NpcEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    descricao: str = Field("", max_length=4000)
    motivacoes: str = Field("", max_length=2000)
    notas: str = Field("", max_length=8000, description="Anotações privadas do mestre")
    ficha_combate: Adversario | None = None
    foto: str | None = Field(None, description="Id devolvido por POST /imagens")


class Npc(NpcEntrada):
    id: str
    revelado: bool = False             # conhecido pelos jogadores (nome, foto e descrição)


class NpcRevelado(BaseModel):
    revelado: bool


def _npc(a: Acesso, mesa_id: str, npc_id: str) -> NpcTabela:
    linha = a.banco.get(NpcTabela, npc_id)
    if linha is None or linha.mesa_id != mesa_id:
        raise NaoEncontrado("NPC não encontrado.")
    return linha


def _npc_saida(linha: NpcTabela) -> Npc:
    return Npc(id=linha.id, nome=linha.nome, descricao=linha.descricao, motivacoes=linha.motivacoes,
               notas=linha.notas, ficha_combate=linha.ficha_combate, foto=linha.foto,
               revelado=bool(linha.revelado))


def _aplicar_npc(a: Acesso, linha: NpcTabela, dados: NpcEntrada):
    linha.nome = dados.nome.strip()
    linha.foto = imagem_valida(a, dados.foto)
    linha.descricao, linha.motivacoes, linha.notas = dados.descricao, dados.motivacoes, dados.notas
    linha.ficha_combate = None
    if dados.ficha_combate is not None:
        dados.ficha_combate.nome = dados.ficha_combate.nome.strip() or linha.nome
        linha.ficha_combate = _salvavel(dados.ficha_combate, "")


@rotas.get("/npcs", response_model=list[Npc])
def listar_npcs(mesa_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id)
    linhas = a.banco.query(NpcTabela).filter_by(mesa_id=mesa_id).order_by(NpcTabela.nome)
    return [_npc_saida(x) for x in linhas]


@rotas.post("/npcs", status_code=201, response_model=Npc)
def criar_npc(mesa_id: str, dados: NpcEntrada, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id, editar=True)
    linha = NpcTabela(id=str(uuid.uuid4()), mesa_id=mesa_id)
    _aplicar_npc(a, linha, dados)
    a.banco.add(linha)
    a.banco.commit()
    return _npc_saida(linha)


@rotas.get("/npcs/{npc_id}", response_model=Npc)
def ver_npc(mesa_id: str, npc_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id)
    return _npc_saida(_npc(a, mesa_id, npc_id))


@rotas.put("/npcs/{npc_id}", response_model=Npc)
def editar_npc(mesa_id: str, npc_id: str, dados: NpcEntrada, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id, editar=True)
    linha = _npc(a, mesa_id, npc_id)
    _aplicar_npc(a, linha, dados)
    a.banco.commit()
    return _npc_saida(linha)


@rotas.delete("/npcs/{npc_id}", status_code=204)
def apagar_npc(mesa_id: str, npc_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id, editar=True)
    a.banco.delete(_npc(a, mesa_id, npc_id))
    a.banco.commit()
    return Response(status_code=204)


@rotas.put("/npcs/{npc_id}/revelado", response_model=Npc)
def revelar_npc(mesa_id: str, npc_id: str, pedido: NpcRevelado, a: Acesso = Depends(acesso)):
    """Torna o NPC conhecido pelos jogadores (nome, foto e descrição; notas e
    motivações continuam só do mestre). Fica conhecido entre as sessões."""
    _mestre(a, mesa_id, editar=True)
    linha = _npc(a, mesa_id, npc_id)
    linha.revelado = pedido.revelado
    a.banco.commit()
    return _npc_saida(linha)