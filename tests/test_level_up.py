import pytest

from motor import Escolha, Opcao, RegraViolada, SubidaDeNivel, Traco


def nivel_simples(nivel, carta, nova_exp=None):
    """Sobe um nível com +1 Evasão e +1 PV (atalho para os testes)."""
    return SubidaDeNivel(
        nivel=nivel,
        escolhas=[Escolha(Opcao.EVASAO), Escolha(Opcao.PV)],
        carta=carta,
        nova_experiencia=nova_exp,
    )


def test_nivel_2_completo(bardo):
    f = bardo.subir_de_nivel(SubidaDeNivel(
        nivel=2,
        escolhas=[
            Escolha(Opcao.TRACOS, tracos=(Traco.PRESENCA, Traco.AGILIDADE)),
            Escolha(Opcao.EXPERIENCIAS, experiencias=("Diplomata", "Cantora de taverna")),
        ],
        carta="core_domain_card_tell_no_lies",
        nova_experiencia="Ladino de palco",
    ))
    assert f.nivel == 2 and f.proficiencia == 2 and f.limiar_maior == 2
    assert f.tracos[Traco.PRESENCA] == 3
    assert f.experiencias == {"Diplomata": 3, "Cantora de taverna": 3, "Ladino de palco": 2}
    assert Traco.PRESENCA in f.tracos_marcados


def test_nivel_2_exige_nova_experiencia(bardo):
    with pytest.raises(RegraViolada, match="nova Experiência"):
        bardo.subir_de_nivel(nivel_simples(2, "core_domain_card_tell_no_lies"))


def test_precisa_de_dois_avancos(bardo):
    with pytest.raises(RegraViolada, match="exatamente 2"):
        bardo.subir_de_nivel(SubidaDeNivel(
            nivel=2, escolhas=[Escolha(Opcao.EVASAO)],
            carta="core_domain_card_tell_no_lies", nova_experiencia="X"))


def test_erro_nao_altera_personagem(bardo):
    with pytest.raises(RegraViolada):
        bardo.subir_de_nivel(nivel_simples(2, "carta_que_nao_existe", "X"))
    assert bardo.ficha().nivel == 1 and bardo.historico == []


def test_slot_esgotado_no_tier(bardo):
    bardo.subir_de_nivel(nivel_simples(2, "core_domain_card_tell_no_lies", "X"))
    # Evasão só tem 1 quadradinho no tier 2
    with pytest.raises(RegraViolada, match="Não há mais espaços"):
        bardo.subir_de_nivel(nivel_simples(3, "core_domain_card_troublemaker"))


def test_proficiencia_nao_existe_no_tier_2(bardo):
    with pytest.raises(RegraViolada, match="não existe no tier 2"):
        bardo.subir_de_nivel(SubidaDeNivel(
            nivel=2, escolhas=[Escolha(Opcao.PROFICIENCIA)],
            carta="core_domain_card_tell_no_lies", nova_experiencia="X"))


def test_traco_marcado_nao_sobe_de_novo(bardo):
    bardo.subir_de_nivel(SubidaDeNivel(
        nivel=2,
        escolhas=[Escolha(Opcao.TRACOS, tracos=(Traco.PRESENCA, Traco.AGILIDADE)), Escolha(Opcao.PV)],
        carta="core_domain_card_tell_no_lies", nova_experiencia="X"))
    with pytest.raises(RegraViolada, match="marcado"):
        bardo.subir_de_nivel(SubidaDeNivel(
            nivel=3,
            escolhas=[Escolha(Opcao.TRACOS, tracos=(Traco.PRESENCA, Traco.FORCA)), Escolha(Opcao.PV)],
            carta="core_domain_card_troublemaker"))



def test_nivel_5_limpa_marcas_e_permite_subclasse(bardo_nivel_4):
    bardo = bardo_nivel_4
    f = bardo.subir_de_nivel(SubidaDeNivel(
        5, [Escolha(Opcao.SUBCLASSE), Escolha(Opcao.TRACOS, tracos=(Traco.FORCA, Traco.PRESENCA))],
        "core_domain_card_hypnotic_shimmer", nova_experiencia="Y"))
    assert f.estagio_subclasse == "especializacao"
    assert f.tracos[Traco.FORCA] == 1  # -1 inicial, +1 no nível 4, +1 no nível 5
    assert f.proficiencia == 3
    # subclasse risca a multiclasse do tier 3
    assert not any(o["opcao"] is Opcao.MULTICLASSE and o["tier"] == 3
                   for o in bardo.opcoes_disponiveis())


def test_multiclasse(bardo_nivel_4):
    bardo = bardo_nivel_4
    f = bardo.subir_de_nivel(SubidaDeNivel(
        5, [Escolha(Opcao.MULTICLASSE, classe="core_class_warrior", dominio="BLADE",
                    subclasse="core_subclass_call_of_the_brave")],
        carta="core_domain_card_get_back_up",  # BLADE nível 1 <= metade de 5
        nova_experiencia="Y"))
    assert f.multiclasse["dominio"] == "BLADE"
    assert "core_domain_card_get_back_up" in f.cartas
    opcoes = {(o["tier"], o["opcao"]) for o in bardo.opcoes_disponiveis()}
    assert (3, Opcao.SUBCLASSE) not in opcoes
    assert (4, Opcao.MULTICLASSE) not in opcoes


def _multiclasse_guerreiro_nivel_5(carta):
    return SubidaDeNivel(
        5, [Escolha(Opcao.MULTICLASSE, classe="core_class_warrior", dominio="BLADE",
                    subclasse="core_subclass_call_of_the_brave")],
        carta=carta, nova_experiencia="Y")


def test_carta_multiclasse_limitada_a_metade_do_nivel(bardo_nivel_4):
    # SRD: "half your level or lower (rounded up)". No nível 5: até nível 3.
    with pytest.raises(RegraViolada, match="não está disponível"):
        bardo_nivel_4.subir_de_nivel(_multiclasse_guerreiro_nivel_5("core_domain_card_deadly_focus"))  # 4
    f = bardo_nivel_4.subir_de_nivel(_multiclasse_guerreiro_nivel_5("core_domain_card_scramble"))     # 3
    assert "core_domain_card_scramble" in f.cartas


def test_desfazer_e_ficha_em_nivel_passado(bardo_nivel_4):
    bardo = bardo_nivel_4
    assert bardo.ficha(ate_nivel=2).nivel == 2
    bardo.desfazer_ultimo_nivel()
    assert bardo.ficha().nivel == 3


def test_linha_do_tempo(bardo):
    bardo.subir_de_nivel(nivel_simples(2, "core_domain_card_tell_no_lies", "X"))
    tempo = bardo.linha_do_tempo()
    assert len(tempo) == 10
    assert [e["status"] for e in tempo[:3]] == ["feito", "feito", "futuro"]
    assert any("Conquista de tier" in i for i in tempo[4]["itens"])  # nível 5


def test_linha_do_tempo_mostra_nomes_e_nao_ids(bardo):
    bardo.subir_de_nivel(nivel_simples(2, "core_domain_card_tell_no_lies", "X"))
    tempo = bardo.linha_do_tempo()
    criacao, nivel2 = tempo[0]["itens"], tempo[1]["itens"]
    assert "Classe: Bard" in criacao
    assert "Subclasse: Troubadour" in criacao
    assert "Carta: Inspirational Words" in criacao
    assert "Carta: Book of Ava" in criacao
    assert "Carta: Tell No Lies" in nivel2
    todos = [i for e in tempo for i in e["itens"]]
    assert not any("core_" in i for i in todos)
