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
    return _hash.verify(senha, hash_salvo)


def criar_token(usuario_id: str, agora: datetime | None = None) -> str:
    agora = agora or datetime.now(timezone.utc)
    dados = {"sub": usuario_id, "iat": agora, "exp": agora + timedelta(minutes=EXPIRA_MINUTOS)}
    return jwt.encode(dados, _SEGREDO, algorithm=ALGORITMO)


def usuario_do_token(token: str) -> str:
    """Devolve o id do usuário; TokenInvalido se a assinatura não bater ou o prazo vencer."""
    try:
        dados = jwt.decode(token, _SEGREDO, algorithms=[ALGORITMO], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError as erro:
        raise TokenInvalido(str(erro)) from erro
    return dados["sub"]
