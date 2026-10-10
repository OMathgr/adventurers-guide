"""Quem está fazendo a requisição.

`usuario_atual` é a dependência que as rotas protegidas usam: lê o token
do cabeçalho `Authorization: Bearer <token>` e devolve o usuário.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import sessao_do_banco
from .seguranca import TokenInvalido, usuario_do_token
from .tabelas import UsuarioTabela

# tokenUrl faz o botão "Authorize" da página /docs funcionar
_esquema = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _nao_autenticado(motivo: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, motivo,
                         headers={"WWW-Authenticate": "Bearer"})


def usuario_atual(token: str = Depends(_esquema),
                  banco: Session = Depends(sessao_do_banco)) -> UsuarioTabela:
    try:
        usuario_id = usuario_do_token(token)
    except TokenInvalido:
        raise _nao_autenticado("Token inválido ou expirado. Faça login de novo.")
    usuario = banco.get(UsuarioTabela, usuario_id)
    if usuario is None:   # conta apagada depois de o token ser emitido
        raise _nao_autenticado("Usuário não existe mais.")
    return usuario


@dataclass
class Acesso:
    """Banco + usuário autenticado: o que toda rota de personagem precisa."""

    banco: Session
    usuario_id: str


def acesso(usuario: UsuarioTabela = Depends(usuario_atual),
           banco: Session = Depends(sessao_do_banco)) -> Acesso:
    return Acesso(banco, usuario.id)
