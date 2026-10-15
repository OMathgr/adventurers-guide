"""Corpos de requisição e atalhos usados nos testes da API."""

from fastapi.testclient import TestClient

BARDO = {
    "nome": "Lira",
    "classe": "core_class_bard",
    "subclasse": "core_subclass_troubadour",
    "ancestralidade": "core_ancestry_faun",
    "comunidade": "core_community_highborne",
    "tracos": {"PRESENCE": 2, "AGILITY": 1, "KNOWLEDGE": 1,
               "FINESSE": 0, "INSTINCT": 0, "STRENGTH": -1},
    "experiencias": ["Diplomata", "Cantora de taverna"],
    "cartas": ["core_domain_card_inspirational_words", "core_domain_card_book_of_ava"],
}

NIVEL_2 = {
    "nivel": 2,
    "escolhas": [{"opcao": "EVASAO"}, {"opcao": "PV"}],
    "carta": "core_domain_card_tell_no_lies",
    "nova_experiencia": "Viajante",
}


def entrar(cliente: TestClient, email: str, senha: str = "senha-forte-123", nome: str = "Ana") -> dict:
    """Cadastra (se preciso) e faz login; devolve o cabeçalho de autorização."""
    cliente.post("/auth/cadastro", json={"email": email, "nome": nome, "senha": senha})
    resposta = cliente.post("/auth/login", data={"username": email, "password": senha})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def colocar_em_jogo(cliente: TestClient, personagem_id: str, jogador: dict | None = None,
                    mesa: dict | None = None, mestre: dict | None = None) -> dict:
    """Põe o personagem numa sessão em andamento: marcas de jogo só valem nela.

    Sem `mesa`, o Guilherme cria uma mesa (e é o mestre); o dono do personagem
    (`jogador`, padrão: o cliente logado) entra nela. Devolve mesa, sessão e
    o cabeçalho do mestre."""
    jogador = jogador or {}
    if mesa is None:
        mestre = entrar(cliente, "gui@exemplo.com", nome="Guilherme")
        mesa = cliente.post("/mesas", json={"nome": "Mesa de teste"}, headers=mestre).json()
        cliente.post(f"/mesas/entrar/{mesa['codigo_convite']}", headers=jogador)
    if cliente.get(f"/personagens/{personagem_id}", headers=jogador).status_code == 200:
        cliente.put(f"/personagens/{personagem_id}/mesa", json={"mesa_id": mesa["id"]}, headers=jogador)
    sessao = cliente.post(f"/mesas/{mesa['id']}/sessoes", json={"titulo": "Sessão"}, headers=mestre).json()
    cliente.put(f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/status", json={"status": "em_andamento"}, headers=mestre)
    r = cliente.post(f"/mesas/{mesa['id']}/sessoes/{sessao['id']}/participantes",
                     json={"personagem_id": personagem_id}, headers=jogador)
    assert r.status_code == 200, r.text
    return {"mesa": mesa, "sessao": sessao, "mestre": mestre}
