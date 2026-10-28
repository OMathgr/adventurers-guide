"""Matriz de acesso: TODA rota da API (pelo OpenAPI, então as novas entram
sozinhas) é chamada por quem não deveria poder, e precisa recusar (401, 403
ou 404). A tela só esconde botões; quem decide é a API.

- Alguém de fora da mesa, com conta: nada da mesa nem dos personagens dos outros.
- Uma jogadora da mesa (sem permissões de mestre): nada do lado do mestre, nem
  agir no personagem de outro jogador; só o que é de qualquer membro.

O corpo de cada pedido é gerado do OpenAPI (válido), para a resposta refletir o
acesso e não um corpo malformado. Rotas que a pessoa PODE usar ficam nas listas
abaixo e não são chamadas (só as recusas interessam aqui).
"""

import re

import pytest
from dados_api import BARDO, colocar_em_jogo, entrar

from api.main import app

NEGADO = {401, 403, 404}

# rotas sem dono de recurso: públicas ou só do próprio usuário (a rota usa o login)
PROPRIAS = {
    ("POST", "/auth/cadastro"), ("POST", "/auth/login"), ("POST", "/auth/renovar"), ("GET", "/auth/eu"),
    ("DELETE", "/auth/eu"), ("POST", "/auth/recuperar"), ("POST", "/auth/redefinir"), ("GET", "/auth/provedores"),
    ("GET", "/auth/google"), ("POST", "/auth/google/ligar"), ("GET", "/auth/google/retorno"), ("DELETE", "/auth/google"),
    ("POST", "/personagens"), ("GET", "/personagens"), ("GET", "/mesas"), ("POST", "/mesas"),
    ("POST", "/mesas/entrar/{codigo}"), ("POST", "/imagens"),
    ("GET", "/imagens/{imagem_id}"),   # pública pelo id (aleatório): o navegador carrega por <img>, sem login
}

# o que qualquer membro da mesa pode (a jogadora não é testada nestas)
DE_QUALQUER_MEMBRO = {
    ("GET", "/mesas/{mesa_id}"), ("POST", "/mesas/{mesa_id}/sair"),
    ("GET", "/mesas/{mesa_id}/personagens/{personagem_id}/resumo"),
    ("GET", "/mesas/{mesa_id}/sessoes"), ("GET", "/mesas/{mesa_id}/sessoes/{sessao_id}/jogo"),
    ("GET", "/mesas/{mesa_id}/revelado"), ("GET", "/mesas/{mesa_id}/quadro-da-campanha"),
    ("GET", "/mesas/{mesa_id}/repouso"), ("GET", "/mesas/{mesa_id}/sessoes/{sessao_id}/repouso"),
    ("GET", "/mesas/{mesa_id}/sessoes/{sessao_id}/rolagens"),
    ("POST", "/mesas/{mesa_id}/sessoes/{sessao_id}/rolagens"),        # rolagem livre, sem personagem
}


def _rotas():
    for caminho, metodos in app.openapi()["paths"].items():
        for metodo, op in metodos.items():
            yield metodo.upper(), caminho, op


def _exemplo(schema: dict, comps: dict, profundidade=0):
    """Um valor válido (mínimo) para o esquema do OpenAPI."""
    if "$ref" in schema:
        return _exemplo(comps[schema["$ref"].split("/")[-1]], comps, profundidade)
    for chave in ("anyOf", "oneOf"):
        if chave in schema:
            opcoes = [s for s in schema[chave] if s.get("type") != "null"]
            return _exemplo(opcoes[0], comps, profundidade) if opcoes else None
    if "allOf" in schema:
        return _exemplo(schema["allOf"][0], comps, profundidade)
    if "enum" in schema:
        return schema["enum"][0]
    if m := re.fullmatch(r"\^\((\w+)\|.*\)\$", schema.get("pattern", "")):
        return m.group(1)   # "^(jogador|mestre)$": a primeira alternativa
    if "default" in schema and profundidade > 0:
        return schema["default"]
    tipo = schema.get("type")
    if tipo == "object" or "properties" in schema:
        return {k: _exemplo(v, comps, profundidade + 1) for k, v in schema.get("properties", {}).items()
                if k in schema.get("required", [])}
    if tipo == "array":
        return []
    if tipo == "integer" or tipo == "number":
        return schema.get("minimum", schema.get("exclusiveMinimum", 0) + 1 if "exclusiveMinimum" in schema else 1)
    if tipo == "boolean":
        return False
    if schema.get("format") == "email":
        return "x@exemplo.com"
    return "x" * max(schema.get("minLength", 1), 1)


@pytest.fixture
def mundo(cliente):
    """Ana cria a mesa e mestra uma sessão em andamento; Bia e Carlos jogam nela.
    Há encontro com inimigo, loja, NPC, inimigo, item da mesa, rolagem, repouso aberto e foto."""
    mesa = cliente.post("/mesas", json={"nome": "Mesa"}).json()
    bia = entrar(cliente, "bia@exemplo.com", nome="Bia")
    carlos = entrar(cliente, "carlos@exemplo.com", nome="Carlos")
    ze = entrar(cliente, "ze@exemplo.com", nome="Zé")   # de fora
    ids = {"mesa_id": mesa["id"]}
    for h in (bia, carlos):
        cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=h)
    lira = cliente.post("/personagens", json=BARDO, headers=bia).json()["id"]
    bruno = cliente.post("/personagens", json={**BARDO, "nome": "Bruno"}, headers=carlos).json()["id"]
    jogo = colocar_em_jogo(cliente, lira, jogador=bia, mesa=mesa, mestre={})
    sessao = jogo["sessao"]
    cliente.put(f"/personagens/{bruno}/mesa", json={"mesa_id": mesa["id"]}, headers=carlos)
    base = f"/mesas/{mesa['id']}/sessoes/{sessao['id']}"
    cliente.post(f"{base}/participantes", json={"personagem_id": bruno}, headers=carlos)
    encontro = cliente.post(f"{base}/encontros", json={"nome": "Emboscada"}).json()
    adv = cliente.get("/srd/adversarios").json()[0]["id"]
    enc = cliente.post(f"{base}/encontros/{encontro['id']}/combatentes", json={"origem": "srd", "id": adv}).json()
    loja = cliente.post(f"{base}/lojas", json={"nome": "Loja"}).json()
    npc = cliente.post(f"/mesas/{mesa['id']}/npcs", json={"nome": "Velho"}).json()
    inimigo = cliente.post(f"/mesas/{mesa['id']}/inimigos/do-srd/{adv}").json()
    item = cliente.post(f"/mesas/{mesa['id']}/itens", json={"tipo": "COMUM", "nome": "Chave"}).json()
    rolagem = cliente.post(f"{base}/rolagens", json={"tipo": "livre", "expressao": "1d6"}).json()
    repouso = cliente.post(f"{base}/repouso", json={"tipo": "curto"}).json()
    foto = cliente.post("/imagens", files={"arquivo": ("a.png", _PNG, "image/png")}).json()["id"]
    carlos_id = cliente.get("/auth/eu", headers=carlos).json()["id"]
    ids.update(sessao_id=sessao["id"], personagem_id=bruno, encontro_id=encontro["id"],
               combatente_id=enc["combatentes"][0]["id"], loja_id=loja["id"],
               npc_id=npc["id"], inimigo_id=inimigo["id"], item_id=item["id"], rolagem_id=rolagem["id"],
               repouso_id=repouso["id"], imagem_id=foto, usuario_id=carlos_id, codigo="ZZZZZZZZ",
               carta="core_domain_card_inspirational_words", indice="0", nivel="2", condicao="VULNERAVEL",
               livre_id="x", classe_id="core_class_bard", adversario_id=adv)
    return {"ids": ids, "bia": bia, "ze": ze}


def _chamar(cliente, metodo, caminho, op, ids, headers, comps):
    url = re.sub(r"\{(\w+)\}", lambda m: str(ids[m.group(1)]), caminho)
    query = {p["name"]: ids.get(p["name"], "x") for p in op.get("parameters", [])
             if p["in"] == "query" and p.get("required")}
    corpo = None
    conteudo = (op.get("requestBody") or {}).get("content", {})
    if "application/json" in conteudo:
        corpo = _exemplo(conteudo["application/json"]["schema"], comps)
        if isinstance(corpo, dict):   # ids que aparecem no corpo apontam para os recursos de verdade
            corpo = {k: ids.get(k, v) for k, v in corpo.items()}
    return cliente.request(metodo, url, params=query, json=corpo, headers=headers)


def _vazamentos(cliente, mundo, quem: str, liberadas: set) -> list[str]:
    comps = app.openapi()["components"]["schemas"]
    falhas = []
    for metodo, caminho, op in _rotas():
        if (metodo, caminho) in PROPRIAS | liberadas or caminho.startswith("/srd"):
            continue
        r = _chamar(cliente, metodo, caminho, op, mundo["ids"], mundo[quem], comps)
        if r.status_code not in NEGADO:
            falhas.append(f"{metodo} {caminho} -> {r.status_code} {r.text[:120]}")
    return falhas


def test_quem_e_de_fora_nao_alcanca_nada_da_mesa(cliente, mundo):
    assert _vazamentos(cliente, mundo, "ze", set()) == []


def test_jogadora_nao_alcanca_o_lado_do_mestre_nem_os_outros_personagens(cliente, mundo):
    assert _vazamentos(cliente, mundo, "bia", DE_QUALQUER_MEMBRO) == []


# PNG 1x1 válido
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
