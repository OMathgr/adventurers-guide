"""Aplicação FastAPI.

Rode com:  uvicorn api.main:app --reload
Documentação interativa em http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from motor import RegraViolada

from . import concorrencia
from .mesas import SemPermissao
from .repositorio import NaoEncontrado
from .rotas import (auth, conteudo, encontros, eventos, imagens, inventario, jogo, lojas, mesas, rolagens, personagens, quadro, repouso,
                    revelado, sessao, sessoes, srd)

app = FastAPI(
    title="Adventurer's Guide",
    description="Construtor de personagem e estado de jogo de Daggerheart (SRD 1.0).",
    version="0.2.0",
)
app.include_router(auth.rotas)
app.include_router(srd.rotas)
app.include_router(personagens.rotas)
app.include_router(sessao.rotas)
app.include_router(mesas.rotas)
app.include_router(conteudo.rotas)
app.include_router(sessoes.rotas)
app.include_router(encontros.rotas)
app.include_router(imagens.rotas)
app.include_router(revelado.rotas)
app.include_router(quadro.rotas)
app.include_router(eventos.rotas)
app.include_router(inventario.rotas)
app.include_router(inventario.rotas_mestre)
app.include_router(lojas.rotas)
app.include_router(repouso.rotas)
app.include_router(jogo.rotas)
app.include_router(rolagens.rotas)


concorrencia.registrar(app)
app.add_middleware(concorrencia.RefazerEmConflito)


@app.exception_handler(RegraViolada)
def regra_violada(_: Request, erro: RegraViolada):
    # 422: o pedido está bem formado, mas as regras do jogo não permitem
    return JSONResponse(status_code=422, content={"detail": str(erro), "tipo": "regra"})


@app.exception_handler(NaoEncontrado)
def nao_encontrado(_: Request, erro: NaoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(erro)})


@app.exception_handler(SemPermissao)
def sem_permissao(_: Request, erro: SemPermissao):
    return JSONResponse(status_code=403, content={"detail": str(erro)})
