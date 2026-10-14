"""Quadro da sessão (só o responsável edita) e quadro da campanha (o revelado, para todos)."""

import pytest
from dados_api import BARDO, entrar


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


@pytest.fixture
def bia(cliente, mesa):
    h = entrar(cliente, "bia@exemplo.com", nome="Bia")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    return {"Authorization": h["Authorization"]}


@pytest.fixture
def sessao(cliente, mesa):
    return cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "A ponte"}).json()


def q_url(mesa, sessao):
    return f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/quadro"


def test_quadro_comeca_vazio_e_salva(cliente, mesa, sessao):
    vazio = cliente.get(q_url(mesa, sessao)).json()
    assert vazio.pop("versao") and vazio == {"cartoes": [], "ligacoes": [], "itens": {}}
    npc = cliente.post(f"/mesas/{mesa['id']}/npcs", json={"nome": "Marlowe", "descricao": "Ferreiro"}).json()
    quadro = {
        "cartoes": [
            {"id": "a", "tipo": "nota", "x": 10, "y": 20, "titulo": "A ponte", "texto": "**Emboscada**", "cor": "perigo"},
            {"id": "b", "tipo": "item", "item_tipo": "npc", "item_id": npc["id"]},
            {"id": "c", "tipo": "item", "item_tipo": "inimigo", "item_id": "apagado"},
        ],
        "ligacoes": [{"id": "l1", "de": "a", "para": "b", "rotulo": "trai"}],
    }
    salvo = cliente.put(q_url(mesa, sessao), json=quadro).json()
    assert [c["id"] for c in salvo["cartoes"]] == ["a", "b", "c"]
    assert salvo["itens"][f"npc:{npc['id']}"]["nome"] == "Marlowe"
    assert salvo["itens"]["inimigo:apagado"] == {"nome": "(removido)", "foto": None, "descricao": "", "existe": False}
    assert cliente.get(q_url(mesa, sessao)).json()["ligacoes"][0]["rotulo"] == "trai"


def test_quadro_invalido_e_acesso(cliente, mesa, sessao, bia):
    r = cliente.put(q_url(mesa, sessao), json={"cartoes": [{"id": "a", "tipo": "nota"}],
                                                "ligacoes": [{"id": "l", "de": "a", "para": "x"}]})
    assert r.status_code == 422 and r.json()["tipo"] == "regra"
    assert cliente.get(q_url(mesa, sessao), headers=bia).status_code == 404       # jogadora
    assert cliente.put(q_url(mesa, sessao), json={"cartoes": [], "ligacoes": []}, headers=bia).status_code == 404


def test_quadro_da_campanha_junta_o_revelado(cliente, mesa, sessao, bia):
    pid = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    cliente.put(q_url(mesa, sessao), json={
        "cartoes": [
            {"id": "a", "tipo": "nota", "titulo": "Pista", "texto": "O selo é falso", "revelado": True},
            {"id": "b", "tipo": "item", "item_tipo": "personagem", "item_id": pid, "revelado": True},
            {"id": "c", "tipo": "nota", "titulo": "Segredo", "texto": "O rei é o vilão"},
        ],
        "ligacoes": [{"id": "l1", "de": "a", "para": "b"}, {"id": "l2", "de": "a", "para": "c", "rotulo": "esconde"}],
    })
    outra = cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sem nada revelado"}).json()
    cliente.put(q_url(mesa, outra), json={"cartoes": [{"id": "x", "tipo": "nota", "titulo": "Privado"}], "ligacoes": []})

    campanha = cliente.get(f"/mesas/{mesa['id']}/quadro-da-campanha", headers=bia).json()
    assert [r["titulo"] for r in campanha] == ["A ponte"]                      # só sessões com algo revelado
    regiao = campanha[0]
    assert [c["id"] for c in regiao["cartoes"]] == ["a", "b"]                 # o segredo não aparece
    assert [l["id"] for l in regiao["ligacoes"]] == ["l1"]                    # nem a seta para ele
    assert regiao["itens"] == {f"personagem:{pid}": {"nome": "Lira", "foto": None, "descricao": "", "existe": True}}


def test_quadro_da_campanha_so_para_membros(cliente, mesa):
    estranho = entrar(cliente, "zed@exemplo.com", nome="Zed")
    r = cliente.get(f"/mesas/{mesa['id']}/quadro-da-campanha", headers={"Authorization": estranho["Authorization"]})
    assert r.status_code == 404
