"""Backup do banco SQLite (api/backup.py)."""

import sqlite3
from datetime import datetime, timedelta, timezone

from api.backup import fazer_backup


def test_copia_o_banco_e_guarda_so_as_ultimas(tmp_path):
    banco = tmp_path / "adventurers.db"
    with sqlite3.connect(banco) as c:
        c.execute("create table t (x)")
        c.execute("insert into t values (42)")
    pasta = tmp_path / "backups"
    inicio = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for dia in range(5):
        ultimo = fazer_backup(banco, pasta, guardar=3, agora=inicio + timedelta(days=dia))
    copias = sorted(p.name for p in pasta.iterdir())
    assert copias == ["adventurers-20261003-000000.db", "adventurers-20261004-000000.db", "adventurers-20261005-000000.db"]
    with sqlite3.connect(ultimo) as c:
        assert c.execute("select x from t").fetchone() == (42,)
