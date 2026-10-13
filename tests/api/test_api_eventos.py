"""Avisos ao vivo: quem recebe o quê quando algo muda (e quem não recebe)."""

import pytest
from dados_api import BARDO, entrar

from api.eventos import central
from api.rotas import eventos as rota_eventos


def _id(cliente, h):
    return cliente.get("/auth/eu", headers=h).json()["id"]


def _auth(h):
    return {"Authorization": h["Authorization"]}


@pytest.fixture
def cena(cliente):
    """Ana (mestre) com uma mesa; Bia (jogadora) com um personagem nela; Zed de fora."""
    mesa = cliente.post("/mesas", json={"nome": "M"}).json()
    bia = _auth(entrar(cliente, "bia@exemplo.com", nome="Bia"))
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia)
    pid = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    zed = _auth(entrar(cliente, "zed@exemplo.com", nome="Zed"))
    ids = {"ana": _id(cliente, {}), "bia": _id(cliente, bia), "zed": _id(cliente, zed)}
    recebidos = {nome: [] for nome in ids}
    cancelar = [central.assinar(i, recebidos[n].append) for n, i in ids.items()]
    yield {"mesa": mesa, "bia": bia, "zed": zed, "pid": pid, "ids": ids, "recebidos": recebidos}
    for c in cancelar:
        c()


def test_dano_do_mestre_avisa_a_dona_da_ficha_e_a_mesa_mas_nao_quem_e_de_fora(cliente, cena):
    cliente.post(f"/mesas/{cena['mesa']['id']}/personagens/{cena['pid']}/dano", json={"dano": 1})
    aviso = {"tipo": "personagem", "id": cena["pid"], "mesa_id": cena["mesa"]["id"]}
    assert aviso in cena["recebidos"]["bia"]
    assert aviso in cena["recebidos"]["ana"]
    assert cena["recebidos"]["zed"] == []


def test_medo_da_sessao_avisa_os_jogadores_da_mesa(cliente, cena):
    s = cliente.post(f"/mesas/{cena['mesa']['id']}/sessoes", json={"titulo": "A ponte"}).json()
    cena["recebidos"]["bia"].clear()
    cliente.post(f"/mesas/{cena['mesa']['id']}/sessoes/{s['id']}/medo", json={"delta": 1})
    assert {"tipo": "mesa", "id": cena["mesa"]["id"]} in cena["recebidos"]["bia"]
    assert cena["recebidos"]["zed"] == []


def test_aviso_nao_leva_dados(cliente, cena):
    cliente.post(f"/mesas/{cena['mesa']['id']}/npcs", json={"nome": "Segredo", "notas": "O rei é o vilão"})
    for aviso in cena["recebidos"]["bia"]:
        assert set(aviso) <= {"tipo", "id", "mesa_id"}


def test_personagem_sem_mesa_avisa_so_o_dono(cliente, cena):
    solto = cliente.post("/personagens", json=BARDO, headers=cena["zed"]).json()["id"]
    cliente.post(f"/personagens/{solto}/sessao/esperanca/gastar", json={"quantidade": 1}, headers=cena["zed"])
    assert {"tipo": "personagem", "id": solto, "mesa_id": None} in cena["recebidos"]["zed"]
    assert all(a.get("id") != solto for a in cena["recebidos"]["bia"] + cena["recebidos"]["ana"])


def test_mesa_apagada_avisa_quem_era_membro(cliente, cena):
    cena["recebidos"]["bia"].clear()
    assert cliente.delete(f"/mesas/{cena['mesa']['id']}").status_code == 204
    assert {"tipo": "mesa", "id": cena["mesa"]["id"]} in cena["recebidos"]["bia"]


def test_erro_nao_avisa(cliente, cena):
    cena["recebidos"]["ana"].clear()
    r = cliente.post(f"/mesas/{cena['mesa']['id']}/sessoes", json={"titulo": ""})   # inválido
    assert r.status_code == 422 and cena["recebidos"]["ana"] == []


def test_presenca_na_lista_de_membros(cliente, cena):
    membros = {m["nome"]: m["online"] for m in cliente.get(f"/mesas/{cena['mesa']['id']}").json()["membros"]}
    assert membros == {"Ana": True, "Bia": True}   # as duas estão "conectadas" (assinaram a central)


def test_fluxo_exige_token(anonimo):
    assert anonimo.get("/eventos", params={"token": "invalido"}).status_code == 401


def test_fluxo_abre_com_conectado(cliente, monkeypatch):
    monkeypatch.setattr(rota_eventos, "INTERVALO_PING", 0.05)
    monkeypatch.setattr(rota_eventos, "DURACAO_MAXIMA", 0.3)   # o cliente de teste espera o fluxo acabar
    token = cliente.headers["Authorization"].split()[1]
    with cliente.stream("GET", "/eventos", params={"token": token}) as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        primeira = next(linha for linha in r.iter_lines() if linha)
    assert primeira == 'data: {"tipo": "conectado"}'
