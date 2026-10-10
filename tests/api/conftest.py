import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db import Base, criar_engine, sessao_do_banco
from api.main import app
from dados_api import BARDO


@pytest.fixture
def cliente():
    """API com um banco SQLite em memória novo para cada teste."""
    engine = criar_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)

    def banco_de_teste():
        with fabrica() as sessao:
            yield sessao

    app.dependency_overrides[sessao_do_banco] = banco_de_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def bardo_id(cliente):
    resposta = cliente.post("/personagens", json=BARDO)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]
