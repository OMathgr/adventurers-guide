"""Catálogo do SRD (somente leitura): o que a interface precisa para montar
as listas de escolha."""

from fastapi import APIRouter, HTTPException

from motor import (Adversario, Ancestralidade, Arma, Armadura, CartaDeDominio, Classe, Comunidade, Item,
                   Subclasse, TipoAdversario, TipoDeItem)

from ..repositorio import biblioteca

rotas = APIRouter(prefix="/srd", tags=["SRD"])


@rotas.get("/classes", response_model=list[Classe])
def classes():
    return list(biblioteca().classes.values())


@rotas.get("/classes/{classe_id}/subclasses", response_model=list[Subclasse])
def subclasses(classe_id: str):
    bib = biblioteca()
    if classe_id not in bib.classes:
        raise HTTPException(404, f"Classe {classe_id} não encontrada.")
    return bib.subclasses_da_classe(bib.classes[classe_id])


@rotas.get("/ancestralidades", response_model=list[Ancestralidade])
def ancestralidades():
    return list(biblioteca().ancestralidades.values())


@rotas.get("/comunidades", response_model=list[Comunidade])
def comunidades():
    return list(biblioteca().comunidades.values())


@rotas.get("/armas", response_model=list[Arma])
def armas(tier: int | None = None):
    return [a for a in biblioteca().armas.values() if tier is None or a.tier == tier]


@rotas.get("/itens", response_model=list[Item])
def itens(tipo: TipoDeItem | None = None):
    """Itens (tabela de saque), consumíveis, itens iniciais e de classe (em ordem de tipo e da tabela d60)."""
    ordem = list(TipoDeItem)
    lista = [i for i in biblioteca().itens.values() if tipo is None or i.tipo is tipo]
    return sorted(lista, key=lambda i: (ordem.index(i.tipo), i.rolagem or 0, i.nome))


@rotas.get("/armaduras", response_model=list[Armadura])
def armaduras(tier: int | None = None):
    return [a for a in biblioteca().armaduras.values() if tier is None or a.tier == tier]


@rotas.get("/adversarios", response_model=list[Adversario])
def adversarios(patamar: int | None = None, tipo: TipoAdversario | None = None):
    """Adversários do SRD (base para os inimigos que o mestre usa na mesa)."""
    return sorted((a for a in biblioteca().adversarios.values()
                   if (patamar is None or a.patamar == patamar) and (tipo is None or a.tipo is tipo)),
                  key=lambda a: (a.patamar, a.nome))


@rotas.get("/adversarios/{adversario_id}", response_model=Adversario)
def adversario(adversario_id: str):
    a = biblioteca().adversarios.get(adversario_id)
    if a is None:
        raise HTTPException(404, f"Adversário {adversario_id} não encontrado.")
    return a


@rotas.get("/dominios")
def dominios() -> dict[str, str]:
    """Código -> nome de exibição dos domínios (ex.: "BLADE": "Lâmina")."""
    bib = biblioteca()
    return {d: bib.nome_dominio(d) for d in sorted({c.dominio for c in bib.cartas.values()})}


@rotas.get("/cartas", response_model=list[CartaDeDominio])
def cartas(dominio: str | None = None, nivel_max: int = 10):
    dominios = [dominio] if dominio else {c.dominio for c in biblioteca().cartas.values()}
    return biblioteca().cartas_disponiveis(dominios, nivel_max)
