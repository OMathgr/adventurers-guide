"""Fotos: envio (com login, tipo e tamanho conferidos) e uso em personagem, NPC e inimigo."""

from datetime import datetime, timedelta, timezone

from dados_api import entrar
from test_api_conteudo import INIMIGO

from api.seguranca import criar_passe_de_imagens

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def enviar(cliente, dados, nome="foto.png", tipo="image/png"):
    return cliente.post("/imagens", files={"arquivo": (nome, dados, tipo)})


def test_envia_e_le_a_imagem_com_o_passe(cliente):
    r = enviar(cliente, PNG)
    assert r.status_code == 201
    imagem = r.json()
    assert imagem["url"] == f"/imagens/{imagem['id']}"
    passe = cliente.post("/imagens/passe").json()["passe"]
    cliente.headers.pop("Authorization")   # a tag <img> não manda token: o passe vai no link
    lida = cliente.get(imagem["url"], params={"passe": passe})
    assert lida.status_code == 200 and lida.content == PNG
    assert lida.headers["content-type"] == "image/png"
    assert lida.headers["x-content-type-options"] == "nosniff"
    assert lida.headers["cache-control"].startswith("private")
    assert cliente.get("/imagens/nao-existe", params={"passe": passe}).status_code == 404


def test_sem_passe_valido_a_imagem_nao_abre(cliente):
    foto = enviar(cliente, PNG).json()["id"]
    login = cliente.headers["Authorization"].removeprefix("Bearer ")
    assert cliente.get(f"/imagens/{foto}").status_code == 401   # nem com o login no cabeçalho
    assert cliente.get(f"/imagens/{foto}", params={"passe": "inventado"}).status_code == 401
    assert cliente.get(f"/imagens/{foto}", params={"passe": login}).status_code == 401   # o login não entra em link


def test_o_passe_expira_em_ate_duas_horas_e_e_estavel_durante_a_hora(cliente):
    foto = enviar(cliente, PNG).json()["id"]
    uid = cliente.get("/auth/eu").json()["id"]
    agora = datetime.now(timezone.utc)
    assert cliente.get(f"/imagens/{foto}", params={"passe": criar_passe_de_imagens(uid, agora)}).status_code == 200
    vencido = criar_passe_de_imagens(uid, agora - timedelta(hours=2, seconds=1))
    assert cliente.get(f"/imagens/{foto}", params={"passe": vencido}).status_code == 401
    hora = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    assert criar_passe_de_imagens(uid, hora) == criar_passe_de_imagens(uid, hora + timedelta(minutes=59))
    assert criar_passe_de_imagens(uid, hora) != criar_passe_de_imagens(uid, hora + timedelta(hours=1))


def test_o_passe_nao_serve_como_login(cliente):
    passe = cliente.post("/imagens/passe").json()["passe"]
    cliente.headers.pop("Authorization")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {passe}"}).status_code == 401


def test_passe_exige_login(anonimo):
    assert anonimo.post("/imagens/passe").status_code == 401


def test_passe_de_conta_excluida_nao_abre_mais(cliente):
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    foto = enviar(cliente, PNG).json()["id"]
    passe = cliente.post("/imagens/passe", headers=bia).json()["passe"]
    assert cliente.get(f"/imagens/{foto}", params={"passe": passe}).status_code == 200
    cliente.request("DELETE", "/auth/eu", json={"email": "bia@exemplo.com"}, headers=bia)
    assert cliente.get(f"/imagens/{foto}", params={"passe": passe}).status_code == 401


def test_tipo_pelos_bytes_e_tamanho(cliente):
    # o nome e o Content-Type dizem PNG, mas o conteúdo é texto
    r = enviar(cliente, b"<svg onload=alert(1)>", tipo="image/png")
    assert r.status_code == 422 and "JPG, PNG ou WebP" in r.json()["detail"]
    assert enviar(cliente, JPG, "x.png", "image/png").json()["id"]           # vale o conteúdo
    grande = enviar(cliente, PNG + b"\x00" * (2 * 1024 * 1024))
    assert grande.status_code == 422 and "2 MB" in grande.json()["detail"]


def test_envio_exige_login(anonimo):
    assert anonimo.post("/imagens", files={"arquivo": ("f.png", PNG, "image/png")}).status_code == 401


def test_foto_no_personagem_npc_e_inimigo(cliente, bardo_id):
    foto = enviar(cliente, PNG).json()["id"]
    r = cliente.put(f"/personagens/{bardo_id}/foto", json={"imagem_id": foto})
    assert r.json()["foto"] == foto
    assert cliente.get("/personagens").json()[0]["foto"] == foto
    assert cliente.put(f"/personagens/{bardo_id}/foto", json={"imagem_id": "inventada"}).status_code == 404
    assert cliente.put(f"/personagens/{bardo_id}/foto", json={"imagem_id": None}).json()["foto"] is None

    mesa = cliente.post("/mesas", json={"nome": "M"}).json()
    npc = cliente.post(f"/mesas/{mesa['id']}/npcs", json={"nome": "Marlowe", "foto": foto}).json()
    assert npc["foto"] == foto
    inimigo = cliente.post(f"/mesas/{mesa['id']}/inimigos", json={**INIMIGO, "foto": foto}).json()
    assert inimigo["foto"] == foto
    assert cliente.post(f"/mesas/{mesa['id']}/inimigos", json={**INIMIGO, "foto": "x"}).status_code == 404
