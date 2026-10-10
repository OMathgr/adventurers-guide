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
