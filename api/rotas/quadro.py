"""Quadros (mapas mentais): o de cada sessão e o da campanha.

- Quadro da sessão: segue o acesso da sessão (`api/sessoes.py`): só o mestre
  responsável edita; quem recebeu a sessão compartilhada só vê.
- Quadro da campanha: qualquer membro da mesa vê; junta os cartões REVELADOS
  dos quadros de todas as sessões (e as ligações entre dois revelados). Não se
  edita direto: enche conforme os mestres revelam.

Cartões de item mostram nome e foto do NPC/inimigo/encontro/personagem; a API
resolve isso (para os jogadores, só dos cartões revelados).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, TypeAdapter

from motor.quadro import Cartao, Ligacao, Quadro, TipoCartao, so_revelado, validar

from ..autenticacao import Acesso, acesso
from ..concorrencia import conferir, versao_de
from ..mesas import membro
from ..sessoes import sessao_do_mestre
from .. import npcs
from ..tabelas import EncontroTabela, InimigoTabela, MesaTabela, NpcTabela, SessaoTabela

rotas = APIRouter(prefix="/mesas/{mesa_id}", tags=["Quadros"])
_QUADRO = TypeAdapter(Quadro)


class ItemNoQuadro(BaseModel):
    nome: str
    foto: str | None = None
    descricao: str = ""
    existe: bool = True          # o item pode ter sido apagado depois de ir para o quadro


class QuadroSaida(BaseModel):
    cartoes: list[Cartao]
    ligacoes: list[Ligacao]
    itens: dict[str, ItemNoQuadro]   # "npc:<id>" → nome, foto...
    versao: str = ""                 # mande de volta ao salvar (api/concorrencia.py)


class QuadroDaSessao(QuadroSaida):
    sessao_id: str
    titulo: str


def _quadro(sessao: SessaoTabela) -> Quadro:
    return _QUADRO.validate_python(sessao.quadro or {})


def _resolver(a: Acesso, mesa: MesaTabela, q: Quadro) -> dict[str, ItemNoQuadro]:
    """Nome/foto de cada item referenciado pelos cartões deste quadro."""
    itens: dict[str, ItemNoQuadro] = {}
    for c in q.cartoes:
        if c.tipo is not TipoCartao.ITEM or not c.item_id:
            continue
        chave = f"{c.item_tipo.value}:{c.item_id}"
        if chave in itens:
            continue
        item = None
        if c.item_tipo.value == "npc":
            n = a.banco.get(NpcTabela, c.item_id)
            if n and n.mesa_id == mesa.id:
                quem = membro(a.banco, mesa.id, a.usuario_id)
                item = (ItemNoQuadro(nome=n.nome, foto=n.foto, descricao=n.descricao)
                        if npcs.visivel_para(a.banco, n, quem) else ItemNoQuadro(nome="NPC oculto"))
        elif c.item_tipo.value == "inimigo":
            i = a.banco.get(InimigoTabela, c.item_id)
            if i and i.mesa_id == mesa.id:
                item = ItemNoQuadro(nome=i.dados["nome"], foto=i.dados.get("foto"))
        elif c.item_tipo.value == "encontro":
            e = a.banco.get(EncontroTabela, c.item_id)
            if e and e.mesa_id == mesa.id:
                item = ItemNoQuadro(nome=e.nome)
        else:
            p = next((p for p in mesa.personagens if p.id == c.item_id), None)
            if p:
                item = ItemNoQuadro(nome=p.nome or "Sem nome", foto=p.foto)
        itens[chave] = item or ItemNoQuadro(nome="(removido)", existe=False)
    return itens


def _saida(a: Acesso, mesa: MesaTabela, q: Quadro) -> dict:
    dados = _QUADRO.dump_python(q, mode="json")
    return {"cartoes": dados["cartoes"], "ligacoes": dados["ligacoes"], "itens": _resolver(a, mesa, q)}


@rotas.get("/sessoes/{sessao_id}/quadro", response_model=QuadroSaida)
def ver_quadro(mesa_id: str, sessao_id: str, a: Acesso = Depends(acesso)):
    s = sessao_do_mestre(a, mesa_id, sessao_id)
    return {**_saida(a, a.banco.get(MesaTabela, mesa_id), _quadro(s)), "versao": versao_de(s.quadro or {})}


@rotas.put("/sessoes/{sessao_id}/quadro", response_model=QuadroSaida)
def salvar_quadro(mesa_id: str, sessao_id: str, quadro: Quadro, versao: str | None = None,
                  a: Acesso = Depends(acesso)):
    """Grava o quadro inteiro (a tela salva sozinha depois de cada mudança)."""
    s = sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    conferir(versao, s.quadro or {})
    validar(quadro)
    s.quadro = _QUADRO.dump_python(quadro, mode="json")
    a.banco.commit()
    return {**_saida(a, a.banco.get(MesaTabela, mesa_id), quadro), "versao": versao_de(s.quadro)}


@rotas.get("/quadro-da-campanha", response_model=list[QuadroDaSessao])
def quadro_da_campanha(mesa_id: str, a: Acesso = Depends(acesso)):
    """O revelado de todas as sessões, uma região por sessão (na ordem em que foram criadas)."""
    mesa = membro(a.banco, mesa_id, a.usuario_id).mesa
    regioes = []
    for s in a.banco.query(SessaoTabela).filter_by(mesa_id=mesa_id).order_by(SessaoTabela.criado_em):
        visivel = so_revelado(_quadro(s))
        if visivel.cartoes:
            regioes.append(QuadroDaSessao(sessao_id=s.id, titulo=s.titulo, **_saida(a, mesa, visivel)))
    return regioes
