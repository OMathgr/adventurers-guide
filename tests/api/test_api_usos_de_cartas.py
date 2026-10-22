"""Usar carta pela API: no seu personagem e num aliado da mesma sessão."""

from dados_api import BARDO, colocar_em_jogo, entrar

GUARDIAO = {
    "nome": "Bram", "classe": "core_class_guardian", "subclasse": "core_subclass_vengeance",
    "ancestralidade": "core_ancestry_faun", "comunidade": "core_community_highborne",
    "tracos": {"STRENGTH": 2, "PRESENCE": 1, "KNOWLEDGE": 1, "FINESSE": 0, "INSTINCT": 0, "AGILITY": -1},
    "experiencias": ["Ferreiro", "Soldado"],
    "cartas": ["core_domain_card_get_back_up", "core_domain_card_i_am_your_shield"],
}
PALAVRAS = "core_domain_card_inspirational_words"


def test_palavras_inspiradoras_num_aliado(cliente):
    lira = cliente.post("/personagens", json={**BARDO, "cartas": [PALAVRAS, "core_domain_card_book_of_ava"]}).json()["id"]
    jogo = colocar_em_jogo(cliente, lira)
    mesa, sessao = jogo["mesa"], jogo["sessao"]
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia)
    bram = cliente.post("/personagens", json=GUARDIAO, headers=bia).json()["id"]
    cliente.put(f"/personagens/{bram}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    base = f"/mesas/{mesa['id']}/sessoes/{sessao['id']}"
    cliente.post(f"{base}/participantes", json={"personagem_id": bram}, headers=bia)
    cliente.post(f"/personagens/{bram}/sessao/estresse/marcar", json={"quantidade": 2}, headers=bia)

    r = cliente.post(f"{base}/cartas/usar", json={"personagem_id": lira, "carta": PALAVRAS, "alvos": [bram], "opcao": "pf"})
    assert r.status_code == 200, r.text
    assert "Bram: limpou 1 PF." in r.json()["notas"]
    assert cliente.get(f"/personagens/{bram}", headers=bia).json()["estresse_marcado"] == 1   # salvo no aliado
    assert r.json()["registro"]["resultado"]["titulo"] == "Carta: Palavras Inspiradoras"
    registro = cliente.get(f"{base}/rolagens", headers=bia).json()
    assert registro[0]["resultado"]["tipo"] == "carta"   # o grupo vê no registro ao vivo

    # o aliado precisa estar jogando a sessão; e o personagem tem de ser seu
    r = cliente.post(f"{base}/cartas/usar", json={"personagem_id": lira, "carta": PALAVRAS, "alvos": ["outro"], "opcao": "pf"})
    assert r.status_code == 404
    r = cliente.post(f"{base}/cartas/usar", json={"personagem_id": bram, "carta": PALAVRAS, "opcao": "pf"})
    assert r.status_code == 404
