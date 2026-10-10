def url(pid, caminho):
    return f"/personagens/{pid}/sessao/{caminho}"


def test_dano_persiste(cliente, bardo_id):
    cliente.put(f"/personagens/{bardo_id}/equipamento", json={"armadura": "core_armor_leather_armor"})
    r = cliente.post(url(bardo_id, "dano"), json={"dano": 14, "usar_armadura": True}).json()
    assert r["resultado"]["gravidade"] == 3 and r["resultado"]["pv_marcados"] == 2
    f = cliente.get(f"/personagens/{bardo_id}").json()
    assert (f["pv_marcados"], f["armadura_marcada"]) == (2, 1)


def test_estresse_imposto_e_custo(cliente, bardo_id):
    f = cliente.post(url(bardo_id, "estresse/marcar"), json={"quantidade": 8}).json()
    assert (f["estresse_marcado"], f["pv_marcados"]) == (6, 2)
    r = cliente.post(url(bardo_id, "estresse/marcar"), json={"quantidade": 1, "como": "custo"})
    assert r.status_code == 422


def test_esperanca(cliente, bardo_id):
    assert cliente.post(url(bardo_id, "esperanca/ganhar"), json={"quantidade": 10}).json()["esperanca"] == 6
    assert cliente.post(url(bardo_id, "esperanca/gastar"), json={"quantidade": 4}).json()["esperanca"] == 2
    assert cliente.post(url(bardo_id, "esperanca/gastar"), json={"quantidade": 5}).status_code == 422


def test_descanso(cliente, bardo_id):
    cliente.post(url(bardo_id, "pv/marcar"), json={"quantidade": 3})
    r = cliente.post(url(bardo_id, "descanso"), json={
        "tipo": "curto", "movimentos": ["CUIDAR_FERIDAS", "PREPARAR"], "rolagens": [1, None]}).json()
    assert r["resultados"][0]["recuperado"] == 2   # 1 + tier 1
    assert r["ficha"]["pv_marcados"] == 1
    r = cliente.post(url(bardo_id, "descanso"), json={
        "tipo": "longo", "movimentos": ["CUIDAR_FERIDAS", "PREPARAR"]}).json()
    assert r["ficha"]["pv_marcados"] == 0


def test_limite_de_descansos_curtos_sobrevive_entre_requisicoes(cliente, bardo_id):
    curto = {"tipo": "curto", "movimentos": ["PREPARAR", "PREPARAR"]}
    for _ in range(3):
        assert cliente.post(url(bardo_id, "descanso"), json=curto).status_code == 200
    assert cliente.post(url(bardo_id, "descanso"), json=curto).status_code == 422


def test_impenetrable_uma_vez_por_descanso_sobrevive_entre_requisicoes(cliente, bardo_id):
    cliente.put(f"/personagens/{bardo_id}/equipamento", json={"armadura": "core_armor_dragonscale_armor"})
    cliente.post(url(bardo_id, "pv/marcar"), json={"quantidade": 4})
    primeiro = cliente.post(url(bardo_id, "dano"), json={"dano": 5, "evitar_queda": True}).json()
    assert not primeiro["resultado"]["caiu"]
    segundo = cliente.post(url(bardo_id, "dano"), json={"dano": 5, "evitar_queda": True}).json()
    assert segundo["resultado"]["caiu"]


def test_regras_da_mesa(cliente, bardo_id):
    cliente.put(f"/personagens/{bardo_id}/equipamento", json={"armadura": "core_armor_leather_armor"})
    cliente.put(url(bardo_id, "regras"), json={"dano_massivo": True})
    r = cliente.post(url(bardo_id, "dano"), json={"dano": 28}).json()
    assert r["resultado"]["gravidade"] == 4


def test_companheiro_inexistente(cliente, bardo_id):
    r = cliente.post(url(bardo_id, "companheiro/dano"), json={})
    assert r.status_code == 422 and "companheiro" in r.json()["detail"]
