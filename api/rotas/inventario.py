"""Inventário: ouro, itens, consumíveis e armas guardadas.

O dono mexe em tudo. O mestre com a permissão "dar_itens" pode dar (ou tirar)
ouro e itens de um personagem da mesa; usar consumível e trocar de arma são
só do dono. As regras ficam no motor (motor/inventario.py).
"""

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from motor import Personagem, RegraViolada, TipoDeItem
from motor.inventario import MOEDAS_POR_PUNHADO, OURO_MAXIMO, decompor, exigir_moedas

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..esquemas import FichaSaida, ficha_saida
from ..mesas import Permissao, exigir, membro
from .personagens import executar

rotas = APIRouter(prefix="/personagens/{personagem_id}/inventario", tags=["Inventário"])
rotas_mestre = APIRouter(prefix="/mesas/{mesa_id}/personagens/{personagem_id}/inventario", tags=["Inventário"])


# --- formatos --------------------------------------------------------------------------------

class Ouro(BaseModel):
    baus: int
    bolsas: int
    punhados: int
    total: int        # em punhados
    maximo: int
    moedas: int = 0   # regra opcional: moedas além dos punhados (0 a 9)


class ItemNoInventario(BaseModel):
    id: str
    nome: str
    nome_original: str
    tipo: TipoDeItem
    texto: str
    quantidade: int
    efeito_automatico: bool       # usar já mexe em PV/PF/Esperança
    dado: str | None              # dado a rolar ao usar ("1d4+1")
    escolha: bool                 # escolher PV ou PF ao usar
    reliquia: str | None          # atributo (ex.: AGILIDADE) ou EXPERIENCIA


class ItemLivreSaida(BaseModel):
    id: str
    nome: str
    descricao: str
    quantidade: int


class ArmaGuardada(BaseModel):
    indice: int
    id: str
    nome: str
    principal: bool
    duas_maos: bool
    tier: int


class InventarioSaida(BaseModel):
    ouro: Ouro
    itens: list[ItemNoInventario]
    livres: list[ItemLivreSaida]
    armas: list[ArmaGuardada]
    experiencia_da_reliquia: str | None
    usa_moedas: bool            # regra opcional ligada (pela mesa, ou pelo personagem sem mesa)
    moedas_pela_mesa: bool      # quem decide é a mesa (o personagem está numa)


class MudarOuro(BaseModel):
    punhados: int = Field(0, description="Positivo ganha, negativo gasta.")
    moedas: int = Field(0, description="Regra opcional; mesmo sinal dos punhados.")


class UsarMoedas(BaseModel):
    usar: bool


class ItemEntrada(BaseModel):
    item_id: str
    quantidade: int = Field(1, ge=1)


class ItemLivreEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    descricao: str = Field("", max_length=2000)
    quantidade: int = Field(1, ge=1)


class ArmaEntrada(BaseModel):
    arma_id: str


class Usar(BaseModel):
    rolagem: int | None = None
    escolha: Literal["PV", "PF"] | None = None


class UsoSaida(BaseModel):
    notas: list[str]
    inventario: InventarioSaida
    ficha: FichaSaida


class Troca(BaseModel):
    em_perigo: bool


class ReliquiaEntrada(BaseModel):
    experiencia: str | None


def saida(p: Personagem) -> InventarioSaida:
    bib, inv = p.bib, p.inventario
    itens = []
    for item_id, qtd in inv.itens.items():
        i = bib.itens[item_id]
        ef = i.efeito
        dado = ef.dado if ef else None
        itens.append(ItemNoInventario(
            id=i.id, nome=i.nome, nome_original=i.nome_original, tipo=i.tipo, texto=i.texto, quantidade=qtd,
            efeito_automatico=ef is not None, dado=dado, escolha=bool(ef and ef.escolha),
            reliquia=i.reliquia.value if hasattr(i.reliquia, "value") else i.reliquia))
    ordem = list(TipoDeItem)
    itens.sort(key=lambda x: (ordem.index(x.tipo), x.nome))
    armas = [ArmaGuardada(indice=n, id=a, nome=bib.armas[a].nome, principal=bib.armas[a].primaria,
                          duas_maos=bib.armas[a].duas_maos, tier=bib.armas[a].tier)
             for n, a in enumerate(inv.armas)]
    usa = p.usa_moedas
    return InventarioSaida(
        ouro=Ouro(**decompor(inv.ouro), total=inv.ouro, maximo=OURO_MAXIMO, moedas=inv.moedas if usa else 0),
        itens=itens, livres=[ItemLivreSaida(**vars(x)) for x in inv.livres], armas=armas,
        experiencia_da_reliquia=inv.experiencia_da_reliquia, usa_moedas=usa,
        moedas_pela_mesa=p.moedas_da_mesa is not None)


# --- ações (as mesmas para o dono e para o mestre) ------------------------------------------

def _ouro(pedido: MudarOuro) -> Callable[[Personagem], None]:
    def acao(p: Personagem):
        exigir_moedas(p.usa_moedas, pedido.moedas)
        valor = pedido.punhados * MOEDAS_POR_PUNHADO + pedido.moedas   # em moedas
        if valor >= 0:
            p.inventario.ganhar_ouro(0, valor)
        else:
            p.inventario.gastar_ouro(0, -valor)
    return acao


def _dar_item(pedido: ItemEntrada):
    return lambda p: p.inventario.adicionar(p.bib, pedido.item_id, pedido.quantidade)


def _tirar_item(item_id: str, quantidade: int):
    return lambda p: p.inventario.remover(p.bib, item_id, quantidade)


def _dar_livre(pedido: ItemLivreEntrada):
    return lambda p: p.inventario.adicionar_livre(pedido.nome, pedido.descricao, pedido.quantidade)


def _tirar_livre(livre_id: str, quantidade: int):
    return lambda p: p.inventario.remover_livre(livre_id, quantidade)


def _dar_arma(pedido: ArmaEntrada):
    return lambda p: p.inventario.guardar_arma(p.bib, pedido.arma_id)


def _no_dono(a: Acesso, personagem_id: str, acao) -> InventarioSaida:
    def executar_e_mostrar(p: Personagem):
        acao(p)
        return saida(p)
    return executar(a, personagem_id, executar_e_mostrar)


def _no_mestre(a: Acesso, mesa_id: str, personagem_id: str, acao) -> InventarioSaida:
    exigir(membro(a.banco, mesa_id, a.usuario_id), Permissao.DAR_ITENS)
    linha = repositorio.linha_na_mesa(a.banco, mesa_id, personagem_id)
    p = repositorio.montar(linha)
    acao(p)
    repositorio.gravar(a.banco, linha, p)
    return saida(p)


# --- dono -------------------------------------------------------------------------------------

@rotas.get("", response_model=InventarioSaida)
def ver(personagem_id: str, a: Acesso = Depends(acesso)):
    return saida(repositorio.carregar(a.banco, a.usuario_id, personagem_id))


@rotas.post("/ouro", response_model=InventarioSaida)
def mudar_ouro(personagem_id: str, pedido: MudarOuro, a: Acesso = Depends(acesso)):
    return _no_dono(a, personagem_id, _ouro(pedido))


@rotas.post("/itens", response_model=InventarioSaida)
def adicionar_item(personagem_id: str, pedido: ItemEntrada, a: Acesso = Depends(acesso)):
    return _no_dono(a, personagem_id, _dar_item(pedido))


@rotas.delete("/itens/{item_id}", response_model=InventarioSaida)
def remover_item(personagem_id: str, item_id: str, quantidade: int = 1, a: Acesso = Depends(acesso)):
    return _no_dono(a, personagem_id, _tirar_item(item_id, quantidade))


@rotas.post("/itens/{item_id}/usar", response_model=UsoSaida)
def usar(personagem_id: str, item_id: str, pedido: Usar, a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        notas = p.usar_consumivel(item_id, pedido.rolagem, pedido.escolha)
        return UsoSaida(notas=notas, inventario=saida(p), ficha=ficha_saida(p.ficha()))
    return executar(a, personagem_id, acao)


@rotas.post("/livres", response_model=InventarioSaida)
def adicionar_livre(personagem_id: str, pedido: ItemLivreEntrada, a: Acesso = Depends(acesso)):
    return _no_dono(a, personagem_id, _dar_livre(pedido))


@rotas.delete("/livres/{livre_id}", response_model=InventarioSaida)
def remover_livre(personagem_id: str, livre_id: str, quantidade: int = 1, a: Acesso = Depends(acesso)):
    return _no_dono(a, personagem_id, _tirar_livre(livre_id, quantidade))


@rotas.post("/armas", response_model=InventarioSaida)
def guardar_arma(personagem_id: str, pedido: ArmaEntrada, a: Acesso = Depends(acesso)):
    return _no_dono(a, personagem_id, _dar_arma(pedido))


@rotas.delete("/armas/{indice}", response_model=InventarioSaida)
def descartar_arma(personagem_id: str, indice: int, a: Acesso = Depends(acesso)):
    return _no_dono(a, personagem_id, lambda p: p.inventario.descartar_arma(indice))


@rotas.post("/armas/{indice}/trocar", response_model=FichaSaida)
def trocar_arma(personagem_id: str, indice: int, pedido: Troca, a: Acesso = Depends(acesso)):
    return ficha_saida(executar(a, personagem_id, lambda p: p.trocar_arma(indice, pedido.em_perigo)))


@rotas.put("/moedas", response_model=InventarioSaida)
def usar_moedas(personagem_id: str, pedido: UsarMoedas, a: Acesso = Depends(acesso)):
    """Regra opcional das moedas para um personagem sem mesa (na mesa, quem decide é ela)."""
    def acao(p: Personagem):
        if p.moedas_da_mesa is not None:
            raise RegraViolada("Este personagem está numa mesa: a regra das moedas é definida por ela.")
        p.inventario.usar_moedas = pedido.usar
    return _no_dono(a, personagem_id, acao)


@rotas.put("/reliquia", response_model=InventarioSaida)
def experiencia_da_reliquia(personagem_id: str, pedido: ReliquiaEntrada, a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        if pedido.experiencia is not None and pedido.experiencia not in p.ficha().experiencias:
            raise RegraViolada("Escolha uma das suas Experiências.")
        p.inventario.experiencia_da_reliquia = pedido.experiencia
    return _no_dono(a, personagem_id, acao)


# --- mestre (permissão "dar_itens") --------------------------------------------------------

@rotas_mestre.get("", response_model=InventarioSaida)
def ver_na_mesa(mesa_id: str, personagem_id: str, a: Acesso = Depends(acesso)):
    exigir(membro(a.banco, mesa_id, a.usuario_id), Permissao.VER_FICHAS)
    return saida(repositorio.montar(repositorio.linha_na_mesa(a.banco, mesa_id, personagem_id)))


@rotas_mestre.post("/ouro", response_model=InventarioSaida)
def mudar_ouro_na_mesa(mesa_id: str, personagem_id: str, pedido: MudarOuro, a: Acesso = Depends(acesso)):
    return _no_mestre(a, mesa_id, personagem_id, _ouro(pedido))


@rotas_mestre.post("/itens", response_model=InventarioSaida)
def dar_item(mesa_id: str, personagem_id: str, pedido: ItemEntrada, a: Acesso = Depends(acesso)):
    return _no_mestre(a, mesa_id, personagem_id, _dar_item(pedido))


@rotas_mestre.delete("/itens/{item_id}", response_model=InventarioSaida)
def tirar_item(mesa_id: str, personagem_id: str, item_id: str, quantidade: int = 1,
               a: Acesso = Depends(acesso)):
    return _no_mestre(a, mesa_id, personagem_id, _tirar_item(item_id, quantidade))


@rotas_mestre.post("/livres", response_model=InventarioSaida)
def dar_livre(mesa_id: str, personagem_id: str, pedido: ItemLivreEntrada, a: Acesso = Depends(acesso)):
    return _no_mestre(a, mesa_id, personagem_id, _dar_livre(pedido))


@rotas_mestre.delete("/livres/{livre_id}", response_model=InventarioSaida)
def tirar_livre(mesa_id: str, personagem_id: str, livre_id: str, quantidade: int = 1,
                a: Acesso = Depends(acesso)):
    return _no_mestre(a, mesa_id, personagem_id, _tirar_livre(livre_id, quantidade))


@rotas_mestre.post("/armas", response_model=InventarioSaida)
def dar_arma(mesa_id: str, personagem_id: str, pedido: ArmaEntrada, a: Acesso = Depends(acesso)):
    return _no_mestre(a, mesa_id, personagem_id, _dar_arma(pedido))
