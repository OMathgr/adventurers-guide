"""Cartas disparadas por rolagens, pela API: o registro diz quais cartas da sua
mão a rolagem dispara, e usar com `rolagem_id` vale uma vez por rolagem."""

from dados_api import colocar_em_jogo, entrar

GUERREIRO = {
    "nome": "Kai", "classe": "core_class_warrior", "subclasse": "core_subclass_call_of_the_brave",
    "ancestralidade": "core_ancestry_faun", "comunidade": "core_community_highborne",
    "tracos": {"STRENGTH": 2, "AGILITY": 1, "INSTINCT": 1, "FINESSE": 0, "PRESENCE": 0, "KNOWLEDGE": -1},
    "experiencias": ["Soldado", "Caçador"],
    "cartas": ["core_domain_card_get_back_up", "core_domain_card_whirlwind"],
}
FEROCIDADE = "core_domain_card_ferocity"


def test_dano_oferece_a_carta_no_registro_uma_vez(cliente):
    pid = cliente.post("/personagens", json=GUERREIRO).json()["id"]
    r = cliente.post(f"/personagens/{pid}/niveis", json={
        "nivel": 2, "escolhas": [{"opcao": "PV"}, {"opcao": "ESTRESSE"}], "carta": FEROCIDADE, "nova_experiencia": "Briga"})
    assert r.status_code == 200, r.text
    cliente.put(f"/personagens/{pid}/equipamento", json={"principal": "core_weapon_broadsword"})
    mestre = entrar(cliente, "gui@exemplo.com", nome="Guilherme")
    mesa = cliente.post("/mesas", json={"nome": "Mesa"}, headers=mestre).json()
    cliente.put(f"/mesas/{mesa['id']}/nivel", json={"nivel_maximo": 2}, headers=mestre)
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}")
    jogo = colocar_em_jogo(cliente, pid, mesa=mesa, mestre=mestre)
    base = f"/mesas/{mesa['id']}/sessoes/{jogo['sessao']['id']}"
    cliente.post(f"/personagens/{pid}/sessao/esperanca/ganhar", json={"quantidade": 2})

    dano = cliente.post(f"{base}/rolagens", json={"tipo": "dano", "personagem_id": pid, "ataque": 0}).json()
    registro = cliente.get(f"{base}/rolagens", params={"personagem_id": pid}).json()
    assert FEROCIDADE in registro[0]["cartas"]
    corpo = {"personagem_id": pid, "carta": FEROCIDADE, "rolagem_id": dano["id"]}
    r = cliente.post(f"{base}/cartas/usar", json=corpo)
    assert r.status_code == 200, r.text
    registro = cliente.get(f"{base}/rolagens", params={"personagem_id": pid}).json()
    rolagem = next(x for x in registro if x["id"] == dano["id"])
    assert rolagem["cartas"] == [] and rolagem["resultado"]["cartas_usadas"] == [FEROCIDADE]
    r = cliente.post(f"{base}/cartas/usar", json=corpo)
    assert r.status_code == 422 and "já foi usada nesta rolagem" in r.json()["detail"]
