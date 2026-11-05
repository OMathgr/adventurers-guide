"""Fluxo de avisos ao vivo (Server-Sent Events): `GET /eventos?passe=...`.

O EventSource do navegador não manda cabeçalhos, e URLs vão parar em logs: em
vez do login, vai na URL um passe de 1 minuto (`POST /eventos/passe`, com login)
que só serve para abrir o fluxo. A conexão aberta segue depois que ele vence.
Cada aviso é uma linha `data: {"tipo": ..., "id": ...}`; a cada 15 s vai um
comentário (`: ping`) para manter a conexão viva atrás de proxies.
"""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import sessao_do_banco
from ..eventos import avisar_presenca, central
from ..autenticacao import Acesso, acesso, usuario_do_passe_ao_vivo
from ..seguranca import criar_passe_ao_vivo

rotas = APIRouter(tags=["Ao vivo"])
INTERVALO_PING = 15.0  # segundos (os testes diminuem)
# o fluxo se renova a cada hora (o EventSource reconecta sozinho); os testes usam bem menos
DURACAO_MAXIMA = 3600.0


def _presenca(engine, usuario_id: str):
    with Session(bind=engine) as s:
        avisar_presenca(s, usuario_id)


class PasseAoVivo(BaseModel):
    passe: str


@rotas.post("/eventos/passe", response_model=PasseAoVivo)
def passe(a: Acesso = Depends(acesso)):
    return PasseAoVivo(passe=criar_passe_ao_vivo(a.usuario_id))


@rotas.get("/eventos")
async def eventos(request: Request, passe: str, banco: Session = Depends(sessao_do_banco)):
    # mesma validação das rotas (inclui sessões derrubadas pela troca de senha)
    usuario_id = (await run_in_threadpool(usuario_do_passe_ao_vivo, banco, passe)).id
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
