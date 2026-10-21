from dados_api import BARDO, NIVEL_2, colocar_em_jogo


def test_criar_e_ler_ficha(cliente, bardo_id):
    f = cliente.get(f"/personagens/{bardo_id}").json()
    assert (f["nome"], f["nivel"], f["evasao"], f["pv_max"]) == ("Lira", 1, 10, 5)
    assert f["tracos"]["PRESENCE"] == 2
    assert "slots_usados" not in f   # controle interno do motor não vaza


def test_criacao_invalida_vira_422(cliente):
    resposta = cliente.post("/personagens", json={**BARDO, "tracos": {**BARDO["tracos"], "STRENGTH": 2}})
    assert resposta.status_code == 422
    assert resposta.json()["tipo"] == "regra"
    assert "Distribua" in resposta.json()["detail"]


def test_json_mal_formado_tambem_e_422_mas_de_validacao(cliente):
    resposta = cliente.post("/personagens", json={"nome": "sem resto"})
    assert resposta.status_code == 422
    assert "tipo" not in resposta.json()


def test_personagem_inexistente(cliente):
    assert cliente.get("/personagens/nao-existe").status_code == 404


def test_listar(cliente, bardo_id):
    assert cliente.get("/personagens").json() == [
        {"id": bardo_id, "nome": "Lira", "nivel": 1, "classe": "core_class_bard", "mesa_id": None, "foto": None,
         "em_jogo": None}]


def test_subir_de_nivel_persiste(cliente, bardo_id):
    resposta = cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEL_2)
    assert resposta.status_code == 200, resposta.text
    f = cliente.get(f"/personagens/{bardo_id}").json()   # nova requisição: veio do banco
    assert (f["nivel"], f["evasao"], f["pv_max"], f["proficiencia"]) == (2, 11, 6, 2)
    assert cliente.get("/personagens").json()[0]["nivel"] == 2


def test_nivel_invalido_nao_salva_nada(cliente, bardo_id):
    resposta = cliente.post(f"/personagens/{bardo_id}/niveis", json={**NIVEL_2, "nova_experiencia": None})
    assert resposta.status_code == 422
    assert cliente.get(f"/personagens/{bardo_id}").json()["nivel"] == 1


def test_desfazer_nivel(cliente, bardo_id):
    cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEL_2)
    assert cliente.delete(f"/personagens/{bardo_id}/niveis/ultimo").json()["nivel"] == 1
    assert cliente.get(f"/personagens/{bardo_id}").json()["nivel"] == 1
    # refazer o nível com outras escolhas sobrescreve o que estava salvo
    outro = {**NIVEL_2, "escolhas": [{"opcao": "ESTRESSE"}, {"opcao": "PV"}]}
    cliente.post(f"/personagens/{bardo_id}/niveis", json=outro)
    f = cliente.get(f"/personagens/{bardo_id}").json()
    assert (f["evasao"], f["estresse_max"]) == (10, 7)


def test_ficha_em_nivel_passado(cliente, bardo_id):
    cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEL_2)
    assert cliente.get(f"/personagens/{bardo_id}", params={"ate_nivel": 1}).json()["nivel"] == 1


def test_linha_do_tempo_e_opcoes(cliente, bardo_id):
    tempo = cliente.get(f"/personagens/{bardo_id}/linha-do-tempo").json()
    assert len(tempo) == 10 and "Classe: Bardo" in tempo[0]["itens"]
    assert tempo[0]["quadros"] == []
    assert tempo[1]["quadros"][0]["tier"] == 2
    assert {"opcao": "PV", "limite": 2, "custo": 1, "antes": 0, "neste": 0, "riscados": 0} \
        in tempo[1]["quadros"][0]["opcoes"]
    opcoes = cliente.get(f"/personagens/{bardo_id}/opcoes").json()
    assert {"tier": 2, "opcao": "PV", "restantes": 2, "custo": 1} in opcoes


def test_opcoes_de_carta(cliente, bardo_id):
    cartas = cliente.post(f"/personagens/{bardo_id}/cartas/opcoes", json={"para": "nivel"}).json()
    ids = [c["id"] for c in cartas]
    assert "core_domain_card_tell_no_lies" in ids
    assert all(c["nivel"] <= 2 for c in cartas)


def test_equipar_persiste_e_valida(cliente, bardo_id):
    f = cliente.put(f"/personagens/{bardo_id}/equipamento",
                    json={"principal": "core_weapon_broadsword",
                          "armadura": "core_armor_leather_armor"}).json()
    assert f["ataques"][0]["arma"] == "Espada Larga" and f["pontuacao_armadura"] == 3
    assert f["ataques"][0]["arma_original"] == "Broadsword"   # nome do SRD fica junto
    assert cliente.get(f"/personagens/{bardo_id}").json()["armadura"] == "Armadura de Couro"
    ruim = cliente.put(f"/personagens/{bardo_id}/equipamento",
                       json={"principal": "core_weapon_longsword", "secundaria": "core_weapon_shortsword"})
    assert ruim.status_code == 422
    assert cliente.get(f"/personagens/{bardo_id}").json()["ataques"][0]["arma"] == "Espada Larga"
    eq = cliente.get(f"/personagens/{bardo_id}/equipamento").json()
    assert eq.pop("versao")   # versão do conteúdo, para avisar quando dois editam ao mesmo tempo
    assert (eq.pop("armas_proprias"), eq.pop("armaduras_proprias")) == ([], [])   # nenhum item do mestre
    assert eq == {"principal": "core_weapon_broadsword", "secundaria": None, "armadura": "core_armor_leather_armor",
                  "traco_principal": None, "traco_secundaria": None}   # Versatilidade: sem troca


def test_guardar_e_recuperar_carta(cliente, bardo_id):
    colocar_em_jogo(cliente, bardo_id)   # o custo de troca marca Fadiga: só conta em jogo
    carta = "core_domain_card_inspirational_words"
    f = cliente.post(f"/personagens/{bardo_id}/cartas/{carta}/guardar").json()
    assert f["cartas_cofre"] == [carta]
    f = cliente.post(f"/personagens/{bardo_id}/cartas/{carta}/recuperar", json={}).json()
    assert f["cartas_cofre"] == [] and f["estresse_marcado"] > 0   # Recall Cost
    assert cliente.get(f"/personagens/{bardo_id}").json()["estresse_marcado"] == f["estresse_marcado"]


def test_apagar(cliente, bardo_id):
    cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEL_2)
    assert cliente.delete(f"/personagens/{bardo_id}").status_code == 204
    assert cliente.get(f"/personagens/{bardo_id}").status_code == 404
    assert cliente.get("/personagens").json() == []


def test_beastbound_com_companheiro(cliente):
    ranger = {
        "nome": "Tália", "classe": "core_class_ranger", "subclasse": "core_subclass_beastbound",
        "ancestralidade": "core_ancestry_faun", "comunidade": "core_community_highborne",
        "tracos": {"AGILITY": 2, "INSTINCT": 1, "FINESSE": 1,
                   "STRENGTH": 0, "PRESENCE": 0, "KNOWLEDGE": -1},
        "experiencias": ["Caçadora", "Rastreadora"],
        "cartas": ["core_domain_card_deft_maneuvers", "core_domain_card_gifted_tracker"],
        "companheiro": {"nome": "Brasa", "experiencias": ["Farejar", "Vigiar"]},
    }
    rid = cliente.post("/personagens", json=ranger).json()["id"]
    cliente.post(f"/personagens/{rid}/niveis", json={
        "nivel": 2, "escolhas": [{"opcao": "PV"}, {"opcao": "ESTRESSE"}],
        "carta": "core_domain_card_ferocity", "nova_experiencia": "Viajante",
        "experiencia_companheiro": "Uivar",
        "treinos": [{"opcao": "FEROZ", "alvo": "DANO"}]})
    comp = cliente.get(f"/personagens/{rid}").json()["companheiro"]
    assert (comp["dado"], comp["dano"]) == ("d8", "2d8")
    assert comp["experiencias"]["Uivar"] == 2


def test_proximo_nivel(cliente, bardo_id):
    p = cliente.get(f"/personagens/{bardo_id}/proximo-nivel").json()
    assert (p["nivel"], p["nova_experiencia"], p["avancos"], p["treinos"]) == (2, True, 2, 0)
    assert {"tier": 2, "opcao": "PV", "restantes": 2, "custo": 1} in p["opcoes"]


def test_ficha_traz_habilidades_de_classe_e_subclasse(cliente, bardo_id):
    f = cliente.get(f"/personagens/{bardo_id}").json()
    assert {(h["tipo"], h["nome"]) for h in f["habilidades"]} == {
        ("esperanca", "Fazer uma Cena"), ("classe", "Inspiração"), ("fundacao", "Artista Talentoso")}


def test_cartas_extras_do_proximo_nivel(cliente, bardo_id):
    """O bardo (Trovador) não ganha carta a mais; o endpoint responde 0."""
    resposta = cliente.post(f"/personagens/{bardo_id}/cartas/extras",
                            json={"escolhas": [{"opcao": "PV"}, {"opcao": "ESTRESSE"}]})
    assert resposta.status_code == 200 and resposta.json() == 0
