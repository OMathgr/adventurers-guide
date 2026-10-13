"""Sessões do mestre (responsável, compartilhamento, Medo) e os encontros dentro delas."""

import pytest
from dados_api import BARDO, entrar
from test_api_conteudo import INIMIGO


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


@pytest.fixture
def bia(cliente, mesa):
    """Jogadora da mesa."""
    h = entrar(cliente, "bia@exemplo.com", nome="Bia")
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    return h


@pytest.fixture
def carlos(cliente, mesa):
    """Outro mestre da mesa."""
    h = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h).json()
    carlos_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Carlos")
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})
    h["id"] = carlos_id
    return h


@pytest.fixture
def sessao(cliente, mesa):
    return cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sessão 1"}).json()


def url(mesa, resto=""):
    return f"/mesas/{mesa['id']}{resto}"


def s_url(mesa, sessao, resto=""):
    return url(mesa, f"/sessoes/{sessao['id']}{resto}")


def _so_auth(h):
    return {"Authorization": h["Authorization"]}


# --- Sessão ------------------------------------------------------------------------------

def test_criar_sessao_e_medo_comeca_no_numero_de_personagens(cliente, mesa, bia):
    for _ in range(3):   # três personagens na mesa
        pid = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
        cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    s = cliente.post(url(mesa, "/sessoes"), json={"titulo": "A ponte", "data": "2026-10-20"}).json()
    assert (s["medo"], s["status"], s["sou_responsavel"], s["data"]) == (3, "planejada", True, "2026-10-20")
    assert s["encontros"] == [] and s["compartilhada_com"] == []
    # a mestre também joga nesta mesa (em outra sessão): o personagem dela não conta na sessão dela
    meu = cliente.post("/personagens", json=BARDO).json()["id"]
    cliente.put(f"/personagens/{meu}/mesa", json={"mesa_id": mesa["id"]})
    assert cliente.post(url(mesa, "/sessoes"), json={"titulo": "B"}).json()["medo"] == 3   # 4 personagens − 1
    # para a Bia (dona dos outros 3), se ela mestrar uma sessão, só o da Ana conta
    bia_id = next(m["usuario_id"] for m in cliente.get(url(mesa)).json()["membros"] if m["nome"] == "Bia")
    cliente.put(url(mesa, f"/membros/{bia_id}"), json={"papel": "mestre"})
    assert cliente.post(url(mesa, "/sessoes"), json={"titulo": "C"}, headers=bia).json()["medo"] == 1


def test_dados_status_e_medo_da_sessao(cliente, mesa, sessao, bia):
    s = cliente.put(s_url(mesa, sessao), json={"titulo": "A ponte", "resumo": "Chegar à cidade",
                                               "notas": "O ferreiro é espião", "npcs": ["n1", "n1"]}).json()
    assert (s["resumo"], s["notas"], s["npcs"]) == ("Chegar à cidade", "O ferreiro é espião", ["n1"])
    assert cliente.put(s_url(mesa, sessao, "/medo"), json={"valor": 5}).json()["medo"] == 5
    assert cliente.post(s_url(mesa, sessao, "/medo"), json={"delta": 20}).json()["medo"] == 12
    assert cliente.post(s_url(mesa, sessao, "/medo"), json={"delta": -13}).status_code == 422
    # o Medo só aparece para os jogadores com a sessão em andamento (sem o título)
    assert cliente.get(url(mesa), headers=bia).json()["medo_em_jogo"] == []
    cliente.put(s_url(mesa, sessao, "/status"), json={"status": "em_andamento"})
    assert cliente.get(url(mesa), headers=bia).json()["medo_em_jogo"] == [
        {"sessao_id": sessao["id"], "mestre": "Ana", "medo": 12}]
    assert cliente.put(s_url(mesa, sessao, "/status"), json={"status": "pausada"}).status_code == 422


def test_sessao_e_privada_do_responsavel(cliente, mesa, sessao, bia, carlos):
    # jogador e outro mestre não veem
    assert cliente.get(url(mesa, "/sessoes"), headers=_so_auth(bia)).status_code == 404
    assert cliente.get(url(mesa, "/sessoes"), headers=_so_auth(carlos)).json() == []
    assert cliente.get(s_url(mesa, sessao), headers=_so_auth(carlos)).status_code == 404
    # o responsável compartilha: Carlos vê, mas não muda nem conduz
    s = cliente.put(s_url(mesa, sessao, "/compartilhar"), json={"mestres": [carlos["id"]]}).json()
    assert s["compartilhada_com"] == [carlos["id"]]
    visto = cliente.get(s_url(mesa, sessao), headers=_so_auth(carlos)).json()
    assert visto["titulo"] == "Sessão 1" and visto["sou_responsavel"] is False
    assert cliente.post(s_url(mesa, sessao, "/medo"), json={"delta": 1}, headers=_so_auth(carlos)).status_code == 403
    assert cliente.post(s_url(mesa, sessao, "/encontros"), json={"nome": "X"},
                        headers=_so_auth(carlos)).status_code == 403
    # só com mestres da mesa
    bia_id = next(m["usuario_id"] for m in cliente.get(url(mesa)).json()["membros"] if m["nome"] == "Bia")
    assert cliente.put(s_url(mesa, sessao, "/compartilhar"), json={"mestres": [bia_id]}).status_code == 422


def test_criar_sessao_exige_preparar(cliente, mesa, carlos):
    assert cliente.post(url(mesa, "/sessoes"), json={"titulo": "Do Carlos"}, headers=_so_auth(carlos)).status_code == 201
    cliente.put(url(mesa, "/permissoes"), json={"ver_fichas": True, "aplicar_dano": True,
                                                  "aplicar_condicoes": True, "preparar": False, "nivel": True})
    assert cliente.post(url(mesa, "/sessoes"), json={"titulo": "Outra"}, headers=_so_auth(carlos)).status_code == 403
    # a sessão do Carlos é dele: a criadora da mesa não vê
    assert cliente.get(url(mesa, "/sessoes")).json() == []


def test_apagar_sessao_leva_os_encontros(cliente, mesa, sessao):
    e = cliente.post(s_url(mesa, sessao, "/encontros"), json={"nome": "Emboscada na ponte"}).json()
    assert cliente.delete(s_url(mesa, sessao)).status_code == 204
    assert cliente.get(s_url(mesa, sessao, f"/encontros/{e['id']}")).status_code == 404


# --- Encontros -----------------------------------------------------------------------------

def test_encontro_com_copias_do_srd_da_mesa_e_de_npc(cliente, mesa, sessao):
    inimigo = cliente.post(url(mesa, "/inimigos"), json=INIMIGO).json()
    npc = cliente.post(url(mesa, "/npcs"), json={"nome": "Marlowe", "ficha_combate": INIMIGO}).json()
    e = cliente.post(s_url(mesa, sessao, "/encontros"), json={"nome": "Emboscada na ponte"}).json()
    base = s_url(mesa, sessao, f"/encontros/{e['id']}/combatentes")
    e = cliente.post(base, json={"origem": "srd", "id": "srd_dire_wolf", "quantidade": 2}).json()
    e = cliente.post(base, json={"origem": "inimigo", "id": inimigo["id"]}).json()
    e = cliente.post(base, json={"origem": "npc", "id": npc["id"]}).json()
    rotulos = [c["rotulo"] for c in e["combatentes"]]
    # o inimigo e a ficha do NPC têm o mesmo nome: o primeiro ganha "1" quando chega o segundo
    assert rotulos[2:] == ["Cão de Guarda Sombrio 1", "Cão de Guarda Sombrio 2"]
    assert rotulos[0].endswith(" 1") and rotulos[1].endswith(" 2")
    assert e["combatentes"][0]["origem"] == "srd:srd_dire_wolf"
    resumo = cliente.get(s_url(mesa, sessao, "/encontros")).json()
    assert resumo == [{"id": e["id"], "nome": "Emboscada na ponte", "combatentes": 4, "derrotados": 0}]
    assert cliente.get(s_url(mesa, sessao)).json()["encontros"] == resumo


def test_dano_marcas_e_condicoes(cliente, mesa, sessao):
    e = cliente.post(s_url(mesa, sessao, "/encontros"), json={"nome": "Toca"}).json()
    e = cliente.post(s_url(mesa, sessao, f"/encontros/{e['id']}/combatentes"),
                     json={"origem": "srd", "id": "srd_acid_burrower"}).json()
    c = e["combatentes"][0]
    base = s_url(mesa, sessao, f"/encontros/{e['id']}/combatentes/{c['id']}")
    r = cliente.post(f"{base}/dano", json={"dano": 16, "resistente": True}).json()
    assert r["resultado"] == {"dano": 8, "gravidade": 2, "pv_marcados": 2, "derrotado": False}
    e = cliente.put(f"{base}/marcas", json={"pv_marcados": 8, "pf_marcados": 1}).json()
    assert e["combatentes"][0]["derrotado"] is True
    assert cliente.put(f"{base}/marcas", json={"pv_marcados": 99, "pf_marcados": 0}).status_code == 422
    e = cliente.post(f"{base}/condicoes", json={"condicao": "Vulnerable"}).json()
    assert e["combatentes"][0]["condicoes"] == ["VULNERAVEL"]
    e = cliente.delete(f"{base}/condicoes/VULNERAVEL").json()
    assert e["combatentes"][0]["condicoes"] == []
    assert cliente.delete(base).json()["combatentes"] == []


def test_guia_de_batalha(cliente, mesa, sessao, bia):
    e = cliente.post(s_url(mesa, sessao, "/encontros"), json={"nome": "Toca"}).json()
    # padrão: sem personagens na mesa conta 4 PJs; mesa nova (nível 1) é patamar 1
    assert (e["guia"]["opcoes"]["pjs"], e["guia"]["opcoes"]["patamar"], e["guia"]["base"]) == (4, 1, 14)
    base = s_url(mesa, sessao, f"/encontros/{e['id']}")
    e = cliente.post(f"{base}/combatentes", json={"origem": "srd", "id": "srd_acid_burrower", "quantidade": 2}).json()
    tipo = e["combatentes"][0]["adversario"]["tipo"]
    custo = {"SOLO": 5, "BRUTAMONTES": 4, "LIDER": 3}.get(tipo, 2)
    assert e["guia"]["gasto"] == 2 * custo
    e = cliente.put(f"{base}/guia", json={"pjs": 3, "patamar": 1, "mais_dificil": True}).json()
    assert e["guia"]["base"] == 11 and e["guia"]["total"] - e["guia"]["gasto"] == e["guia"]["saldo"]
    assert cliente.get(base).json()["guia"]["opcoes"]["pjs"] == 3                     # ficou salvo
    r = cliente.put(f"{base}/guia", json={"pjs": 3, "mais_facil": True, "mais_dificil": True})
    assert r.status_code == 422 and r.json()["tipo"] == "regra"
    assert cliente.put(f"{base}/guia", json={"pjs": 3}, headers=_so_auth(bia)).status_code == 404   # jogadora


def test_encontro_de_outra_sessao(cliente, mesa, sessao):
    outra = cliente.post(url(mesa, "/sessoes"), json={"titulo": "Sessão 2"}).json()
    e = cliente.post(s_url(mesa, sessao, "/encontros"), json={"nome": "Toca"}).json()
    assert cliente.get(s_url(mesa, outra, f"/encontros/{e['id']}")).status_code == 404


def test_origem_invalida(cliente, mesa, sessao):
    e = cliente.post(s_url(mesa, sessao, "/encontros"), json={"nome": "Toca"}).json()
    npc = cliente.post(url(mesa, "/npcs"), json={"nome": "Sem combate"}).json()
    base = s_url(mesa, sessao, f"/encontros/{e['id']}/combatentes")
    assert cliente.post(base, json={"origem": "npc", "id": npc["id"]}).status_code == 404
    assert cliente.post(base, json={"origem": "srd", "id": "nao_existe"}).status_code == 404
    assert cliente.post(base, json={"origem": "outra", "id": "x"}).status_code == 422
