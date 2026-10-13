"""Senhas e tokens de acesso.

- Senhas: hash Argon2 (pwdlib). A senha em texto nunca é guardada.
- Tokens: JWT assinado (HS256) com o id do usuário e prazo de validade.

Configuração por variáveis de ambiente:
- JWT_SECRET: chave de assinatura. OBRIGATÓRIA em produção. Sem ela, é
  gerada uma chave aleatória ao iniciar (bom para desenvolvimento, mas os
  tokens deixam de valer a cada reinício do servidor).
- JWT_EXPIRA_MINUTOS: validade do token (padrão: 60).
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

_log = logging.getLogger(__name__)
_hash = PasswordHash.recommended()   # Argon2

ALGORITMO = "HS256"
EXPIRA_MINUTOS = int(os.environ.get("JWT_EXPIRA_MINUTOS", "60"))
_SEGREDO = os.environ.get("JWT_SECRET")
if not _SEGREDO:
    _SEGREDO = secrets.token_urlsafe(32)
    _log.warning("JWT_SECRET não definido: usando chave temporária (tokens caem ao reiniciar).")


class TokenInvalido(Exception):
    pass


def gerar_hash(senha: str) -> str:
    return _hash.hash(senha)


def senha_confere(senha: str, hash_salvo: str) -> bool:
    if not hash_salvo:   # conta criada pelo Google, ainda sem senha
        return False
    return _hash.verify(senha, hash_salvo)


def criar_token(usuario_id: str, agora: datetime | None = None) -> str:
    agora = agora or datetime.now(timezone.utc)
    # iat com fração de segundo: trocar a senha derruba até o token emitido no mesmo segundo
    dados = {"sub": usuario_id, "iat": agora.timestamp(), "exp": agora + timedelta(minutes=EXPIRA_MINUTOS)}
    return jwt.encode(dados, _SEGREDO, algorithm=ALGORITMO)


def usuario_do_token(token: str) -> str:
    """Devolve o id do usuário; TokenInvalido se a assinatura não bater ou o prazo vencer."""
    return dados_do_token(token)["sub"]


def dados_do_token(token: str) -> dict:
    """Conteúdo de um token de acesso (sub, iat, exp). Tokens de outro tipo
    (`typ`, ex.: o estado do login com o Google) não servem como acesso."""
    try:
        dados = jwt.decode(token, _SEGREDO, algorithms=[ALGORITMO], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError as erro:
        raise TokenInvalido(str(erro)) from erro
    if "typ" in dados:
        raise TokenInvalido("Este token não é de acesso.")
    return dados


def assinar(tipo: str, dados: dict, minutos: int) -> str:
    """Token assinado de uso interno (não serve como acesso), com prazo curto."""
    agora = datetime.now(timezone.utc)
    return jwt.encode({**dados, "typ": tipo, "exp": agora + timedelta(minutes=minutos)}, _SEGREDO, algorithm=ALGORITMO)


def ler_assinado(tipo: str, token: str) -> dict:
    try:
        dados = jwt.decode(token, _SEGREDO, algorithms=[ALGORITMO], options={"require": ["typ", "exp"]})
    except jwt.PyJWTError as erro:
        raise TokenInvalido(str(erro)) from erro
    if dados["typ"] != tipo:
        raise TokenInvalido("Token de outro tipo.")
    return dados
