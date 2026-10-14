"""Servidor de produção (api/servidor.py): API em /api e a interface em /."""

import pytest
from fastapi.testclient import TestClient

import api.servidor as servidor


@pytest.fixture
def site(anonimo, tmp_path, monkeypatch):
    """O servidor de produção com uma interface de mentira (e o banco de teste do `anonimo`)."""
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "sw.js").write_text("// sw", encoding="utf-8")
    (tmp_path / "icone.svg").write_text("<svg/>", encoding="utf-8")
    monkeypatch.setattr(servidor, "PASTA_WEB", tmp_path)
    with TestClient(servidor.app) as c:
        yield c


def test_api_fica_em_barra_api(site):
    assert site.get("/api/auth/provedores").status_code == 200
    assert site.get("/api/srd/classes").json()[0]["id"].startswith("core_class_")
    assert site.get("/saude").json() == {"ok": True}


def test_rotas_do_react_devolvem_o_index(site):
    for caminho in ("/", "/mesas/123", "/personagens/abc?visao=inventario", "/entrar/google"):
        r = site.get(caminho)
        assert r.status_code == 200 and r.text == "<html>app</html>", caminho


def test_arquivos_da_raiz_e_service_worker_sem_cache(site):
    assert site.get("/icone.svg").text == "<svg/>"
    r = site.get("/sw.js")
    assert r.text == "// sw" and r.headers["cache-control"] == "no-cache"


def test_nao_sai_da_pasta_da_interface(site):
    r = site.get("/..%2F..%2Fpyproject.toml")
    assert r.text == "<html>app</html>"   # nada fora de web/dist: cai no index
