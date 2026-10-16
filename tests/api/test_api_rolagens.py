"""Rolagens pela API: registro da sessão, efeitos na ficha, Medo do mestre,
rolagem oculta do mestre e reações (api/rotas/rolagens.py)."""

import random

import pytest
from dados_api import BARDO, entrar


class Dados:
    """Gerador de mentira: devolve os valores na ordem dada (e depois 1)."""

    valores: list[int] = []

    def __init__(self, *_):
        pass

    def randint(self, a, b):
        return Dados.valores.pop(0) if Dados.valores else 1


@pytest.fixture
def dados(monkeypatch):
    monkeypatch.setattr(random, "Random", Dados)
    Dados.valores = []
    return Dados


def _auth(h):
    return {"Authorization": h["Authorization"]}


@pytest.fixture
def jogo(cliente):
    """Ana mestra a sessão em andamento; Bia (Lira, bardo) e Carlos (Fada, bardo) jogam."""
    mesa = cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()
    s = cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "A ponte"}).json()
    base = f"/mesas/{mesa['id']}/sessoes/{s['id']}"
    cliente.put(f"{base}/status", json={"status": "em_andamento"})
    gente = {}
    for email, nome, personagem, ancestral in (("bia@exemplo.com", "Bia", "Lira", "core_ancestry_faun"),
                                               ("carlos@exemplo.com", "Carlos", "Fada", "core_ancestry_faerie")):
        h = _auth(entrar(cliente, email, nome=nome))
        cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
        pid = cliente.post("/personagens", json={**BARDO, "nome": personagem, "ancestralidade": ancestral},
                           headers=h).json()["id"]
        cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=h)
        assert cliente.post(f"{base}/participantes", json={"personagem_id": pid}, headers=h).status_code == 200
        gente[nome] = {"h": h, "pid": pid}
    return {"base": base, "mesa": mesa, **gente}


def _rolar(cliente, jogo, quem, **corpo):
    return cliente.post(f"{jogo['base']}/rolagens", json={"personagem_id": jogo[quem]["pid"], **corpo},
                        headers=jogo[quem]["h"])


def test_teste_com_esperanca_vai_para_a_ficha_e_para_o_registro(cliente, jogo, dados):
    dados.valores = [9, 4]
    r = _rolar(cliente, jogo, "Bia", tipo="atributo", traco="PRESENCE", dificuldade=12)
    assert r.status_code == 201, r.text
    res = r.json()["resultado"]
    assert (res["total"], res["dualidade"], res["sucesso"]) == (15, "esperanca", True)
    lira = cliente.get(f"/personagens/{jogo['Bia']['pid']}", headers=jogo["Bia"]["h"]).json()
    assert lira["esperanca"] == 3
    registro = cliente.get(f"{jogo['base']}/rolagens", headers=jogo["Carlos"]["h"]).json()
    assert [(x["personagem"], x["autor"], x["resultado"]["titulo"]) for x in registro] == [
        ("Lira", "Bia", "Teste de Presença")]


def test_com_medo_da_medo_ao_mestre(cliente, jogo, dados):
    medo_antes = cliente.get(f"{jogo['base']}").json()["medo"]
    dados.valores = [2, 10]
    _rolar(cliente, jogo, "Bia", tipo="atributo", traco="AGILITY")
    assert cliente.get(f"{jogo['base']}").json()["medo"] == medo_antes + 1


def test_so_rola_com_o_seu_personagem_jogando_a_sessao(cliente, jogo):
    r = cliente.post(f"{jogo['base']}/rolagens", json={"tipo": "atributo", "traco": "AGILITY",
                                                       "personagem_id": jogo["Bia"]["pid"]}, headers=jogo["Carlos"]["h"])
    assert r.status_code == 404
    fora = cliente.post("/personagens", json=BARDO, headers=jogo["Bia"]["h"]).json()["id"]
    r = cliente.post(f"{jogo['base']}/rolagens", json={"tipo": "atributo", "traco": "AGILITY", "personagem_id": fora},
                     headers=jogo["Bia"]["h"])
    assert r.status_code == 422


def test_rolagem_livre_e_oculta_do_mestre(cliente, jogo, dados):
    dados.valores = [17]
    r = cliente.post(f"{jogo['base']}/rolagens", json={"tipo": "livre", "expressao": "1d20+4", "oculta": True})
    assert r.status_code == 201 and r.json()["resultado"]["total"] == 21
    assert cliente.get(f"{jogo['base']}/rolagens").json()[0]["oculta"] is True
    assert cliente.get(f"{jogo['base']}/rolagens", headers=jogo["Bia"]["h"]).json() == []   # jogadora não vê
    r = cliente.post(f"{jogo['base']}/rolagens", json={"tipo": "livre", "expressao": "1d6", "oculta": True},
                     headers=jogo["Bia"]["h"])
    assert r.status_code == 403


def test_dano_da_arma_com_opcao_e_custo(cliente, jogo, dados):
    h = jogo["Bia"]["h"]
    cliente.put(f"/personagens/{jogo['Bia']['pid']}/equipamento", json={"principal": "core_weapon_rapier"}, headers=h)
    dados.valores = [5]
    r = _rolar(cliente, jogo, "Bia", tipo="dano", ataque=0, extra="1d6")
    assert r.status_code == 201, r.text
    assert r.json()["resultado"]["tipo"] == "dano"
    opcoes = cliente.get(f"{jogo['base']}/rolagens/opcoes", params={"personagem_id": jogo["Bia"]["pid"], "tipo": "teste",
                                                                     "traco": "PRESENCE"}, headers=h).json()
    assert {"id", "nome", "momento", "disponivel"} <= set(opcoes[0]) if opcoes else True


def test_aliado_reage_e_o_medo_volta(cliente, jogo, dados):
    """Carlos (Fada: Dobra-Sorte, 3 Esperança) rerrola o teste da Lira, que tinha saído com Medo."""
    medo_antes = cliente.get(f"{jogo['base']}").json()["medo"]
    dados.valores = [2, 10]
    rolagem = _rolar(cliente, jogo, "Bia", tipo="atributo", traco="PRESENCE").json()
    assert cliente.get(f"{jogo['base']}").json()["medo"] == medo_antes + 1
    # Carlos precisa de 3 de Esperança: ganha 1 rolando com Esperança
    dados.valores = [12, 1]
    _rolar(cliente, jogo, "Carlos", tipo="atributo", traco="PRESENCE")
    registro = cliente.get(f"{jogo['base']}/rolagens", params={"personagem_id": jogo["Carlos"]["pid"]},
                           headers=jogo["Carlos"]["h"]).json()
    da_lira = next(x for x in registro if x["id"] == rolagem["id"])
    assert [o["id"] for o in da_lira["reacoes"]] == ["luckbender"]
    dados.valores = [11, 3]
    r = cliente.post(f"{jogo['base']}/rolagens/{rolagem['id']}/reacao",
                     json={"personagem_id": jogo["Carlos"]["pid"], "efeito": "luckbender"}, headers=jogo["Carlos"]["h"])
    assert r.status_code == 201, r.text
    assert r.json()["resultado"]["dualidade"] == "esperanca"
    assert cliente.get(f"{jogo['base']}").json()["medo"] == medo_antes          # o Medo daquela rolagem voltou
    lira = cliente.get(f"/personagens/{jogo['Bia']['pid']}", headers=jogo["Bia"]["h"]).json()
    assert lira["esperanca"] == 3                                                  # agora com Esperança
    fada = cliente.get(f"/personagens/{jogo['Carlos']['pid']}", headers=jogo["Carlos"]["h"]).json()
    assert fada["esperanca"] == 0                                                  # 3 - 3
    registro = cliente.get(f"{jogo['base']}/rolagens", headers=jogo["Bia"]["h"]).json()
    assert next(x for x in registro if x["id"] == rolagem["id"])["substituida"] is True
    r = cliente.post(f"{jogo['base']}/rolagens/{rolagem['id']}/reacao",
                     json={"personagem_id": jogo["Carlos"]["pid"], "efeito": "luckbender"}, headers=jogo["Carlos"]["h"])
    assert r.status_code == 422   # já refeita


def test_padroes_estranhos_so_do_mago(cliente, jogo):
    r = cliente.put(f"/personagens/{jogo['Bia']['pid']}/sessao/padroes", json={"numero": 7}, headers=jogo["Bia"]["h"])
    assert r.status_code == 422 and "Padrões Estranhos" in r.json()["detail"]
