"""Cartas com passivo pela API: a ficha já vem com o efeito, e as que pedem
escolha recebem os benefícios na subida de nível."""

GUARDIAO = {
    "nome": "Bram", "classe": "core_class_guardian", "subclasse": "core_subclass_vengeance",
    "ancestralidade": "core_ancestry_faun", "comunidade": "core_community_highborne",
    "tracos": {"STRENGTH": 2, "PRESENCE": 1, "KNOWLEDGE": 1, "FINESSE": 0, "INSTINCT": 0, "AGILITY": -1},
    "experiencias": ["Ferreiro", "Soldado"],
    "cartas": ["core_domain_card_bare_bones", "core_domain_card_get_back_up"],
}
VITALITY = "core_domain_card_vitality"


def subir(cliente, pid, nivel, carta=None, beneficios=None):
    if carta is None:
        opcoes = cliente.post(f"/personagens/{pid}/cartas/opcoes", json={"para": "nivel"}).json()
        carta = next(c["id"] for c in opcoes if not c["passivo"] and not c["escolha"])
    escolhas = [{"opcao": "PV"}, {"opcao": "ESTRESSE"}] if nivel != 4 else [
        {"opcao": "EVASAO"}, {"opcao": "EXPERIENCIAS", "experiencias": ["Ferreiro", "Soldado"]}]
    corpo = {"nivel": nivel, "escolhas": escolhas, "carta": carta,
             "nova_experiencia": f"E{nivel}" if nivel in (2, 5, 8) else None,
             "beneficios_de_carta": beneficios or {}}
    return cliente.post(f"/personagens/{pid}/niveis", json=corpo)


def test_ficha_vem_com_o_passivo(cliente):
    pid = cliente.post("/personagens", json=GUARDIAO).json()["id"]
    f = cliente.get(f"/personagens/{pid}").json()
    assert (f["pontuacao_armadura"], f["limiar_maior"], f["limiar_grave"]) == (3 + 2, 9 + 1, 19 + 1)
    assert f["cartas_aplicadas"] == ["core_domain_card_bare_bones"]
    assert "bonus_limiares" not in f   # interno: já está somado nos limiares
    carta = next(c for c in cliente.get("/srd/cartas?dominio=VALOR").json() if c["id"] == "core_domain_card_bare_bones")
    assert (carta["passivo"]["condicao"], carta["passivo"]["efeito"]) == ("sem_armadura", "OSSOS_EXPOSTOS")


def test_vitality_pela_subida_de_nivel(cliente):
    pid = cliente.post("/personagens", json=GUARDIAO).json()["id"]
    cliente.post(f"/personagens/{pid}/cartas/core_domain_card_bare_bones/guardar")   # só os limiares sem armadura
    for nivel in (2, 3, 4):
        assert subir(cliente, pid, nivel).status_code == 200
    antes = cliente.get(f"/personagens/{pid}").json()
    r = subir(cliente, pid, 5, VITALITY)
    assert r.status_code == 422 and "Vitalidade" in r.json()["detail"]   # nome traduzido
    r = subir(cliente, pid, 5, VITALITY, {VITALITY: ["ESTRESSE", "LIMIARES"]})
    assert r.status_code == 200, r.text
    f = cliente.get(f"/personagens/{pid}").json()   # do banco: o histórico guarda a escolha
    assert f["estresse_max"] == antes["estresse_max"] + 1 + 1
    assert (f["limiar_maior"], f["limiar_grave"]) == (5 + 2, 10 + 2)
    assert VITALITY in f["cartas_cofre"]
    r = cliente.post(f"/personagens/{pid}/cartas/{VITALITY}/recuperar", json={"em_descanso": True})
    assert r.status_code == 422 and "para sempre" in r.json()["detail"]
