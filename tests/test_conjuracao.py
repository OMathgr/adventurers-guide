from motor import Conjuracao, Escolha, Opcao, SubidaDeNivel, Traco

# Bardo base (conftest): Troubadour conjura com Presença 2; Conhecimento 1.


def test_bardo_conjura_com_presenca(bardo):
    assert bardo.ficha().conjuracoes == [Conjuracao("Troubadour", Traco.PRESENCA, 2)]


def test_subclasse_sem_conjuracao(bib, guerreiro):
    assert guerreiro.ficha().conjuracoes == []


def test_conjuracao_acompanha_o_traco(bardo):
    bardo.subir_de_nivel(SubidaDeNivel(
        nivel=2,
        escolhas=[Escolha(Opcao.EVASAO), Escolha(Opcao.TRACOS, tracos=(Traco.PRESENCA, Traco.FORCA))],
        carta="core_domain_card_tell_no_lies",
        nova_experiencia="Viajante",
    ))
    assert bardo.ficha().conjuracoes[0].bonus == 3


def test_modificador_de_traco_do_equipamento_afeta_conjuracao(bardo):
    bardo.equipar(armadura="core_armor_bellamoi_fine_armor")    # Gilded: +1 Presença
    assert bardo.ficha().conjuracoes[0].bonus == 3
    bardo.equipar(armadura="core_armor_savior_chainmail")       # Difficult: -1 em tudo
    assert bardo.ficha().conjuracoes[0].bonus == 1


def test_channeling_soma_na_conjuracao(bardo):
    bardo.equipar(armadura="core_armor_channeling_armor")       # +1 to Spellcast Rolls
    f = bardo.ficha()
    assert f.conjuracoes[0].bonus == 3
    assert f.tracos[Traco.PRESENCA] == 2                        # o traço em si não muda


def test_multiclasse_conjuradora_adiciona_segunda_conjuracao(bardo_nivel_4):
    bardo_nivel_4.equipar(armadura="core_armor_channeling_armor")
    bardo_nivel_4.subir_de_nivel(SubidaDeNivel(
        5, [Escolha(Opcao.MULTICLASSE, classe="core_class_wizard", dominio="SPLENDOR",
                    subclasse="core_subclass_school_of_knowledge")],
        carta="core_domain_card_hypnotic_shimmer",
        nova_experiencia="Y",
    ))
    assert bardo_nivel_4.ficha().conjuracoes == [
        Conjuracao("Troubadour", Traco.PRESENCA, 2 + 1),
        Conjuracao("School of Knowledge", Traco.CONHECIMENTO, 1 + 1),
    ]
