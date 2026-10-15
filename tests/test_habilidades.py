"""Habilidades de classe e de subclasse: na ficha desde o nível 1 (Esperança,
classe e fundamental), as aprimoradas ao subir a subclasse, e as que mudam
números (limiares, PV, PF, Evasão, cartas a mais, Treinamento de Combate)."""
import pytest

from motor import Biblioteca, Criacao, Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel, Traco

TRACOS = {Traco.PRESENCA: 2, Traco.AGILIDADE: 1, Traco.CONHECIMENTO: 1,
          Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1}


def cartas_nivel_1(bib, classe, quantas=2):
    dominios = bib.classes[classe].dominios
    return sorted(c.id for c in bib.cartas.values() if c.nivel == 1 and c.dominio in dominios)[:quantas]


def criar(bib, classe, subclasse, cartas=2):
    return Personagem(bib, Criacao(
        nome="Teste", classe=classe, subclasse=subclasse, ancestralidade="core_ancestry_faun",
        comunidade="core_community_highborne", tracos=dict(TRACOS), experiencias=["A", "B"],
        cartas=cartas_nivel_1(bib, classe, cartas)))


def carta_nova(p, escolhas=(), menos=()):
    """Primeira carta possível no próximo nível que não esteja em `menos`."""
    return next(c.id for c in p.cartas_para_nivel(list(escolhas)) if c.id not in menos)


def subir(p, escolhas, extras=0):
    """Sobe um nível com estes avanços (e as cartas a mais, se houver)."""
    nivel = p.ficha().nivel + 1
    carta = carta_nova(p, escolhas)
    outras = []
    for _ in range(extras):
        outras.append(carta_nova(p, escolhas, menos=[carta, *outras]))
    return p.subir_de_nivel(SubidaDeNivel(nivel, list(escolhas), carta, cartas_extras=outras,
                                          nova_experiencia=f"E{nivel}" if nivel in (2, 5, 8) else None))


# patamar 2 não tem carta de subclasse: a especialização vem no nível 5 e a maestria no 8
SUBCLASSE = [Escolha(Opcao.SUBCLASSE), Escolha(Opcao.PV)]
NIVEIS_2_A_4 = [[Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)], [Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)],
                [Escolha(Opcao.EVASAO), Escolha(Opcao.EXPERIENCIAS, experiencias=("A", "B"))]]
NIVEIS_6_E_7 = [[Escolha(Opcao.ESTRESSE), Escolha(Opcao.ESTRESSE)], [Escolha(Opcao.PV), Escolha(Opcao.EVASAO)]]


def ate_o_nivel_4(p):
    for escolhas in NIVEIS_2_A_4:
        subir(p, escolhas)


def ate_o_nivel_7_com_especializacao(p, extras=0):
    ate_o_nivel_4(p)
    subir(p, SUBCLASSE, extras)
    for escolhas in NIVEIS_6_E_7:
        subir(p, escolhas)


@pytest.fixture(scope="module")
def pt():
    return Biblioteca(idioma="pt-BR")


def por_tipo(ficha):
    return {(h.tipo, h.nome_original) for h in ficha.habilidades}


# --- O que aparece na ficha --------------------------------------------------------

def test_nivel_1_tem_esperanca_classe_e_fundamental(bardo):
    assert por_tipo(bardo.ficha()) == {
        ("esperanca", "Make a Scene"), ("classe", "Rally"), ("fundacao", "Gifted Performer")}
    rally = next(h for h in bardo.ficha().habilidades if h.nome_original == "Rally")
    assert rally.origem == "Bard" and not rally.automatica and "d6" in rally.descricao


def test_especializacao_e_maestria_entram_ao_subir_a_subclasse(bib):
    p = criar(bib, "core_class_bard", "core_subclass_troubadour")
    ate_o_nivel_7_com_especializacao(p)
    assert ("especializacao", "Maestro") in por_tipo(p.ficha())
    assert not any(t == "maestria" for t, _ in por_tipo(p.ficha()))
    subir(p, SUBCLASSE)
    assert ("maestria", "Virtuoso") in por_tipo(p.ficha())


def test_guardiao_tem_determinacao_numa_habilidade_so(bib):
    p = criar(bib, "core_class_guardian", "core_subclass_stalwart")
    classe = [h for h in p.ficha().habilidades if h.tipo == "classe"]
    assert [h.nome_original for h in classe] == ["Unstoppable"]
    assert "While Unstoppable" in classe[0].descricao


def test_traducao_usa_os_nomes_do_livro(pt):
    p = Personagem(pt, Criacao(
        nome="T", classe="core_class_bard", subclasse="core_subclass_wordsmith",
        ancestralidade="core_ancestry_faun", comunidade="core_community_highborne",
        tracos=dict(TRACOS), experiencias=["A", "B"], cartas=cartas_nivel_1(pt, "core_class_bard")))
    nomes = {h.nome for h in p.ficha().habilidades}
    assert nomes == {"Fazer uma Cena", "Inspiração", "Discurso Inspirador", "Alma de Poeta"}


# --- Números na ficha ----------------------------------------------------------------

def test_baluarte_soma_os_bonus_nos_limiares(bib):
    p = criar(bib, "core_class_guardian", "core_subclass_stalwart")
    f = p.ficha()   # sem armadura: nível e 2x nível, +1 do Resoluto
    assert (f.limiar_maior, f.limiar_grave) == (1 + 1, 2 + 1)
    ate_o_nivel_4(p)
    subir(p, SUBCLASSE)
    f = p.ficha()   # nível 5, +1 +2 (Irrefreável soma)
    assert (f.limiar_maior, f.limiar_grave) == (5 + 3, 10 + 3)
    habilidade = next(h for h in f.habilidades if h.nome_original == "Unrelenting")
    assert habilidade.automatica
    for escolhas in NIVEIS_6_E_7:
        subir(p, escolhas)
    subir(p, SUBCLASSE)
    f = p.ficha()   # nível 8, +1 +2 +3
    assert (f.limiar_maior, f.limiar_grave) == (8 + 6, 16 + 6)


def test_vingador_ganha_um_pf_e_mago_de_batalha_um_pv(bib):
    vingador = criar(bib, "core_class_guardian", "core_subclass_vengeance")
    assert vingador.ficha().estresse_max == 7
    mago = criar(bib, "core_class_wizard", "core_subclass_school_of_war")
    assert mago.ficha().pv_max == bib.classes["core_class_wizard"].pv_iniciais + 1


def test_gatuno_ganha_evasao_na_maestria(bib):
    p = criar(bib, "core_class_rogue", "core_subclass_nightwalker")
    ate_o_nivel_7_com_especializacao(p)
    antes = p.ficha().evasao
    subir(p, SUBCLASSE)   # nível 8: maestria
    assert p.ficha().evasao == antes + 1


def test_sentinela_alada_ganha_4_no_grave_na_maestria(bib):
    p = criar(bib, "core_class_seraph", "core_subclass_winged_sentinel")
    ate_o_nivel_7_com_especializacao(p)
    antes = p.ficha().limiar_grave
    subir(p, SUBCLASSE)
    assert p.ficha().limiar_grave == antes + 2 + 4   # sem armadura o Grave é 2x o nível; +4 da Ascensão


# --- Discípulo do Conhecimento: cartas a mais -------------------------------------------

def test_conhecimento_cria_com_tres_cartas(bib):
    p = criar(bib, "core_class_wizard", "core_subclass_school_of_knowledge", cartas=3)
    assert len(p.ficha().cartas) == 3
    with pytest.raises(RegraViolada, match="Escolha 2 cartas"):
        criar(bib, "core_class_bard", "core_subclass_troubadour", cartas=3)


def test_personagem_salvo_antes_da_regra_continua_carregando(bib):
    """Promissor/Talentoso são direitos: sem a carta a mais (dados antigos) ainda vale."""
    p = criar(bib, "core_class_wizard", "core_subclass_school_of_knowledge", cartas=2)
    ate_o_nivel_4(p)
    f = subir(p, SUBCLASSE, extras=0)
    assert (f.nivel, len(f.cartas)) == (5, 2 + 3 + 1)


def test_conhecimento_ganha_carta_a_mais_na_especializacao(bib):
    p = criar(bib, "core_class_wizard", "core_subclass_school_of_knowledge", cartas=3)
    ate_o_nivel_4(p)
    assert p.cartas_extras(SUBCLASSE) == 1
    assert p.cartas_extras([Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)]) == 0
    with pytest.raises(RegraViolada, match="1 carta"):
        subir(p, SUBCLASSE, extras=2)
    f = subir(p, SUBCLASSE, extras=1)
    assert len(f.cartas) == 3 + 3 + 2   # criação, níveis 2-4, nível 5 com a do Talentoso


def test_carta_a_mais_sem_habilidade_e_recusada(bardo):
    with pytest.raises(RegraViolada, match="nenhuma habilidade"):
        subir(bardo, [Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)], extras=1)


def test_multiclasse_no_conhecimento_pede_a_carta_do_promissor(bardo_nivel_4):
    escolha = [Escolha(Opcao.MULTICLASSE, classe="core_class_wizard", dominio="SPLENDOR",
                       subclasse="core_subclass_school_of_knowledge")]
    assert bardo_nivel_4.cartas_extras(escolha) == 1
    f = subir(bardo_nivel_4, escolha, extras=1)
    assert len(f.cartas) == 5 + 2


# --- Multiclasse e Treinamento de Combate ----------------------------------------------

def test_multiclasse_ganha_habilidade_de_classe_e_fundamental_sem_a_de_esperanca(bardo_nivel_4):
    subir(bardo_nivel_4, [Escolha(Opcao.MULTICLASSE, classe="core_class_warrior", dominio="BLADE",
                                  subclasse="core_subclass_call_of_the_brave")])
    tipos = por_tipo(bardo_nivel_4.ficha())
    assert {("classe", "Attack of Opportunity"), ("classe", "Combat Training"),
            ("fundacao", "Courage"), ("fundacao", "Battle Ritual")} <= tipos
    assert ("esperanca", "No Mercy") not in tipos
    assert ("esperanca", "Make a Scene") in tipos


def test_treinamento_de_combate_soma_o_nivel_no_dano_fisico(guerreiro):
    f = guerreiro.equipar(principal="core_weapon_battleaxe")
    assert f.ataques[0].dano == "1d10+4"   # +3 da arma, +1 do nível


def test_treinamento_de_combate_ignora_empunhadura(guerreiro, bardo):
    f = guerreiro.equipar(principal="core_weapon_battleaxe", secundaria="core_weapon_round_shield")
    assert len(f.ataques) == 2
    with pytest.raises(RegraViolada, match="duas mãos"):
        bardo.equipar(principal="core_weapon_battleaxe", secundaria="core_weapon_round_shield")


# --- Comunidade -------------------------------------------------------------------------

def test_ficha_traz_a_habilidade_da_comunidade(bardo):
    assert [c.nome_original for c in bardo.ficha().caracteristicas_comunidade] == ["Privilege"]


def test_habilidades_de_comunidade_com_os_nomes_do_livro(pt):
    assert {c.id: c.caracteristicas[0].nome for c in pt.comunidades.values()} == {
        "core_community_highborne": "Privilégio", "core_community_loreborne": "Culto",
        "core_community_orderborne": "Princípios", "core_community_ridgeborne": "Firme",
        "core_community_seaborne": "Conhecer a Maré", "core_community_slyborne": "Malandro",
        "core_community_underborne": "Habituado à Penumbra", "core_community_wanderborne": "Mochila de Nômade",
        "core_community_wildborne": "Pés Leves"}
