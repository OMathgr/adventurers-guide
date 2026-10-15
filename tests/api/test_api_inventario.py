"""Inventário pela API: dono, mestre com permissão "dar_itens" e lojas das sessões."""

import pytest
from dados_api import BARDO, colocar_em_jogo, entrar

POCAO = "core_consumable_minor_health_potion"


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
    """Personagem da Bia, na mesa da Ana (mestre)."""
    corpo = {**BARDO, "pocao_inicial": POCAO, "item_de_classe": "core_class_bard_item_1"}
    pid = cliente.post("/personagens", json=corpo, headers=bia).json()["id"]
    cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    return pid


@pytest.fixture
def sessao(cliente, mesa):
    return cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sessão 1"}).json()


def inv(pid):
    return f"/personagens/{pid}/inventario"


def inv_mestre(mesa, pid):
    return f"/mesas/{mesa['id']}/personagens/{pid}/inventario"


def lojas(mesa, sessao, resto=""):
    return f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/lojas{resto}"


# --- dono ---------------------------------------------------------------------------------------

def test_criacao_com_itens_iniciais(cliente, lira, bia):
    r = cliente.get(inv(lira), headers=bia).json()
    assert r["ouro"] == {"baus": 0, "bolsas": 0, "punhados": 1, "total": 1, "maximo": 199, "moedas": 0}
    nomes = {i["nome"] for i in r["itens"]}
    assert {"Tocha", "15 metros de corda", "Suprimentos básicos", "Poção de Vida Menor", "Um romance"} == nomes
    pocao = next(i for i in r["itens"] if i["id"] == POCAO)
    assert (pocao["efeito_automatico"], pocao["dado"], pocao["escolha"]) == (True, "1d4", False)


def test_personagem_sem_itens_iniciais_comeca_vazio(cliente, bardo_id):
    r = cliente.get(inv(bardo_id)).json()
    assert (r["ouro"]["total"], r["itens"], r["livres"], r["armas"]) == (0, [], [], [])


def test_ouro_itens_e_livres(cliente, bardo_id):
    assert cliente.post(inv(bardo_id) + "/ouro", json={"punhados": 23}).json()["ouro"]["bolsas"] == 2
    r = cliente.post(inv(bardo_id) + "/ouro", json={"punhados": -30})
    assert r.status_code == 422 and "Ouro insuficiente" in r.json()["detail"]
    cliente.post(inv(bardo_id) + "/itens", json={"item_id": POCAO, "quantidade": 5})
    r = cliente.post(inv(bardo_id) + "/itens", json={"item_id": POCAO})
    assert r.status_code == 422 and "No máximo 5" in r.json()["detail"]
    livre = cliente.post(inv(bardo_id) + "/livres", json={"nome": "Mapa da Cripta"}).json()["livres"][0]
    assert cliente.delete(inv(bardo_id) + f"/livres/{livre['id']}").json()["livres"] == []
    assert cliente.delete(inv(bardo_id) + f"/itens/{POCAO}?quantidade=2").json()["itens"][0]["quantidade"] == 3


def test_usar_pocao_mexe_na_ficha(cliente, bardo_id):
    colocar_em_jogo(cliente, bardo_id)
    cliente.post(f"/personagens/{bardo_id}/sessao/pv/marcar", json={"quantidade": 4})
    cliente.post(inv(bardo_id) + "/itens", json={"item_id": "core_consumable_health_potion"})
    r = cliente.post(inv(bardo_id) + "/itens/core_consumable_health_potion/usar", json={"rolagem": 3}).json()
    assert r["ficha"]["pv_marcados"] == 0 and "Limpou 4 PV." in r["notas"]
    assert r["inventario"]["itens"] == []


def test_armas_de_inventario_e_troca(cliente, bardo_id):
    colocar_em_jogo(cliente, bardo_id)   # em perigo marca 1 PF: só em jogo
    cliente.put(f"/personagens/{bardo_id}/equipamento", json={"principal": "core_weapon_rapier"})
    cliente.post(inv(bardo_id) + "/armas", json={"arma_id": "core_weapon_dagger"})
    ficha = cliente.post(inv(bardo_id) + "/armas/0/trocar", json={"em_perigo": True}).json()
    assert ficha["ataques"][0]["arma_original"] == "Dagger" and ficha["estresse_marcado"] == 1
    assert cliente.get(inv(bardo_id)).json()["armas"][0]["id"] == "core_weapon_rapier"


def test_reliquia_de_experiencia(cliente, bardo_id):
    cliente.post(inv(bardo_id) + "/itens", json={"item_id": "core_loot_honing_relic"})
    r = cliente.put(inv(bardo_id) + "/reliquia", json={"experiencia": "Inventada"})
    assert r.status_code == 422
    cliente.put(inv(bardo_id) + "/reliquia", json={"experiencia": "Diplomata"})
    assert cliente.get(f"/personagens/{bardo_id}").json()["experiencias"]["Diplomata"] == 3


def test_inventario_de_outro_usuario_nao_existe(cliente, lira):
    assert cliente.get(inv(lira)).status_code == 404   # a Ana não é dona da Lira


# --- mestre ---------------------------------------------------------------------------------------

def test_mestre_da_ouro_e_itens(cliente, mesa, lira, bia):
    cliente.post(inv_mestre(mesa, lira) + "/ouro", json={"punhados": 10})
    cliente.post(inv_mestre(mesa, lira) + "/itens", json={"item_id": "core_loot_manacles"})
    cliente.post(inv_mestre(mesa, lira) + "/livres", json={"nome": "Chave da torre"})
    r = cliente.get(inv(lira), headers=bia).json()
    assert r["ouro"]["total"] == 11
    assert any(i["id"] == "core_loot_manacles" for i in r["itens"]) and r["livres"][0]["nome"] == "Chave da torre"


def test_mestre_sem_permissao_e_jogador_nao_dao_itens(cliente, mesa, lira, bia):
    carlos = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos).json()
    carlos_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Carlos")
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})
    cliente.put(f"/mesas/{mesa['id']}/permissoes",
                json={"ver_fichas": True, "aplicar_dano": True, "aplicar_condicoes": True, "dar_itens": False})
    assert cliente.post(inv_mestre(mesa, lira) + "/ouro", json={"punhados": 5}, headers=carlos).status_code == 403
    assert cliente.post(inv_mestre(mesa, lira) + "/ouro", json={"punhados": 5}, headers=bia).status_code == 403
    assert cliente.get(inv_mestre(mesa, lira), headers=carlos).status_code == 200   # ver_fichas


# --- lojas --------------------------------------------------------------------------------------

def _loja_montada(cliente, mesa, sessao):
    loja = cliente.post(lojas(mesa, sessao), json={"nome": "Boticário"}).json()
    r = cliente.put(lojas(mesa, sessao, f"/{loja['id']}"), json={"nome": "Boticário", "visivel": True, "itens": [
        {"tipo": "ITEM", "ref": POCAO, "preco": 2, "estoque": 1},
        {"tipo": "ARMA", "ref": "core_weapon_dagger", "preco": 5},
        {"tipo": "LIVRE", "nome": "Mapa da Cripta", "descricao": "A carvão", "preco": 0},
    ]})
    assert r.status_code == 200, r.text
    return r.json()


def test_montar_loja(cliente, mesa, sessao):
    loja = _loja_montada(cliente, mesa, sessao)
    assert [i["nome"] for i in loja["itens"]] == ["Poção de Vida Menor", "Adaga", "Mapa da Cripta"]
    assert loja["itens"][1]["preco"]["punhados"] == 5 and loja["itens"][0]["texto"] == "Limpe 1d4 PV."
    r = cliente.put(lojas(mesa, sessao, f"/{loja['id']}"),
                    json={"nome": "X", "itens": [{"tipo": "ARMADURA", "ref": "nada", "preco": 1}]})
    assert r.status_code == 422


def test_vender_cobra_entrega_e_baixa_estoque(cliente, mesa, sessao, lira, bia):
    loja = _loja_montada(cliente, mesa, sessao)
    cliente.post(inv_mestre(mesa, lira) + "/ouro", json={"punhados": 9})   # 10 no total
    pocao, adaga = loja["itens"][0]["id"], loja["itens"][1]["id"]
    vendido = cliente.post(lojas(mesa, sessao, f"/{loja['id']}/vender"),
                           json={"item_id": adaga, "personagem_id": lira}).json()
    assert vendido["inventario"]["ouro"]["total"] == 5 and vendido["inventario"]["armas"][0]["id"] == "core_weapon_dagger"
    vendido = cliente.post(lojas(mesa, sessao, f"/{loja['id']}/vender"),
                           json={"item_id": pocao, "personagem_id": lira}).json()
    assert vendido["loja"]["itens"][0]["estoque"] == 0
    r = cliente.post(lojas(mesa, sessao, f"/{loja['id']}/vender"), json={"item_id": pocao, "personagem_id": lira})
    assert r.status_code == 422 and "estoque" in r.json()["detail"]
    assert cliente.get(inv(lira), headers=bia).json()["ouro"]["total"] == 3


def test_venda_sem_ouro_nao_muda_nada(cliente, mesa, sessao, lira, bia):
    loja = _loja_montada(cliente, mesa, sessao)   # Lira tem 1 punhado
    r = cliente.post(lojas(mesa, sessao, f"/{loja['id']}/vender"),
                     json={"item_id": loja["itens"][1]["id"], "personagem_id": lira})
    assert r.status_code == 422
    assert cliente.get(inv(lira), headers=bia).json()["armas"] == []
    assert cliente.get(inv(lira), headers=bia).json()["ouro"]["total"] == 1


def test_jogador_ve_loja_a_mostra_com_a_sessao_em_andamento(cliente, mesa, sessao, bia):
    _loja_montada(cliente, mesa, sessao)
    revelado = f"/mesas/{mesa['id']}/revelado"
    assert cliente.get(revelado, headers=bia).json()["lojas"] == []   # sessão ainda planejada
    cliente.put(f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/status", json={"status": "em_andamento"})
    vista = cliente.get(revelado, headers=bia).json()["lojas"]
    assert vista[0]["nome"] == "Boticário" and len(vista[0]["itens"]) == 3
    # jogador não monta nem vende
    assert cliente.get(lojas(mesa, sessao), headers=bia).status_code == 404


def test_so_o_responsavel_vende(cliente, mesa, sessao, lira):
    loja = _loja_montada(cliente, mesa, sessao)
    carlos = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos).json()
    carlos_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Carlos")
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})
    r = cliente.post(lojas(mesa, sessao, f"/{loja['id']}/vender"),
                     json={"item_id": loja["itens"][2]["id"], "personagem_id": lira}, headers=carlos)
    assert r.status_code == 404   # a sessão não foi compartilhada com ele


# --- regra opcional das moedas ----------------------------------------------------------------

def test_mesa_liga_as_moedas(cliente, mesa, lira, bia):
    r = cliente.post(inv_mestre(mesa, lira) + "/ouro", json={"moedas": 5})
    assert r.status_code == 422 and "moedas" in r.json()["detail"]
    assert cliente.put(f"/mesas/{mesa['id']}/moedas", json={"usar_moedas": True}, headers=bia).status_code == 403
    assert cliente.put(f"/mesas/{mesa['id']}/moedas", json={"usar_moedas": True}).json()["usar_moedas"] is True
    cliente.post(inv_mestre(mesa, lira) + "/ouro", json={"moedas": 15})
    r = cliente.get(inv(lira), headers=bia).json()
    assert (r["ouro"]["total"], r["ouro"]["moedas"], r["usa_moedas"], r["moedas_pela_mesa"]) == (2, 5, True, True)
    r = cliente.put(inv(lira) + "/moedas", json={"usar": False}, headers=bia)
    assert r.status_code == 422   # na mesa, quem decide é a mesa


def test_personagem_sem_mesa_liga_as_proprias_moedas(cliente, bardo_id):
    assert cliente.post(inv(bardo_id) + "/ouro", json={"moedas": 3}).status_code == 422
    assert cliente.put(inv(bardo_id) + "/moedas", json={"usar": True}).json()["usa_moedas"] is True
    r = cliente.post(inv(bardo_id) + "/ouro", json={"punhados": 1, "moedas": 3}).json()
    assert (r["ouro"]["total"], r["ouro"]["moedas"]) == (1, 3)
    r = cliente.post(inv(bardo_id) + "/ouro", json={"punhados": 0, "moedas": -5}).json()
    assert (r["ouro"]["total"], r["ouro"]["moedas"]) == (0, 8)


def test_preco_em_moedas_so_com_a_regra(cliente, mesa, sessao):
    loja = cliente.post(lojas(mesa, sessao), json={"nome": "Padaria"}).json()
    corpo = {"nome": "Padaria", "itens": [{"tipo": "LIVRE", "nome": "Pão", "preco": 0, "moedas": 3}]}
    assert cliente.put(lojas(mesa, sessao, f"/{loja['id']}"), json=corpo).status_code == 422
    cliente.put(f"/mesas/{mesa['id']}/moedas", json={"usar_moedas": True})
    r = cliente.put(lojas(mesa, sessao, f"/{loja['id']}"), json=corpo).json()
    assert r["itens"][0]["preco"]["moedas"] == 3
