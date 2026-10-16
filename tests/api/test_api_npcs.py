"""Quem vê cada NPC: dono, visibilidade (privado, mestres, todos) e o vínculo
com a sessão (api/npcs.py)."""

import pytest
from dados_api import entrar


def _auth(h):
    return {"Authorization": h["Authorization"]}


@pytest.fixture
def mesa(cliente):
    """Ana cria a mesa; Carlos é mestre; Bia é jogadora."""
    mesa = cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()
    pessoas = {}
    for email, nome in (("carlos@exemplo.com", "Carlos"), ("bia@exemplo.com", "Bia")):
        h = _auth(entrar(cliente, email, nome=nome))
        eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h).json()
        pessoas[nome] = {"h": h, "id": next(m["usuario_id"] for m in eu["membros"] if m["nome"] == nome)}
    cliente.put(f"/mesas/{mesa['id']}/membros/{pessoas['Carlos']['id']}", json={"papel": "mestre"})
    return {**mesa, "carlos": pessoas["Carlos"], "bia": pessoas["Bia"]}


def _url(mesa, resto=""):
    return f"/mesas/{mesa['id']}{resto}"


def _npc(cliente, mesa, h=None, **extra):
    corpo = {"nome": "Marlowe", "descricao": "Ferreiro", "notas": "É espião", **extra}
    r = cliente.post(_url(mesa, "/npcs"), json=corpo, headers=h or {})
    assert r.status_code == 201, r.text
    return r.json()


def _visivel(cliente, mesa, npc, visibilidade):
    r = cliente.put(_url(mesa, f"/npcs/{npc['id']}/visibilidade"), json={"visibilidade": visibilidade})
    assert r.status_code == 200, r.text


def test_novo_npc_e_privado_de_quem_criou(cliente, mesa):
    npc = _npc(cliente, mesa)
    assert (npc["visibilidade"], npc["dono"], npc["sou_dono"]) == ("privado", "Ana", True)
    carlos = mesa["carlos"]["h"]
    assert cliente.get(_url(mesa, "/npcs"), headers=carlos).json() == []
    assert cliente.get(_url(mesa, f"/npcs/{npc['id']}"), headers=carlos).status_code == 404
    assert cliente.get(_url(mesa, "/npcs"), headers=mesa["bia"]["h"]).status_code == 404   # jogador: nem a biblioteca


def test_compartilhado_com_mestres_eles_veem_e_usam_mas_nao_editam(cliente, mesa):
    npc = _npc(cliente, mesa)
    _visivel(cliente, mesa, npc, "mestres")
    carlos = mesa["carlos"]["h"]
    visto = cliente.get(_url(mesa, "/npcs"), headers=carlos).json()
    assert [(n["nome"], n["notas"], n["sou_dono"]) for n in visto] == [("Marlowe", "É espião", False)]
    url = _url(mesa, f"/npcs/{npc['id']}")
    assert cliente.put(url, json={"nome": "Outro"}, headers=carlos).status_code == 403
    assert cliente.put(f"{url}/visibilidade", json={"visibilidade": "todos"}, headers=carlos).status_code == 403
    assert cliente.delete(url, headers=carlos).status_code == 403
    # usar: vincular à sessão dele
    s = cliente.post(_url(mesa, "/sessoes"), json={"titulo": "Do Carlos"}, headers=carlos).json()
    r = cliente.put(_url(mesa, f"/sessoes/{s['id']}"), json={"titulo": "Do Carlos", "npcs": [npc["id"]]},
                    headers=carlos)
    assert r.status_code == 200 and r.json()["npcs"] == [npc["id"]]


def test_npc_privado_de_outro_nao_se_vincula_nem_entra_em_encontro(cliente, mesa):
    npc = _npc(cliente, mesa)
    carlos = mesa["carlos"]["h"]
    s = cliente.post(_url(mesa, "/sessoes"), json={"titulo": "Do Carlos"}, headers=carlos).json()
    r = cliente.put(_url(mesa, f"/sessoes/{s['id']}"), json={"titulo": "Do Carlos", "npcs": [npc["id"]]},
                    headers=carlos)
    assert r.status_code == 404
    e = cliente.post(_url(mesa, f"/sessoes/{s['id']}/encontros"), json={"nome": "Briga"}, headers=carlos).json()
    r = cliente.post(_url(mesa, f"/sessoes/{s['id']}/encontros/{e['id']}/combatentes"),
                     json={"origem": "npc", "id": npc["id"]}, headers=carlos)
    assert r.status_code == 404


def test_jogador_so_ve_o_que_e_para_todos_e_esta_vinculado(cliente, mesa):
    so_mestres = _npc(cliente, mesa, nome="Segredo")
    todos = _npc(cliente, mesa, nome="Marlowe")
    _visivel(cliente, mesa, so_mestres, "mestres")
    _visivel(cliente, mesa, todos, "todos")
    s = cliente.post(_url(mesa, "/sessoes"), json={"titulo": "A forja"}).json()
    cliente.put(_url(mesa, f"/sessoes/{s['id']}"), json={"titulo": "A forja", "npcs": [so_mestres["id"], todos["id"]]})
    cliente.put(_url(mesa, f"/sessoes/{s['id']}/status"), json={"status": "em_andamento"})
    bia = mesa["bia"]["h"]
    vista = cliente.get(_url(mesa, f"/sessoes/{s['id']}/jogo"), headers=bia).json()
    assert [n["nome"] for n in vista["npcs"]] == ["Marlowe"]
    assert set(vista["npcs"][0]) == {"id", "nome", "foto", "descricao"}   # nada de notas nem motivações
    # encerrada: continua na consulta da sessão
    cliente.put(_url(mesa, f"/sessoes/{s['id']}/status"), json={"status": "encerrada"})
    vista = cliente.get(_url(mesa, f"/sessoes/{s['id']}/jogo"), headers=bia).json()
    assert [n["nome"] for n in vista["npcs"]] == ["Marlowe"]


def test_dono_que_sai_da_mesa_passa_o_npc_para_quem_criou_a_mesa(cliente, mesa):
    carlos = mesa["carlos"]["h"]
    npc = _npc(cliente, mesa, h=carlos)
    assert cliente.get(_url(mesa, "/npcs")).json() == []   # privado do Carlos
    cliente.post(_url(mesa, "/sair"), headers=carlos)
    meu = cliente.get(_url(mesa, "/npcs")).json()
    assert [(n["id"], n["sou_dono"]) for n in meu] == [(npc["id"], True)]
