"""Mesas: convite, papéis, permissões dos mestres e o que o mestre faz nos
personagens da mesa. O `cliente` é a Ana, que cria a mesa."""

import pytest
from dados_api import BARDO, colocar_em_jogo, entrar


@pytest.fixture
def mesa(cliente):
    resposta = cliente.post("/mesas", json={"nome": "Os Sem-Nome"})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture
def bia(cliente):
    return entrar(cliente, "bia@exemplo.com", nome="Bia")


@pytest.fixture
def carlos(cliente):
    return entrar(cliente, "carlos@exemplo.com", nome="Carlos")


@pytest.fixture
def lira_na_mesa(cliente, mesa, bia):
    """Bia entra na mesa e leva a Lira, que está jogando uma sessão da Ana."""
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia)
    pid = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    r = cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    assert r.status_code == 200, r.text
    colocar_em_jogo(cliente, pid, jogador=bia, mesa=mesa, mestre={})
    return pid


def url(mesa, pid, resto=""):
    return f"/mesas/{mesa['id']}/personagens/{pid}{resto}"


# --- Criar e entrar ------------------------------------------------------------------

def test_criar_mesa(mesa):
    assert (mesa["meu_papel"], mesa["sou_criador"]) == ("mestre", True)
    assert len(mesa["codigo_convite"]) == 8
    assert mesa["permissoes_mestres"] == {"ver_fichas": True, "aplicar_dano": True,
                                          "aplicar_condicoes": True, "preparar": True, "nivel": True,
                                          "dar_itens": True}
    assert mesa["nivel_maximo"] == 1   # mesa nova começa no nível 1
    assert [m["nome"] for m in mesa["membros"]] == ["Ana"]


def test_entrar_pelo_codigo(cliente, mesa, bia):
    r = cliente.post(f"/mesas/entrar/{mesa['codigo_convite'].lower()}", headers=bia)
    assert r.status_code == 200
    assert (r.json()["meu_papel"], r.json()["sou_criador"]) == ("jogador", False)
    assert r.json()["codigo_convite"] is None   # só os mestres veem o código
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia)   # repetir não duplica
    membros = cliente.get(f"/mesas/{mesa['id']}").json()["membros"]
    assert [(m["nome"], m["papel"]) for m in membros] == [("Ana", "mestre"), ("Bia", "jogador")]
    assert cliente.get("/mesas", headers=bia).json() == [
        {"id": mesa["id"], "nome": "Os Sem-Nome", "meu_papel": "jogador"}]


def test_codigo_invalido_e_mesa_alheia(cliente, mesa, bia):
    assert cliente.post("/mesas/entrar/XXXXXXXX", headers=bia).status_code == 404
    assert cliente.get(f"/mesas/{mesa['id']}", headers=bia).status_code == 404   # não é membro


def test_mestre_ve_o_codigo_e_jogador_nao(cliente, mesa, bia):
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia).json()
    vista = cliente.get(f"/mesas/{mesa['id']}", headers=bia).json()
    assert (vista["codigo_convite"], vista["permissoes_mestres"]) == (None, {})   # nem código, nem permissões
    bia_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Bia")
    cliente.put(f"/mesas/{mesa['id']}/membros/{bia_id}", json={"papel": "mestre"})
    assert cliente.get(f"/mesas/{mesa['id']}", headers=bia).json()["codigo_convite"] == mesa["codigo_convite"]


def test_novo_codigo_invalida_o_antigo(cliente, mesa, bia):
    novo = cliente.post(f"/mesas/{mesa['id']}/convite").json()["codigo_convite"]
    assert novo != mesa["codigo_convite"]
    assert cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia).status_code == 404
    assert cliente.post(f"/mesas/entrar/{novo}", headers=bia).status_code == 200


# --- Vincular personagem -----------------------------------------------------------------

def test_personagem_aparece_na_mesa(cliente, mesa, lira_na_mesa):
    personagens = cliente.get(f"/mesas/{mesa['id']}").json()["personagens"]
    assert [{k: p[k] for k in ("id", "nome", "nivel", "classe", "jogador", "foto")} for p in personagens] == [
        {"id": lira_na_mesa, "nome": "Lira", "nivel": 1, "classe": "core_class_bard", "jogador": "Bia", "foto": None}]


def test_personagem_fica_preso_a_mesa(cliente, mesa, bia, lira_na_mesa):
    outra = cliente.post("/mesas", json={"nome": "Outra"}, headers=bia).json()
    r = cliente.put(f"/personagens/{lira_na_mesa}/mesa", json={"mesa_id": outra["id"]}, headers=bia)
    assert r.status_code == 422 and "cópia" in r.json()["detail"]
    # não dá para simplesmente tirar da mesa
    assert cliente.put(f"/personagens/{lira_na_mesa}/mesa", json={"mesa_id": None}, headers=bia).status_code == 422


def test_so_leva_para_mesa_que_participa(cliente, mesa, bia):
    pid = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    assert cliente.put(f"/personagens/{pid}/mesa", json={"mesa_id": mesa["id"]},
                       headers=bia).status_code == 404


# --- O mestre na mesa ----------------------------------------------------------------------

def test_mestre_ve_a_ficha_e_aplica_dano_e_condicoes(cliente, mesa, bia, lira_na_mesa):
    assert cliente.get(url(mesa, lira_na_mesa)).json()["nome"] == "Lira"
    dano = cliente.post(url(mesa, lira_na_mesa, "/dano"), json={"dano": 1}).json()
    assert dano["resultado"]["pv_marcados"] == 2   # sem armadura, nível 1: limiares 1 / 2
    cliente.post(url(mesa, lira_na_mesa, "/condicoes"), json={"condicao": "Vulnerable"})
    f = cliente.get(f"/personagens/{lira_na_mesa}", headers=bia).json()   # a dona vê o efeito
    assert (f["pv_marcados"], f["condicoes"]) == (2, ["VULNERAVEL"])
    r = cliente.delete(url(mesa, lira_na_mesa, "/condicoes/vulneravel"))
    assert r.json()["condicoes"] == []


def test_mestre_nao_edita_o_resto(cliente, lira_na_mesa):
    """Pelas rotas do dono, o personagem da Bia não existe para a Ana."""
    assert cliente.get(f"/personagens/{lira_na_mesa}").status_code == 404
    assert cliente.put(f"/personagens/{lira_na_mesa}/equipamento",
                       json={"principal": "core_weapon_broadsword"}).status_code == 404


def test_personagem_fora_da_mesa(cliente, mesa, bia):
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia)
    pid = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]   # não vinculado
    assert cliente.get(url(mesa, pid)).status_code == 404


def test_jogador_nao_tem_poderes_de_mestre(cliente, mesa, carlos, lira_na_mesa):
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos)
    assert cliente.get(url(mesa, lira_na_mesa), headers=carlos).status_code == 403
    assert cliente.post(url(mesa, lira_na_mesa, "/dano"), json={"dano": 3},
                        headers=carlos).status_code == 403


def test_permissoes_valem_para_todos_os_mestres(cliente, mesa, carlos, lira_na_mesa):
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos).json()
    carlos_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Carlos")
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})
    assert cliente.post(url(mesa, lira_na_mesa, "/dano"), json={"dano": 1},
                        headers=carlos).status_code == 200
    cliente.put(f"/mesas/{mesa['id']}/permissoes",
                json={"ver_fichas": True, "aplicar_dano": False, "aplicar_condicoes": True})
    assert cliente.post(url(mesa, lira_na_mesa, "/dano"), json={"dano": 1},
                        headers=carlos).status_code == 403
    assert cliente.get(f"/mesas/{mesa['id']}", headers=carlos).json()["minhas_permissoes"] == [
        "ver_fichas", "aplicar_condicoes", "preparar", "nivel", "dar_itens"]
    # o criador continua podendo tudo
    assert cliente.post(url(mesa, lira_na_mesa, "/dano"), json={"dano": 1}).status_code == 200


def test_so_o_criador_administra(cliente, mesa, carlos):
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos).json()
    carlos_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Carlos")
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})
    m = mesa["id"]
    assert cliente.post(f"/mesas/{m}/convite", headers=carlos).status_code == 403
    assert cliente.put(f"/mesas/{m}/permissoes", headers=carlos,
                       json={"ver_fichas": False, "aplicar_dano": False,
                             "aplicar_condicoes": False}).status_code == 403
    assert cliente.put(f"/mesas/{m}", json={"nome": "X"}, headers=carlos).status_code == 403
    assert cliente.delete(f"/mesas/{m}", headers=carlos).status_code == 403


# --- Sair, remover, apagar --------------------------------------------------------------------

def test_sair_desvincula_os_personagens(cliente, mesa, bia, lira_na_mesa):
    assert cliente.post(f"/mesas/{mesa['id']}/sair", headers=bia).status_code == 204
    lira = cliente.get("/personagens", headers=bia).json()[0]
    assert (lira["mesa_id"], lira["em_jogo"]) == (None, None)   # e saiu da sessão em andamento
    assert cliente.get(f"/mesas/{mesa['id']}").json()["personagens"] == []


def test_criador_nao_sai(cliente, mesa):
    assert cliente.post(f"/mesas/{mesa['id']}/sair").status_code == 403


def test_remover_membro(cliente, mesa, bia, lira_na_mesa):
    bia_id = cliente.get("/auth/eu", headers=bia).json()["id"]
    r = cliente.delete(f"/mesas/{mesa['id']}/membros/{bia_id}").json()
    assert [m["nome"] for m in r["membros"]] == ["Ana"] and r["personagens"] == []
    assert cliente.get("/personagens", headers=bia).json()[0]["em_jogo"] is None   # saiu da sessão também
    assert cliente.get(f"/mesas/{mesa['id']}", headers=bia).status_code == 404


def test_criador_tira_um_personagem_da_mesa(cliente, mesa, bia, lira_na_mesa):
    r = cliente.delete(url(mesa, lira_na_mesa))
    assert r.status_code == 200, r.text
    assert r.json()["personagens"] == []
    assert [m["nome"] for m in r.json()["membros"]] == ["Ana", "Bia"]   # a Bia continua na mesa
    lira = cliente.get("/personagens", headers=bia).json()[0]
    assert (lira["mesa_id"], lira["em_jogo"]) == (None, None)   # e saiu da sessão em andamento
    assert cliente.get(f"/personagens/{lira_na_mesa}", headers=bia).status_code == 200   # não foi apagada
    # sem mesa, pode ir para outra (ou voltar)
    r = cliente.put(f"/personagens/{lira_na_mesa}/mesa", json={"mesa_id": mesa["id"]}, headers=bia)
    assert r.status_code == 200


def test_dono_tira_o_proprio_personagem(cliente, mesa, bia, lira_na_mesa):
    r = cliente.delete(url(mesa, lira_na_mesa), headers=bia)
    assert r.status_code == 200 and r.json()["personagens"] == []
    assert r.json()["sou_criador"] is False   # a mesa devolvida é a vista da Bia


def test_so_criador_ou_dono_tiram_o_personagem(cliente, mesa, bia, carlos, lira_na_mesa):
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos)
    assert cliente.delete(url(mesa, lira_na_mesa), headers=carlos).status_code == 403
    carlos_id = cliente.get("/auth/eu", headers=carlos).json()["id"]
    cliente.put(f"/mesas/{mesa['id']}/membros/{carlos_id}", json={"papel": "mestre"})
    assert cliente.delete(url(mesa, lira_na_mesa), headers=carlos).status_code == 403   # mestre também não
    assert len(cliente.get(f"/mesas/{mesa['id']}").json()["personagens"]) == 1


def test_tirar_personagem_de_fora_da_mesa(cliente, mesa, bia, lira_na_mesa):
    outra = cliente.post("/mesas", json={"nome": "Outra"}).json()
    assert cliente.delete(url(outra, lira_na_mesa)).status_code == 404       # não está nela
    assert cliente.delete(url(mesa, lira_na_mesa), headers=entrar(cliente, "x@exemplo.com")).status_code == 404


def test_apagar_mesa_mantem_os_personagens(cliente, mesa, bia, lira_na_mesa):
    assert cliente.delete(f"/mesas/{mesa['id']}").status_code == 204
    assert cliente.get("/personagens", headers=bia).json()[0]["mesa_id"] is None
    assert cliente.get(f"/personagens/{lira_na_mesa}", headers=bia).status_code == 200


# --- Condições pelo próprio jogador -----------------------------------------------------------

def test_jogador_marca_as_proprias_condicoes(cliente, bardo_id):
    colocar_em_jogo(cliente, bardo_id)
    f = cliente.post(f"/personagens/{bardo_id}/sessao/condicoes", json={"condicao": "Oculto"}).json()
    assert f["condicoes"] == ["OCULTO"]
    f = cliente.delete(f"/personagens/{bardo_id}/sessao/condicoes/OCULTO").json()
    assert f["condicoes"] == []


# --- Ficha simplificada (jogadores veem os personagens uns dos outros) -------------------------

def test_outro_jogador_ve_a_ficha_simplificada(cliente, mesa, lira_na_mesa, carlos):
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos)   # Carlos, jogador
    cliente.post(url(mesa, lira_na_mesa, "/dano"), json={"dano": 1})   # sem armadura no nível 1: dano Maior, 2 PV
    r = cliente.get(url(mesa, lira_na_mesa, "/resumo"), headers=carlos)
    assert r.status_code == 200, r.text
    f = r.json()
    assert (f["nome"], f["jogador"], f["nivel"], f["classe"], f["subclasse"]) == ("Lira", "Bia", 1, "Bardo", "Trovador")
    assert (f["ancestralidade"], f["comunidade"]) == ("Fauno", "Aristocrática")
    assert (f["pv_max"], f["pv_marcados"], f["esperanca"]) == (5, 2, 2)
    # só o combinado: nada de atributos, cartas, equipamento ou inventário
    assert not {"tracos", "cartas", "ataques", "experiencias", "evasao", "inventario"} & set(f)


def test_quem_nao_esta_na_mesa_nao_ve(cliente, mesa, lira_na_mesa, carlos):
    assert cliente.get(url(mesa, lira_na_mesa, "/resumo"), headers=carlos).status_code == 404


def test_personagem_de_outra_mesa_nao_aparece(cliente, mesa, bia):
    cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=bia)
    fora = cliente.post("/personagens", json=BARDO).json()["id"]   # da Ana, sem mesa
    assert cliente.get(url(mesa, fora, "/resumo"), headers=bia).status_code == 404
