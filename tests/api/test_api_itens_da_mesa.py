"""Itens criados pelo mestre: biblioteca da mesa, entregar (tesouro), equipar
e vender nas lojas. O `cliente` é a Ana, que cria a mesa."""

import pytest
from dados_api import BARDO, entrar

ESPADA = {
    "tipo": "ARMA", "nome": "Lâmina do Eclipse", "descricao": "Forjada na última noite.", "tier": 1,
    "categoria": "PRIMARY_PHYSICAL", "traco": "PRESENCE", "alcance": "MELEE", "dado": "d10",
    "modificador_dano": 2, "tipo_dano": "PHYSICAL",
    "caracteristicas": [{"nome": "Sombria", "descricao": "+1 em Evasão.",
                         "modificadores": [{"alvo": "EVASAO", "valor": 1}]}],
}
TONICO = {"tipo": "CONSUMIVEL", "nome": "Tônico da Bruxa", "descricao": "Amargo.", "limpa_pv": "1d6"}


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


@pytest.fixture
def bia(cliente, mesa):
    h = entrar(cliente, "bia@exemplo.com", nome="Bia")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    return h


@pytest.fixture
def lira(cliente, mesa, bia):
    pid = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    return pid


def itens(mesa, resto=""):
    return f"/mesas/{mesa['id']}/itens{resto}"


def dar(mesa, pid):
    return f"/mesas/{mesa['id']}/personagens/{pid}/inventario/da-mesa"


def criar(cliente, mesa, item):
    r = cliente.post(itens(mesa), json=item)
    assert r.status_code == 201, r.text
    return r.json()


# --- biblioteca da mesa -----------------------------------------------------------------------

def test_criar_listar_e_editar(cliente, mesa):
    espada = criar(cliente, mesa, ESPADA)
    assert (espada["nome"], espada["dado"], espada["caracteristicas"][0]["modificadores"][0]["valor"]) == (
        "Lâmina do Eclipse", "d10", 1)
    assert [i["id"] for i in cliente.get(itens(mesa)).json()] == [espada["id"]]
    r = cliente.put(itens(mesa, f"/{espada['id']}?versao={espada['versao']}"), json={**ESPADA, "dado": "d12"})
    assert r.status_code == 200 and r.json()["dado"] == "d12"
    # salvar por cima de quem editou antes: conflito
    r = cliente.put(itens(mesa, f"/{espada['id']}?versao={espada['versao']}"), json=ESPADA)
    assert r.status_code == 409
    r = cliente.post(itens(mesa), json={**ESPADA, "dado": "d7"})
    assert r.status_code == 422 and "Dado de dano" in r.json()["detail"]


def test_biblioteca_e_so_dos_mestres(cliente, mesa, bia):
    espada = criar(cliente, mesa, ESPADA)
    assert cliente.get(itens(mesa), headers=bia).status_code == 404
    assert cliente.get(itens(mesa, f"/{espada['id']}"), headers=bia).status_code == 404
    assert cliente.post(itens(mesa), json=ESPADA, headers=bia).status_code == 404
    outra = cliente.post("/mesas", json={"nome": "Outra"}).json()
    assert cliente.get(itens(outra, f"/{espada['id']}")).status_code == 404   # de outra mesa


# --- entregar (tesouro) e equipar -----------------------------------------------------------------

def test_dar_arma_e_equipar(cliente, mesa, bia, lira):
    espada = criar(cliente, mesa, ESPADA)
    r = cliente.post(dar(mesa, lira), json={"item_id": espada["id"]})
    assert r.status_code == 200, r.text
    guardada = r.json()["armas"][0]
    assert (guardada["nome"], guardada["principal"]) == ("Lâmina do Eclipse", True)
    eq = cliente.get(f"/personagens/{lira}/equipamento", headers=bia).json()
    assert [a["nome"] for a in eq["armas_proprias"]] == ["Lâmina do Eclipse"] and eq["armaduras_proprias"] == []
    ficha = cliente.put(f"/personagens/{lira}/equipamento", json={"principal": guardada["id"]}, headers=bia).json()
    assert ficha["ataques"][0]["dano"] == "1d10+2"


def test_editar_ou_apagar_o_modelo_nao_muda_o_entregue(cliente, mesa, bia, lira):
    tonico = criar(cliente, mesa, TONICO)
    cliente.post(dar(mesa, lira), json={"item_id": tonico["id"], "quantidade": 2})
    cliente.put(itens(mesa, f"/{tonico['id']}"), json={**TONICO, "descricao": "Doce."})
    cliente.post(dar(mesa, lira), json={"item_id": tonico["id"]})
    inv = cliente.get(f"/personagens/{lira}/inventario", headers=bia).json()["itens"]
    assert sorted((i["texto"], i["quantidade"]) for i in inv) == [("Amargo.", 2), ("Doce.", 1)]
    assert all(i["efeito_automatico"] and i["dado"] == "1d6" for i in inv)
    assert cliente.delete(itens(mesa, f"/{tonico['id']}")).status_code == 204
    assert len(cliente.get(f"/personagens/{lira}/inventario", headers=bia).json()["itens"]) == 2
    assert cliente.post(dar(mesa, lira), json={"item_id": tonico["id"]}).status_code == 404


def test_item_continua_com_o_personagem_fora_da_mesa(cliente, mesa, bia, lira):
    espada = criar(cliente, mesa, ESPADA)
    arma = cliente.post(dar(mesa, lira), json={"item_id": espada["id"]}).json()["armas"][0]["id"]
    cliente.put(f"/personagens/{lira}/equipamento", json={"principal": arma}, headers=bia)
    cliente.delete(f"/mesas/{mesa['id']}/personagens/{lira}")
    ficha = cliente.get(f"/personagens/{lira}", headers=bia).json()
    assert ficha["ataques"][0]["arma"] == "Lâmina do Eclipse"


def test_dar_exige_a_permissao(cliente, mesa, bia, lira):
    espada = criar(cliente, mesa, ESPADA)
    assert cliente.post(dar(mesa, lira), json={"item_id": espada["id"]}, headers=bia).status_code == 403
    cliente.put(f"/mesas/{mesa['id']}/permissoes", json={
        "ver_fichas": True, "aplicar_dano": True, "aplicar_condicoes": True, "dar_itens": False})
    carlos = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos).json()
    carlos_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Carlos")
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})
    assert cliente.post(dar(mesa, lira), json={"item_id": espada["id"]}, headers=carlos).status_code == 403


# --- lojas ------------------------------------------------------------------------------------------

def test_loja_vende_item_da_mesa_e_acompanha_a_edicao(cliente, mesa, bia, lira):
    tonico = criar(cliente, mesa, TONICO)
    sessao = cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sessão 1"}).json()
    base = f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/lojas"
    loja = cliente.post(base, json={"nome": "Boticário"}).json()
    r = cliente.put(f"{base}/{loja['id']}", json={"nome": "Boticário", "itens": [
        {"tipo": "PROPRIO", "ref": tonico["id"], "preco": 2, "estoque": 3}]})
    assert r.status_code == 200, r.text
    item = r.json()["itens"][0]
    assert (item["nome"], item["texto"], item["proprio"]["limpa_pv"]) == ("Tônico da Bruxa", "Amargo.", "1d6")
    # editar o modelo atualiza a loja (ainda não foi vendido)
    cliente.put(itens(mesa, f"/{tonico['id']}"), json={**TONICO, "nome": "Tônico Forte"})
    loja = cliente.get(base).json()[0]
    assert loja["itens"][0]["nome"] == "Tônico Forte"
    cliente.post(f"/mesas/{mesa['id']}/personagens/{lira}/inventario/ouro", json={"punhados": 5})
    vendido = cliente.post(f"{base}/{loja['id']}/vender", json={"item_id": item["id"], "personagem_id": lira})
    assert vendido.status_code == 200, vendido.text
    assert vendido.json()["notas"] == ["Comprou 1× Tônico Forte (2 punhados)."]
    assert [i["nome"] for i in vendido.json()["inventario"]["itens"]] == ["Tônico Forte"]
    # modelo apagado: a loja continua vendendo a última versão (e salvar de novo não quebra)
    cliente.delete(itens(mesa, f"/{tonico['id']}"))
    loja = cliente.get(base).json()[0]
    r = cliente.put(f"{base}/{loja['id']}?versao={loja['versao']}", json={"nome": "Boticário", "itens": [
        {"id": item["id"], "tipo": "PROPRIO", "ref": tonico["id"], "preco": 1}]})
    assert r.status_code == 200 and r.json()["itens"][0]["nome"] == "Tônico Forte"
    r = cliente.put(f"{base}/{loja['id']}", json={"nome": "Boticário", "itens": [
        {"tipo": "PROPRIO", "ref": "nao-existe", "preco": 1}]})
    assert r.status_code == 404
