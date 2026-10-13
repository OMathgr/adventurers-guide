"""Nível máximo da mesa, cópia para outra mesa e plano de níveis futuros."""

import pytest
from dados_api import BARDO, entrar

NIVEIS = {
    2: {"nivel": 2, "escolhas": [{"opcao": "EVASAO"}, {"opcao": "PV"}],
        "carta": "core_domain_card_tell_no_lies", "nova_experiencia": "Ladino de palco"},
    3: {"nivel": 3, "escolhas": [{"opcao": "ESTRESSE"}, {"opcao": "PV"}],
        "carta": "core_domain_card_troublemaker"},
}


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


def url(mesa, resto=""):
    return f"/mesas/{mesa['id']}{resto}"


def test_mestre_define_o_nivel_e_ele_trava_o_subir(cliente, mesa, bardo_id):
    assert cliente.put(f"/personagens/{bardo_id}/mesa", json={"mesa_id": mesa["id"]}).status_code == 200
    r = cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEIS[2])
    assert r.status_code == 422 and "nível 1" in r.json()["detail"]
    proximo = cliente.get(f"/personagens/{bardo_id}/proximo-nivel").json()
    assert (proximo["limite_mesa"], proximo["bloqueado_pela_mesa"]) == (1, True)
    assert cliente.put(url(mesa, "/nivel"), json={"nivel_maximo": 2}).json()["nivel_maximo"] == 2
    assert cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEIS[2]).status_code == 200
    assert cliente.put(url(mesa, "/nivel"), json={"nivel_maximo": 11}).status_code == 422


def test_permissao_de_nivel(cliente, mesa):
    carlos = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    eu = cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=carlos).json()
    assert cliente.put(url(mesa, "/nivel"), json={"nivel_maximo": 3}, headers=carlos).status_code == 403   # jogador
    carlos_id = next(m["usuario_id"] for m in eu["membros"] if m["nome"] == "Carlos")
    cliente.put(url(mesa, f"/membros/{carlos_id}"), json={"papel": "mestre"})
    assert cliente.put(url(mesa, "/nivel"), json={"nivel_maximo": 3}, headers=carlos).status_code == 200
    cliente.put(url(mesa, "/permissoes"), json={"ver_fichas": True, "aplicar_dano": True,
                                                  "aplicar_condicoes": True, "preparar": True, "nivel": False})
    assert cliente.put(url(mesa, "/nivel"), json={"nivel_maximo": 4}, headers=carlos).status_code == 403


def test_nivel_acima_do_da_mesa_so_entra_por_copia(cliente, mesa, bardo_id):
    for n in (2, 3):
        cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEIS[n])
    r = cliente.put(f"/personagens/{bardo_id}/mesa", json={"mesa_id": mesa["id"]})
    assert r.status_code == 422 and "cópia" in r.json()["detail"]

    cliente.put(url(mesa, "/nivel"), json={"nivel_maximo": 2})
    copia = cliente.post(f"/personagens/{bardo_id}/copia", json={"mesa_id": mesa["id"]})
    assert copia.status_code == 201, copia.text
    cid = copia.json()["id"]
    assert copia.json()["ficha"]["nivel"] == 2
    assert cliente.get(f"/personagens/{bardo_id}").json()["nivel"] == 3          # original intacto
    lista = {p["id"]: p for p in cliente.get("/personagens").json()}
    assert lista[cid]["mesa_id"] == mesa["id"] and lista[bardo_id]["mesa_id"] is None

    tempo = cliente.get(f"/personagens/{cid}/linha-do-tempo").json()
    assert tempo[2]["planejado"] and tempo[2]["bloqueado_pela_mesa"]
    assert cliente.post(f"/personagens/{cid}/plano/aplicar").status_code == 422      # mesa no 2
    cliente.put(url(mesa, "/nivel"), json={"nivel_maximo": 5})
    assert cliente.get(f"/personagens/{cid}/proximo-nivel").json()["planejado"] is True
    f = cliente.post(f"/personagens/{cid}/plano/aplicar").json()
    assert f["nivel"] == 3
    assert not cliente.get(f"/personagens/{cid}/linha-do-tempo").json()[3]["planejado"]


def test_descartar_plano(cliente, mesa, bardo_id):
    cliente.post(f"/personagens/{bardo_id}/niveis", json=NIVEIS[2])
    cid = cliente.post(f"/personagens/{bardo_id}/copia", json={"mesa_id": mesa["id"]}).json()["id"]
    assert cliente.delete(f"/personagens/{cid}/plano/2").status_code == 204
    assert cliente.get(f"/personagens/{cid}/proximo-nivel").json()["planejado"] is False
    assert cliente.delete(f"/personagens/{cid}/plano/2").status_code == 422


def test_copia_so_para_mesa_que_participa(cliente, bardo_id):
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    alheia = cliente.post("/mesas", json={"nome": "Da Bia"}, headers=bia).json()
    assert cliente.post(f"/personagens/{bardo_id}/copia", json={"mesa_id": alheia["id"]}).status_code == 404
    assert cliente.post(f"/personagens/{bardo_id}/copia", json={"mesa_id": "x"}).status_code == 404


def test_personagem_de_outro_nao_copia(cliente, mesa):
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    dela = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    assert cliente.post(f"/personagens/{dela}/copia", json={"mesa_id": mesa["id"]}).status_code == 404
