"""Fotos: envio (com login, tipo e tamanho conferidos) e uso em personagem, NPC e inimigo."""

from test_api_conteudo import INIMIGO

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def enviar(cliente, dados, nome="foto.png", tipo="image/png"):
    return cliente.post("/imagens", files={"arquivo": (nome, dados, tipo)})


def test_envia_e_le_a_imagem(cliente):
    r = enviar(cliente, PNG)
    assert r.status_code == 201
    imagem = r.json()
    assert imagem["url"] == f"/imagens/{imagem['id']}"
    cliente.headers.pop("Authorization")   # a tag <img> não manda token: leitura aberta pelo id
    anonimo = cliente
    lida = anonimo.get(imagem["url"])
    assert lida.status_code == 200 and lida.content == PNG
    assert lida.headers["content-type"] == "image/png"
    assert lida.headers["x-content-type-options"] == "nosniff"
    assert anonimo.get("/imagens/nao-existe").status_code == 404


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
