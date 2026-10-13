"""O que os jogadores veem do lado do mestre (qualquer membro da mesa).

- Em combate: encontros à mostra (`visivel`) de sessões em andamento. De cada
  inimigo não escondido: nome na luta, foto, vitalidade (cheia, metade, baixa,
  derrotado; nunca os PV) e condições. Nada de dano, habilidades, Dificuldade
  ou outros números.
- NPCs conhecidos: nome, foto e descrição (nunca notas nem motivações).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, TypeAdapter

from motor.encontro import Combatente

from ..autenticacao import Acesso, acesso
from ..mesas import membro
from ..tabelas import EncontroTabela, NpcTabela, SessaoTabela

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


class VistaDosJogadores(BaseModel):
    combate: list[EncontroVisivel]
    npcs: list[NpcConhecido]


@rotas.get("/revelado", response_model=VistaDosJogadores)
def revelado(mesa_id: str, a: Acesso = Depends(acesso)):
    membro(a.banco, mesa_id, a.usuario_id)   # qualquer membro (mestre também, para conferir)
    combate = []
    consulta = (a.banco.query(EncontroTabela, SessaoTabela)
                .join(SessaoTabela, EncontroTabela.sessao_id == SessaoTabela.id)
                .filter(EncontroTabela.mesa_id == mesa_id, EncontroTabela.visivel.is_(True),
                        SessaoTabela.status == "em_andamento")
                .order_by(EncontroTabela.criado_em))
    for encontro, sessao in consulta:
        inimigos = [InimigoVisivel(id=c.id, rotulo=c.rotulo, foto=c.adversario.foto, vitalidade=c.vitalidade,
                                   condicoes=c.condicoes)
                    for c in _COMBATENTES.validate_python(encontro.combatentes) if not c.escondido]
        combate.append(EncontroVisivel(id=encontro.id, nome=encontro.nome, mestre=sessao.responsavel.nome,
                                       inimigos=inimigos))
    npcs = (a.banco.query(NpcTabela).filter(NpcTabela.mesa_id == mesa_id, NpcTabela.revelado.is_(True))
            .order_by(NpcTabela.nome))
    return VistaDosJogadores(combate=combate, npcs=[NpcConhecido(id=n.id, nome=n.nome, foto=n.foto, descricao=n.descricao)
                                          for n in npcs])
