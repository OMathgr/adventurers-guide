# Imagem de produção do Adventurer's Guide: a interface (web/dist) e a API num
# processo só (api/servidor.py). Funciona em ARM (VM gratuita da Oracle) e x86.

# --- 1. interface ---------------------------------------------------------------------------
FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- 2. API --------------------------------------------------------------------------------
FROM python:3.14-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
# só as dependências da API (lidas do pyproject.toml; o projeto não é instalado como pacote)
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" \
        > requisitos.txt \
    && pip install --no-cache-dir -r requisitos.txt
COPY motor/ motor/
COPY api/ api/
COPY data/ data/
COPY migrations/ migrations/
COPY alembic.ini ./
COPY --from=web /web/dist web/dist

# o banco e os backups ficam num volume (sobrevivem a atualizar a imagem)
ENV DATABASE_URL=sqlite:////dados/adventurers.db
VOLUME /dados
EXPOSE 8000
# aplica as migrações e sobe UM processo (o ao vivo guarda as conexões na memória)
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn api.servidor:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
