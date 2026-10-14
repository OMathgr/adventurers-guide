"""Cópia de segurança do banco SQLite (produção).

Usa a API de backup do próprio SQLite: copia certo mesmo com o servidor
gravando ao mesmo tempo (copiar o arquivo direto poderia pegar no meio de
uma gravação). Guarda as últimas N cópias.

    python -m api.backup                 # uma cópia agora
    python -m api.backup --a-cada 24     # uma cópia a cada 24 horas (serviço do docker compose)

Variáveis: DATABASE_URL (sqlite:///...), PASTA_BACKUP (padrão: backups/ ao
lado do banco), BACKUPS_GUARDADOS (padrão: 14).
"""

import argparse
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger("backup")


def caminho_do_banco(url: str) -> Path:
    if not url.startswith("sqlite:///"):
        raise SystemExit("O backup automático é só para SQLite (no PostgreSQL, use o backup do provedor ou pg_dump).")
    return Path(url.removeprefix("sqlite:///"))


def fazer_backup(banco: Path, pasta: Path, guardar: int = 14, agora: datetime | None = None) -> Path:
    """Copia o banco para pasta/adventurers-AAAAMMDD-HHMMSS.db e apaga as cópias mais antigas."""
    pasta.mkdir(parents=True, exist_ok=True)
    agora = agora or datetime.now(timezone.utc)
    destino = pasta / f"adventurers-{agora:%Y%m%d-%H%M%S}.db"
    origem = sqlite3.connect(banco)
    try:
        copia = sqlite3.connect(destino)
        try:
            origem.backup(copia)
        finally:
            copia.close()
    finally:
        origem.close()
    for velho in sorted(pasta.glob("adventurers-*.db"))[:-guardar]:
        velho.unlink()
    return destino


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--a-cada", type=float, metavar="HORAS", help="repete a cada tantas horas")
    opcoes = argumentos.parse_args()
    banco = caminho_do_banco(os.environ.get("DATABASE_URL", "sqlite:///adventurers.db"))
    pasta = Path(os.environ.get("PASTA_BACKUP", banco.parent / "backups"))
    guardar = int(os.environ.get("BACKUPS_GUARDADOS", "14"))
    while True:
        if banco.exists():
            _log.info("Backup feito: %s", fazer_backup(banco, pasta, guardar))
        else:
            _log.warning("Banco ainda não existe: %s", banco)
        if not opcoes.a_cada:
            return
        time.sleep(opcoes.a_cada * 3600)


if __name__ == "__main__":
    main()
