"""As migrações do Alembic precisam criar exatamente as tabelas de api/tabelas.py."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from api.db import Base, criar_engine


def test_migracoes_batem_com_as_tabelas(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migrado.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = criar_engine(url)
    with engine.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)
    engine.dispose()
    assert diferencas == [], "Gere uma migração: alembic revision --autogenerate -m '...'"


def test_migrar_nao_apaga_dados(tmp_path, monkeypatch):
    """No SQLite, recriar a tabela `mesas` (o "batch" do Alembic) apaga em cascata
    membros, sessões e lojas e desvincula os personagens. Mudança em `mesas`
    precisa ser um ALTER TABLE simples."""
    from sqlalchemy import text

    url = f"sqlite:///{(tmp_path / 'dados.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "ce777afa6c3f")   # antes do inventário (e de tudo o que veio depois)
    engine = criar_engine(url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO usuarios (id, email, nome, senha_hash, criado_em) "
                       "VALUES ('u1', 'a@a.com', 'Ana', 'x', '2026-01-01')"))
        c.execute(text("INSERT INTO mesas (id, nome, criador_id, codigo_convite, permissoes_mestres, nivel_maximo, "
                       "criado_em) VALUES ('m1', 'Mesa', 'u1', 'ABC', '{}', 3, '2026-01-01')"))
        c.execute(text("INSERT INTO membros_mesa (mesa_id, usuario_id, papel, entrou_em) "
                       "VALUES ('m1', 'u1', 'mestre', '2026-01-01')"))
        c.execute(text("INSERT INTO sessoes (id, mesa_id, responsavel_id, titulo, resumo, notas, status, medo, "
                       "compartilhada_com, npcs, inimigos, quadro, criado_em, atualizado_em) VALUES "
                       "('s1', 'm1', 'u1', 'S', '', '', 'planejada', 0, '[]', '[]', '[]', '{}', '2026-01-01', '2026-01-01')"))
        c.execute(text("INSERT INTO personagens (id, dono_id, mesa_id, nome, criacao, equipamento, cofre, sessao, plano, "
                       "criado_em, atualizado_em) VALUES ('p1', 'u1', 'm1', 'Lira', '{}', '{}', '[]', '{}', '[]', "
                       "'2026-01-01', '2026-01-01')"))
        c.execute(text("INSERT INTO subidas_de_nivel (personagem_id, nivel, dados) VALUES ('p1', 2, '{}')"))

    def contar():
        with engine.connect() as c:
            return (c.execute(text("SELECT count(*) FROM membros_mesa")).scalar(),
                    c.execute(text("SELECT count(*) FROM sessoes")).scalar(),
                    c.execute(text("SELECT mesa_id FROM personagens")).scalar(),
                    c.execute(text("SELECT count(*) FROM subidas_de_nivel")).scalar())

    command.upgrade(config, "head")
    assert contar() == (1, 1, "m1", 1)
    command.downgrade(config, "ce777afa6c3f")
    assert contar() == (1, 1, "m1", 1)
    engine.dispose()


def test_npcs_existentes_ganham_dono_e_visibilidade(tmp_path, monkeypatch):
    """Antes não havia dono: fica quem criou a mesa; o revelado vira "todos", o resto "mestres"."""
    from sqlalchemy import text

    url = f"sqlite:///{(tmp_path / 'npcs.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "45a719f76e56")
    engine = criar_engine(url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO usuarios (id, email, nome, senha_hash, criado_em) "
                       "VALUES ('u1', 'a@a.com', 'Ana', 'x', '2026-01-01')"))
        c.execute(text("INSERT INTO mesas (id, nome, criador_id, codigo_convite, permissoes_mestres, nivel_maximo, "
                       "criado_em) VALUES ('m1', 'Mesa', 'u1', 'ABC', '{}', 3, '2026-01-01')"))
        for npc_id, revelado in (("n1", 1), ("n2", 0)):
            c.execute(text("INSERT INTO npcs (id, mesa_id, nome, descricao, motivacoes, notas, revelado, criado_em, "
                           f"atualizado_em) VALUES ('{npc_id}', 'm1', 'X', '', '', '', {revelado}, '2026-01-01', "
                           "'2026-01-01')"))
    command.upgrade(config, "head")
    with engine.connect() as c:
        linhas = c.execute(text("SELECT id, dono_id, visibilidade FROM npcs ORDER BY id")).all()
    assert [tuple(x) for x in linhas] == [("n1", "u1", "todos"), ("n2", "u1", "mestres")]
    engine.dispose()
