import re

from motor import Alvo, Escolha, Modificador, Opcao, SubidaDeNivel, Traco
from motor.srd import ALVOS_SRD, _modificadores

# Bardo base (conftest): Evasão 10, Agilidade 1, Acuidade 0, Força -1.


# --- Leitura do texto do SRD ------------------------------------------------------

def test_le_bonus_fixos_do_texto():
    assert _modificadores("-2 to Evasion; -1 to Agility") == (
        Modificador(Alvo.EVASAO, -2), Modificador(Traco.AGILIDADE, -1))
    assert _modificadores("+5 to Armor Score; -1 to Evasion.") == (
        Modificador(Alvo.PONTUACAO_ARMADURA, 5), Modificador(Alvo.EVASAO, -1))
    assert _modificadores("+1 to attack rolls") == (Modificador(Alvo.ATAQUE, 1),)
    assert len(_modificadores("-1 to all character traits and Evasion")) == 7


def test_parte_condicional_vira_so_texto():
    assert _modificadores("-1 to Agility; on a successful attack, all adversaries "
                          "within Very Close range must mark a Stress.") == (
        Modificador(Traco.AGILIDADE, -1),)
    assert _modificadores("+3 to primary weapon damage to targets within Melee range") == ()
    assert _modificadores("When you roll a 1 on a damage die, it deals 6 damage instead.") == ()


# Bônus "+N to X" que sabemos ser condicionais ou sem campo na ficha.
CONHECIDOS_SO_TEXTO = {
    "primary weapon damage within Melee range",               # Double Duty
    "primary weapon damage to targets within Melee range",    # Paired
    "Spellcast Rolls",                                        # Channeling
}


def test_todo_bonus_fixo_do_srd_e_reconhecido(bib):
    """Se o SRD ganhar um alvo novo (ex.: SRD 2.0), este teste avisa em vez de
    o bônus ser ignorado em silêncio."""
    desconhecidos = set()
    pecas = [*bib.armas.values(), *bib.armaduras.values()]
    for c in (c for p in pecas for c in p.caracteristicas):
        for trecho in c.descricao.split(";"):
            m = re.fullmatch(r"\s*[+-]\d+ to (.+?)\.?\s*", trecho)
            if m and m.group(1) not in ALVOS_SRD and m.group(1) not in CONHECIDOS_SO_TEXTO:
                desconhecidos.add(m.group(1))
    assert desconhecidos == set()


# --- Efeito na ficha -----------------------------------------------------------

def test_armadura_muito_pesada(bardo):
    bardo.equipar(armadura="core_armor_full_plate_armor")  # Very Heavy
    f = bardo.ficha()
    assert f.evasao == 8
    assert f.tracos[Traco.AGILIDADE] == 0
    assert (f.limiar_maior, f.limiar_grave) == (9, 18)
    assert f.armadura == "Full Plate Armor"
    assert [c.nome for c in f.caracteristicas_armadura] == ["Very Heavy"]


def test_armadura_flexivel(bardo):
    bardo.equipar(armadura="core_armor_gambeson_armor")
    assert bardo.ficha().evasao == 11


def test_escudo_soma_armadura_e_tira_evasao(bardo):
    bardo.equipar(principal="core_weapon_broadsword", secundaria="core_weapon_tower_shield",
                  armadura="core_armor_leather_armor")
    f = bardo.ficha()
    assert f.pontuacao_armadura == 3 + 2
    assert f.evasao == 9


def test_bonus_de_ataque_vale_so_para_a_propria_arma(bardo):
    bardo.equipar(principal="core_weapon_broadsword", secundaria="core_weapon_shortsword")
    espada, curta = bardo.ficha().ataques
    assert espada.bonus == 1 + 1      # Agilidade + Reliable
    assert curta.bonus == 1           # Agilidade


def test_penalidade_de_traco_da_arma_afeta_ficha(bardo):
    bardo.equipar(principal="core_weapon_halberd")  # Cumbersome: -1 Acuidade
    assert bardo.ficha().tracos[Traco.ACUIDADE] == -1


def test_ataque_usa_traco_ja_modificado(bardo):
    bardo.equipar(principal="core_weapon_longsword", armadura="core_armor_full_plate_armor")
    assert bardo.ficha().ataques[0].bonus == 0   # Agilidade 1 - 1 (Very Heavy)


def test_caracteristica_condicional_aparece_como_texto(bardo):
    bardo.equipar(principal="core_weapon_broadsword", secundaria="core_weapon_shortsword")
    paired = bardo.ficha().ataques[1].caracteristicas[0]
    assert paired.nome == "Paired"
    assert paired.modificadores == ()
    assert "Melee range" in paired.descricao


def test_modificadores_nao_acumulam_ao_subir_de_nivel(bardo):
    bardo.equipar(armadura="core_armor_full_plate_armor")
    f = bardo.subir_de_nivel(SubidaDeNivel(
        nivel=2,
        escolhas=[Escolha(Opcao.EVASAO), Escolha(Opcao.TRACOS, tracos=(Traco.AGILIDADE, Traco.FORCA))],
        carta="core_domain_card_tell_no_lies",
        nova_experiencia="Viajante",
    ))
    assert f.evasao == 10 + 1 - 2
    assert f.tracos[Traco.AGILIDADE] == 1 + 1 - 1
    assert bardo.ficha() == f
