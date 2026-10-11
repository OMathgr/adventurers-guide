"""Sessão do mestre: Medo e encontros (privados dos mestres)."""

import pytest
from dados_api import entrar
from test_api_conteudo import INIMIGO


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


@pytest.fixture
def bia(cliente, mesa):
    """Jogadora da mesa."""
    h = entrar(cliente, "bia@exemplo.com", nome="Bia")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    return h


def url(mesa, resto=""):
    return f"/mesas/{mesa['id']}{resto}"


def test_medo_visivel_para_todos_e_so_mestre_muda(cliente, mesa, bia):
    assert cliente.get(url(mesa)).json()["medo"] == 0
    assert cliente.put(url(mesa, "/medo"), json={"valor": 3}).json() == {"medo": 3}
    assert cliente.post(url(mesa, "/medo"), json={"delta": 20}).json() == {"medo": 12}   # máximo
    assert cliente.post(url(mesa, "/medo"), json={"delta": -2}).json() == {"medo": 10}
    r = cliente.post(url(mesa, "/medo"), json={"delta": -11})
    assert r.status_code == 422 and r.json()["tipo"] == "regra"
    assert cliente.get(url(mesa), headers=bia).json()["medo"] == 10      # jogadora vê
    assert cliente.post(url(mesa, "/medo"), json={"delta": 1}, headers=bia).status_code == 404


def test_encontro_com_copias_do_srd_da_mesa_e_de_npc(cliente, mesa):
    inimigo = cliente.post(url(mesa, "/inimigos"), json=INIMIGO).json()
    npc = cliente.post(url(mesa, "/npcs"), json={"nome": "Marlowe", "ficha_combate": INIMIGO}).json()
    e = cliente.post(url(mesa, "/encontros"), json={"nome": "Emboscada na estrada"}).json()
    base = url(mesa, f"/encontros/{e['id']}/combatentes")
    e = cliente.post(base, json={"origem": "srd", "id": "srd_dire_wolf", "quantidade": 2}).json()
    e = cliente.post(base, json={"origem": "inimigo", "id": inimigo["id"]}).json()
    e = cliente.post(base, json={"origem": "npc", "id": npc["id"]}).json()
    rotulos = [c["rotulo"] for c in e["combatentes"]]
    # o inimigo e a ficha do NPC têm o mesmo nome: o primeiro ganha "1" quando chega o segundo
    assert rotulos[2:] == ["Cão de Guarda Sombrio 1", "Cão de Guarda Sombrio 2"]
    assert rotulos[0].endswith(" 1") and rotulos[1].endswith(" 2")
    assert e["combatentes"][0]["origem"] == "srd:srd_dire_wolf"
    resumo = cliente.get(url(mesa, "/encontros")).json()
    assert resumo == [{"id": e["id"], "nome": "Emboscada na estrada", "combatentes": 4, "derrotados": 0}]


def test_dano_marcas_e_condicoes(cliente, mesa):
    e = cliente.post(url(mesa, "/encontros"), json={"nome": "Toca"}).json()
    e = cliente.post(url(mesa, f"/encontros/{e['id']}/combatentes"),
                     json={"origem": "srd", "id": "srd_acid_burrower"}).json()
    c = e["combatentes"][0]
    base = url(mesa, f"/encontros/{e['id']}/combatentes/{c['id']}")
    r = cliente.post(f"{base}/dano", json={"dano": 16, "resistente": True}).json()
    assert r["resultado"] == {"dano": 8, "gravidade": 2, "pv_marcados": 2, "derrotado": False}
    assert r["encontro"]["combatentes"][0]["pv_marcados"] == 2
    e = cliente.put(f"{base}/marcas", json={"pv_marcados": 8, "pf_marcados": 1}).json()
    assert e["combatentes"][0]["derrotado"] is True
    assert cliente.put(f"{base}/marcas", json={"pv_marcados": 99, "pf_marcados": 0}).status_code == 422
    e = cliente.post(f"{base}/condicoes", json={"condicao": "Vulnerable"}).json()
    assert e["combatentes"][0]["condicoes"] == ["VULNERAVEL"]
    e = cliente.delete(f"{base}/condicoes/VULNERAVEL").json()
    assert e["combatentes"][0]["condicoes"] == []
    e = cliente.delete(base).json()
    assert e["combatentes"] == []


def test_privado_e_permissao_preparar(cliente, mesa, bia):
    e = cliente.post(url(mesa, "/encontros"), json={"nome": "Toca"}).json()
    assert cliente.get(url(mesa, "/encontros"), headers=bia).status_code == 404
    assert cliente.get(url(mesa, f"/encontros/{e['id']}"), headers=bia).status_code == 404
    # Bia vira mestre sem "preparar": conduz a luta, mas não monta encontros
    cliente.put(url(mesa, "/permissoes"), json={"ver_fichas": True, "aplicar_dano": True,
                                                  "aplicar_condicoes": True, "preparar": False})
    bia_id = cliente.get(url(mesa)).json()["membros"][1]["usuario_id"]
    cliente.put(url(mesa, f"/membros/{bia_id}"), json={"papel": "mestre"})
    assert cliente.post(url(mesa, "/encontros"), json={"nome": "X"}, headers=bia).status_code == 403
    e = cliente.post(url(mesa, f"/encontros/{e['id']}/combatentes"),
                     json={"origem": "srd", "id": "srd_giant_rat"}).json()
    c = e["combatentes"][0]
    r = cliente.post(url(mesa, f"/encontros/{e['id']}/combatentes/{c['id']}/dano"), json={"dano": 1}, headers=bia)
    assert r.status_code == 200 and r.json()["resultado"]["derrotado"] is True
    assert cliente.post(url(mesa, "/medo"), json={"delta": 1}, headers=bia).json() == {"medo": 1}


def test_origem_invalida(cliente, mesa):
    e = cliente.post(url(mesa, "/encontros"), json={"nome": "Toca"}).json()
    npc = cliente.post(url(mesa, "/npcs"), json={"nome": "Sem combate"}).json()
    base = url(mesa, f"/encontros/{e['id']}/combatentes")
    assert cliente.post(base, json={"origem": "npc", "id": npc["id"]}).status_code == 404
    assert cliente.post(base, json={"origem": "srd", "id": "nao_existe"}).status_code == 404
    assert cliente.post(base, json={"origem": "outra", "id": "x"}).status_code == 422
