"""Cadastro, login (senha ou Google), recuperação de senha e conta."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from motor import RegraViolada

from .. import conta, correio, google
from ..autenticacao import usuario_atual
from ..db import sessao_do_banco
from ..seguranca import TokenInvalido, assinar, criar_token, gerar_hash, ler_assinado, verificar_senha
from ..tabelas import IdentidadeTabela, RecuperacaoTabela, UsuarioTabela

rotas = APIRouter(prefix="/auth", tags=["Conta"])

VALIDADE_RECUPERACAO = timedelta(hours=1)
INTERVALO_RECUPERACAO = timedelta(minutes=1)   # no máximo um e-mail por minuto para cada conta
COOKIE_GOOGLE = "ag_google"


class Cadastro(BaseModel):
    email: EmailStr
    nome: str = Field(min_length=1, max_length=120)
    senha: str = Field(min_length=8, max_length=128)


class Usuario(BaseModel):
    id: str
    email: str
    nome: str
    tem_senha: bool = True      # conta criada pelo Google começa sem senha
    google: bool = False        # conta Google ligada


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PedidoDeRecuperacao(BaseModel):
    email: EmailStr


class NovaSenha(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    senha: str = Field(min_length=8, max_length=128)


class Provedores(BaseModel):
    google: bool


class LinkDeLogin(BaseModel):
    url: str


def _por_email(banco: Session, email: str) -> UsuarioTabela | None:
    return banco.scalar(select(UsuarioTabela).where(UsuarioTabela.email == email.lower()))


def _usuario(banco: Session, u: UsuarioTabela) -> Usuario:
    google_ligado = banco.scalar(select(IdentidadeTabela.sub).where(
        IdentidadeTabela.usuario_id == u.id, IdentidadeTabela.provedor == "google")) is not None
    return Usuario(id=u.id, email=u.email, nome=u.nome, tem_senha=bool(u.senha_hash), google=google_ligado)


@rotas.post("/cadastro", status_code=201, response_model=Usuario)
def cadastrar(dados: Cadastro, banco: Session = Depends(sessao_do_banco)):
    if _por_email(banco, dados.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este e-mail.")
    usuario = UsuarioTabela(id=str(uuid.uuid4()), email=dados.email.lower(),
                            nome=dados.nome.strip(), senha_hash=gerar_hash(dados.senha))
    banco.add(usuario)
    banco.commit()
    return _usuario(banco, usuario)


@rotas.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), banco: Session = Depends(sessao_do_banco)):
    """Formulário OAuth2 padrão: o e-mail vai no campo `username`."""
    usuario = _por_email(banco, form.username)
    confere, novo_hash = verificar_senha(form.password, usuario.senha_hash) if usuario else (False, None)
    # mesma mensagem para e-mail inexistente e senha errada: não revela quem tem conta
    if not confere:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.",
                            headers={"WWW-Authenticate": "Bearer"})
    if novo_hash:   # salvo com os parâmetros antigos (pesados): regrava no formato leve
        usuario.senha_hash = novo_hash
        banco.commit()
    return Token(access_token=criar_token(usuario.id))


@rotas.post("/renovar", response_model=Token)
def renovar(usuario: UsuarioTabela = Depends(usuario_atual)):
    """Token novo para quem ainda tem um válido. A interface chama enquanto a
    pessoa usa o app: assim só cai quem fica parado mais que a validade (2 h)."""
    return Token(access_token=criar_token(usuario.id))


@rotas.get("/eu", response_model=Usuario)
def eu(usuario: UsuarioTabela = Depends(usuario_atual), banco: Session = Depends(sessao_do_banco)):
    return _usuario(banco, usuario)


class ConfirmacaoDeExclusao(BaseModel):
    email: str = Field(description="O e-mail da conta, digitado para confirmar")


@rotas.delete("/eu", status_code=204)
def apagar_conta(dados: ConfirmacaoDeExclusao, usuario: UsuarioTabela = Depends(usuario_atual),
                 banco: Session = Depends(sessao_do_banco)):
    """Apaga a conta e os personagens dela, para sempre. As mesas que ela criou
    passam para outro mestre e as sessões que ela mestrou ficam (api/conta.py)."""
    if dados.email.strip().lower() != usuario.email.lower():
        raise RegraViolada("Digite o e-mail da sua conta para confirmar.")
    conta.apagar_conta(banco, usuario)   # mesma sessão da dependência (o FastAPI reaproveita)
    return Response(status_code=204)


# --- Esqueci minha senha ------------------------------------------------------------------------

def _hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _utc(momento: datetime) -> datetime:
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)   # o SQLite devolve sem fuso


@rotas.post("/recuperar", status_code=202)
def pedir_recuperacao(dados: PedidoDeRecuperacao, tarefas: BackgroundTasks,
                      banco: Session = Depends(sessao_do_banco)):
    """Manda o link para criar uma senha nova. A resposta é sempre a mesma (e o
    e-mail sai depois da resposta): ninguém descobre por aqui quem tem conta.
    Serve também para quem entrou pelo Google criar uma senha."""
    usuario = _por_email(banco, dados.email)
    if usuario is not None:
        ultimo = banco.scalar(select(RecuperacaoTabela.criado_em).where(RecuperacaoTabela.usuario_id == usuario.id)
                              .order_by(RecuperacaoTabela.criado_em.desc()))
        if ultimo is None or _agora() - _utc(ultimo) >= INTERVALO_RECUPERACAO:
            token = secrets.token_urlsafe(32)
            # um link por vez: pedir de novo invalida o anterior
            banco.execute(delete(RecuperacaoTabela).where(RecuperacaoTabela.usuario_id == usuario.id))
            banco.add(RecuperacaoTabela(token_hash=_hash_do_token(token), usuario_id=usuario.id,
                                        criado_em=_agora(), expira_em=_agora() + VALIDADE_RECUPERACAO))
            banco.commit()
            link = f"{correio.URL_DO_APP}/redefinir-senha?token={quote(token)}"
            acao = "criar uma nova senha" if usuario.senha_hash else "criar uma senha"
            tarefas.add_task(
                correio.enviar, usuario.email, "Adventurer's Guide: nova senha",
                f"Olá, {usuario.nome}!\n\nPara {acao}, abra este link (vale por 1 hora):\n{link}\n\n"
                "Se não foi você que pediu, ignore este e-mail: sua senha continua a mesma.")
    return {"detail": "Se houver uma conta com esse e-mail, enviamos um link para criar uma nova senha."}


@rotas.post("/redefinir", response_model=Token)
def redefinir_senha(dados: NovaSenha, banco: Session = Depends(sessao_do_banco)):
    """Troca a senha com o link do e-mail (uma vez só) e já entra. Derruba as
    sessões abertas: quem estava logado com a senha antiga precisa entrar de novo."""
    pedido = banco.get(RecuperacaoTabela, _hash_do_token(dados.token))
    if pedido is None or _utc(pedido.expira_em) < _agora():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link inválido ou vencido. Peça um novo.")
    usuario = banco.get(UsuarioTabela, pedido.usuario_id)
    usuario.senha_hash = gerar_hash(dados.senha)
    usuario.tokens_validos_desde = _agora()
    banco.execute(delete(RecuperacaoTabela).where(RecuperacaoTabela.usuario_id == usuario.id))
    banco.commit()
    return Token(access_token=criar_token(usuario.id))


# --- Login com o Google -------------------------------------------------------------------------

@rotas.get("/provedores", response_model=Provedores)
def provedores():
    """Quais plataformas de login estão configuradas (a tela só mostra essas)."""
    return Provedores(google=google.configurado())


def _exigir_google():
    if not google.configurado():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Login com o Google não está configurado.")


@rotas.get("/google", include_in_schema=False)
def entrar_com_google(ligar: str | None = None):
    """Começa o login: guarda estado e PKCE num cookie curto e vai para o Google.
    `ligar` (de /auth/google/ligar) liga o Google à conta de quem já está logado."""
    _exigir_google()
    estado = secrets.token_urlsafe(24)
    verificador, desafio = google.novo_pkce()
    dados = {"estado": estado, "verificador": verificador}
    if ligar:
        try:
            dados["ligar"] = ler_assinado("ligar_google", ligar)["usuario"]
        except TokenInvalido:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link para ligar o Google vencido. Tente de novo.")
    resposta = RedirectResponse(google.url_de_autorizacao(estado, desafio), status_code=302)
    resposta.set_cookie(COOKIE_GOOGLE, assinar("login_google", dados, minutos=10), max_age=600,
                        httponly=True, samesite="lax", secure=correio.URL_DO_APP.startswith("https"))
    return resposta


@rotas.post("/google/ligar", response_model=LinkDeLogin)
def link_para_ligar_google(usuario: UsuarioTabela = Depends(usuario_atual)):
    """Para ligar o Google a uma conta já logada: um bilhete de 5 minutos (o
    token de acesso não vai na URL)."""
    _exigir_google()
    bilhete = assinar("ligar_google", {"usuario": usuario.id}, minutos=5)
    return LinkDeLogin(url=f"/auth/google?ligar={quote(bilhete)}")


def _para_o_app(caminho: str) -> RedirectResponse:
    resposta = RedirectResponse(f"{correio.URL_DO_APP}{caminho}", status_code=302)
    resposta.delete_cookie(COOKIE_GOOGLE)
    return resposta


@rotas.get("/google/retorno", include_in_schema=False)
def retorno_do_google(request: Request, code: str | None = None, state: str | None = None,
                      error: str | None = None, banco: Session = Depends(sessao_do_banco)):
    """O Google volta para cá. Entra na conta ligada a esse Google; senão, na
    conta com o mesmo e-mail (verificado pelo Google), que passa a aceitar os
    dois jeitos de entrar; senão, cria uma conta nova (sem senha)."""
    def erro(mensagem: str, ligando: bool = False):
        return _para_o_app(f"{'/conta' if ligando else '/entrar'}?erro={quote(mensagem)}")

    try:
        dados = ler_assinado("login_google", request.cookies.get(COOKIE_GOOGLE, ""))
    except TokenInvalido:
        return erro("O login com o Google demorou demais ou veio de outro navegador. Tente de novo.")
    ligando = "ligar" in dados
    if error or not code:
        return erro("Login com o Google cancelado.", ligando)
    if not state or not secrets.compare_digest(state, dados["estado"]):
        return erro("Resposta do Google não confere. Tente de novo.", ligando)
    try:
        pessoa = google.trocar_codigo(code, dados["verificador"])
    except google.FalhaNoGoogle as falha:
        return erro(str(falha), ligando)

    ja_ligada = banco.get(IdentidadeTabela, ("google", pessoa["sub"]))
    if ligando:
        if ja_ligada and ja_ligada.usuario_id != dados["ligar"]:
            return erro("Esta conta Google já está ligada a outra conta.", True)
        usuario = banco.get(UsuarioTabela, dados["ligar"])
        if usuario is None:
            return erro("Conta não encontrada.")
    elif ja_ligada:
        usuario = banco.get(UsuarioTabela, ja_ligada.usuario_id)
    else:
        usuario = _por_email(banco, pessoa["email"]) if pessoa["email_verificado"] else None
        if usuario is None:
            if not pessoa["email_verificado"]:
                return erro("O Google não confirmou este e-mail.")
            usuario = UsuarioTabela(id=str(uuid.uuid4()), email=pessoa["email"],
                                    nome=(pessoa["nome"] or pessoa["email"].split("@")[0])[:120], senha_hash="")
            banco.add(usuario)
            banco.flush()   # o usuário precisa existir antes da identidade (chave estrangeira)
    if ja_ligada is None:
        banco.add(IdentidadeTabela(provedor="google", sub=pessoa["sub"], usuario_id=usuario.id, email=pessoa["email"]))
    banco.commit()
    if ligando:
        return _para_o_app("/conta?ligado=google")
    # no fragmento (#): o token não vai para servidores nem para logs no caminho
    return _para_o_app(f"/entrar/google#token={criar_token(usuario.id)}")


@rotas.delete("/google", response_model=Usuario)
def desligar_google(usuario: UsuarioTabela = Depends(usuario_atual), banco: Session = Depends(sessao_do_banco)):
    if not usuario.senha_hash:
        raise HTTPException(422, "Crie uma senha antes de desligar o Google, senão não haverá como entrar.")
    banco.execute(delete(IdentidadeTabela).where(IdentidadeTabela.usuario_id == usuario.id,
                                                 IdentidadeTabela.provedor == "google"))
    banco.commit()
    return _usuario(banco, usuario)
