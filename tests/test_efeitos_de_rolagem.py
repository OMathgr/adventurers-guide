"""O catálogo data/efeitos_de_rolagem.json e como o motor o aplica."""
import json

import pytest

from motor import Criacao, OpcaoEscolhida, Personagem, RegraViolada, Traco
from motor.rolagem import Dualidade, PapelDoDado
from motor.srd import PASTA_DADOS

TIPOS_CONHECIDOS = {
    "bonus", "dados", "proficiencia", "vantagem", "desvantagem", "ignora_desvantagem", "dado_esperanca",
    "dobra_atributo", "experiencia_com_fadiga", "experiencia_d6_gratis", "soma_no_dado", "limpa_fadiga_no_sucesso",
    "gasta_marcador", "marcador_no_medo", "esperanca_falha_com_medo", "rerrola_esperanca_1", "vantagem_apos_falha",
    "nota_d6", "dado_de_dano", "dado_extra_descarta_menor", "explode_maximo", "troca_valor", "rerrola_valores",
    "dobra_iguais", "dobra_maior_dado", "multiplica_dano", "soma_dado_medo_do_ataque", "nota_valor", "rolagem_extra",
    "rerrola_dualidade", "rerrola_teste", "rerrola_esperanca", "rerrola_um_dado", "troca_dualidade",
    "medo_vira_esperanca", "rerrola_dano", "maximiza_um_dado",
}

TRACOS = {Traco.FORCA: 2, Traco.AGILIDADE: 1, Traco.INSTINTO: 1, Traco.ACUIDADE: 0, Traco.PRESENCA: 0,
          Traco.CONHECIMENTO: -1}


class Dados:
    def __init__(self, *valores):
        self.valores = list(valores)
        self.faces: list[int] = []

    def randint(self, a, b):
        self.faces.append(b)
        return self.valores.pop(0)


def com_dados(p, *valores):
    p.sessao.rng = Dados(*valores)
    return p.sessao.rng


def criar(bib, classe, subclasse, cartas, ancestralidade="core_ancestry_faun", comunidade="core_community_highborne",
          tracos=TRACOS):
    return Personagem(bib, Criacao(nome="T", classe=classe, subclasse=subclasse, ancestralidade=ancestralidade,
                                   comunidade=comunidade, tracos=dict(tracos), experiencias=["A", "B"], cartas=cartas))


def ids(opcoes):
    return {o.id for o in opcoes}


# --- O catálogo bate com o SRD ------------------------------------------------------------------

def test_todo_efeito_aponta_para_algo_que_existe_no_srd(bib):
    catalogo = json.load(open(PASTA_DADOS / "efeitos_de_rolagem.json", encoding="utf-8"))["efeitos"]
    srd = PASTA_DADOS / "srd"
    habilidades = set()
    for c in json.load(open(srd / "classes.json", encoding="utf-8")):
        habilidades |= {f["name"]["en-US"] for f in [c["hopeFeature"]] + c["classFeatures"]}
    for s in json.load(open(srd / "subclasses.json", encoding="utf-8")):
        for e in ("foundation", "specialization", "mastery"):
            habilidades |= {f["name"]["en-US"] for f in s[e]["features"]}
    nomes = {
        "habilidade": habilidades,
        "ancestralidade": {c.nome_original for a in bib.ancestralidades.values() for c in a.caracteristicas},
        "comunidade": {c.nome_original for a in bib.comunidades.values() for c in a.caracteristicas},
        "arma": {c.nome_original for a in bib.armas.values() for c in a.caracteristicas},
        "armadura": {c.nome_original for a in bib.armaduras.values() for c in a.caracteristicas},
        "carta": set(bib.cartas),
    }
    for e in catalogo:
        fonte = e["fonte"]
        assert (fonte.get("nome") or fonte.get("id")) in nomes[fonte["tipo"]], e["id"]
        assert {x["tipo"] for x in e["efeitos"]} <= TIPOS_CONHECIDOS, e["id"]
    assert len({e["id"] for e in catalogo}) == len(catalogo)


# --- Armas e dano ------------------------------------------------------------------------------

def test_poderoso_rola_um_a_mais_e_descarta_o_menor(bib, guerreiro):
    guerreiro.equipar(principal="core_weapon_greatsword")   # Massive: d10, -1 Evasão
    com_dados(guerreiro, 3, 9)   # 1d10 + o dado a mais
    r = guerreiro.rolar_dano(ataque=0)
    assert [d.valor for d in r.dados if not d.descartado] == [9]
    assert any(d.descartado and d.valor == 3 for d in r.dados)


def test_brutal_explode_no_maximo_e_perfeccionista_troca_o_1(bib):
    from motor.rolagem import PlanoDeDano, rolar_dano
    r = rolar_dano(PlanoDeDano("x", "2d6", explode=True), Dados(6, 2, 6, 1))
    assert [d.valor for d in r.dados] == [6, 2, 6, 1] and r.total == 15
    r = rolar_dano(PlanoDeDano("x", "2d6", troca_valor={1: 6}), Dados(1, 4))
    assert r.total == 10 and r.dados[0].original == 1


def test_critico_e_furia_divina_dobram(bib):
    from motor.rolagem import PlanoDeDano, rolar_dano
    r = rolar_dano(PlanoDeDano("x", "2d8+3", critico=True), Dados(2, 5))
    assert r.total == 2 + 5 + 3 + 16
    r = rolar_dano(PlanoDeDano("x", "1d8+2", multiplica=2), Dados(4))
    assert r.total == 12


def test_ataque_furtivo_e_opcao_com_dados_pelo_patamar(bib):
    p = criar(bib, "core_class_rogue", "core_subclass_nightwalker",
              ["core_domain_card_pick_and_pull", "core_domain_card_rain_of_blades"])
    p.equipar(principal="core_weapon_dagger")
    assert "sneak_attack" in ids(p.opcoes_de_rolagem("dano", ataque=0))
    com_dados(p, 4, 6)   # 1d8 da adaga + 1d6 (patamar 1)
    r = p.rolar_dano(ataque=0, opcoes=[OpcaoEscolhida("sneak_attack")])
    assert [d.valor for d in r.dados] == [4, 6] and r.dados[1].papel is PapelDoDado.EXTRA
    assert "Ataque Furtivo" in r.opcoes or any("Sneak" in o for o in r.opcoes)


def test_opcao_com_custo_paga_e_com_limite_trava(bib):
    p = criar(bib, "core_class_seraph", "core_subclass_divine_wielder",
              ["core_domain_card_bolt_beacon", "core_domain_card_i_am_your_shield"])
    # Golpe Característico não é desta carta; uso uma de comunidade: Princípios (Disciplinada) 1x por descanso
    p2 = criar(bib, "core_class_seraph", "core_subclass_divine_wielder",
               ["core_domain_card_bolt_beacon", "core_domain_card_i_am_your_shield"], comunidade="core_community_orderborne")
    dados = com_dados(p2, 15, 3)
    p2.rolar_teste("atributo", "STRENGTH", opcoes=[OpcaoEscolhida("dedicated")])
    assert dados.faces == [20, 12]
    o = next(x for x in p2.opcoes_de_rolagem("teste", "STRENGTH") if x.id == "dedicated")
    assert not o.disponivel and "descanso" in o.motivo
    with pytest.raises(RegraViolada):
        p2.rolar_teste("atributo", "STRENGTH", opcoes=[OpcaoEscolhida("dedicated")])
    p2.sessao.terminar_repouso(longo=False)
    assert next(x for x in p2.opcoes_de_rolagem("teste", "STRENGTH") if x.id == "dedicated").disponivel
    assert "dedicated" not in ids(p.opcoes_de_rolagem("teste", "STRENGTH"))   # sem a comunidade


def test_custo_sem_saldo_nao_muda_nada(bib, guerreiro):
    guerreiro.sessao.esperanca = 0
    p = criar(bib, "core_class_sorcerer", "core_subclass_elemental_origin",
              ["core_domain_card_rune_ward", "core_domain_card_pick_and_pull"])
    p.sessao.esperanca = 0
    with pytest.raises(RegraViolada, match="Esperança insuficiente"):
        p.rolar_teste("atributo", "STRENGTH", opcoes=[OpcaoEscolhida("elementalist_teste")])


# --- Automáticos no teste -------------------------------------------------------------------------

def test_coragem_da_esperanca_na_falha_com_medo(bib, guerreiro):
    com_dados(guerreiro, 2, 9)
    r = guerreiro.rolar_teste("atributo", "STRENGTH", dificuldade=20)
    assert (r.dualidade, r.sucesso, guerreiro.sessao.esperanca) == (Dualidade.MEDO, False, 3)


def test_inevitavel_guarda_vantagem_depois_da_falha(bib):
    p = criar(bib, "core_class_guardian", "core_subclass_stalwart",
              ["core_domain_card_bare_bones", "core_domain_card_get_back_up"])
    p.cofre = []
    # põe Inevitável na mão (nível 6 da Valor): basta estar em cartas_ativas para o motor
    p.criacao.cartas.append("core_domain_card_inevitable")
    p._ficha_inicial.cartas.append("core_domain_card_inevitable")
    com_dados(p, 2, 3)
    p.rolar_teste("atributo", "STRENGTH", dificuldade=20)
    assert p.sessao.proxima_vantagem
    dados = com_dados(p, 5, 4, 3)
    r = p.rolar_teste("atributo", "STRENGTH")
    assert dados.faces == [12, 12, 6] and r.vantagem == 1 and not p.sessao.proxima_vantagem


def test_conhecer_a_mare_junta_marcadores_no_medo_e_gasta(bib):
    p = criar(bib, "core_class_guardian", "core_subclass_stalwart",
              ["core_domain_card_bare_bones", "core_domain_card_get_back_up"], comunidade="core_community_seaborne")
    com_dados(p, 2, 9)
    p.rolar_teste("atributo", "STRENGTH")
    assert p.sessao.marcadores_rolagem == {"know_the_tide": 1}
    com_dados(p, 2, 9)
    p.rolar_teste("atributo", "STRENGTH")   # nível 1: no máximo 1 marcador
    assert p.sessao.marcadores_rolagem == {"know_the_tide": 1}
    com_dados(p, 9, 2)
    r = p.rolar_teste("atributo", "STRENGTH", opcoes=[OpcaoEscolhida("know_the_tide", quantidade=1)])
    assert r.total == 9 + 2 + 2 + 1 and p.sessao.marcadores_rolagem == {"know_the_tide": 0}


def test_bem_vivido_e_adepto_nas_experiencias(bib):
    p = criar(bib, "core_class_wizard", "core_subclass_school_of_knowledge",
              ["core_domain_card_book_of_ava", "core_domain_card_bolt_beacon", "core_domain_card_book_of_illiat"],
              tracos={Traco.CONHECIMENTO: 2, Traco.AGILIDADE: 1, Traco.PRESENCA: 1, Traco.ACUIDADE: 0,
                      Traco.INSTINTO: 0, Traco.FORCA: -1})
    com_dados(p, 9, 3)
    r = p.rolar_teste("atributo", "KNOWLEDGE", experiencias=["A"], opcoes=[OpcaoEscolhida("adept")])
    assert r.total == 9 + 3 + 2 + 4   # Experiência +2 em dobro
    assert (p.sessao.estresse_marcado, p.sessao.esperanca) == (1, 3)   # pagou 1 PF; com Esperança +1


# --- Reações ---------------------------------------------------------------------------------

def test_destemido_vira_medo_em_esperanca_e_devolve_o_medo(bib):
    p = criar(bib, "core_class_warrior", "core_subclass_call_of_the_brave",
              ["core_domain_card_get_back_up", "core_domain_card_whirlwind"], ancestralidade="core_ancestry_infernis")
    com_dados(p, 2, 9)
    r = p.rolar_teste("atributo", "STRENGTH")
    assert r.medo_gerado == 1
    novo = p.reagir(r, "fearless")
    assert (novo.dualidade, novo.medo_gerado, p.sessao.esperanca, p.sessao.estresse_marcado) == (
        Dualidade.ESPERANCA, 0, 3, 2)


def test_sorte_da_arma_so_na_falha(bib):
    p = criar(bib, "core_class_sorcerer", "core_subclass_elemental_origin",
              ["core_domain_card_rune_ward", "core_domain_card_pick_and_pull"])
    p.equipar(principal="core_weapon_axe_of_fortunis")   # Lucky
    com_dados(p, 9, 3)
    r = p.rolar_teste("ataque", 0, dificuldade=5)
    with pytest.raises(RegraViolada, match="falha"):
        p.reagir(r, "lucky")
    com_dados(p, 2, 3)
    r = p.rolar_teste("ataque", 0, dificuldade=30)
    com_dados(p, 12, 11)
    novo = p.reagir(r, "lucky")
    assert novo.dualidade is Dualidade.ESPERANCA and p.sessao.estresse_marcado == 1


def test_dobra_sorte_e_de_qualquer_um_e_tranquiliza_so_de_aliado(bib, bardo):
    fada = criar(bib, "core_class_bard", "core_subclass_troubadour",
                 ["core_domain_card_inspirational_words", "core_domain_card_book_of_ava"],
                 ancestralidade="core_ancestry_faerie")
    fada.sessao.esperanca = 5
    com_dados(bardo, 2, 9)
    r = bardo.rolar_teste("atributo", "PRESENCE")
    com_dados(bardo, 10, 1)
    novo = fada.reagir(r, "luckbender", dono=bardo)
    assert (novo.dualidade, fada.sessao.esperanca) == (Dualidade.ESPERANCA, 2)
    assert bardo.sessao.esperanca == 3   # a primeira (com Medo) não deu nada; a nova deu +1
    with pytest.raises(RegraViolada, match="sessão"):
        fada.reagir(novo, "luckbender", dono=bardo)   # uma vez por sessão


def test_instintos_felinos_rerrola_o_dado_de_esperanca_em_agilidade(bib):
    p = criar(bib, "core_class_rogue", "core_subclass_nightwalker",
              ["core_domain_card_pick_and_pull", "core_domain_card_rain_of_blades"], ancestralidade="core_ancestry_katari")
    p.sessao.esperanca = 4
    com_dados(p, 1, 8)
    r = p.rolar_teste("atributo", "AGILITY")
    com_dados(p, 11)
    novo = p.reagir(r, "feline_instincts")
    assert [d.valor for d in novo.dados[:2]] == [11, 8] and novo.dualidade is Dualidade.ESPERANCA
    assert "feline_instincts" not in ids(p.opcoes_de_rolagem("teste", "STRENGTH"))


def test_magia_volatil_rerrola_o_dano_magico(bib):
    p = criar(bib, "core_class_sorcerer", "core_subclass_elemental_origin",
              ["core_domain_card_rune_ward", "core_domain_card_pick_and_pull"])
    p.equipar(principal="core_weapon_hand_runes")
    p.sessao.esperanca = 3
    com_dados(p, 1)
    r = p.rolar_dano(ataque=0)
    com_dados(p, 9)
    novo = p.reagir(r, "volatile_magic")
    assert novo.dados[0].valor == 9 and p.sessao.esperanca == 0
