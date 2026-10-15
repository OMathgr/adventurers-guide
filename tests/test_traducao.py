"""Tradução pt-BR: tudo do SRD precisa ter tradução, e traduzir não pode
mudar nenhuma regra (as regras leem o inglês)."""

import pytest

from motor import Biblioteca, Personagem



@pytest.fixture(scope="module")
def pt():
    return Biblioteca(idioma="pt-BR")


def test_nada_ficou_sem_traducao(pt):
    assert pt.traducoes_faltando == []


def test_nomes_traduzidos_e_original_guardado(pt):
    bardo = pt.classes["core_class_bard"]
    assert (bardo.nome, bardo.nome_original, bardo.codigo) == ("Bardo", "Bard", "BARD")
    espada = pt.armas["core_weapon_improved_broadsword"]   # composta: base + qualidade
    assert (espada.nome, espada.nome_original) == ("Espada Larga Aprimorada", "Improved Broadsword")
    assert pt.armas["core_weapon_legendary_battleaxe"].nome == "Machado de Batalha Lendário"
    assert pt.armas["core_weapon_advanced_glowing_rings"].nome == "Anéis Luminosos Avançados"
    assert pt.nome_dominio("BLADE") == "Lâmina"


def test_nomes_da_heranca_seguem_a_edicao_brasileira(pt):
    """Subclasses, ancestralidades e comunidades com os nomes do livro básico
    brasileiro (pp. 14-16); só os nomes, nunca o texto."""
    esperado = {
        "core_subclass_wordsmith": "Beletrista", "core_subclass_beastbound": "Treinador",
        "core_subclass_nightwalker": "Gatuno", "core_subclass_syndicate": "Mafioso",
        "core_subclass_call_of_the_slayer": "Escolhido da Matança", "core_subclass_stalwart": "Baluarte",
        "core_subclass_warden_of_the_elements": "Protetor dos Elementos",
        "core_subclass_school_of_war": "Discípulo da Guerra", "core_subclass_elemental_origin": "Elementalista",
        "core_ancestry_clank": "Clank", "core_ancestry_halfling": "Pequenino", "core_ancestry_ribbet": "Quacho",
        "core_ancestry_infernis": "Infernis", "core_ancestry_galapa": "Galapa", "core_ancestry_drakona": "Drakona",
        "core_community_highborne": "Aristocrática", "core_community_slyborne": "Fora da lei",
        "core_community_wanderborne": "Nômade", "core_community_underborne": "Subterrânea",
    }
    todos = {**pt.subclasses, **pt.ancestralidades, **pt.comunidades}
    assert {i: todos[i].nome for i in esperado} == esperado


def test_texto_das_cartas_inclui_listas_e_magias(pt):
    assert "• +1 nos seus testes de Conjuração" in pt.cartas["core_domain_card_arcana_touched"].texto
    assert pt.cartas["core_domain_card_book_of_ava"].texto.startswith("Empurrão de Poder:")


def test_traduzir_nao_muda_regras(pt):
    en = Biblioteca()
    for i, arma in en.armas.items():
        traduzida = pt.armas[i]
        assert [(c.modificadores, c.requisitos, c.efeito) for c in arma.caracteristicas] == \
               [(c.modificadores, c.requisitos, c.efeito) for c in traduzida.caracteristicas], i
    for i, a in en.ancestralidades.items():
        assert [c.efeito for c in a.caracteristicas] == [c.efeito for c in pt.ancestralidades[i].caracteristicas]


def test_personagem_com_biblioteca_traduzida(pt, criacao_bardo):
    p = Personagem(pt, criacao_bardo)
    p.equipar(principal="core_weapon_broadsword", armadura="core_armor_chainmail_armor")
    f = p.ficha()
    assert f.ataques[0].arma == "Espada Larga"
    assert f.evasao == 9                                   # Heavy (Pesada) continua valendo
    assert f.caracteristicas_armadura[0].nome == "Pesada"
    assert p.linha_do_tempo()[0]["itens"][0] == "Classe: Bardo"


def test_nomes_das_cartas_e_dominios_seguem_a_edicao_brasileira(pt):
    """Nomes das cartas e dos domínios do livro básico brasileiro (apêndice,
    pp. 328-342); só os nomes, o texto continua sendo tradução nossa do SRD."""
    esperado = {
        "core_domain_card_wall_walk": "Caminhar na Parede", "core_domain_card_falling_sky": "Chuva Arcana",
        "core_domain_card_bone_touched": "Dom da Falange", "core_domain_card_sage_touched": "Dom da Sabedoria",
        "core_domain_card_book_of_exota": "Livro de Ecsota", "core_domain_card_bolt_beacon": "Raio Luminoso",
        # empates de domínio/nível/custo desfeitos pelo texto da carta
        "core_domain_card_bare_bones": "Armadura Corporal", "core_domain_card_forceful_push": "Imposição",
        "core_domain_card_brace": "Resistir", "core_domain_card_tactician": "Táticas",
    }
    assert {i: pt.cartas[i].nome for i in esperado} == esperado
    assert [pt.nome_dominio(d) for d in ("BONE", "SAGE", "MIDNIGHT")] == ["Falange", "Sabedoria", "Meia-noite"]
    # a carta cita o próprio nome novo no texto
    assert "Dado de Aspecto Selvagem" in pt.cartas["core_domain_card_wild_surge"].texto


def test_nomes_do_equipamento_seguem_a_edicao_brasileira(pt):
    """Armas e armaduras com os nomes do livro básico brasileiro (pp. 115-127),
    inclusive o gênero das versões aprimorada/avançada/lendária."""
    esperado = {
        "core_weapon_cutlass": "Alfange", "core_weapon_returning_blade": "Lâmina do Retorno",
        "core_weapon_hammer_of_exota": "Martelo de Ecsota", "core_weapon_flickerfly_blade": "Lâmina do Oscilume",
        "core_weapon_swinging_ropeblade": "Dardo de Corda", "core_weapon_grappler": "Gancho",
        "core_weapon_primer_shard": "Lasca de Apoio",
        "core_weapon_legendary_greatsword": "Montante Lendária",   # o livro trata montante no feminino
        "core_weapon_improved_tower_shield": "Escudo-Torre Aprimorado",
    }
    assert {i: pt.armas[i].nome for i in esperado} == esperado
    armaduras = {
        "core_armor_gambeson_armor": "Gibão", "core_armor_harrowbone_armor": "Armadura do Tormento",
        "core_armor_bladefare_armor": "Armadura Passalâmina", "core_armor_veritas_opal_armor": "Armadura de Opala da Verdade",
        "core_armor_advanced_gambeson_armor": "Gibão Avançado",
    }
    assert {i: pt.armaduras[i].nome for i in armaduras} == armaduras


def test_caracteristicas_seguem_a_edicao_brasileira_com_o_genero_do_item(pt):
    """Características com os nomes do livro (pp. 115-127); "Heavy" concorda com
    o item, como no livro: Pesado na arma, Pesada na armadura."""
    def nomes(item):
        return [c.nome for c in item.caracteristicas]
    assert nomes(pt.armas["core_weapon_warhammer"]) == ["Pesado"]
    assert nomes(pt.armaduras["core_armor_chainmail_armor"]) == ["Pesada"]
    assert nomes(pt.armaduras["core_armor_full_plate_armor"]) == ["Muito Pesada"]
    assert nomes(pt.armas["core_weapon_halberd"]) == ["Inconveniente"]
    assert nomes(pt.armas["core_weapon_rapier"]) == ["Veloz"]
    assert nomes(pt.armas["core_weapon_greatstaff"]) == ["Poderoso"]
    assert nomes(pt.armas["core_weapon_round_shield"]) == ["Armadura"]
    assert nomes(pt.armas["core_weapon_blessed_anlace"]) == ["Vitalizante"]
    assert nomes(pt.armaduras["core_armor_elundrian_chain_armor"]) == ["Égide"]
    # Painful vale para arma e armadura com o mesmo nome
    assert nomes(pt.armas["core_weapon_bloodstaff"]) == nomes(pt.armaduras["core_armor_runes_of_fortification"])         == ["Excruciante"]
