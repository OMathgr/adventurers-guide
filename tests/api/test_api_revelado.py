"""Revelar aos jogadores: encontros à mostra (vitalidade e condições, nunca os
números) e NPCs conhecidos (sem notas nem motivações)."""

import pytest
from dados_api import entrar


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


@pytest.fixture
def bia(cliente, mesa):
    h = entrar(cliente, "bia@exemplo.com", nome="Bia")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    return {"Authorization": h["Authorization"]}


def url(mesa, resto=""):
    return f"/mesas/{mesa['id']}{resto}"


@pytest.fixture
def encontro(cliente, mesa):
    s = cliente.post(url(mesa, "/sessoes"), json={"titulo": "A ponte"}).json()
    base = url(mesa, f"/sessoes/{s['id']}")
    e = cliente.post(f"{base}/encontros", json={"nome": "Emboscada na ponte"}).json()
    e = cliente.post(f"{base}/encontros/{e['id']}/combatentes",
                     json={"origem": "srd", "id": "srd_acid_burrower", "quantidade": 2}).json()
    return {"sessao": f"{base}", "base": f"{base}/encontros/{e['id']}", "dados": e}


def test_jogador_ve_so_com_encontro_a_mostra_e_sessao_em_andamento(cliente, mesa, bia, encontro):
    vazio = {"combate": [], "npcs": [], "lojas": []}
    assert cliente.get(url(mesa, "/revelado"), headers=bia).json() == vazio
    e = cliente.put(f"{encontro['base']}/visivel", json={"visivel": True}).json()
    assert e["visivel"] is True
    assert cliente.get(url(mesa, "/revelado"), headers=bia).json() == vazio     # sessão ainda planejada
    cliente.put(f"{encontro['sessao']}/status", json={"status": "em_andamento"})
    combate = cliente.get(url(mesa, "/revelado"), headers=bia).json()["combate"]
    assert [(x["nome"], x["mestre"]) for x in combate] == [("Emboscada na ponte", "Ana")]
    inimigo = combate[0]["inimigos"][0]
    # só nome, foto, vitalidade e condições: nada de PV, dano, habilidades ou Dificuldade
    assert set(inimigo) == {"id", "rotulo", "foto", "vitalidade", "condicoes"}
    assert inimigo["vitalidade"] == "vida_cheia"


def test_vitalidade_condicoes_e_inimigo_escondido(cliente, mesa, bia, encontro):
    cliente.put(f"{encontro['base']}/visivel", json={"visivel": True})
    cliente.put(f"{encontro['sessao']}/status", json={"status": "em_andamento"})
    c1, c2 = encontro["dados"]["combatentes"]
    pv = c1["adversario"]["pv"]   # 8 PV: 1/3 é 2,67; com 2 restando é vida baixa (com 3 ainda seria metade)
    cliente.put(f"{encontro['base']}/combatentes/{c1['id']}/marcas", json={"pv_marcados": pv - 2, "pf_marcados": 0})
    cliente.post(f"{encontro['base']}/combatentes/{c1['id']}/condicoes", json={"condicao": "Vulnerable"})
    e = cliente.put(f"{encontro['base']}/combatentes/{c2['id']}/escondido", json={"escondido": True}).json()
    assert [c["escondido"] for c in e["combatentes"]] == [False, True]
    inimigos = cliente.get(url(mesa, "/revelado"), headers=bia).json()["combate"][0]["inimigos"]
    assert [(i["rotulo"], i["vitalidade"], i["condicoes"]) for i in inimigos] == [
        (c1["rotulo"], "vida_baixa", ["VULNERAVEL"])]


def test_so_o_responsavel_mostra(cliente, mesa, bia, encontro):
    assert cliente.put(f"{encontro['base']}/visivel", json={"visivel": True}, headers=bia).status_code == 404


def test_npc_para_todos_aparece_so_vinculado_a_sessao_em_andamento(cliente, mesa, bia):
    npc = cliente.post(url(mesa, "/npcs"), json={"nome": "Marlowe", "descricao": "Ferreiro da vila",
                                                 "motivacoes": "Vingança", "notas": "É espião"}).json()
    assert npc["visibilidade"] == "privado"
    cliente.put(url(mesa, f"/npcs/{npc['id']}/visibilidade"), json={"visibilidade": "todos"})
    assert cliente.get(url(mesa, "/revelado"), headers=bia).json()["npcs"] == []   # sem sessão vinculada
    s = cliente.post(url(mesa, "/sessoes"), json={"titulo": "A forja"}).json()
    cliente.put(url(mesa, f"/sessoes/{s['id']}"), json={"titulo": "A forja", "npcs": [npc["id"]]})
    assert cliente.get(url(mesa, "/revelado"), headers=bia).json()["npcs"] == []   # ainda planejada
    cliente.put(url(mesa, f"/sessoes/{s['id']}/status"), json={"status": "em_andamento"})
    conhecido = [{"id": npc["id"], "nome": "Marlowe", "foto": None, "descricao": "Ferreiro da vila"}]
    assert cliente.get(url(mesa, "/revelado"), headers=bia).json()["npcs"] == conhecido
    assert cliente.get(url(mesa, f"/sessoes/{s['id']}/jogo"), headers=bia).json()["npcs"] == conhecido
    assert cliente.put(url(mesa, f"/npcs/{npc['id']}/visibilidade"), json={"visibilidade": "privado"},
                       headers=bia).status_code == 404


def test_quem_nao_e_da_mesa_nao_ve(cliente, mesa):
    estranho = entrar(cliente, "zed@exemplo.com", nome="Zed")
    assert cliente.get(url(mesa, "/revelado"), headers={"Authorization": estranho["Authorization"]}).status_code == 404
