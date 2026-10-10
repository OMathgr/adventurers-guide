import pytest

from motor import Biblioteca, Criacao, Escolha, Opcao, Personagem, SubidaDeNivel, Traco


@pytest.fixture(scope="session")
def bib():
    return Biblioteca()


@pytest.fixture
def criacao_bardo():
    return Criacao(
        nome="Lira",
        classe="core_class_bard",
        subclasse="core_subclass_troubadour",
        ancestralidade="core_ancestry_faun",   # sem efeito numérico
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


@pytest.fixture
def bardo_nivel_4(bardo):
    """Bardo pronto para o nível 5 (onde dá para multiclassear)."""
    bardo.subir_de_nivel(SubidaDeNivel(2, [Escolha(Opcao.EVASAO), Escolha(Opcao.PV)],
                                       "core_domain_card_tell_no_lies", nova_experiencia="X"))
    bardo.subir_de_nivel(SubidaDeNivel(3, [Escolha(Opcao.ESTRESSE), Escolha(Opcao.PV)],
                                       "core_domain_card_troublemaker"))
    bardo.subir_de_nivel(SubidaDeNivel(4, [Escolha(Opcao.ESTRESSE),
                                           Escolha(Opcao.TRACOS, tracos=(Traco.FORCA, Traco.INSTINTO))],
                                       "core_domain_card_invisibility"))
    return bardo


@pytest.fixture
def guerreiro(bib):
    return Personagem(bib, Criacao(
        nome="Bruna",
        classe="core_class_warrior",
        subclasse="core_subclass_call_of_the_brave",
        ancestralidade="core_ancestry_faun",   # sem efeito numérico
        comunidade="core_community_highborne",
        tracos={
            Traco.FORCA: 2, Traco.AGILIDADE: 1, Traco.INSTINTO: 1,
            Traco.ACUIDADE: 0, Traco.PRESENCA: 0, Traco.CONHECIMENTO: -1,
        },
        experiencias=["Soldada", "Ferreira"],
        cartas=["core_domain_card_get_back_up", "core_domain_card_whirlwind"],
    ))
