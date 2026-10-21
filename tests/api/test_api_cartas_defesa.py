"""Cartas no dano recebido e no lugar do movimento de morte, pela API."""

from dados_api import colocar_em_jogo, entrar

GUARDIAO = {
    "nome": "Bram", "classe": "core_class_guardian", "subclasse": "core_subclass_vengeance",
    "ancestralidade": "core_ancestry_faun", "comunidade": "core_community_highborne",
    "tracos": {"STRENGTH": 2, "PRESENCE": 1, "KNOWLEDGE": 1, "FINESSE": 0, "INSTINCT": 0, "AGILITY": -1},
    "experiencias": ["Ferreiro", "Soldado"],
    "cartas": ["core_domain_card_get_back_up", "core_domain_card_i_am_your_shield"],
}
ESCOLHAS = {2: ["PV", "ESTRESSE"], 3: ["PV", "ESTRESSE"], 4: ["EVASAO", "EXPERIENCIAS"],
            5: ["PV", "ESTRESSE"], 6: ["PV", "ESTRESSE"]}


def subir_ate(cliente, pid, alvo, cartas):
    for n in range(2, alvo + 1):
        opcoes = cliente.post(f"/personagens/{pid}/cartas/opcoes", json={"para": "nivel"}).json()
        carta = cartas.get(n) or next(c["id"] for c in opcoes if not c["passivo"] and not c["escolha"])
        escolhas = [{"opcao": o, **({"experiencias": ["Ferreiro", "Soldado"]} if o == "EXPERIENCIAS" else {})}
                    for o in ESCOLHAS[n]]
        r = cliente.post(f"/personagens/{pid}/niveis", json={
            "nivel": n, "escolhas": escolhas, "carta": carta, "nova_experiencia": f"E{n}" if n in (2, 5) else None})
        assert r.status_code == 200, r.text


def test_mestre_aplica_dano_com_a_carta_do_jogador(cliente):
    pid = cliente.post("/personagens", json=GUARDIAO).json()["id"]
    jogo = colocar_em_jogo(cliente, pid)
    url = f"/mesas/{jogo['mesa']['id']}/personagens/{pid}/dano"
    ficha = cliente.get(f"/mesas/{jogo['mesa']['id']}/personagens/{pid}", headers=jogo["mestre"]).json()
    assert [d["carta"] for d in ficha["defesas_de_carta"]] == ["core_domain_card_get_back_up"]
    r = cliente.post(url, json={"dano": 30, "cartas": ["core_domain_card_get_back_up"]}, headers=jogo["mestre"])
    assert r.status_code == 200, r.text
    assert (r.json()["resultado"]["pv_marcados"], r.json()["ficha"]["estresse_marcado"]) == (2, 1)


def test_battle_hardened_no_lugar_do_movimento_de_morte(cliente):
    pid = cliente.post("/personagens", json=GUARDIAO).json()["id"]
    subir_ate(cliente, pid, 6, {6: "core_domain_card_battle_hardened"})
    mestre = entrar(cliente, "gui@exemplo.com", nome="Guilherme")
    mesa = cliente.post("/mesas", json={"nome": "Mesa"}, headers=mestre).json()
    cliente.put(f"/mesas/{mesa['id']}/nivel", json={"nivel_maximo": 6}, headers=mestre)
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}")
    colocar_em_jogo(cliente, pid, mesa=mesa, mestre=mestre)
    ficha = cliente.get(f"/personagens/{pid}").json()
    if "core_domain_card_battle_hardened" in ficha["cartas_cofre"]:   # mão cheia: traz para a mão
        sai = next(c for c in ficha["cartas_ativas"] if c != "core_domain_card_get_back_up")
        cliente.post(f"/personagens/{pid}/cartas/core_domain_card_battle_hardened/recuperar",
                     json={"no_lugar_de": sai, "em_descanso": True})
    cliente.post(f"/personagens/{pid}/sessao/pv/marcar", json={"quantidade": ficha["pv_max"]})
    r = cliente.post(f"/personagens/{pid}/sessao/morte/carta", json={"carta": "core_domain_card_battle_hardened"})
    assert r.status_code == 200, r.text
    assert r.json()["ficha"]["pv_marcados"] == ficha["pv_max"] - 1 and r.json()["ficha"]["alternativas_a_morte"] == []
    r = cliente.post(f"/personagens/{pid}/sessao/morte/carta", json={"carta": "core_domain_card_get_back_up"})
    assert r.status_code == 422
