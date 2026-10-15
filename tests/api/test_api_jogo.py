"""Sessão de jogo do lado dos jogadores: listar, entrar, a vista da sessão,
sair e as fichas de quem está jogando (api/rotas/jogo.py)."""

import pytest
from dados_api import BARDO, entrar


@pytest.fixture
def mesa(cliente):
    """Ana cria a mesa (mestre); Bia e Carlos são jogadores, cada um com um personagem nela."""
    mesa = cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()
    jogadores = {}
    for email, nome, personagem in (("bia@exemplo.com", "Bia", "Lira"), ("carlos@exemplo.com", "Carlos", "Bruno")):
        h = entrar(cliente, email, nome=nome)
        cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
        pid = cliente.post("/personagens", json={**BARDO, "nome": personagem}, headers=h).json()["id"]
        cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=h)
        jogadores[nome] = {"h": h, "pid": pid}
    return {**mesa, "bia": jogadores["Bia"], "carlos": jogadores["Carlos"]}


def _sessoes(mesa):
    return f"/mesas/{mesa['id']}/sessoes"


def _nova(cliente, mesa, titulo="Sessão 1", status="em_andamento"):
    s = cliente.post(_sessoes(mesa), json={"titulo": titulo}).json()
    if status != "planejada":
        cliente.put(f"{_sessoes(mesa)}/{s['id']}/status", json={"status": status})
    return s


def _entrar(cliente, mesa, sessao, quem):
    return cliente.post(f"{_sessoes(mesa)}/{sessao['id']}/participantes",
                        json={"personagem_id": quem["pid"]}, headers=quem["h"])


def test_jogador_ve_so_as_sessoes_em_andamento_e_encerradas(cliente, mesa):
    planejada = _nova(cliente, mesa, "Planejada", "planejada")
    andamento = _nova(cliente, mesa, "Hoje")
    bia = mesa["bia"]["h"]
    lista = cliente.get(_sessoes(mesa), headers=bia).json()
    assert [(s["titulo"], s["status"], s["posso_gerir"]) for s in lista] == [("Hoje", "em_andamento", False)]
    assert cliente.get(f"{_sessoes(mesa)}/{planejada['id']}/jogo", headers=bia).status_code == 404
    # o lado do mestre (planejamento, notas) continua só do mestre
    assert cliente.get(f"{_sessoes(mesa)}/{andamento['id']}", headers=bia).status_code == 404


def test_entrar_e_a_vista_da_sessao(cliente, mesa):
    s = _nova(cliente, mesa)
    r = _entrar(cliente, mesa, s, mesa["bia"])
    assert r.status_code == 200, r.text
    vista = r.json()
    assert (vista["mestre"], vista["medo"], vista["meus"]) == ("Ana", 2, [mesa["bia"]["pid"]])
    lira = vista["participantes"][0]["resumo"]
    assert (lira["nome"], lira["pv_marcados"], lira["esperanca"]) == ("Lira", 0, 2)
    assert _entrar(cliente, mesa, s, mesa["bia"]).status_code == 200   # entrar de novo não duplica
    _entrar(cliente, mesa, s, mesa["carlos"])
    vista = cliente.get(f"{_sessoes(mesa)}/{s['id']}/jogo", headers=mesa["carlos"]["h"]).json()
    assert [p["resumo"]["nome"] for p in vista["participantes"]] == ["Lira", "Bruno"]
    assert cliente.get(_sessoes(mesa)).json()[0]["participantes"] == 2
    assert cliente.get("/personagens", headers=mesa["bia"]["h"]).json()[0]["em_jogo"] == {
        "sessao_id": s["id"], "titulo": "Sessão 1"}


def test_regras_para_entrar(cliente, mesa):
    planejada = _nova(cliente, mesa, "Depois", "planejada")
    assert _entrar(cliente, mesa, planejada, mesa["bia"]).status_code == 404   # nem aparece para ela
    s = _nova(cliente, mesa)
    # personagem de outra pessoa
    r = cliente.post(f"{_sessoes(mesa)}/{s['id']}/participantes", json={"personagem_id": mesa["carlos"]["pid"]},
                     headers=mesa["bia"]["h"])
    assert r.status_code == 404
    # quem mestra a sessão não joga nela
    meu = cliente.post("/personagens", json=BARDO).json()["id"]
    cliente.put(f"/personagens/{meu}/mesa", json={"mesa_id": mesa["id"]})
    r = cliente.post(f"{_sessoes(mesa)}/{s['id']}/participantes", json={"personagem_id": meu})
    assert r.status_code == 422 and "mestra" in r.json()["detail"]
    # um personagem joga uma sessão por vez
    outra = _nova(cliente, mesa, "Outra")
    assert _entrar(cliente, mesa, s, mesa["bia"]).status_code == 200
    r = _entrar(cliente, mesa, outra, mesa["bia"])
    assert r.status_code == 422 and "outra sessão" in r.json()["detail"]


def test_sair_descarta_as_marcas_desta_sessao(cliente, mesa):
    s = _nova(cliente, mesa)
    bia = mesa["bia"]
    _entrar(cliente, mesa, s, bia)
    cliente.post(f"/personagens/{bia['pid']}/sessao/pv/marcar", json={"quantidade": 2}, headers=bia["h"])
    # Carlos não tira a Lira; a Bia (dona) tira
    url = f"{_sessoes(mesa)}/{s['id']}/participantes/{bia['pid']}"
    assert cliente.delete(url, headers=mesa["carlos"]["h"]).status_code == 403
    assert cliente.delete(url, headers=bia["h"]).json()["participantes"] == []
    assert cliente.get(f"/personagens/{bia['pid']}", headers=bia["h"]).json()["pv_marcados"] == 0


def test_ficha_completa_e_do_dono_e_do_mestre(cliente, mesa):
    s = _nova(cliente, mesa)
    _entrar(cliente, mesa, s, mesa["bia"])
    url = f"{_sessoes(mesa)}/{s['id']}/participantes/{mesa['bia']['pid']}"
    assert cliente.get(url, headers=mesa["bia"]["h"]).json()["nome"] == "Lira"
    assert cliente.get(url).status_code == 200                                  # Ana, mestre (ver_fichas)
    assert cliente.get(url, headers=mesa["carlos"]["h"]).status_code == 403     # outro jogador: só o resumo


def test_mestre_age_em_quem_esta_jogando(cliente, mesa):
    s = _nova(cliente, mesa)
    lira = mesa["bia"]["pid"]
    r = cliente.post(f"/mesas/{mesa['id']}/personagens/{lira}/dano", json={"dano": 1})
    assert r.status_code == 422   # ainda não entrou: não há marcas onde aplicar
    _entrar(cliente, mesa, s, mesa["bia"])
    assert cliente.post(f"/mesas/{mesa['id']}/personagens/{lira}/dano", json={"dano": 1}).status_code == 200
    vista = cliente.get(f"{_sessoes(mesa)}/{s['id']}/jogo", headers=mesa["carlos"]["h"]).json()
    assert vista["participantes"][0]["resumo"]["pv_marcados"] == 2


def test_revelado_e_lojas_sao_da_propria_sessao(cliente, mesa):
    hoje, outra = _nova(cliente, mesa, "Hoje"), _nova(cliente, mesa, "Outra mesa do dia")
    for s, nome in ((hoje, "Mercado"), (outra, "Feira")):
        loja = cliente.post(f"{_sessoes(mesa)}/{s['id']}/lojas", json={"nome": nome}).json()
        cliente.put(f"{_sessoes(mesa)}/{s['id']}/lojas/{loja['id']}",
                    json={"nome": nome, "visivel": True, "itens": []})
    vista = cliente.get(f"{_sessoes(mesa)}/{hoje['id']}/jogo", headers=mesa["bia"]["h"]).json()
    assert [l["nome"] for l in vista["lojas"]] == ["Mercado"]
    cliente.put(f"{_sessoes(mesa)}/{hoje['id']}/status", json={"status": "encerrada"})
    vista = cliente.get(f"{_sessoes(mesa)}/{hoje['id']}/jogo", headers=mesa["bia"]["h"]).json()
    assert vista["status"] == "encerrada" and vista["lojas"] == []


def test_reabrir_sessao_com_personagem_jogando_outra(cliente, mesa):
    primeira = _nova(cliente, mesa, "Primeira")
    _entrar(cliente, mesa, primeira, mesa["bia"])
    cliente.put(f"{_sessoes(mesa)}/{primeira['id']}/status", json={"status": "encerrada"})
    segunda = _nova(cliente, mesa, "Segunda")
    _entrar(cliente, mesa, segunda, mesa["bia"])
    r = cliente.put(f"{_sessoes(mesa)}/{primeira['id']}/status", json={"status": "em_andamento"})
    assert r.status_code == 422 and "Lira" in r.json()["detail"]


def test_fora_de_jogo_nao_se_paga_fadiga_nem_se_usa_pocao(cliente, mesa):
    bia = mesa["bia"]
    base = f"/personagens/{bia['pid']}"
    cliente.post(f"{base}/inventario/itens", json={"item_id": "core_consumable_health_potion"}, headers=bia["h"])
    r = cliente.post(f"{base}/inventario/itens/core_consumable_health_potion/usar", json={}, headers=bia["h"])
    assert r.status_code == 422
    carta = "core_domain_card_inspirational_words"
    cliente.post(f"{base}/cartas/{carta}/guardar", headers=bia["h"])
    assert cliente.post(f"{base}/cartas/{carta}/recuperar", json={}, headers=bia["h"]).status_code == 422
    # no descanso (sem custo) pode
    assert cliente.post(f"{base}/cartas/{carta}/recuperar", json={"em_descanso": True},
                        headers=bia["h"]).status_code == 200
