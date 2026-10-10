import pytest

from motor import Criacao, Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel, Traco


def subir_para_nivel_2(personagem):
    personagem.subir_de_nivel(SubidaDeNivel(
        nivel=2,
        escolhas=[Escolha(Opcao.EVASAO), Escolha(Opcao.PV)],
        carta="core_domain_card_tell_no_lies",
        nova_experiencia="Viajante",
    ))


@pytest.fixture
def guerreiro(bib):
    return Personagem(bib, Criacao(
        nome="Bruna",
        classe="core_class_warrior",
        subclasse="core_subclass_call_of_the_brave",
        ancestralidade="core_ancestry_clank",
        comunidade="core_community_highborne",
        tracos={
            Traco.FORCA: 2, Traco.AGILIDADE: 1, Traco.INSTINTO: 1,
            Traco.ACUIDADE: 0, Traco.PRESENCA: 0, Traco.CONHECIMENTO: -1,
        },
        experiencias=["Soldada", "Ferreira"],
        cartas=["core_domain_card_get_back_up", "core_domain_card_whirlwind"],
    ))


# --- Biblioteca ---------------------------------------------------------------

def test_biblioteca_carrega_armas_e_armaduras(bib):
    espada = bib.armas["core_weapon_longsword"]
    assert espada.nome == "Longsword"
    assert espada.traco is Traco.AGILIDADE
    assert espada.dado == "d10"
    assert espada.modificador_dano == 3
    assert espada.duas_maos

    couro = bib.armaduras["core_armor_leather_armor"]
    assert (couro.limiar_maior, couro.limiar_grave, couro.pontuacao) == (6, 13, 3)


# --- Armadura e limiares --------------------------------------------------------

def test_sem_armadura_limiares_sao_nivel_e_dobro(bardo):
    ficha = bardo.ficha()
    assert (ficha.limiar_maior, ficha.limiar_grave, ficha.pontuacao_armadura) == (1, 2, 0)


def test_armadura_soma_nivel_aos_limiares(bardo):
    bardo.equipar(armadura="core_armor_leather_armor")
    ficha = bardo.ficha()
    assert (ficha.limiar_maior, ficha.limiar_grave, ficha.pontuacao_armadura) == (7, 14, 3)

    subir_para_nivel_2(bardo)
    assert (bardo.ficha().limiar_maior, bardo.ficha().limiar_grave) == (8, 15)


# --- Armas e ataques -------------------------------------------------------------

def test_ataque_usa_traco_da_arma_e_proficiencia_no_dano(bardo):
    bardo.equipar(principal="core_weapon_mace")
    ataque = bardo.ficha().ataques[0]
    assert ataque.arma == "Mace"
    assert ataque.traco is Traco.FORCA
    assert ataque.dano == "1d8+1"

    subir_para_nivel_2(bardo)  # conquista de tier: Proficiência 2
    assert bardo.ficha().ataques[0].dano == "2d8+1"


def test_dano_sem_modificador(bardo):
    bardo.equipar(principal="core_weapon_broadsword")
    assert bardo.ficha().ataques[0].dano == "1d8"


def test_principal_e_secundaria_geram_dois_ataques(bardo):
    bardo.equipar(principal="core_weapon_broadsword", secundaria="core_weapon_shortsword")
    assert [a.arma for a in bardo.ficha().ataques] == ["Broadsword", "Shortsword"]


def test_arma_de_duas_maos_impede_secundaria(bardo):
    with pytest.raises(RegraViolada):
        bardo.equipar(principal="core_weapon_longsword", secundaria="core_weapon_shortsword")


def test_arma_no_espaco_errado(bardo):
    with pytest.raises(RegraViolada):
        bardo.equipar(principal="core_weapon_shortsword")
    with pytest.raises(RegraViolada):
        bardo.equipar(secundaria="core_weapon_broadsword")


def test_arma_magica_exige_traco_de_conjuracao(bardo, guerreiro):
    bardo.equipar(principal="core_weapon_wand")  # Troubadour conjura com Presença
    with pytest.raises(RegraViolada):
        guerreiro.equipar(principal="core_weapon_wand")


def test_equipamento_inexistente(bardo):
    with pytest.raises(RegraViolada):
        bardo.equipar(principal="core_weapon_sabre_de_luz")
    with pytest.raises(RegraViolada):
        bardo.equipar(armadura="core_armor_de_papelao")


def test_equipar_invalido_nao_muda_nada(bardo):
    bardo.equipar(principal="core_weapon_broadsword", armadura="core_armor_leather_armor")
    with pytest.raises(RegraViolada):
        bardo.equipar(principal="core_weapon_longsword", secundaria="core_weapon_shortsword")
    ficha = bardo.ficha()
    assert [a.arma for a in ficha.ataques] == ["Broadsword"]
    assert ficha.pontuacao_armadura == 3
