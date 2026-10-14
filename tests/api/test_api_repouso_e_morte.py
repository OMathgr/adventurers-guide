"""Repouso do grupo (o mestre abre, os jogadores escolhem) e movimentos de morte pela API."""

import pytest
from dados_api import BARDO, entrar


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


def _jogador(cliente, mesa, email, nome, personagem):
    h = entrar(cliente, email, nome=nome)
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    pid = cliente.post("/personagens", json={**BARDO, "nome": personagem}, headers=h).json()["id"]
    cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=h)
    return h, pid


@pytest.fixture
def grupo(cliente, mesa):
    bia, lira = _jogador(cliente, mesa, "bia@exemplo.com", "Bia", "Lira")
    carlos, bruno = _jogador(cliente, mesa, "carlos@exemplo.com", "Carlos", "Bruno")
    sessao = cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sessão 1"}).json()
    return {"bia": bia, "lira": lira, "carlos": carlos, "bruno": bruno, "sessao": sessao}


def _url(mesa, resto=""):
    return f"/mesas/{mesa['id']}{resto}"


def _abrir(cliente, mesa, grupo, tipo="curto"):
    r = cliente.post(_url(mesa, f"/sessoes/{grupo['sessao']['id']}/repouso"), json={"tipo": tipo})
    assert r.status_code == 201, r.text
    return r.json()


def _ficha(cliente, h, pid):
    return cliente.get(f"/personagens/{pid}", headers=h).json()


def test_repouso_curto_com_aliado_e_preparar_em_grupo(cliente, mesa, grupo):
    cliente.post(_url(mesa, f"/personagens/{grupo['bruno']}/dano"), json={"dano": 1})   # Bruno: 2 PV marcados
    rep = _abrir(cliente, mesa, grupo)
    assert {p["nome"] for p in rep["participantes"]} == {"Lira", "Bruno"}
    vista = cliente.get(_url(mesa, "/repouso"), headers=grupo["bia"]).json()
    assert (vista["status"], vista["tipo"], vista["sou_responsavel"]) == ("aberto", "curto", False)

    base = _url(mesa, f"/repouso/{rep['id']}/escolhas")
    r = cliente.put(f"{base}/{grupo['lira']}", headers=grupo["bia"], json={"movimentos": [
        {"movimento": "CUIDAR_FERIDAS", "alvo": grupo["bruno"], "rolagem": 1}, {"movimento": "PREPARAR_EM_GRUPO"}]})
    assert r.status_code == 200, r.text
    # o Carlos não escolhe pela Lira; escolha inválida é recusada na hora
    assert cliente.put(f"{base}/{grupo['lira']}", headers=grupo["carlos"],
                       json={"movimentos": [{"movimento": "PREPARAR"}, {"movimento": "PREPARAR"}]}).status_code == 403
    r = cliente.put(f"{base}/{grupo['bruno']}", headers=grupo["carlos"], json={"movimentos": [
        {"movimento": "PREPARAR", "alvo": grupo["lira"]}, {"movimento": "PREPARAR"}]})
    assert r.status_code == 422
    cliente.put(f"{base}/{grupo['bruno']}", headers=grupo["carlos"], json={"movimentos": [
        {"movimento": "PREPARAR_EM_GRUPO"}, {"movimento": "ALIVIAR_ESTRESSE", "rolagem": 1}]})

    medo_antes = cliente.get(_url(mesa, f"/sessoes/{grupo['sessao']['id']}")).json()["medo"]
    fim = cliente.post(_url(mesa, f"/sessoes/{grupo['sessao']['id']}/repouso/{rep['id']}/encerrar"),
                       json={"rolagem_medo": 3}).json()
    assert (fim["status"], fim["medo_ganho"]) == ("concluido", 3)
    assert cliente.get(_url(mesa, f"/sessoes/{grupo['sessao']['id']}")).json()["medo"] == min(12, medo_antes + 3)
    bruno = _ficha(cliente, grupo["carlos"], grupo["bruno"])
    lira = _ficha(cliente, grupo["bia"], grupo["lira"])
    assert bruno["pv_marcados"] == 0                       # a Lira tratou: 1 + patamar 1 = 2
    assert (lira["esperanca"], bruno["esperanca"]) == (4, 4)   # preparar-se em grupo: +2 cada
    # o resultado fica à vista para a mesa
    assert cliente.get(_url(mesa, "/repouso"), headers=grupo["bia"]).json()["status"] == "concluido"


def test_repouso_longo_da_medo_pelo_numero_de_personagens(cliente, mesa, grupo):
    rep = _abrir(cliente, mesa, grupo, "longo")
    for h, pid in ((grupo["bia"], grupo["lira"]), (grupo["carlos"], grupo["bruno"])):
        cliente.put(_url(mesa, f"/repouso/{rep['id']}/escolhas/{pid}"), headers=h,
                    json={"movimentos": [{"movimento": "PREPARAR"}, {"movimento": "PROJETO"}]})
    fim = cliente.post(_url(mesa, f"/sessoes/{grupo['sessao']['id']}/repouso/{rep['id']}/encerrar"),
                       json={"rolagem_medo": 2}).json()
    assert fim["medo_ganho"] == 4   # 1d4 (2) + 2 personagens


def test_encerrar_sem_todos_escolherem_e_cancelar(cliente, mesa, grupo):
    rep = _abrir(cliente, mesa, grupo)
    r = cliente.post(_url(mesa, f"/sessoes/{grupo['sessao']['id']}/repouso/{rep['id']}/encerrar"), json={})
    assert r.status_code == 422 and "falta escolher" in r.json()["detail"]
    assert cliente.post(_url(mesa, f"/sessoes/{grupo['sessao']['id']}/repouso"), json={"tipo": "longo"}).status_code == 422
    assert cliente.post(_url(mesa, f"/sessoes/{grupo['sessao']['id']}/repouso/{rep['id']}/cancelar")).json()["status"] == "cancelado"
    _abrir(cliente, mesa, grupo, "longo")   # agora pode abrir outro


def test_jogador_nao_abre_repouso(cliente, mesa, grupo):
    r = cliente.post(_url(mesa, f"/sessoes/{grupo['sessao']['id']}/repouso"), json={"tipo": "curto"},
                     headers=grupo["bia"])
    assert r.status_code == 404


# --- Morte ----------------------------------------------------------------------------------------

def _derrubar(cliente, mesa, pid):
    for _ in range(3):
        cliente.post(_url(mesa, f"/personagens/{pid}/dano"), json={"dano": 20})


def test_evitar_a_morte_cicatriz_e_cura(cliente, mesa, grupo):
    _derrubar(cliente, mesa, grupo["lira"])
    f = _ficha(cliente, grupo["bia"], grupo["lira"])
    assert f["precisa_movimento_de_morte"]
    r = cliente.post(f"/personagens/{grupo['lira']}/sessao/morte", headers=grupo["bia"],
                     json={"movimento": "EVITAR_A_MORTE", "rolagem_esperanca": 1}).json()
    assert r["resultado"]["cicatriz"] and r["ficha"]["inconsciente"] and r["ficha"]["esperanca_max"] == 5
    f = cliente.put(f"/personagens/{grupo['lira']}/sessao/cicatrizes/0", headers=grupo["bia"],
                    json={"impacto": "MEDO", "descricao": "Água funda"}).json()
    assert f["cicatrizes"] == [{"impacto": "MEDO", "descricao": "Água funda"}]
    # a mestre cura a cicatriz (a critério dela)
    f = cliente.post(_url(mesa, f"/personagens/{grupo['lira']}/cicatrizes/0/curar")).json()
    assert f["esperanca_max"] == 6 and f["cicatrizes"] == []


def test_quem_morre_sai_do_repouso_e_do_medo(cliente, mesa, grupo):
    _derrubar(cliente, mesa, grupo["bruno"])
    r = cliente.post(f"/personagens/{grupo['bruno']}/sessao/morte", headers=grupo["carlos"],
                     json={"movimento": "ARRISCAR_TUDO", "rolagem_esperanca": 2, "rolagem_medo": 9}).json()
    assert r["resultado"]["morreu"] and r["ficha"]["morto"]
    m = cliente.get(_url(mesa)).json()
    assert next(p for p in m["personagens"] if p["id"] == grupo["bruno"])["morto"]
    rep = _abrir(cliente, mesa, grupo)
    assert [p["nome"] for p in rep["participantes"]] == ["Lira"]
    nova = cliente.post(_url(mesa, "/sessoes"), json={"titulo": "Sessão 2"}).json()
    assert nova["medo"] == 1   # só a Lira joga
