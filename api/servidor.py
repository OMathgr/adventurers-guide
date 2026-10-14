"""Servidor de produção: a API em /api e a interface (web/dist) em /.

Mesmo endereço para os dois, como no desenvolvimento (lá quem junta é o
proxy do Vite): o navegador fala com uma origem só, sem CORS, e o fluxo ao
vivo (/api/eventos) e o retorno do Google (/api/auth/google/retorno) ficam
iguais. Rode com UM processo (o ao vivo guarda as conexões na memória):

    uvicorn api.servidor:app --host 0.0.0.0 --port 8000 --proxy-headers

Variáveis: as da API (DATABASE_URL, JWT_SECRET, APP_URL, API_URL, SMTP_*,
GOOGLE_*) e WEB_DIST (padrão: web/dist).
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles

from .main import app as api

PASTA_WEB = Path(os.environ.get("WEB_DIST", Path(__file__).resolve().parent.parent / "web" / "dist"))

# Em produção (APP_URL com https), sem uma chave forte os logins cairiam a cada
# reinício (e uma chave fraca deixaria forjar logins): melhor nem subir.
if os.environ.get("APP_URL", "").startswith("https://") and len(os.environ.get("JWT_SECRET", "")) < 32:
    raise RuntimeError("Defina JWT_SECRET (pelo menos 32 caracteres aleatórios) no deploy/.env.")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)


@app.get("/saude", include_in_schema=False)
def saude():
    """Para o Docker/Caddy saberem se o servidor está de pé."""
    return {"ok": True}


if (PASTA_WEB / "assets").is_dir():
    # arquivos com hash no nome: podem ficar em cache "para sempre"
    app.mount("/assets", StaticFiles(directory=PASTA_WEB / "assets"), name="assets")


@app.get("/{caminho:path}", include_in_schema=False)
def interface(caminho: str):
    """Arquivos da raiz (ícones, manifesto, service worker) ou, para qualquer
    outra rota (/mesas/123...), o index.html: quem resolve a rota é o React."""
    if not (PASTA_WEB / "index.html").is_file():
        return Response("A interface não foi gerada: rode `npm run build` em web/.", status_code=503)
    arquivo = (PASTA_WEB / caminho).resolve()
    if caminho and arquivo.is_file() and PASTA_WEB.resolve() in arquivo.parents:
        # o service worker e o manifesto não podem ficar presos em cache (senão o app não atualiza)
        sem_cache = arquivo.name in ("sw.js", "manifest.webmanifest")
        return FileResponse(arquivo, headers={"Cache-Control": "no-cache"} if sem_cache else None)
    return FileResponse(PASTA_WEB / "index.html", headers={"Cache-Control": "no-cache"})
