"""Duas pessoas mexendo na mesma coisa ao mesmo tempo.

1. **Ações** (dano, Esperança, usar item, vender, Medo...): personagens,
   sessões, encontros, lojas e mesas têm a coluna `versao`, e o SQLAlchemy grava
   com `WHERE versao = <lida>`. Se outra gravação passou na frente, sai
   `StaleDataError`; aqui ela vira 409 marcado, e o `RefazerEmConflito` roda o
   pedido de novo (até 3 vezes) sobre o estado atualizado. Como as ações são
   comandos ("3 de dano"), refazer não perde nada: as duas valem.
2. **Formulários** que salvam tudo de uma vez (planejamento, quadro, loja,
   inimigo, NPC, equipamento): a tela manda a `versao` do conteúdo que carregou
   (um hash só dos campos do formulário, para dano no personagem não "conflitar"
   com a troca de equipamento). Se mudou, 409 com `tipo: "conflito"` e a tela
   deixa escolher entre ver a versão atual e salvar a sua por cima (sem versão).
"""

import hashlib
import json

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

TENTATIVAS = 3
_MARCA = b"x-refazer"   # cabeçalho interno: só o middleware vê


class ConflitoDeEdicao(Exception):
    pass


def versao_de(*conteudo) -> str:
    """Hash curto do conteúdo de um formulário (o que a tela edita)."""
    texto = json.dumps(conteudo, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


def conferir(versao_enviada: str | None, *conteudo_atual):
    """Recusa se a tela editou uma versão que não é mais a atual. Sem versão
    (None), salva por cima: é o "salvar a minha mesmo assim"."""
    if versao_enviada is not None and versao_enviada != versao_de(*conteudo_atual):
        raise ConflitoDeEdicao("Isto foi salvo em outro lugar (outra aba, outro aparelho ou outro mestre) "
                               "enquanto você editava.")


def registrar(app):
    @app.exception_handler(StaleDataError)
    def gravacao_simultanea(_: Request, __: StaleDataError):
        return JSONResponse(status_code=409, headers={_MARCA.decode(): "1"}, content={
            "detail": "Outra pessoa mexeu nisto ao mesmo tempo. Tente de novo.", "tipo": "simultaneo"})

    @app.exception_handler(ConflitoDeEdicao)
    def conflito(_: Request, erro: ConflitoDeEdicao):
        return JSONResponse(status_code=409, content={"detail": str(erro), "tipo": "conflito"})


class RefazerEmConflito:
    """Middleware ASGI: guarda o corpo do pedido e, se a resposta for o 409 de
    gravação simultânea, roda o pedido de novo (com sessão de banco nova, então
    com o estado atualizado). GET não grava, então passa direto (o fluxo ao vivo
    também é GET)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        corpo = b""
        while True:
            mensagem = await receive()
            corpo += mensagem.get("body", b"")
            if not mensagem.get("more_body"):
                break

        for tentativa in range(TENTATIVAS):
            entregue = False

            async def receber():
                nonlocal entregue
                if not entregue:
                    entregue = True
                    return {"type": "http.request", "body": corpo, "more_body": False}
                return await receive()   # depois do corpo, o que vier (ex.: o cliente desconectou)

            guardadas = []

            async def guardar(mensagem):
                guardadas.append(mensagem)

            await self.app(scope, receber, guardar)
            inicio = guardadas[0] if guardadas else None
            refazer = (inicio and inicio["type"] == "http.response.start" and inicio["status"] == 409
                       and any(nome == _MARCA for nome, _ in inicio.get("headers", [])))
            if refazer and tentativa < TENTATIVAS - 1:
                continue
            if inicio is not None and refazer:   # desistiu: entrega o 409 sem a marca interna
                inicio = {**inicio, "headers": [(n, v) for n, v in inicio["headers"] if n != _MARCA]}
                guardadas[0] = inicio
            for mensagem in guardadas:
                await send(mensagem)
            return
