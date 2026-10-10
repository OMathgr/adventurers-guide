def test_catalogo(cliente):
    classes = cliente.get("/srd/classes").json()
    assert any(c["id"] == "core_class_bard" for c in classes)
    subs = cliente.get("/srd/classes/core_class_bard/subclasses").json()
    assert {s["id"] for s in subs} == {"core_subclass_troubadour", "core_subclass_wordsmith"}
    assert cliente.get("/srd/classes/nada/subclasses").status_code == 404
    anc = cliente.get("/srd/ancestralidades").json()
    gigante = next(a for a in anc if a["id"] == "core_ancestry_giant")
    assert [c["nome"] for c in gigante["caracteristicas"]] == ["Endurance", "Reach"]
    assert len(cliente.get("/srd/comunidades").json()) > 0


def test_armas_armaduras_e_cartas_filtradas(cliente):
    assert all(a["tier"] == 1 for a in cliente.get("/srd/armas", params={"tier": 1}).json())
    assert cliente.get("/srd/armaduras", params={"tier": 1}).json()[0]["tier"] == 1
    cartas = cliente.get("/srd/cartas", params={"dominio": "GRACE", "nivel_max": 2}).json()
    assert cartas and all(c["dominio"] == "GRACE" and c["nivel"] <= 2 for c in cartas)
