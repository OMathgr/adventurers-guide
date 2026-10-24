"""Excluir a conta sem levar junto o que é dos outros.

O banco apaga em cascata tudo o que aponta para o usuário. Antes disso:
- mesas que ele criou e têm outros membros passam para o mestre mais antigo
  (sem mestre, o jogador mais antigo, que vira mestre); mesa sem mais ninguém
  é apagada (os personagens dos outros, se houver, ficam sem mesa);
- sessões que ele mestrou em mesas que continuam passam para quem criou a mesa;
- fotos dele usadas por NPCs e inimigos de mesas que continuam passam para quem
  criou a mesa (senão a cascata das imagens as apagaria).
Os personagens dele são apagados (com as marcas e rolagens). NPCs que eram
dele passam sozinhos para quem criou a mesa (api/npcs.py).
"""

from sqlalchemy.orm import Session

from .mesas import MESTRE
from .tabelas import (ImagemTabela, InimigoTabela, MembroTabela, MesaTabela, NpcTabela, SessaoTabela,
                      UsuarioTabela)


def _herdeiro(mesa: MesaTabela, usuario_id: str) -> MembroTabela | None:
    outros = sorted((m for m in mesa.membros if m.usuario_id != usuario_id), key=lambda m: m.entrou_em)
    return next((m for m in outros if m.papel == MESTRE), outros[0] if outros else None)


def _passar_fotos(banco: Session, usuario_id: str, mesa_id: str, novo_dono: str):
    fotos = {n.foto for n in banco.query(NpcTabela).filter_by(mesa_id=mesa_id) if n.foto}
    fotos |= {i.dados.get("foto") for i in banco.query(InimigoTabela).filter_by(mesa_id=mesa_id) if i.dados.get("foto")}
    for foto in fotos:
        imagem = banco.get(ImagemTabela, foto)
        if imagem is not None and imagem.dono_id == usuario_id:
            imagem.dono_id = novo_dono


def apagar_conta(banco: Session, usuario: UsuarioTabela):
    uid = usuario.id
    for mesa in banco.query(MesaTabela).filter_by(criador_id=uid).all():
        herdeiro = _herdeiro(mesa, uid)
        if herdeiro is None:
            for p in mesa.personagens:
                p.mesa_id = None
            banco.delete(mesa)
            continue
        herdeiro.papel = MESTRE
        mesa.criador_id = herdeiro.usuario_id
    banco.flush()
    # sessões que ele mestrou (nas mesas dele que continuam e nas de outras pessoas)
    for s in banco.query(SessaoTabela).filter_by(responsavel_id=uid).all():
        s.responsavel_id = banco.get(MesaTabela, s.mesa_id).criador_id
    # nas mesas onde ele é membro e que continuam: sessões compartilhadas com ele
    # e fotos dele em NPCs e inimigos
    for m in banco.query(MembroTabela).filter_by(usuario_id=uid).all():
        mesa = m.mesa
        if mesa.criador_id == uid:
            continue
        for s in banco.query(SessaoTabela).filter_by(mesa_id=mesa.id):
            if uid in (s.compartilhada_com or []):
                s.compartilhada_com = [x for x in s.compartilhada_com if x != uid]
        _passar_fotos(banco, uid, mesa.id, mesa.criador_id)
    banco.delete(usuario)
    banco.commit()
