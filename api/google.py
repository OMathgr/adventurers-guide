"""Login com o Google (OpenID Connect, fluxo "authorization code" com PKCE).

Configuração por variáveis de ambiente (sem elas, o botão nem aparece):
- GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET: do app criado no Google Cloud
  Console (APIs e serviços > Credenciais > ID do cliente OAuth, tipo "Aplicativo da Web").
- API_URL: endereço público da API, para montar o retorno
  `{API_URL}/auth/google/retorno` (cadastre exatamente este endereço no
  Google). Padrão: http://localhost:5173/api (a API atrás do proxy do Vite).

O `id_token` vem direto do Google, pela troca do código em HTTPS, então não
precisa conferir a assinatura (OpenID Connect Core, 3.1.3.7); conferimos
emissor, público, validade e e-mail verificado.
"""

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
import urllib.request

URL_AUTORIZAR = "https://accounts.google.com/o/oauth2/v2/auth"
URL_TOKEN = "https://oauth2.googleapis.com/token"
EMISSORES = {"https://accounts.google.com", "accounts.google.com"}


class FalhaNoGoogle(Exception):
    pass


def _client_id() -> str | None:
    return os.environ.get("GOOGLE_CLIENT_ID")


def configurado() -> bool:
    return bool(_client_id() and os.environ.get("GOOGLE_CLIENT_SECRET"))


def url_de_retorno() -> str:
    return os.environ.get("API_URL", "http://localhost:5173/api").rstrip("/") + "/auth/google/retorno"


def novo_pkce() -> tuple[str, str]:
    """(verificador, desafio) do PKCE: o código só serve para quem começou o login."""
    verificador = secrets.token_urlsafe(48)
    desafio = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b"=").decode()
    return verificador, desafio


def url_de_autorizacao(estado: str, desafio: str) -> str:
    return URL_AUTORIZAR + "?" + urllib.parse.urlencode({
        "client_id": _client_id(), "redirect_uri": url_de_retorno(), "response_type": "code",
        "scope": "openid email profile", "state": estado, "code_challenge": desafio,
        "code_challenge_method": "S256", "prompt": "select_account",
    })


def _postar(url: str, campos: dict) -> dict:
    """POST de formulário; separado para os testes trocarem pela resposta falsa."""
    pedido = urllib.request.Request(url, data=urllib.parse.urlencode(campos).encode(), method="POST",
                                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(pedido, timeout=15) as resposta:
            return json.load(resposta)
    except (OSError, ValueError) as erro:
        raise FalhaNoGoogle(f"Não foi possível falar com o Google: {erro}") from erro


def _payload(id_token: str) -> dict:
    try:
        meio = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(meio + "=" * (-len(meio) % 4)))
    except (IndexError, ValueError) as erro:
        raise FalhaNoGoogle("Resposta do Google inválida.") from erro


def trocar_codigo(codigo: str, verificador: str) -> dict:
    """Troca o código pelo id_token e devolve {sub, email, email_verificado, nome}."""
    resposta = _postar(URL_TOKEN, {
        "code": codigo, "client_id": _client_id(), "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": url_de_retorno(), "grant_type": "authorization_code", "code_verifier": verificador,
    })
    if "id_token" not in resposta:
        raise FalhaNoGoogle(resposta.get("error_description") or resposta.get("error") or "O Google recusou o login.")
    dados = _payload(resposta["id_token"])
    if dados.get("iss") not in EMISSORES or dados.get("aud") != _client_id() or dados.get("exp", 0) < time.time():
        raise FalhaNoGoogle("Resposta do Google inválida.")
    return {"sub": str(dados["sub"]), "email": (dados.get("email") or "").lower(),
            "email_verificado": dados.get("email_verified") is True,
            "nome": dados.get("name") or dados.get("given_name") or ""}
