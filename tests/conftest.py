import pytest

from motor import Biblioteca, Criacao, Personagem, Traco


@pytest.fixture(scope="session")
def bib():
    return Biblioteca()


@pytest.fixture
def criacao_bardo():
    return Criacao(
        nome="Lira",
        classe="core_class_bard",
        subclasse="core_subclass_troubadour",
        ancestralidade="core_ancestry_clank",
        comunidade="core_community_highborne",
        tracos={
            Traco.PRESENCA: 2, Traco.AGILIDADE: 1, Traco.CONHECIMENTO: 1,
            Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1,
        },
        experiencias=["Diplomata", "Cantora de taverna"],
        cartas=["core_domain_card_inspirational_words", "core_domain_card_book_of_ava"],
    )


@pytest.fixture
def bardo(bib, criacao_bardo):
    return Personagem(bib, criacao_bardo)
