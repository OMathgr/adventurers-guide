"""Quem está fazendo a requisição.

`usuario_atual` é a dependência que as rotas protegidas usam: lê o token
do cabeçalho `Authorization: Bearer <token>` e devolve o usuário.
"""

from dataclasses import dataclass
from datetime import timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import sessao_do_banco
from .seguranca import TokenInvalido, dados_do_token
from .tabelas import UsuarioTabela

# tokenUrl faz o botão "Authorize" da página /docs funcionar
_esquema = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _nao_autenticado(motivo: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, motivo,
                         headers={"WWW-Authenticate": "Bearer"})


def usuario_do_acesso(banco: Session, token: str) -> UsuarioTabela:
    """Valida o token e devolve o usuário; 401 se não valer mais."""
    try:
        dados = dados_do_token(token)
    except TokenInvalido:
        raise _nao_autenticado("Token inválido ou expirado. Faça login de novo.")
    usuario = banco.get(UsuarioTabela, dados["sub"])
    if usuario is None:   # conta apagada depois de o token ser emitido
        raise _nao_autenticado("Usuário não existe mais.")
    desde = usuario.tokens_validos_desde
    if desde is not None and dados.get("iat", 0) < desde.replace(tzinfo=desde.tzinfo or timezone.utc).timestamp():
        raise _nao_autenticado("A senha foi trocada. Faça login de novo.")
    return usuario


def usuario_atual(token: str = Depends(_esquema),
                  banco: Session = Depends(sessao_do_banco)) -> UsuarioTabela:
    return usuario_do_acesso(banco, token)


@dataclass
class Acesso:
    """Banco + usuário autenticado: o que toda rota de personagem precisa."""

    banco: Session
    usuario_id: str


def acesso(usuario: UsuarioTabela = Depends(usuario_atual),
           banco: Session = Depends(sessao_do_banco)) -> Acesso:
    return Acesso(banco, usuario.id)
