"""Recuperação de senha e login com o Google (o Google é simulado)."""

import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from dados_api import entrar

import api.correio
import api.google
from api.tabelas import RecuperacaoTabela


@pytest.fixture
def caixa(monkeypatch):
    """E-mails "enviados" (nada sai de verdade)."""
    enviados = []
    monkeypatch.setattr(api.correio, "enviar", lambda para, assunto, texto: enviados.append((para, assunto, texto)))
    return enviados


def _token_do_link(texto: str) -> str:
    link = next(linha for linha in texto.splitlines() if "/redefinir-senha?token=" in linha)
    return parse_qs(urlparse(link).query)["token"][0]


# --- Esqueci minha senha ------------------------------------------------------------------------

def test_recuperar_e_redefinir(anonimo, caixa):
    antigo = entrar(anonimo, "ana@exemplo.com")
    r = anonimo.post("/auth/recuperar", json={"email": "ANA@exemplo.com"})
    assert r.status_code == 202
    (para, _, texto), = caixa
    assert para == "ana@exemplo.com" and "vale por 1 hora" in texto
    token = _token_do_link(texto)

    r = anonimo.post("/auth/redefinir", json={"token": token, "senha": "nova-senha-123"})
    assert r.status_code == 200
    novo = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert anonimo.get("/auth/eu", headers=novo).status_code == 200
    # a sessão aberta com a senha antiga cai
    r = anonimo.get("/auth/eu", headers=antigo)
    assert r.status_code == 401 and "senha foi trocada" in r.json()["detail"]
    # o link vale uma vez só
    assert anonimo.post("/auth/redefinir", json={"token": token, "senha": "outra-senha-123"}).status_code == 400
    # a senha nova entra; a antiga não
    assert anonimo.post("/auth/login", data={"username": "ana@exemplo.com", "password": "nova-senha-123"}).status_code == 200
    assert anonimo.post("/auth/login", data={"username": "ana@exemplo.com", "password": "senha-forte-123"}).status_code == 401


def test_email_desconhecido_tem_a_mesma_resposta(anonimo, caixa):
    entrar(anonimo, "ana@exemplo.com")
    conhecido = anonimo.post("/auth/recuperar", json={"email": "ana@exemplo.com"})
    desconhecido = anonimo.post("/auth/recuperar", json={"email": "ninguem@exemplo.com"})
    assert (conhecido.status_code, conhecido.json()) == (desconhecido.status_code, desconhecido.json())
    assert len(caixa) == 1


def test_um_email_por_minuto_e_o_novo_link_vence_o_antigo(anonimo, caixa):
    entrar(anonimo, "ana@exemplo.com")
    anonimo.post("/auth/recuperar", json={"email": "ana@exemplo.com"})
    anonimo.post("/auth/recuperar", json={"email": "ana@exemplo.com"})
    assert len(caixa) == 1


def test_link_vencido(anonimo, caixa):
    from api.db import sessao_do_banco
    from api.main import app
    entrar(anonimo, "ana@exemplo.com")
    anonimo.post("/auth/recuperar", json={"email": "ana@exemplo.com"})
    banco = next(app.dependency_overrides[sessao_do_banco]())
    pedido = banco.query(RecuperacaoTabela).one()
    pedido.expira_em = pedido.criado_em   # já venceu
    banco.commit()
    r = anonimo.post("/auth/redefinir", json={"token": _token_do_link(caixa[0][2]), "senha": "nova-senha-123"})
    assert r.status_code == 400 and "vencido" in r.json()["detail"]


# --- Google -------------------------------------------------------------------------------------

def _id_token(**dados) -> str:
    """id_token falso (o que importa é o conteúdo; a assinatura não é conferida)."""
    corpo = {"iss": "https://accounts.google.com", "aud": "cliente-teste", "exp": time.time() + 600,
             "sub": "g-123", "email": "ana@gmail.com", "email_verified": True, "name": "Ana do Google", **dados}
    meio = base64.urlsafe_b64encode(json.dumps(corpo).encode()).rstrip(b"=").decode()
    return f"cabecalho.{meio}.assinatura"


@pytest.fixture
def google_falso(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cliente-teste")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "segredo-teste")
    resposta = {"dados": {}}
    pedidos = []

    def postar(url, campos):
        pedidos.append(campos)
        return {"id_token": _id_token(**resposta["dados"])}
    monkeypatch.setattr(api.google, "_postar", postar)
    resposta["pedidos"] = pedidos
    return resposta


def _login_google(cliente, inicio="/auth/google"):
    """Faz o vai e volta: /auth/google -> (Google) -> /auth/google/retorno. Devolve o destino final."""
    r = cliente.get(inicio, follow_redirects=False)
    assert r.status_code == 302, r.text
    url = urlparse(r.headers["location"])
    assert url.netloc == "accounts.google.com"
    estado = parse_qs(url.query)["state"][0]
    r = cliente.get(f"/auth/google/retorno?code=codigo-123&state={estado}", follow_redirects=False)
    assert r.status_code == 302
    return r.headers["location"]


def _token_do_destino(destino: str) -> dict:
    assert "/entrar/google#token=" in destino, destino
    return {"Authorization": f"Bearer {destino.split('#token=')[1]}"}


def test_provedores(anonimo, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    assert anonimo.get("/auth/provedores").json() == {"google": False}
    assert anonimo.get("/auth/google", follow_redirects=False).status_code == 404
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "x")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "y")
    assert anonimo.get("/auth/provedores").json() == {"google": True}


def test_google_cria_conta_sem_senha(anonimo, google_falso):
    h = _token_do_destino(_login_google(anonimo))
    eu = anonimo.get("/auth/eu", headers=h).json()
    assert (eu["email"], eu["nome"], eu["tem_senha"], eu["google"]) == ("ana@gmail.com", "Ana do Google", False, True)
    assert google_falso["pedidos"][0]["code_verifier"]   # PKCE
    # sem senha, não entra pelo formulário
    assert anonimo.post("/auth/login", data={"username": "ana@gmail.com", "password": ""}).status_code in (401, 422)
    # entrar de novo cai na mesma conta
    assert anonimo.get("/auth/eu", headers=_token_do_destino(_login_google(anonimo))).json()["id"] == eu["id"]


def test_google_junta_com_a_conta_do_mesmo_email(anonimo, google_falso):
    h = entrar(anonimo, "ana@gmail.com")
    minha = anonimo.get("/auth/eu", headers=h).json()
    eu = anonimo.get("/auth/eu", headers=_token_do_destino(_login_google(anonimo))).json()
    assert eu["id"] == minha["id"] and eu["tem_senha"] and eu["google"]


def test_google_sem_email_verificado_nao_junta(anonimo, google_falso):
    entrar(anonimo, "ana@gmail.com")
    google_falso["dados"] = {"email_verified": False}
    destino = _login_google(anonimo)
    assert "/entrar?erro=" in destino


def test_estado_errado_e_recusado(anonimo, google_falso):
    anonimo.get("/auth/google", follow_redirects=False)
    r = anonimo.get("/auth/google/retorno?code=x&state=outro", follow_redirects=False)
    assert "/entrar?erro=" in r.headers["location"]
    # sem o cookie (outro navegador)
    anonimo.cookies.clear()
    r = anonimo.get("/auth/google/retorno?code=x&state=outro", follow_redirects=False)
    assert "/entrar?erro=" in r.headers["location"]


def test_ligar_e_desligar_o_google(anonimo, google_falso):
    h = entrar(anonimo, "ana@exemplo.com")   # e-mail diferente do Google
    url = anonimo.post("/auth/google/ligar", headers=h).json()["url"]
    destino = _login_google(anonimo, url)
    assert destino.endswith("/conta?ligado=google")
    assert anonimo.get("/auth/eu", headers=h).json()["google"] is True
    # agora o Google entra nesta conta
    assert anonimo.get("/auth/eu", headers=_token_do_destino(_login_google(anonimo))).json()["email"] == "ana@exemplo.com"
    assert anonimo.delete("/auth/google", headers=h).json()["google"] is False


def test_conta_so_com_google_nao_desliga_e_cria_senha_pela_recuperacao(anonimo, google_falso, caixa):
    h = _token_do_destino(_login_google(anonimo))
    assert anonimo.delete("/auth/google", headers=h).status_code == 422
    anonimo.post("/auth/recuperar", json={"email": "ana@gmail.com"})
    assert "criar uma senha" in caixa[0][2]
    anonimo.post("/auth/redefinir", json={"token": _token_do_link(caixa[0][2]), "senha": "senha-nova-123"})
    assert anonimo.post("/auth/login", data={"username": "ana@gmail.com", "password": "senha-nova-123"}).status_code == 200


def test_token_interno_nao_serve_de_acesso(anonimo):
    from api.seguranca import assinar
    falso = assinar("ligar_google", {"sub": "qualquer"}, minutos=5)
    assert anonimo.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401
