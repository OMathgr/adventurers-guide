"""Rolagens: expressões, teste de dualidade e o que ele aplica na ficha."""
import pytest

from motor import Criacao, Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel, Traco
from motor.rolagem import Dualidade, PapelDoDado, ler_expressao, rolar_expressao


class Dados:
    """rng de mentira: devolve os valores na ordem dada (e confere as faces)."""

    def __init__(self, *valores):
        self.valores = list(valores)
        self.faces: list[int] = []

    def randint(self, a, b):
        self.faces.append(b)
        return self.valores.pop(0)


def com_dados(p: Personagem, *valores) -> Dados:
    p.sessao.rng = Dados(*valores)
    return p.sessao.rng


# --- Expressões ------------------------------------------------------------------------------

def test_le_expressoes_com_varios_dados_e_numeros():
    assert ler_expressao("2d8+1d6-1") == ([(1, 2, 8), (1, 1, 6)], -1)
    assert ler_expressao(" d20 + 3 ") == ([(1, 1, 20)], 3)
    for ruim in ("", "2x8", "d1", "2d8+", "60d6"):
        with pytest.raises(RegraViolada):
            ler_expressao(ruim)


def test_rolar_expressao_e_dano_critico():
    r = rolar_expressao("2d8+3", Dados(5, 2), "Dano")
    assert ([d.valor for d in r.dados], r.total) == ([5, 2], 10)
    r = rolar_expressao("2d8+3", Dados(5, 2), "Dano", critico=True)
    assert r.total == 5 + 2 + 3 + 16   # crítico: soma o máximo dos dados


# --- Teste de dualidade ----------------------------------------------------------------------

def test_teste_com_esperanca_ganha_esperanca(bardo):
    com_dados(bardo, 9, 4)
    r = bardo.rolar_teste("atributo", "PRESENCE", dificuldade=13)
    assert (r.dualidade, r.total, r.sucesso) == (Dualidade.ESPERANCA, 9 + 4 + 2, True)
    assert bardo.sessao.esperanca == 3 and r.medo_gerado == 0


def test_teste_com_medo_da_medo_ao_mestre(bardo):
    com_dados(bardo, 2, 10)
    r = bardo.rolar_teste("atributo", "STRENGTH", dificuldade=15)
    assert (r.dualidade, r.total, r.sucesso, r.medo_gerado) == (Dualidade.MEDO, 2 + 10 - 1, False, 1)
    assert bardo.sessao.esperanca == 2


def test_critico_sempre_acerta_ganha_esperanca_e_limpa_fadiga(bardo):
    bardo.sessao.marcar_estresse(2)
    com_dados(bardo, 3, 3)
    r = bardo.rolar_teste("atributo", "STRENGTH", dificuldade=20)
    assert (r.dualidade, r.sucesso) == (Dualidade.CRITICO, True)
    assert (bardo.sessao.esperanca, bardo.sessao.estresse_marcado) == (3, 1)


def test_reacao_nao_gera_esperanca_nem_medo(bardo):
    com_dados(bardo, 2, 10)
    r = bardo.rolar_teste("atributo", "AGILITY", reacao=True)
    assert (r.medo_gerado, bardo.sessao.esperanca, r.efeitos) == (0, 2, [])


def test_vantagem_soma_d6_e_desvantagem_subtrai_e_se_cancelam(bardo):
    dados = com_dados(bardo, 5, 4, 6)
    r = bardo.rolar_teste("atributo", "PRESENCE", vantagem=True)
    assert r.total == 5 + 4 + 2 + 6 and dados.faces == [12, 12, 6]
    assert r.dados[2].papel is PapelDoDado.VANTAGEM
    com_dados(bardo, 5, 4, 6)
    assert bardo.rolar_teste("atributo", "PRESENCE", desvantagem=True).total == 5 + 4 + 2 - 6
    dados = com_dados(bardo, 5, 4)
    assert bardo.rolar_teste("atributo", "PRESENCE", vantagem=True, desvantagem=True).total == 5 + 4 + 2
    assert dados.faces == [12, 12]


def test_experiencias_custam_esperanca_e_somam(bardo):
    com_dados(bardo, 1, 8)
    r = bardo.rolar_teste("atributo", "PRESENCE", experiencias=["Diplomata", "Cantora de taverna"])
    assert r.total == 1 + 8 + 2 + 2 + 2
    assert bardo.sessao.esperanca == 0   # 2 - 2 (com Medo: não ganha)
    with pytest.raises(RegraViolada, match="Esperança"):
        bardo.rolar_teste("atributo", "PRESENCE", experiencias=["Diplomata"])


def test_ataque_usa_o_bonus_da_arma_e_dano_da_ficha(bardo):
    bardo.equipar(principal="core_weapon_rapier")
    com_dados(bardo, 7, 3)
    r = bardo.rolar_teste("ataque", 0)
    f = bardo.ficha()
    assert r.total == 7 + 3 + f.ataques[0].bonus and r.titulo.startswith("Ataque:")
    com_dados(bardo, 6, 3)
    d = bardo.rolar_dano(ataque=0, extra="1d6")   # 1d8 da rapieira + 1d6 extra
    assert d.expressao == f.ataques[0].dano + "+1d6"


def test_dano_de_carta_usa_a_proficiencia_quando_o_texto_manda(bib):
    criacao = Criacao(nome="Lia", classe="core_class_wizard", subclasse="core_subclass_school_of_war",
                      ancestralidade="core_ancestry_faun", comunidade="core_community_highborne",
                      tracos={Traco.CONHECIMENTO: 2, Traco.AGILIDADE: 1, Traco.PRESENCA: 1,
                              Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1},
                      experiencias=["A", "B"], cartas=["core_domain_card_book_of_ava", "core_domain_card_bolt_beacon"])
    p = Personagem(bib, criacao)
    com_dados(p, 4)
    r = p.rolar_dano(carta="core_domain_card_bolt_beacon")   # "d8+2 ... using your Proficiency": 1d8+2
    assert (r.expressao, r.total) == ("1d8+2", 6)
    with pytest.raises(RegraViolada, match="mão"):
        p.rolar_dano(carta="core_domain_card_book_of_grynn")


def test_padroes_estranhos_do_mago(bib):
    criacao = Criacao(nome="Lia", classe="core_class_wizard", subclasse="core_subclass_school_of_war",
                      ancestralidade="core_ancestry_faun", comunidade="core_community_highborne",
                      tracos={Traco.CONHECIMENTO: 2, Traco.AGILIDADE: 1, Traco.PRESENCA: 1,
                              Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1},
                      experiencias=["A", "B"], cartas=["core_domain_card_book_of_ava", "core_domain_card_bolt_beacon"])
    p = Personagem(bib, criacao)
    p.definir_padroes_estranhos(7)
    com_dados(p, 2, 7)   # com Medo, mas o 7 saiu no Dado de Medo
    r = p.rolar_teste("atributo", "KNOWLEDGE")
    assert p.sessao.esperanca == 3 and any("Padrões Estranhos" in e for e in r.efeitos)
    with pytest.raises(RegraViolada):
        p.definir_padroes_estranhos(13)


def test_padroes_estranhos_so_para_quem_tem(bardo):
    with pytest.raises(RegraViolada, match="Padrões Estranhos"):
        bardo.definir_padroes_estranhos(5)


def test_enfrentar_o_desafio_usa_d20_com_pouca_vida(bib):
    p = Personagem(bib, Criacao(
        nome="Bruna", classe="core_class_warrior", subclasse="core_subclass_call_of_the_brave",
        ancestralidade="core_ancestry_faun", comunidade="core_community_highborne",
        tracos={Traco.FORCA: 2, Traco.AGILIDADE: 1, Traco.INSTINTO: 1,
                Traco.ACUIDADE: 0, Traco.PRESENCA: 0, Traco.CONHECIMENTO: -1},
        experiencias=["A", "B"], cartas=["core_domain_card_get_back_up", "core_domain_card_whirlwind"]))
    for nivel, escolhas in ((2, [Opcao.PV, Opcao.ESTRESSE]), (3, [Opcao.PV, Opcao.ESTRESSE]),
                            (4, [Opcao.EVASAO, Opcao.EXPERIENCIAS])):
        carta = p.cartas_para_nivel()[0].id
        p.subir_de_nivel(SubidaDeNivel(nivel, [Escolha(o, experiencias=("A", "B") if o is Opcao.EXPERIENCIAS else ())
                                               for o in escolhas], carta,
                                       nova_experiencia="C" if nivel == 2 else None))
    p.subir_de_nivel(SubidaDeNivel(5, [Escolha(Opcao.SUBCLASSE), Escolha(Opcao.PV)], p.cartas_para_nivel()[0].id,
                                   nova_experiencia="D"))
    dados = com_dados(p, 5, 3)
    p.rolar_teste("atributo", "STRENGTH")
    assert dados.faces == [12, 12]   # vida cheia: d12
    p.sessao.marcar_pv(p.ficha().pv_max - 2)
    dados = com_dados(p, 15, 3)
    r = p.rolar_teste("atributo", "STRENGTH")
    assert dados.faces == [20, 12] and r.dados[0].faces == 20
