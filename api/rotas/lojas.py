"""Lojas de uma sessão: o mestre responsável monta (itens, preços, estoque) e
vende para os personagens da mesa, cobrando o ouro e entregando o item.

Acesso como o dos encontros: só o responsável monta e vende; mestres com quem
ele compartilhou a sessão só veem; vender também exige a permissão
"dar_itens". Os jogadores veem a loja à mostra em /mesas/{id}/revelado.
"""

import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, TypeAdapter

from motor import loja as regras_loja
from motor.inventario import decompor, exigir_moedas
from motor.loja import ItemDaLoja, TipoNaLoja

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..mesas import Permissao, exigir, membro
from ..repositorio import NaoEncontrado, biblioteca
from ..sessoes import sessao_do_mestre
from ..tabelas import LojaTabela, MesaTabela
from .inventario import InventarioSaida, Ouro, saida as saida_inventario

rotas = APIRouter(prefix="/mesas/{mesa_id}/sessoes/{sessao_id}/lojas", tags=["Lojas"])
_ITENS = TypeAdapter(list[ItemDaLoja])


class ItemDaLojaSaida(BaseModel):
    id: str
    tipo: TipoNaLoja
    ref: str | None
    nome: str
    texto: str             # descrição do item (catálogo ou do mestre)
    preco: Ouro
    estoque: int | None


class LojaSaida(BaseModel):
    id: str
    nome: str
    visivel: bool
    itens: list[ItemDaLojaSaida]


class ItemDaLojaEntrada(BaseModel):
    id: str = ""
    tipo: TipoNaLoja
    ref: str | None = None
    nome: str = Field("", max_length=120)
    descricao: str = Field("", max_length=2000)
    preco: int = Field(ge=0, description="Em punhados (1 bolsa = 10, 1 baú = 100).")
    moedas: int = Field(0, ge=0, le=9, description="Regra opcional das moedas.")
    estoque: int | None = Field(None, ge=0)


class LojaEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    visivel: bool = False
    itens: list[ItemDaLojaEntrada] = []


class NomeLoja(BaseModel):
    nome: str = Field(min_length=1, max_length=120)


class Venda(BaseModel):
    item_id: str
    personagem_id: str
    quantidade: int = Field(1, ge=1)


class VendaSaida(BaseModel):
    notas: list[str]
    loja: LojaSaida
    inventario: InventarioSaida


def itens_saida(itens: list[dict]) -> list[ItemDaLojaSaida]:
    bib = biblioteca()
    saida = []
    for item in _ITENS.validate_python(itens):
        texto = bib.itens[item.ref].texto if item.tipo is TipoNaLoja.ITEM else item.descricao
        saida.append(ItemDaLojaSaida(id=item.id, tipo=item.tipo, ref=item.ref, nome=regras_loja.nome(bib, item),
                                     texto=texto, preco=Ouro(**decompor(item.preco), total=item.preco, maximo=0,
                                                             moedas=item.moedas),
                                     estoque=item.estoque))
    return saida


def _saida(linha: LojaTabela) -> LojaSaida:
    return LojaSaida(id=linha.id, nome=linha.nome, visivel=linha.visivel, itens=itens_saida(linha.itens))


def linha_mesa(a: Acesso, mesa_id: str) -> MesaTabela:
    return a.banco.get(MesaTabela, mesa_id)


def _linha(a: Acesso, sessao_id: str, loja_id: str) -> LojaTabela:
    linha = a.banco.get(LojaTabela, loja_id)
    if linha is None or linha.sessao_id != sessao_id:
        raise NaoEncontrado("Loja não encontrada.")
    return linha


@rotas.get("", response_model=list[LojaSaida])
def listar(mesa_id: str, sessao_id: str, a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id)
    linhas = a.banco.query(LojaTabela).filter_by(sessao_id=sessao_id).order_by(LojaTabela.criado_em)
    return [_saida(x) for x in linhas]


@rotas.post("", status_code=201, response_model=LojaSaida)
def criar(mesa_id: str, sessao_id: str, dados: NomeLoja, a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    linha = LojaTabela(id=str(uuid.uuid4()), mesa_id=mesa_id, sessao_id=sessao_id, nome=dados.nome.strip(), itens=[])
    a.banco.add(linha)
    a.banco.commit()
    return _saida(linha)


@rotas.put("/{loja_id}", response_model=LojaSaida)
def salvar(mesa_id: str, sessao_id: str, loja_id: str, dados: LojaEntrada, a: Acesso = Depends(acesso)):
    """Salva a loja inteira (nome, à mostra, itens com preço e estoque)."""
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    linha = _linha(a, sessao_id, loja_id)
    itens = [ItemDaLoja(**i.model_dump()) for i in dados.itens]
    regras_loja.validar(biblioteca(), itens)
    exigir_moedas(linha_mesa(a, mesa_id).usar_moedas, max((i.moedas for i in itens), default=0))
    linha.nome, linha.visivel = dados.nome.strip(), dados.visivel
    linha.itens = _ITENS.dump_python(itens, mode="json")
    a.banco.commit()
    return _saida(linha)


@rotas.delete("/{loja_id}", status_code=204)
def apagar(mesa_id: str, sessao_id: str, loja_id: str, a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    a.banco.delete(_linha(a, sessao_id, loja_id))
    a.banco.commit()
    return Response(status_code=204)


@rotas.post("/{loja_id}/vender", response_model=VendaSaida)
def vender(mesa_id: str, sessao_id: str, loja_id: str, pedido: Venda, a: Acesso = Depends(acesso)):
    """Cobra o ouro do personagem, entrega o item e baixa o estoque, tudo junto:
    se o motor recusar (ouro, espaço, limite), nada muda."""
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    exigir(membro(a.banco, mesa_id, a.usuario_id), Permissao.DAR_ITENS)
    linha = _linha(a, sessao_id, loja_id)
    itens = _ITENS.validate_python(linha.itens)
    item = next((i for i in itens if i.id == pedido.item_id), None)
    if item is None:
        raise NaoEncontrado("Item não encontrado nesta loja.")
    personagem_linha = repositorio.linha_na_mesa(a.banco, mesa_id, pedido.personagem_id)
    personagem = repositorio.montar(personagem_linha)
    notas = regras_loja.vender(personagem, item, pedido.quantidade)
    linha.itens = _ITENS.dump_python(itens, mode="json")
    repositorio.gravar(a.banco, personagem_linha, personagem)   # commit da venda inteira
    return VendaSaida(notas=notas, loja=_saida(linha), inventario=saida_inventario(personagem))

