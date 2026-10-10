"""Cadastro, login e conta."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..autenticacao import usuario_atual
from ..db import sessao_do_banco
from ..seguranca import criar_token, gerar_hash, senha_confere
from ..tabelas import UsuarioTabela

rotas = APIRouter(prefix="/auth", tags=["Conta"])


class Cadastro(BaseModel):
    email: EmailStr
    nome: str = Field(min_length=1, max_length=120)
    senha: str = Field(min_length=8, max_length=128)


class Usuario(BaseModel):
    id: str
    email: str
    nome: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _por_email(banco: Session, email: str) -> UsuarioTabela | None:
    return banco.scalar(select(UsuarioTabela).where(UsuarioTabela.email == email.lower()))


@rotas.post("/cadastro", status_code=201, response_model=Usuario)
def cadastrar(dados: Cadastro, banco: Session = Depends(sessao_do_banco)):
    if _por_email(banco, dados.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")
    usuario = UsuarioTabela(id=str(uuid.uuid4()), email=dados.email.lower(),
                            nome=dados.nome.strip(), senha_hash=gerar_hash(dados.senha))
    banco.add(usuario)
    banco.commit()
    return Usuario(id=usuario.id, email=usuario.email, nome=usuario.nome)


@rotas.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), banco: Session = Depends(sessao_do_banco)):
    """Formulário OAuth2 padrão: o e-mail vai no campo `username`."""
    usuario = _por_email(banco, form.username)
    # mesma mensagem para e-mail inexistente e senha errada: não revela quem tem conta
    if usuario is None or not senha_confere(form.password, usuario.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.",
                            headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=criar_token(usuario.id))


@rotas.get("/eu", response_model=Usuario)
def eu(usuario: UsuarioTabela = Depends(usuario_atual)):
    return Usuario(id=usuario.id, email=usuario.email, nome=usuario.nome)


@rotas.delete("/eu", status_code=204)
def apagar_conta(usuario: UsuarioTabela = Depends(usuario_atual),
                 banco: Session = Depends(sessao_do_banco)):
    """Apaga a conta e todos os personagens dela."""
    banco.delete(usuario)   # mesma sessão da dependência (o FastAPI reaproveita)
    banco.commit()
    return Response(status_code=204)
