"""O que os jogadores veem do lado do mestre (qualquer membro da mesa).

- Em combate: encontros à mostra (`visivel`) de sessões em andamento. De cada
  inimigo não escondido: nome na luta, foto, vitalidade (cheia, metade, baixa,
  derrotado; nunca os PV) e condições. Nada de dano, habilidades, Dificuldade
  ou outros números.
- NPCs exibidos para todos e vinculados à sessão: nome, foto e descrição (nunca
  notas nem motivações).
- Lojas à mostra (`visivel`) de sessões em andamento: itens, preços e estoque.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, TypeAdapter

from motor.encontro import Combatente

from ..autenticacao import Acesso, acesso
from ..mesas import membro
from .. import npcs
from ..tabelas import EncontroTabela, LojaTabela, NpcTabela, SessaoTabela
from .lojas import ItemDaLojaSaida, itens_saida

rotas = APIRouter(prefix="/mesas/{mesa_id}", tags=["Para os jogadores"])
_COMBATENTES = TypeAdapter(list[Combatente])


class InimigoVisivel(BaseModel):
    id: str
    rotulo: str
    foto: str | None
    vitalidade: str              # vida_cheia, metade_da_vida, vida_baixa, derrotado
    condicoes: list[str]


class EncontroVisivel(BaseModel):
    id: str
    nome: str
    mestre: str
    inimigos: list[InimigoVisivel]


class NpcConhecido(BaseModel):
    id: str
    nome: str
    foto: str | None
    descricao: str


class LojaVisivel(BaseModel):
    id: str
    nome: str
    mestre: str
    itens: list[ItemDaLojaSaida]


class VistaDosJogadores(BaseModel):
    combate: list[EncontroVisivel]
    npcs: list[NpcConhecido]
    lojas: list[LojaVisivel] = []


def combate_visivel(a: Acesso, mesa_id: str, sessao_id: str | None = None) -> list[EncontroVisivel]:
    """Encontros à mostra das sessões em andamento (ou só de `sessao_id`)."""
    combate = []
    consulta = (a.banco.query(EncontroTabela, SessaoTabela)
                .join(SessaoTabela, EncontroTabela.sessao_id == SessaoTabela.id)
                .filter(EncontroTabela.mesa_id == mesa_id, EncontroTabela.visivel.is_(True),
                        SessaoTabela.status == "em_andamento")
                .order_by(EncontroTabela.criado_em))
    if sessao_id:
        consulta = consulta.filter(SessaoTabela.id == sessao_id)
    for encontro, sessao in consulta:
        inimigos = [InimigoVisivel(id=c.id, rotulo=c.rotulo, foto=c.adversario.foto, vitalidade=c.vitalidade,
                                   condicoes=c.condicoes)
                    for c in _COMBATENTES.validate_python(encontro.combatentes) if not c.escondido]
        combate.append(EncontroVisivel(id=encontro.id, nome=encontro.nome, mestre=sessao.responsavel.nome,
                                       inimigos=inimigos))
    return combate


def npcs_conhecidos(a: Acesso, mesa_id: str, sessao_id: str | None = None) -> list[NpcConhecido]:
    """NPCs exibidos para todos e vinculados à sessão (`sessao_id`) ou, sem ela,
    a alguma sessão em andamento da mesa."""
    if sessao_id:
        sessoes = [a.banco.get(SessaoTabela, sessao_id)]
    else:
        sessoes = a.banco.query(SessaoTabela).filter_by(mesa_id=mesa_id, status="em_andamento").all()
    ids = {i for s in sessoes if s for i in (s.npcs or [])}
    if not ids:
        return []
    linhas = (a.banco.query(NpcTabela).filter(NpcTabela.mesa_id == mesa_id, NpcTabela.id.in_(ids),
                                              NpcTabela.visibilidade == npcs.TODOS)
              .order_by(NpcTabela.nome))
    return [NpcConhecido(id=n.id, nome=n.nome, foto=n.foto, descricao=n.descricao) for n in linhas]


def lojas_visiveis(a: Acesso, mesa_id: str, sessao_id: str | None = None) -> list[LojaVisivel]:
    lojas = (a.banco.query(LojaTabela, SessaoTabela)
             .join(SessaoTabela, LojaTabela.sessao_id == SessaoTabela.id)
             .filter(LojaTabela.mesa_id == mesa_id, LojaTabela.visivel.is_(True),
                     SessaoTabela.status == "em_andamento")
             .order_by(LojaTabela.criado_em))
    if sessao_id:
        lojas = lojas.filter(SessaoTabela.id == sessao_id)
    return [LojaVisivel(id=loja.id, nome=loja.nome, mestre=sessao.responsavel.nome, itens=itens_saida(loja.itens))
            for loja, sessao in lojas]


@rotas.get("/revelado", response_model=VistaDosJogadores)
def revelado(mesa_id: str, a: Acesso = Depends(acesso)):
    """Tudo o que está à mostra na mesa (todas as sessões em andamento). A tela
    usa a vista de cada sessão (`/sessoes/{id}/jogo`)."""
    membro(a.banco, mesa_id, a.usuario_id)   # qualquer membro (mestre também, para conferir)
    return VistaDosJogadores(combate=combate_visivel(a, mesa_id), npcs=npcs_conhecidos(a, mesa_id),
                             lojas=lojas_visiveis(a, mesa_id))
