def test_catalogo(cliente):
    classes = cliente.get("/srd/classes").json()
    assert any(c["id"] == "core_class_bard" for c in classes)
    subs = cliente.get("/srd/classes/core_class_bard/subclasses").json()
    assert {s["id"] for s in subs} == {"core_subclass_troubadour", "core_subclass_wordsmith"}
    assert cliente.get("/srd/classes/nada/subclasses").status_code == 404
    anc = cliente.get("/srd/ancestralidades").json()
    gigante = next(a for a in anc if a["id"] == "core_ancestry_giant")
    assert [c["nome"] for c in gigante["caracteristicas"]] == ["Resistência", "Alcance"]
    assert [c["nome_original"] for c in gigante["caracteristicas"]] == ["Endurance", "Reach"]
    assert (gigante["nome"], gigante["nome_original"]) == ("Gigante", "Giant")
    assert len(cliente.get("/srd/comunidades").json()) > 0


def test_armas_armaduras_e_cartas_filtradas(cliente):
    assert all(a["tier"] == 1 for a in cliente.get("/srd/armas", params={"tier": 1}).json())
    assert cliente.get("/srd/armaduras", params={"tier": 1}).json()[0]["tier"] == 1
    cartas = cliente.get("/srd/cartas", params={"dominio": "GRACE", "nivel_max": 2}).json()
    assert cartas and all(c["dominio"] == "GRACE" and c["nivel"] <= 2 for c in cartas)


def test_dominios_traduzidos(cliente):
    assert cliente.get("/srd/dominios").json()["BLADE"] == "Lâmina"


def test_subclasses_trazem_as_habilidades_das_cartas(cliente):
    subs = cliente.get("/srd/classes/core_class_wizard/subclasses").json()
    conhecimento = next(s for s in subs if s["id"] == "core_subclass_school_of_knowledge")
    assert [h["nome"] for h in conhecimento["fundacao"]] == ["Promissor", "Adepto"]
    assert conhecimento["fundacao"][0]["efeito"] == "CARTA_EXTRA"
    mago = next(c for c in cliente.get("/srd/classes").json() if c["id"] == "core_class_wizard")
    assert mago["habilidade_esperanca"]["nome"] == "Não Dessa Vez"
