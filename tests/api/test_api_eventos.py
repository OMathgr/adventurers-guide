"""Avisos ao vivo: quem recebe o quê quando algo muda (e quem não recebe)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from dados_api import BARDO, colocar_em_jogo, entrar
from fastapi import HTTPException

from api.autenticacao import usuario_do_passe_ao_vivo
from api.eventos import central
from api.rotas import eventos as rota_eventos
from api.seguranca import criar_passe_ao_vivo


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
    colocar_em_jogo(cliente, pid, jogador=bia, mesa=mesa, mestre={})
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


def test_fluxo_exige_passe_valido(anonimo):
    assert anonimo.get("/eventos", params={"passe": "invalido"}).status_code == 401
    assert anonimo.post("/eventos/passe").status_code == 401


def test_o_login_nao_abre_o_fluxo_e_o_passe_nao_serve_de_login(cliente):
    login = cliente.headers["Authorization"].split()[1]
    assert cliente.get("/eventos", params={"passe": login}).status_code == 401
    assert cliente.get("/eventos", params={"token": login}).status_code == 422   # o jeito antigo acabou
    passe = cliente.post("/eventos/passe").json()["passe"]
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {passe}"}).status_code == 401


def test_passe_das_fotos_nao_abre_o_fluxo(cliente):
    passe = cliente.post("/imagens/passe").json()["passe"]
    assert cliente.get("/eventos", params={"passe": passe}).status_code == 401


def test_passe_vale_um_minuto(cliente):
    uid = cliente.get("/auth/eu").json()["id"]
    vencido = criar_passe_ao_vivo(uid, datetime.now(timezone.utc) - timedelta(seconds=61))
    assert cliente.get("/eventos", params={"passe": vencido}).status_code == 401


def test_troca_de_senha_derruba_o_passe_ja_emitido():
    agora = datetime.now(timezone.utc)
    passe = criar_passe_ao_vivo("u1", agora)
    def banco(desde):
        return SimpleNamespace(get=lambda _tabela, _id: SimpleNamespace(tokens_validos_desde=desde))
    assert usuario_do_passe_ao_vivo(banco(agora - timedelta(seconds=1)), passe)
    with pytest.raises(HTTPException) as erro:
        usuario_do_passe_ao_vivo(banco(agora + timedelta(seconds=1)), passe)
    assert erro.value.status_code == 401


def test_fluxo_abre_com_conectado(cliente, monkeypatch):
    monkeypatch.setattr(rota_eventos, "INTERVALO_PING", 0.05)
    monkeypatch.setattr(rota_eventos, "DURACAO_MAXIMA", 0.3)   # o cliente de teste espera o fluxo acabar
    passe = cliente.post("/eventos/passe").json()["passe"]
    with cliente.stream("GET", "/eventos", params={"passe": passe}) as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        primeira = next(linha for linha in r.iter_lines() if linha)
    assert primeira == 'data: {"tipo": "conectado"}'
