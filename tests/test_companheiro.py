import dataclasses

import pytest

from motor import (AlvoFeroz, Companheiro, Criacao, Escolha, Movimento, OpcaoTreino, Opcao,
                   Personagem, RegraViolada, SubidaDeNivel, Traco, Treino)

BRASA = Companheiro("Brasa", ["Farejar", "Vigiar"])


@pytest.fixture
def criacao_ranger():
    return Criacao(
        nome="Tália", classe="core_class_ranger", subclasse="core_subclass_beastbound",
        ancestralidade="core_ancestry_faun", comunidade="core_community_highborne",
        tracos={Traco.AGILIDADE: 2, Traco.INSTINTO: 1, Traco.ACUIDADE: 1,
                Traco.FORCA: 0, Traco.PRESENCA: 0, Traco.CONHECIMENTO: -1},
        experiencias=["Caçadora", "Rastreadora"],
        cartas=["core_domain_card_deft_maneuvers", "core_domain_card_gifted_tracker"],
        companheiro=BRASA,
    )


@pytest.fixture
def ranger(bib, criacao_ranger):
    return Personagem(bib, criacao_ranger)


CARTAS = {2: "core_domain_card_ferocity", 3: "core_domain_card_strategic_approach",
          4: "core_domain_card_conjure_swarm", 5: "core_domain_card_natural_familiar"}
EXP = {2: ("Viajante", "Uivar"), 5: ("Sobrevivente", "Proteger")}


def subir(p, nivel, *treinos, escolhas=None):
    exp, exp_comp = EXP.get(nivel, (None, None))
    return p.subir_de_nivel(SubidaDeNivel(
        nivel, escolhas or [Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)], CARTAS[nivel],
        nova_experiencia=exp, experiencia_companheiro=exp_comp, treinos=list(treinos)))


# --- Criação ------------------------------------------------------------------------

def test_companheiro_inicial(ranger):
    c = ranger.ficha().companheiro
    assert (c.nome, c.evasao, c.estresse_max, c.dado, c.alcance) == ("Brasa", 10, 3, "d6", "MELEE")
    assert c.experiencias == {"Farejar": 2, "Vigiar": 2}
    assert c.dano == "1d6"


def test_beastbound_exige_companheiro(bib, criacao_ranger):
    with pytest.raises(RegraViolada, match="companheiro"):
        Personagem(bib, dataclasses.replace(criacao_ranger, companheiro=None))
    with pytest.raises(RegraViolada, match="Experiências"):
        Personagem(bib, dataclasses.replace(criacao_ranger, companheiro=Companheiro("X", ["A"])))


def test_outra_subclasse_nao_tem_companheiro(bib, criacao_ranger):
    with pytest.raises(RegraViolada, match="não tem companheiro"):
        Personagem(bib, dataclasses.replace(criacao_ranger, subclasse="core_subclass_wayfinder"))


# --- Treinos a cada nível --------------------------------------------------------------

def test_nivel_exige_um_treino_e_experiencia_do_companheiro(ranger):
    with pytest.raises(RegraViolada, match="1 treino"):
        subir(ranger, 2)
    with pytest.raises(RegraViolada, match="companheiro também ganha"):
        ranger.subir_de_nivel(SubidaDeNivel(2, [Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)],
                                            CARTAS[2], nova_experiencia="Viajante",
                                            treinos=[Treino(OpcaoTreino.ATENTO)]))
    c = subir(ranger, 2, Treino(OpcaoTreino.ATENTO)).companheiro
    assert c.evasao == 12 and c.experiencias["Uivar"] == 2
    assert c.dano == "2d6"   # Proficiência 2 no nível 2


@pytest.mark.parametrize("treino, campo, valor", [
    (Treino(OpcaoTreino.RESILIENTE), "estresse_max", 4),
    (Treino(OpcaoTreino.FEROZ, alvo=AlvoFeroz.DANO), "dado", "d8"),
    (Treino(OpcaoTreino.FEROZ, alvo=AlvoFeroz.ALCANCE), "alcance", "VERY_CLOSE"),
])
def test_efeitos_dos_treinos(ranger, treino, campo, valor):
    assert getattr(subir(ranger, 2, treino).companheiro, campo) == valor


def test_inteligente_sobe_experiencia(ranger):
    c = subir(ranger, 2, Treino(OpcaoTreino.INTELIGENTE, experiencia="Farejar")).companheiro
    assert c.experiencias["Farejar"] == 3
    with pytest.raises(RegraViolada, match="Experiência"):
        subir(ranger, 3, Treino(OpcaoTreino.INTELIGENTE, experiencia="Voar"))


def test_feroz_exige_alvo(ranger):
    with pytest.raises(RegraViolada, match="Vicious"):
        subir(ranger, 2, Treino(OpcaoTreino.FEROZ))


def test_luz_na_escuridao_da_espaco_de_esperanca(ranger):
    f = subir(ranger, 2, Treino(OpcaoTreino.LUZ_NA_ESCURIDAO))
    assert f.esperanca_max == 7
    ranger.sessao.ganhar_esperanca(10)
    assert ranger.sessao.esperanca == 7


def test_limite_de_quadradinhos(ranger):
    subir(ranger, 2, Treino(OpcaoTreino.LUZ_NA_ESCURIDAO))
    with pytest.raises(RegraViolada, match="já foi marcado"):
        subir(ranger, 3, Treino(OpcaoTreino.LUZ_NA_ESCURIDAO))


def test_expert_training_da_treino_extra_na_especializacao(ranger):
    subir(ranger, 2, Treino(OpcaoTreino.ATENTO))
    subir(ranger, 3, Treino(OpcaoTreino.ATENTO))
    subir(ranger, 4, Treino(OpcaoTreino.ATENTO), escolhas=[Escolha(Opcao.EVASAO), Escolha(
        Opcao.TRACOS, tracos=(Traco.FORCA, Traco.PRESENCA))])   # PV do tier 2 já esgotou
    especializacao = [Escolha(Opcao.SUBCLASSE), Escolha(Opcao.PV)]
    with pytest.raises(RegraViolada, match="2 treino"):
        subir(ranger, 5, Treino(OpcaoTreino.RESILIENTE), escolhas=especializacao)
    f = subir(ranger, 5, Treino(OpcaoTreino.RESILIENTE), Treino(OpcaoTreino.VINCULO),
              escolhas=especializacao)
    assert f.estagio_subclasse == "especializacao" and f.companheiro.tem(OpcaoTreino.VINCULO)


def test_multiclasse_beastbound_ganha_companheiro_e_treina_depois(bardo_nivel_4):
    multiclasse = Escolha(Opcao.MULTICLASSE, classe="core_class_ranger", dominio="BONE",
                          subclasse="core_subclass_beastbound", companheiro=BRASA)
    with pytest.raises(RegraViolada, match="companheiro"):
        bardo_nivel_4.subir_de_nivel(SubidaDeNivel(
            5, [dataclasses.replace(multiclasse, companheiro=None)],
            "core_domain_card_hypnotic_shimmer", nova_experiencia="Y"))
    f = bardo_nivel_4.subir_de_nivel(SubidaDeNivel(
        5, [multiclasse], "core_domain_card_hypnotic_shimmer", nova_experiencia="Y"))
    assert f.companheiro.nome == "Brasa"   # sem treino no nível em que chegou
    with pytest.raises(RegraViolada, match="1 treino"):
        bardo_nivel_4.subir_de_nivel(SubidaDeNivel(
            6, [Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)], "core_domain_card_book_of_illiat"))


# --- Sessão ---------------------------------------------------------------------------

def test_companheiro_sai_de_cena_no_ultimo_estresse(ranger):
    s = ranger.sessao
    assert not s.companheiro_recebe_dano()
    s.companheiro_recebe_dano()
    assert s.companheiro_recebe_dano()   # 3º Estresse: fora
    assert ranger.ficha().companheiro.fora_de_cena
    with pytest.raises(RegraViolada, match="fora de cena"):
        s.companheiro_recebe_dano()
    s.descanso_curto([Movimento.ALIVIAR_ESTRESSE, Movimento.PREPARAR], [4, None])
    assert s.companheiro_fora                     # só volta no longo
    s.descanso_longo([Movimento.PREPARAR, Movimento.PREPARAR])
    c = ranger.ficha().companheiro
    assert not c.fora_de_cena and c.estresse_marcado == 2


def test_aliviar_estresse_tambem_alivia_o_companheiro(ranger):
    s = ranger.sessao
    s.companheiro_recebe_dano()
    s.companheiro_recebe_dano()
    s.descanso_curto([Movimento.ALIVIAR_ESTRESSE, Movimento.PREPARAR], [1, None])   # 1 + tier 1
    assert s.companheiro_estresse == 0


def test_armored_usa_a_sua_armadura(ranger):
    ranger.equipar(armadura="core_armor_leather_armor")
    with pytest.raises(RegraViolada, match="Blindado"):
        ranger.sessao.companheiro_recebe_dano(usar_armadura=True)
    subir(ranger, 2, Treino(OpcaoTreino.BLINDADO))
    ranger.sessao.companheiro_recebe_dano(usar_armadura=True)
    assert (ranger.sessao.armadura_marcada, ranger.sessao.companheiro_estresse) == (1, 0)


def test_creature_comfort_uma_vez_por_descanso(ranger):
    subir(ranger, 2, Treino(OpcaoTreino.CONFORTO))
    s = ranger.sessao
    s.conforto_do_companheiro(ganhar_esperanca=True)
    assert s.esperanca == 3
    with pytest.raises(RegraViolada, match="já foi usado"):
        s.conforto_do_companheiro(ganhar_esperanca=False)
    s.descanso_curto([Movimento.PREPARAR, Movimento.PREPARAR])
    s.marcar_estresse(1)
    s.conforto_do_companheiro(ganhar_esperanca=False)
    assert s.estresse_marcado == 0


def test_bonded_levanta_com_um_6(ranger):
    subir(ranger, 2, Treino(OpcaoTreino.VINCULO))   # PV máximo 7 (avanço PV)
    s = ranger.sessao
    s.marcar_pv(6)
    r = s.receber_dano(1, rolagens_vinculo=[2, 6, 1])
    assert not r.caiu and "Vínculo" in r.notas[-1]
    assert s.pv_marcados == 6 and s.companheiro_fora


def test_bonded_sem_6_nao_levanta(ranger):
    subir(ranger, 2, Treino(OpcaoTreino.VINCULO))
    s = ranger.sessao
    s.marcar_pv(6)
    assert s.receber_dano(1, rolagens_vinculo=[1, 2, 3]).caiu
    assert s.companheiro_fora


def test_linha_do_tempo_mostra_treinos(ranger):
    subir(ranger, 2, Treino(OpcaoTreino.INTELIGENTE, experiencia="Farejar"))
    itens = ranger.linha_do_tempo()[1]["itens"]
    assert "Companheiro: nova Experiência Uivar +2" in itens
    assert "Treino do companheiro: Inteligente (Farejar)" in itens


def test_sem_companheiro(bardo):
    with pytest.raises(RegraViolada, match="não tem companheiro"):
        bardo.sessao.companheiro_recebe_dano()
