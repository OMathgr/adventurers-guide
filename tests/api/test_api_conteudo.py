"""Inimigos e NPCs da mesa: privados dos mestres."""

import pytest
from dados_api import entrar


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


@pytest.fixture
def bia(cliente, mesa):
    h = entrar(cliente, "bia@exemplo.com", nome="Bia")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    return h


def url(mesa, resto=""):
    return f"/mesas/{mesa['id']}{resto}"


INIMIGO = {
    "nome": "Cão de Guarda Sombrio", "patamar": 1, "tipo": "PADRAO", "dificuldade": 12,
    "limiar_maior": 6, "limiar_grave": 11, "pv": 4, "pf": 2, "ataque": "+1", "arma": "Mordida",
    "alcance": "MELEE", "dano": "1d8+2", "tipo_dano": "PHYSICAL",
    "descricao": "Um cão magro de olhos vermelhos.", "motivacoes": "Cercar, morder, uivar",
    "experiencias": {"Faro": 2},
    "habilidades": [{"nome": "Matilha", "tipo": "PASSIVA", "texto": "+1 no ataque se outro cão estiver perto."}],
}


def test_catalogo_do_srd(anonimo):
    todos = anonimo.get("/srd/adversarios").json()
    assert len(todos) == 129
    solos = anonimo.get("/srd/adversarios", params={"patamar": 1, "tipo": "SOLO"}).json()
    assert solos and all(a["patamar"] == 1 and a["tipo"] == "SOLO" for a in solos)
    assert anonimo.get("/srd/adversarios/srd_acid_burrower").json()["dificuldade"] == 14
    assert anonimo.get("/srd/adversarios/nao_existe").status_code == 404


def test_criar_editar_e_apagar_inimigo(cliente, mesa):
    criado = cliente.post(url(mesa, "/inimigos"), json=INIMIGO)
    assert criado.status_code == 201, criado.text
    iid = criado.json()["id"]
    assert cliente.get(url(mesa, "/inimigos")).json() == [
        {"id": iid, "nome": "Cão de Guarda Sombrio", "patamar": 1, "tipo": "PADRAO", "base_id": None}]
    editado = cliente.put(url(mesa, f"/inimigos/{iid}"), json={**INIMIGO, "pv": 6}).json()
    assert editado["pv"] == 6
    assert cliente.delete(url(mesa, f"/inimigos/{iid}")).status_code == 204
    assert cliente.get(url(mesa, "/inimigos")).json() == []


def test_inimigo_invalido_vira_erro_de_regra(cliente, mesa):
    r = cliente.post(url(mesa, "/inimigos"), json={**INIMIGO, "limiar_grave": 3})
    assert r.status_code == 422 and r.json()["tipo"] == "regra"


def test_copiar_do_srd_e_ajustar(cliente, mesa):
    copia = cliente.post(url(mesa, "/inimigos/do-srd/srd_acid_burrower")).json()
    assert copia["base_id"] == "srd_acid_burrower" and copia["id"] != "srd_acid_burrower"
    ajustada = cliente.put(url(mesa, f"/inimigos/{copia['id']}"), json={**copia, "pv": 12}).json()
    assert ajustada["pv"] == 12 and ajustada["base_id"] == "srd_acid_burrower"
    # o adversário do SRD continua igual
    assert cliente.get("/srd/adversarios/srd_acid_burrower").json()["pv"] == 8


def test_npc_simples_e_com_ficha_de_combate(cliente, mesa):
    npc = cliente.post(url(mesa, "/npcs"), json={
        "nome": "Mestra Ilsa", "descricao": "Taverneira de Vila Alta.",
        "motivacoes": "Proteger a vila", "notas": "Sabe do culto."}).json()
    assert npc["ficha_combate"] is None
    com_ficha = cliente.put(url(mesa, f"/npcs/{npc['id']}"), json={
        "nome": "Mestra Ilsa", "ficha_combate": {**INIMIGO, "nome": ""}}).json()
    assert com_ficha["ficha_combate"]["nome"] == "Mestra Ilsa"   # sem nome, usa o do NPC
    assert [n["nome"] for n in cliente.get(url(mesa, "/npcs")).json()] == ["Mestra Ilsa"]
    ruim = cliente.put(url(mesa, f"/npcs/{npc['id']}"), json={
        "nome": "Mestra Ilsa", "ficha_combate": {**INIMIGO, "pv": 0}})
    assert ruim.status_code == 422


def test_jogador_nao_ve_conteudo_do_mestre(cliente, mesa, bia):
    cliente.post(url(mesa, "/inimigos"), json=INIMIGO)
    assert cliente.get(url(mesa, "/inimigos"), headers=bia).status_code == 404
    assert cliente.get(url(mesa, "/npcs"), headers=bia).status_code == 404
    assert cliente.post(url(mesa, "/inimigos"), json=INIMIGO, headers=bia).status_code == 404


def test_mestre_sem_permissao_de_preparar_so_ve(cliente, mesa, bia):
    bia_id = cliente.get("/auth/eu", headers=bia).json()["id"]
    cliente.put(url(mesa, f"/membros/{bia_id}"), json={"papel": "mestre"})
    cliente.put(url(mesa, "/permissoes"), json={"ver_fichas": True, "aplicar_dano": True,
                                                "aplicar_condicoes": True, "preparar": False})
    assert cliente.get(url(mesa, "/inimigos"), headers=bia).status_code == 200
    assert cliente.post(url(mesa, "/inimigos"), json=INIMIGO, headers=bia).status_code == 403


def test_inimigos_de_outra_mesa(cliente, mesa):
    outra = cliente.post("/mesas", json={"nome": "Outra"}).json()
    iid = cliente.post(url(mesa, "/inimigos"), json=INIMIGO).json()["id"]
    assert cliente.get(f"/mesas/{outra['id']}/inimigos/{iid}").status_code == 404


def test_apagar_mesa_leva_inimigos_e_npcs_junto(cliente, mesa):
    from api.db import sessao_do_banco
    from api.main import app
    from api.tabelas import InimigoTabela, NpcTabela

    cliente.post(url(mesa, "/inimigos"), json=INIMIGO)
    cliente.post(url(mesa, "/npcs"), json={"nome": "Marlowe", "ficha_combate": INIMIGO})
    assert cliente.delete(url(mesa)).status_code == 204
    banco = next(app.dependency_overrides[sessao_do_banco]())
    assert banco.query(InimigoTabela).count() == 0
    assert banco.query(NpcTabela).count() == 0
