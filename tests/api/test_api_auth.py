from datetime import datetime, timedelta, timezone

from dados_api import BARDO, entrar

from api.seguranca import EXPIRA_MINUTOS, criar_token


def cadastrar(c, email="bia@exemplo.com", senha="senha-forte-123", nome="Bia"):
    return c.post("/auth/cadastro", json={"email": email, "nome": nome, "senha": senha})


def login(c, email="bia@exemplo.com", senha="senha-forte-123"):
    return c.post("/auth/login", data={"username": email, "password": senha})


# --- Cadastro e login ---------------------------------------------------------------

def test_cadastro_e_login(anonimo):
    r = cadastrar(anonimo, email="Bia@Exemplo.com")
    assert r.status_code == 201
    assert r.json()["email"] == "bia@exemplo.com"           # e-mail sempre minúsculo
    assert "senha-forte" not in r.text and "hash" not in r.text and "argon2" not in r.text   # nada de senha na resposta
    token = login(anonimo, email="BIA@exemplo.com").json()["access_token"]
    eu = anonimo.get("/auth/eu", headers={"Authorization": f"Bearer {token}"}).json()
    assert (eu["email"], eu["nome"]) == ("bia@exemplo.com", "Bia")


def test_email_repetido(anonimo):
    cadastrar(anonimo)
    assert cadastrar(anonimo, email="BIA@exemplo.com").status_code == 409


def test_cadastro_invalido(anonimo):
    assert cadastrar(anonimo, senha="curta").status_code == 422
    assert cadastrar(anonimo, email="nao-e-email").status_code == 422


def test_login_errado_nao_revela_se_o_email_existe(anonimo):
    cadastrar(anonimo)
    senha_errada = login(anonimo, senha="outra-senha-999")
    email_inexistente = login(anonimo, email="ninguem@exemplo.com")
    assert senha_errada.status_code == email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json()


def test_senha_guardada_como_hash(anonimo):
    from api.tabelas import UsuarioTabela
    from api.db import sessao_do_banco
    from api.main import app
    cadastrar(anonimo)
    banco = next(app.dependency_overrides[sessao_do_banco]())
    usuario = banco.query(UsuarioTabela).one()
    assert usuario.senha_hash.startswith("$argon2") and "senha-forte-123" not in usuario.senha_hash


# --- Rotas protegidas -------------------------------------------------------------------

def test_personagens_exigem_login(anonimo):
    assert anonimo.get("/personagens").status_code == 401
    assert anonimo.post("/personagens", json=BARDO).status_code == 401
    assert anonimo.post("/personagens/x/sessao/dano", json={"dano": 1}).status_code == 401


def test_catalogo_do_srd_e_publico(anonimo):
    assert anonimo.get("/srd/classes").status_code == 200


def test_token_invalido_ou_expirado(anonimo):
    cadastrar(anonimo)
    assert anonimo.get("/auth/eu", headers={"Authorization": "Bearer lixo"}).status_code == 401
    usuario_id = cadastrar(anonimo, email="velho@exemplo.com").json()["id"]
    passado = datetime.now(timezone.utc) - timedelta(minutes=EXPIRA_MINUTOS + 1)
    vencido = criar_token(usuario_id, agora=passado)
    r = anonimo.get("/auth/eu", headers={"Authorization": f"Bearer {vencido}"})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


# --- Cada um vê só os seus personagens ---------------------------------------------------

def test_personagem_de_outro_usuario_parece_inexistente(cliente, bardo_id):
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    assert cliente.get("/personagens", headers=bia).json() == []
    assert cliente.get(f"/personagens/{bardo_id}", headers=bia).status_code == 404
    assert cliente.post(f"/personagens/{bardo_id}/sessao/dano", json={"dano": 3},
                        headers=bia).status_code == 404
    assert cliente.delete(f"/personagens/{bardo_id}", headers=bia).status_code == 404
    # a dona continua vendo e nada mudou
    assert cliente.get(f"/personagens/{bardo_id}").json()["pv_marcados"] == 0


def test_apagar_conta_apaga_os_personagens(cliente, bardo_id):
    assert cliente.delete("/auth/eu").status_code == 204
    assert cliente.get(f"/personagens/{bardo_id}").status_code == 401   # token de conta apagada
    novo = entrar(cliente, "ana@exemplo.com")                             # recria a conta
    assert cliente.get("/personagens", headers=novo).json() == []
