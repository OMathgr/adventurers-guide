"""Itens criados pelo mestre numa mesa: comuns, consumíveis, armas e armaduras
(motor/itens_proprios.py).

Como os inimigos: privado dos mestres (jogador recebe 404); ver exige ser
mestre; criar, editar e apagar exige `preparar`. Entregar é pelo inventário
do personagem (`dar_itens`) ou pelas lojas da sessão. Quem recebe guarda uma
cópia: editar ou apagar o modelo não muda o que já foi entregue. As lojas de
sessões não encerradas acompanham a edição (o item ainda não foi vendido).
"""

import dataclasses
import uuid
from typing import get_type_hints

from fastapi import APIRouter, Depends, Response
from pydantic import create_model
from sqlalchemy.orm import Session

from motor.itens_proprios import ItemProprio, validar
from motor.loja import TipoNaLoja

from ..autenticacao import Acesso, acesso
from ..concorrencia import conferir, versao_de
from ..repositorio import NaoEncontrado
from ..tabelas import ItemDaMesaTabela, LojaTabela, SessaoTabela
from .conteudo import _mestre, _padrao

rotas = APIRouter(prefix="/mesas/{mesa_id}/itens", tags=["Conteúdo do mestre"])

# o ItemProprio do motor + a versão do conteúdo (para avisar quando dois editam ao mesmo tempo)
_TIPOS = get_type_hints(ItemProprio)
ItemDaMesaComVersao = create_model(
    "ItemDaMesaComVersao", versao=(str, ""),
    **{c.name: (_TIPOS[c.name], _padrao(c)) for c in dataclasses.fields(ItemProprio)})


def _salvavel(item: ItemProprio, id_: str) -> dict:
    validar(item)
    item.id = id_
    return item.estado()


def _com_versao(linha: ItemDaMesaTabela) -> dict:
    return {**linha.dados, "versao": versao_de(linha.dados)}


def item_da_mesa(banco: Session, mesa_id: str, item_id: str) -> ItemDaMesaTabela:
    linha = banco.get(ItemDaMesaTabela, item_id)
    if linha is None or linha.mesa_id != mesa_id:
        raise NaoEncontrado("Item não encontrado na mesa.")
    return linha


def _atualizar_lojas(banco: Session, mesa_id: str, linha: ItemDaMesaTabela):
    """Lojas abertas (sessões não encerradas) passam a vender o item editado."""
    lojas = (banco.query(LojaTabela).join(SessaoTabela, LojaTabela.sessao_id == SessaoTabela.id)
             .filter(LojaTabela.mesa_id == mesa_id, SessaoTabela.status != "encerrada"))
    for loja in lojas:
        if any(i["tipo"] == TipoNaLoja.PROPRIO.value and i.get("ref") == linha.id for i in loja.itens):
            loja.itens = [{**i, "proprio": linha.dados} if i["tipo"] == TipoNaLoja.PROPRIO.value
                          and i.get("ref") == linha.id else i for i in loja.itens]


@rotas.get("", response_model=list[ItemProprio])
def listar(mesa_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id)
    linhas = a.banco.query(ItemDaMesaTabela).filter_by(mesa_id=mesa_id).order_by(ItemDaMesaTabela.criado_em)
    return [x.dados for x in linhas]


@rotas.post("", status_code=201, response_model=ItemDaMesaComVersao)
def criar(mesa_id: str, item: ItemProprio, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id, editar=True)
    novo_id = str(uuid.uuid4())
    linha = ItemDaMesaTabela(id=novo_id, mesa_id=mesa_id, dados=_salvavel(item, novo_id))
    a.banco.add(linha)
    a.banco.commit()
    return _com_versao(linha)


@rotas.get("/{item_id}", response_model=ItemDaMesaComVersao)
def ver(mesa_id: str, item_id: str, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id)
    return _com_versao(item_da_mesa(a.banco, mesa_id, item_id))


@rotas.put("/{item_id}", response_model=ItemDaMesaComVersao)
def editar(mesa_id: str, item_id: str, item: ItemProprio, versao: str | None = None, a: Acesso = Depends(acesso)):
    _mestre(a, mesa_id, editar=True)
    linha = item_da_mesa(a.banco, mesa_id, item_id)
    conferir(versao, linha.dados)
    linha.dados = _salvavel(item, item_id)
    _atualizar_lojas(a.banco, mesa_id, linha)
    a.banco.commit()
    return _com_versao(linha)


@rotas.delete("/{item_id}", status_code=204)
def apagar(mesa_id: str, item_id: str, a: Acesso = Depends(acesso)):
    """Apaga o modelo. Quem já recebeu continua com o item; as lojas que o
    vendem continuam vendendo a última versão."""
    _mestre(a, mesa_id, editar=True)
    a.banco.delete(item_da_mesa(a.banco, mesa_id, item_id))
    a.banco.commit()
    return Response(status_code=204)
