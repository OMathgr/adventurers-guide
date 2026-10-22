"""Usar carta (etapa 2 das cartas): custo, limite, marcadores, opções e efeitos
em você ou em aliados, pelo catálogo data/usos_de_cartas.json."""

import json

import pytest

from motor import Criacao, Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel, Traco
from motor.srd import ALTERNATIVAS_A_MORTE, DEFESAS_DE_CARTAS, PASTA_DADOS
from motor.usos_de_cartas import quanto

TRACOS = {Traco.PRESENCA: 2, Traco.AGILIDADE: 1, Traco.CONHECIMENTO: 1,
          Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1}


def carta(nome: str) -> str:
    return f"core_domain_card_{nome}"


def escolhas(nivel: int) -> list[Escolha]:
    posicao = {2: 0, 3: 1, 4: 2, 5: 0, 6: 1, 7: 2, 8: 0, 9: 1, 10: 2}[nivel]
    return [[Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)],
            [Escolha(Opcao.TRACOS, tracos=(Traco.ACUIDADE, Traco.INSTINTO)), Escolha(Opcao.ESTRESSE)],
            [Escolha(Opcao.EVASAO), Escolha(Opcao.EXPERIENCIAS, experiencias=("A", "B"))]][posicao]


def criar(bib, classe, subclasse, iniciais, nivel=1, cartas: dict[int, str] = {}, nome="T", tracos=TRACOS):
    p = Personagem(bib, Criacao(nome=nome, classe=classe, subclasse=subclasse, ancestralidade="core_ancestry_faun",
                                comunidade="core_community_highborne", tracos=dict(tracos),
                                experiencias=["A", "B"], cartas=[carta(c) for c in iniciais]))
    for n in range(2, nivel + 1):
        escolhida = cartas.get(n) or next(c.id for c in p.cartas_para_nivel()
                                          if not (c.passivo or c.escolha or c.fora_do_limite))
        p.subir_de_nivel(SubidaDeNivel(n, escolhas(n), escolhida, nova_experiencia=f"E{n}" if n in (2, 5, 8) else None))
    for c in cartas.values():   # as cartas pedidas ficam na mão
        if c in p.cofre:
            sai = next(x for x in p.ficha().cartas_ativas if x not in cartas.values())
            p.recuperar_carta(c, no_lugar_de=sai, em_descanso=True)
    return p


def bardo(bib, **kw):
    return criar(bib, "core_class_bard", "core_subclass_troubadour", ["inspirational_words", "book_of_ava"], **kw)


def guardiao(bib, nome="Bram", **kw):
    return criar(bib, "core_class_guardian", "core_subclass_vengeance", ["get_back_up", "i_am_your_shield"],
                 nome=nome, **kw)


# --- o catálogo -----------------------------------------------------------------------------------

def test_toda_carta_do_srd_tem_algum_efeito_no_app(bib):
    rolagem = {e["fonte"]["id"] for e in json.load(open(PASTA_DADOS / "efeitos_de_rolagem.json", encoding="utf-8"))["efeitos"]
               if e["fonte"]["tipo"] == "carta"}
    automaticas_no_dano = {carta("unyielding_armor"), carta("on_the_brink")}
    sem = [c.id for c in bib.cartas.values()
           if not (c.uso or c.passivo or c.escolha or c.fora_do_limite or c.id in rolagem
                   or c.id in DEFESAS_DE_CARTAS or c.id in ALTERNATIVAS_A_MORTE or c.id in automaticas_no_dano)]
    assert sem == []


def test_quantidades(bib):
    v = {"n": 3, "conjuracao": 2, "AGILITY": -1, "marcadores": 4, "PRESENCE": 1}
    assert [quanto(x, v, None) for x in ("2xn", "n+1", "conjuracao-PRESENCE", "min1:AGILITY", "metade:n", "marcadores+1")] \
        == [6, 4, 1, 1, 2, 5]


# --- marcadores e aliado: Inspirational Words ----------------------------------------------------------

def test_palavras_inspiradoras_gastam_marcador_no_aliado(bib):
    p, aliado = bardo(bib), guardiao(bib)
    assert p.marcadores_da_carta(carta("inspirational_words")) == 2   # Presença 2 no começo da sessão
    aliado.sessao.estresse_marcado = 3
    r = p.usar_carta(carta("inspirational_words"), [aliado], opcao="pf")
    assert aliado.sessao.estresse_marcado == 2 and p.marcadores_da_carta(carta("inspirational_words")) == 1
    assert "Bram: limpou 1 PF." in r.notas
    with pytest.raises(RegraViolada, match="escolha um aliado"):
        p.usar_carta(carta("inspirational_words"), [], opcao="pv")
    p.usar_carta(carta("inspirational_words"), [aliado], opcao="esperanca")
    with pytest.raises(RegraViolada, match="0 marcador"):
        p.usar_carta(carta("inspirational_words"), [aliado], opcao="esperanca")
    p.sessao.terminar_repouso(longo=True)   # volta ao que a carta dá
    assert p.marcadores_da_carta(carta("inspirational_words")) == 2


def test_opcao_e_obrigatoria_e_carta_precisa_estar_na_mao(bib):
    p = bardo(bib)
    with pytest.raises(RegraViolada, match="escolha uma das opções"):
        p.usar_carta(carta("book_of_ava"))
    p.guardar_carta(carta("book_of_ava"))
    with pytest.raises(RegraViolada, match="precisa estar na mão"):
        p.usar_carta(carta("book_of_ava"), opcao="empurrao")
    with pytest.raises(RegraViolada, match="não se usa assim"):
        p.usar_carta(carta("bare_bones"))


# --- bônus até o descanso: Tava's Armor e Full Surge -------------------------------------------------

def test_armadura_de_tava_no_aliado_ate_o_descanso(bib):
    p, aliado = bardo(bib), guardiao(bib)
    aliado.equipar(armadura="core_armor_leather_armor")
    p.sessao.esperanca = 2
    p.usar_carta(carta("book_of_ava"), [aliado], opcao="armadura")
    assert aliado.ficha().pontuacao_armadura == 4 and p.sessao.esperanca == 1
    aliado.sessao.terminar_repouso(longo=False)
    assert aliado.ficha().pontuacao_armadura == 3


def test_full_surge_mais_2_em_tudo_e_limite(bib):
    p = guardiao(bib, nivel=8, cartas={8: carta("full_surge")})
    antes = p.ficha().tracos
    p.usar_carta(carta("full_surge"))
    assert p.ficha().tracos == {t: v + 2 for t, v in antes.items()} and p.sessao.estresse_marcado == 3
    with pytest.raises(RegraViolada, match="descanso longo"):
        p.usar_carta(carta("full_surge"))
    p.sessao.terminar_repouso(longo=False)
    assert p.ficha().tracos == antes   # o bônus acaba no descanso; o uso só volta no longo
    assert p.estado()["sessao"]["bonus_temporarios"] == {}


# --- quantidade, custo variável, teste --------------------------------------------------------------------

def test_caos_gasta_marcadores_e_recarrega(bib):
    instinto = {**TRACOS, Traco.INSTINTO: 2, Traco.PRESENCA: 0}   # Feiticeiro conjura com Instinto
    p = criar(bib, "core_class_sorcerer", "core_subclass_elemental_origin", ["unleash_chaos", "rune_ward"], tracos=instinto)
    conj = p.ficha().conjuracoes[0].bonus
    assert conj == 2
    assert p.marcadores_da_carta(carta("unleash_chaos")) == conj
    r = p.usar_carta(carta("unleash_chaos"), opcao="lancar", quantidade=conj)
    assert f"{conj}d10" in r.teste and p.marcadores_da_carta(carta("unleash_chaos")) == 0
    with pytest.raises(RegraViolada, match="de 1 a 0"):
        p.usar_carta(carta("unleash_chaos"), opcao="lancar", quantidade=1)
    p.usar_carta(carta("unleash_chaos"), opcao="recarregar")
    assert p.marcadores_da_carta(carta("unleash_chaos")) == conj and p.sessao.estresse_marcado == 1


def test_copycat_custa_metade_do_nivel(bib):
    p = bardo(bib, nivel=9, cartas={9: carta("copycat")})
    p.sessao.esperanca = 5
    p.usar_carta(carta("copycat"), quantidade=7)
    assert p.sessao.esperanca == 1   # metade de 7 = 4 (para cima)


def test_know_thy_enemy_tira_medo(bib):
    p = criar(bib, "core_class_warrior", "core_subclass_call_of_the_brave", ["get_back_up", "whirlwind"],
              nivel=5, cartas={5: carta("know_thy_enemy")})
    p.sessao.esperanca = 1
    r = p.usar_carta(carta("know_thy_enemy"), opcao="medo")
    assert r.medo == 1 and p.sessao.estresse_marcado == 1 and r.teste == "Instinto contra o alvo"


# --- vários alvos ------------------------------------------------------------------------------------------

def test_campo_de_cura_no_grupo(bib):
    p = criar(bib, "core_class_druid", "core_subclass_warden_of_the_elements", ["gifted_tracker", "vicious_entangle"],
              nivel=4, cartas={4: carta("healing_field")})
    aliado = guardiao(bib)
    p.sessao.pv_marcados, aliado.sessao.pv_marcados = 2, 3
    p.usar_carta(carta("healing_field"), [aliado], opcao="um")
    assert (p.sessao.pv_marcados, aliado.sessao.pv_marcados) == (1, 2)


def test_dividir_o_fardo(bib):
    p = bardo(bib, nivel=6, cartas={6: carta("share_the_burden")})
    aliado = guardiao(bib)
    aliado.sessao.estresse_marcado = 2
    with pytest.raises(RegraViolada, match="de 1 a 2"):
        p.usar_carta(carta("share_the_burden"), [aliado], quantidade=3)
    esperanca = p.sessao.esperanca
    p.usar_carta(carta("share_the_burden"), [aliado], quantidade=2)
    assert (aliado.sessao.estresse_marcado, p.sessao.estresse_marcado, p.sessao.esperanca) == (0, 2, esperanca + 2)


def test_codex_touched_pede_4_cartas_de_codice(bib):
    p = bardo(bib, nivel=7, cartas={7: carta("codex_touched")})
    if sum(1 for c in p.cartas_na_mao() if bib.cartas[c].dominio == "CODEX") < 4:
        with pytest.raises(RegraViolada, match="4 cartas"):
            p.usar_carta(carta("codex_touched"), opcao="proficiencia")


def test_selo_da_vida_salva_o_aliado(bib):
    p = criar(bib, "core_class_seraph", "core_subclass_winged_sentinel", ["bolt_beacon", "mending_touch"],
              nivel=4, cartas={4: carta("life_ward")})
    aliado = guardiao(bib)
    p.sessao.esperanca = 3
    p.usar_carta(carta("life_ward"), [aliado])
    aliado.sessao.pv_marcados = aliado.ficha().pv_max
    assert carta("life_ward") in aliado.ficha().alternativas_a_morte
    aliado.sessao.evitar_morte_com_carta(carta("life_ward"))
    assert aliado.sessao.pv_marcados == aliado.ficha().pv_max - 1 and "Selo da Vida" not in aliado.sessao.condicoes
