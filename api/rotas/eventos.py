"""Fluxo de avisos ao vivo (Server-Sent Events): `GET /eventos?token=...`.

O EventSource do navegador não manda cabeçalhos, então o token vem na URL.
Cada aviso é uma linha `data: {"tipo": ..., "id": ...}`; a cada 15 s vai um
comentário (`: ping`) para manter a conexão viva atrás de proxies.
"""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import sessao_do_banco
from ..eventos import avisar_presenca, central
from ..autenticacao import usuario_do_acesso

rotas = APIRouter(tags=["Ao vivo"])
INTERVALO_PING = 15.0  # segundos (os testes diminuem)
# o fluxo se renova a cada hora (o EventSource reconecta sozinho); os testes usam bem menos
DURACAO_MAXIMA = 3600.0


def _presenca(engine, usuario_id: str):
    with Session(bind=engine) as s:
        avisar_presenca(s, usuario_id)


@rotas.get("/eventos")
async def eventos(request: Request, token: str, banco: Session = Depends(sessao_do_banco)):
    # mesma validação das rotas (inclui sessões derrubadas pela troca de senha)
    usuario_id = (await run_in_threadpool(usuario_do_acesso, banco, token)).id
    engine = banco.get_bind()   # a sessão da requisição fecha antes do fim do fluxo

    fila: asyncio.Queue = asyncio.Queue()
    laco = asyncio.get_running_loop()
    # os commits acontecem em outras threads: a entrega passa para o laço do fluxo
    cancelar = central.assinar(usuario_id, lambda ev: laco.call_soon_threadsafe(fila.put_nowait, ev))
    await run_in_threadpool(_presenca, engine, usuario_id)

    async def gerar():
        fim = laco.time() + DURACAO_MAXIMA
        try:
            yield f"data: {json.dumps({'tipo': 'conectado'})}\n\n"
            while laco.time() < fim and not await request.is_disconnected():
                try:
                    evento = await asyncio.wait_for(fila.get(), min(INTERVALO_PING, max(0.0, fim - laco.time())))
                    yield f"data: {json.dumps(evento)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            cancelar()
            await run_in_threadpool(_presenca, engine, usuario_id)

    return StreamingResponse(gerar(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
