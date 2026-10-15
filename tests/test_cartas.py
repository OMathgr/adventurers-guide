import pytest

from motor import Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel

# Bardo: domínios GRACE e CODEX. Cria com 2 cartas e ganha 1 por nível,
# então no nível 4 (bardo_nivel_4) tem 5 cartas: o loadout está cheio.

PALAVRAS = "core_domain_card_inspirational_words"   # nível 1, criação
LIVRO = "core_domain_card_book_of_ava"              # nível 1, criação
MULTICLASSE_MAGO = Escolha(Opcao.MULTICLASSE, classe="core_class_wizard", dominio="SPLENDOR",
                           subclasse="core_subclass_school_of_war")


def ids(cartas):
    return [c.id for c in cartas]


def subida_2(carta, escolhas=None, troca=None):
    return SubidaDeNivel(2, escolhas or [Escolha(Opcao.EVASAO), Escolha(Opcao.PV)],
                         carta, nova_experiencia="X", troca_carta=troca)


def subida_5(carta):
    return SubidaDeNivel(5, [Escolha(Opcao.EVASAO), Escolha(Opcao.PV)], carta, nova_experiencia="Y")


# --- Listagem: carta do nível ------------------------------------------------------

def test_cartas_para_nivel_respeitam_dominio_e_nivel(bardo):
    opcoes = bardo.cartas_para_nivel()
    assert opcoes
    assert all(c.dominio in ("GRACE", "CODEX") and c.nivel <= 2 for c in opcoes)
    assert PALAVRAS not in ids(opcoes) and LIVRO not in ids(opcoes)
    assert "core_domain_card_tell_no_lies" in ids(opcoes)


def test_toda_carta_listada_e_aceita_e_as_outras_nao(bib, criacao_bardo, bardo):
    """A listagem e a validação usam a mesma regra; este teste garante isso."""
    listadas = set(ids(bardo.cartas_para_nivel()))
    for carta in bib.cartas:
        tentativa = Personagem(bib, criacao_bardo)
        try:
            tentativa.subir_de_nivel(subida_2(carta))
            aceita = True
        except RegraViolada:
            aceita = False
        assert aceita == (carta in listadas), carta


def test_multiclasse_marcada_no_nivel_libera_dominio_novo(bardo_nivel_4):
    sem = bardo_nivel_4.cartas_para_nivel()
    com = bardo_nivel_4.cartas_para_nivel([MULTICLASSE_MAGO])
    assert not any(c.dominio == "SPLENDOR" for c in sem)
    esplendor = [c for c in com if c.dominio == "SPLENDOR"]
    assert esplendor and max(c.nivel for c in esplendor) == 3   # metade de 5, arredondada para cima


def test_carta_do_avanco_sai_da_lista_do_passo_4(bardo):
    escolhas = [Escolha(Opcao.CARTA_DOMINIO, carta="core_domain_card_tell_no_lies"), Escolha(Opcao.PV)]
    assert "core_domain_card_tell_no_lies" not in ids(bardo.cartas_para_nivel(escolhas))


def test_nivel_com_duas_cartas(bardo):
    """Marcando o avanço CARTA_DOMINIO, o nível rende 2 cartas (avanço + passo 4)."""
    avanco = bardo.cartas_para_avanco()[0].id
    escolhas = [Escolha(Opcao.CARTA_DOMINIO, carta=avanco), Escolha(Opcao.PV)]
    passo_4 = bardo.cartas_para_nivel(escolhas)[0].id
    f = bardo.subir_de_nivel(subida_2(passo_4, escolhas))
    assert len(f.cartas) == 4 and {avanco, passo_4} <= set(f.cartas)


# --- Listagem: avanço CARTA_DOMINIO -----------------------------------------------

def test_cartas_para_avanco_limitadas_pelo_tier(bardo_nivel_4):
    assert max(c.nivel for c in bardo_nivel_4.cartas_para_avanco()) == 5          # tier 3, nível 5
    assert max(c.nivel for c in bardo_nivel_4.cartas_para_avanco(tier=2)) == 4    # quadradinho do tier 2


# --- Listagem: troca -------------------------------------------------------------

def test_cartas_para_troca(bardo):
    opcoes = bardo.cartas_para_troca(PALAVRAS, carta_do_nivel="core_domain_card_tell_no_lies")
    assert opcoes and all(c.nivel <= 1 for c in opcoes)
    assert PALAVRAS not in ids(opcoes) and "core_domain_card_tell_no_lies" not in ids(opcoes)
    with pytest.raises(RegraViolada):
        bardo.cartas_para_troca("core_domain_card_troublemaker")   # não tem


# --- Loadout e cofre --------------------------------------------------------------

def test_cartas_da_criacao_comecam_no_loadout(bardo):
    f = bardo.ficha()
    assert f.cartas_ativas == [PALAVRAS, LIVRO] and f.cartas_cofre == []


def test_carta_nova_vai_para_o_cofre_com_loadout_cheio(bardo_nivel_4):
    assert len(bardo_nivel_4.ficha().cartas_ativas) == 5
    f = bardo_nivel_4.subir_de_nivel(subida_5("core_domain_card_hypnotic_shimmer"))
    assert f.cartas_cofre == ["core_domain_card_hypnotic_shimmer"]
    assert len(f.cartas_ativas) == 5 and len(f.cartas) == 6


def test_guardar_e_recuperar_carta(bib, bardo):
    bardo.guardar_carta(PALAVRAS)
    assert bardo.ficha().cartas_cofre == [PALAVRAS]
    assert bardo.recuperar_carta(PALAVRAS) == bib.cartas[PALAVRAS].custo_recall
    assert bardo.ficha().cartas_cofre == []
    bardo.guardar_carta(PALAVRAS)
    assert bardo.recuperar_carta(PALAVRAS, em_descanso=True) == 0


def test_recuperar_com_loadout_cheio_exige_troca(bardo_nivel_4):
    bardo_nivel_4.subir_de_nivel(subida_5("core_domain_card_hypnotic_shimmer"))
    with pytest.raises(RegraViolada, match="Mão cheia"):
        bardo_nivel_4.recuperar_carta("core_domain_card_hypnotic_shimmer")
    bardo_nivel_4.recuperar_carta("core_domain_card_hypnotic_shimmer", no_lugar_de=PALAVRAS)
    f = bardo_nivel_4.ficha()
    assert f.cartas_cofre == [PALAVRAS]
    assert "core_domain_card_hypnotic_shimmer" in f.cartas_ativas


def test_erros_de_cofre(bardo):
    with pytest.raises(RegraViolada):
        bardo.guardar_carta("core_domain_card_troublemaker")    # não tem
    with pytest.raises(RegraViolada):
        bardo.recuperar_carta(PALAVRAS)                         # não está no cofre
    bardo.guardar_carta(PALAVRAS)
    with pytest.raises(RegraViolada):
        bardo.guardar_carta(PALAVRAS)                           # já está
    with pytest.raises(RegraViolada):
        bardo.recuperar_carta(PALAVRAS, no_lugar_de=PALAVRAS)   # a que sai não está ativa


def test_desfazer_nivel_tira_a_carta_do_cofre(bardo_nivel_4):
    bardo_nivel_4.subir_de_nivel(subida_5("core_domain_card_hypnotic_shimmer"))
    bardo_nivel_4.desfazer_ultimo_nivel()
    assert bardo_nivel_4.cofre == []
    assert len(bardo_nivel_4.ficha().cartas_ativas) == 5


def test_troca_de_carta_guardada_mantem_no_cofre(bardo):
    bardo.guardar_carta(PALAVRAS)
    f = bardo.subir_de_nivel(subida_2("core_domain_card_tell_no_lies",
                                      troca=(PALAVRAS, "core_domain_card_book_of_illiat")))
    assert f.cartas_cofre == ["core_domain_card_book_of_illiat"]


# --- Mão cheia ao subir de nível ("Trocando ao Subir de Nível") ----------------------

SHIMMER = "core_domain_card_hypnotic_shimmer"


def _subida_5_reserva(*para_reserva):
    s = subida_5(SHIMMER)
    s.para_reserva = list(para_reserva)
    return s


def test_mao_cheia_carta_antiga_vai_para_a_reserva_sem_custo(bardo_nivel_4):
    f = bardo_nivel_4.subir_de_nivel(_subida_5_reserva(PALAVRAS))
    assert f.cartas_cofre == [PALAVRAS]
    assert SHIMMER in f.cartas_ativas and len(f.cartas_ativas) == 5
    assert f.estresse_marcado == 0


def test_para_reserva_so_cartas_que_ja_tinha_e_no_maximo_as_novas(bardo_nivel_4):
    with pytest.raises(RegraViolada, match="já tinha"):
        bardo_nivel_4.subir_de_nivel(_subida_5_reserva(SHIMMER))            # a nova
    with pytest.raises(RegraViolada, match="no máximo 1"):
        bardo_nivel_4.subir_de_nivel(_subida_5_reserva(PALAVRAS, LIVRO))   # ganha só 1 carta
    assert bardo_nivel_4.historico[-1].nivel == 4                         # nada mudou


def test_desfazer_devolve_a_carta_para_a_mao(bardo_nivel_4):
    bardo_nivel_4.subir_de_nivel(_subida_5_reserva(PALAVRAS))
    bardo_nivel_4.desfazer_ultimo_nivel()
    f = bardo_nivel_4.ficha()
    assert f.cartas_cofre == [] and PALAVRAS in f.cartas_ativas


def test_multiclasse_exige_dominio_novo(bardo_nivel_4):
    # Bardo já tem Códice; Mago é Códice + Esplendor: só Esplendor vale
    codice = Escolha(Opcao.MULTICLASSE, classe="core_class_wizard", dominio="CODEX",
                     subclasse="core_subclass_school_of_war")
    with pytest.raises(RegraViolada, match="já tem acesso"):
        bardo_nivel_4.subir_de_nivel(SubidaDeNivel(5, [codice], SHIMMER, nova_experiencia="Y"))
    f = bardo_nivel_4.subir_de_nivel(SubidaDeNivel(5, [MULTICLASSE_MAGO], SHIMMER, nova_experiencia="Y"))
    assert f.multiclasse["dominio"] == "SPLENDOR"
