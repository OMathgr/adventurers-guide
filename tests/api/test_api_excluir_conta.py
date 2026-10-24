"""Excluir a conta (api/conta.py): confirma digitando o e-mail; as mesas que a
pessoa criou passam para outro mestre e as sessões que ela mestrou ficam."""

from dados_api import BARDO, entrar


def excluir(cliente, headers=None, email="ana@exemplo.com"):
    return cliente.request("DELETE", "/auth/eu", json={"email": email}, headers=headers or {})


def membros(cliente, mesa_id, headers):
    return {m["nome"]: (m["papel"], m["criador"]) for m in cliente.get(f"/mesas/{mesa_id}", headers=headers).json()["membros"]}


def test_precisa_digitar_o_proprio_email(cliente):
    r = excluir(cliente, email="outra@exemplo.com")
    assert r.status_code == 422 and "e-mail da sua conta" in r.json()["detail"]
    assert cliente.get("/auth/eu").status_code == 200   # nada foi apagado


def test_mesa_passa_para_o_mestre_mais_antigo(cliente):
    mesa = cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    carlos = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    for h in (bia, carlos):
        cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    carlos_id = cliente.get("/auth/eu", headers=carlos).json()["id"]
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})   # Carlos é mestre; Bia, jogadora
    sessao = cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sessão 1"}).json()
    lira = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    cliente.put(f"/personagens/{lira}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)

    assert excluir(cliente).status_code == 204
    assert membros(cliente, mesa["id"], carlos) == {"Bia": ("jogador", False), "Carlos": ("mestre", True)}
    # a sessão que a Ana mestrava passou para o Carlos (novo criador) e continua
    s = cliente.get(f"/mesas/{mesa['id']}/sessoes/{sessao['id']}", headers=carlos).json()
    assert s["titulo"] == "Sessão 1" and s["sou_responsavel"]
    assert cliente.get(f"/personagens/{lira}", headers=bia).json()["nome"] == "Lira"   # o da Bia continua na mesa


def test_sem_mestre_o_jogador_mais_antigo_vira_mestre(cliente):
    mesa = cliente.post("/mesas", json={"nome": "Mesa"}).json()
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    carlos = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia)
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos)
    excluir(cliente)
    assert membros(cliente, mesa["id"], bia) == {"Bia": ("mestre", True), "Carlos": ("jogador", False)}


def test_mesa_sem_mais_ninguem_e_apagada(cliente):
    mesa = cliente.post("/mesas", json={"nome": "Sozinha"}).json()
    excluir(cliente)
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    assert cliente.get(f"/mesas/{mesa['id']}", headers=bia).status_code == 404


def test_sessao_mestrada_na_mesa_de_outra_pessoa_fica_com_o_criador(cliente):
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    mesa = cliente.post("/mesas", json={"nome": "Mesa da Bia"}, headers=bia).json()
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}")
    ana_id = cliente.get("/auth/eu").json()["id"]
    cliente.put(f"/mesas/{mesa['id']}/membros/{ana_id}", json={"papel": "mestre"}, headers=bia)
    sessao = cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Da Ana"}).json()
    foto = cliente.post("/imagens", files={"arquivo": ("a.png", _PNG, "image/png")}).json()["id"]
    npc = cliente.post(f"/mesas/{mesa['id']}/npcs", json={"nome": "Velho", "foto": foto}).json()
    excluir(cliente)
    s = cliente.get(f"/mesas/{mesa['id']}/sessoes/{sessao['id']}", headers=bia).json()
    assert s["titulo"] == "Da Ana" and s["sou_responsavel"]
    # o NPC da Ana passa para a Bia, com a foto
    npcs = cliente.get(f"/mesas/{mesa['id']}/npcs", headers=bia).json()
    assert [(n["id"], n["foto"], n["sou_dono"]) for n in npcs] == [(npc["id"], foto, True)]
    assert cliente.get(f"/imagens/{foto}", headers=bia).status_code == 200


# PNG 1x1 válido
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
