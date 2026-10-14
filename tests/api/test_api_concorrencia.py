"""Duas pessoas mexendo na mesma coisa ao mesmo tempo (api/concorrencia.py)."""

import pytest
from dados_api import BARDO

import api.repositorio as repositorio
from api.db import sessao_do_banco
from api.main import app
from api.tabelas import PersonagemTabela


@pytest.fixture
def outra_pessoa():
    """Uma sessão de banco separada, como a de outro pedido rodando junto."""
    gerador = app.dependency_overrides[sessao_do_banco]()
    banco = next(gerador)
    yield banco
    banco.close()


def _intrometer(monkeypatch, outra_pessoa, pid, vezes=1):
    """Faz "outra pessoa" gravar no personagem bem entre o ler e o gravar do pedido."""
    gravar = repositorio.gravar
    chamadas = {"intromissoes": 0, "gravacoes": 0}

    def gravar_com_intromissao(banco, linha, personagem):
        chamadas["gravacoes"] += 1
        if chamadas["intromissoes"] < vezes:
            chamadas["intromissoes"] += 1
            outra = outra_pessoa.get(PersonagemTabela, pid, populate_existing=True)
            p = repositorio.montar(outra)
            p.sessao.marcar_pv(1)            # a mestre aplica 1 PV no mesmo instante
            gravar(outra_pessoa, outra, p)
        gravar(banco, linha, personagem)

    monkeypatch.setattr(repositorio, "gravar", gravar_com_intromissao)
    return chamadas


def test_acoes_ao_mesmo_tempo_as_duas_valem(cliente, monkeypatch, outra_pessoa):
    pid = cliente.post("/personagens", json=BARDO).json()["id"]
    chamadas = _intrometer(monkeypatch, outra_pessoa, pid)
    r = cliente.post(f"/personagens/{pid}/sessao/esperanca/gastar", json={"quantidade": 1})
    assert r.status_code == 200, r.text
    f = r.json()
    # a Esperança gasta (o pedido refeito) e o PV marcado pela "outra pessoa": nada se perdeu
    assert (f["esperanca"], f["pv_marcados"]) == (1, 1)
    assert chamadas["gravacoes"] == 2   # a primeira bateu na outra; a segunda, sobre o estado novo, passou


def test_desiste_depois_de_tres_tentativas(cliente, monkeypatch, outra_pessoa):
    pid = cliente.post("/personagens", json=BARDO).json()["id"]
    _intrometer(monkeypatch, outra_pessoa, pid, vezes=99)
    r = cliente.post(f"/personagens/{pid}/sessao/esperanca/gastar", json={"quantidade": 1})
    assert r.status_code == 409 and r.json()["tipo"] == "simultaneo"
    assert "x-refazer" not in r.headers   # a marca interna não sai para a tela
    assert cliente.get(f"/personagens/{pid}").json()["esperanca"] == 2   # a ação não valeu (e o erro diz para tentar de novo)


def test_gravar_sem_concorrencia_sobe_a_versao(cliente, outra_pessoa):
    pid = cliente.post("/personagens", json=BARDO).json()["id"]
    antes = outra_pessoa.get(PersonagemTabela, pid).versao
    cliente.post(f"/personagens/{pid}/sessao/pv/marcar", json={"quantidade": 1})
    outra_pessoa.expire_all()
    assert outra_pessoa.get(PersonagemTabela, pid).versao == antes + 1


# --- Formulários: avisar quando alguém salvou antes ------------------------------------------

from test_api_conteudo import INIMIGO  # noqa: E402


@pytest.fixture
def mesa(cliente):
    return cliente.post("/mesas", json={"nome": "Os Sem-Nome"}).json()


@pytest.fixture
def sessao(cliente, mesa):
    return cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sessão 1"}).json()


def _formulario(cliente, url_ver, url_salvar, corpo_a, corpo_b):
    """Duas abas abrem o mesmo formulário; a A salva; a B (com a versão velha) é avisada;
    sem versão, a B salva por cima."""
    velha = cliente.get(url_ver).json()["versao"]
    a = cliente.put(f"{url_salvar}?versao={velha}", json=corpo_a)
    assert a.status_code == 200, a.text
    b = cliente.put(f"{url_salvar}?versao={velha}", json=corpo_b)
    assert b.status_code == 409 and b.json()["tipo"] == "conflito"
    assert "enquanto você editava" in b.json()["detail"]
    # a versão nova (devolvida ao salvar) serve para o próximo salvamento
    assert cliente.put(f"{url_salvar}?versao={cliente.get(url_ver).json()['versao']}", json=corpo_a).status_code == 200
    assert cliente.put(url_salvar, json=corpo_b).status_code == 200   # "salvar a minha por cima"


def test_planejamento_da_sessao(cliente, mesa, sessao):
    u = f"/mesas/{mesa['id']}/sessoes/{sessao['id']}"
    _formulario(cliente, u, u, {"titulo": "A ponte"}, {"titulo": "O porto"})
    assert cliente.get(u).json()["titulo"] == "O porto"


def test_quadro_da_sessao(cliente, mesa, sessao):
    u = f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/quadro"
    cartao = lambda texto: {"cartoes": [{"id": "c1", "tipo": "nota", "x": 0, "y": 0, "texto": texto}], "ligacoes": []}  # noqa: E731
    _formulario(cliente, u, u, cartao("um"), cartao("dois"))


def test_loja(cliente, mesa, sessao):
    base = f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/lojas"
    loja = cliente.post(base, json={"nome": "Boticário"}).json()
    u = f"{base}/{loja['id']}"
    velha = loja["versao"]
    assert cliente.put(f"{u}?versao={velha}", json={"nome": "Boticário A"}).status_code == 200
    assert cliente.put(f"{u}?versao={velha}", json={"nome": "Boticário B"}).status_code == 409


def test_inimigo_e_npc(cliente, mesa):
    iid = cliente.post(f"/mesas/{mesa['id']}/inimigos", json=INIMIGO).json()["id"]
    u = f"/mesas/{mesa['id']}/inimigos/{iid}"
    _formulario(cliente, u, u, {**INIMIGO, "pv": 6}, {**INIMIGO, "pv": 9})
    nid = cliente.post(f"/mesas/{mesa['id']}/npcs", json={"nome": "Ilsa"}).json()["id"]
    u = f"/mesas/{mesa['id']}/npcs/{nid}"
    _formulario(cliente, u, u, {"nome": "Ilsa, a ferreira"}, {"nome": "Ilsa, a espiã"})


def test_equipamento_nao_conflita_com_dano(cliente):
    pid = cliente.post("/personagens", json=BARDO).json()["id"]
    versao = cliente.get(f"/personagens/{pid}/equipamento").json()["versao"]
    cliente.post(f"/personagens/{pid}/sessao/pv/marcar", json={"quantidade": 1})   # a mestre aplica dano no meio
    r = cliente.put(f"/personagens/{pid}/equipamento?versao={versao}", json={"principal": "core_weapon_rapier"})
    assert r.status_code == 200, r.text
    # mas trocar o equipamento em outra aba, sim
    r = cliente.put(f"/personagens/{pid}/equipamento?versao={versao}", json={"principal": "core_weapon_dagger"})
    assert r.status_code == 409 and r.json()["tipo"] == "conflito"
