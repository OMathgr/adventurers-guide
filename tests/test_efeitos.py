"""Características que mudam como dano, armadura e descanso funcionam."""

import pytest

from motor import Efeito, Movimento, RegraViolada, TipoDano

# Bardo nível 1: 5 PV, 6 Estresse, Esperança 2. Limiares = base da armadura + 1.


def armadura(bardo, nome):
    bardo.equipar(armadura=f"core_armor_{nome}")
    return bardo.sessao


def test_todo_efeito_existe_no_srd(bib):
    """Os efeitos são reconhecidos pelo nome; se o SRD mudar um nome, este teste avisa."""
    fontes = [*bib.armas.values(), *bib.armaduras.values(), *bib.ancestralidades.values()]
    encontrados = {c.efeito for p in fontes for c in p.caracteristicas if c.efeito}
    assert encontrados == set(Efeito)


def test_painful_de_arma_nao_vira_efeito(bib):
    painful = next(c for c in bib.armas["core_weapon_bloodstaff"].caracteristicas
                   if c.nome == "Painful")
    assert painful.efeito is None


# --- Fortified ---------------------------------------------------------------------

def test_fortified_reduz_dois_niveis(bardo):
    sessao = armadura(bardo, "full_fortified_armor")     # limiares 16 / 41
    r = sessao.receber_dano(41, usar_armadura=True)       # grave -> menor
    assert (r.pv_marcados, r.espacos_marcados) == (1, 1)
    assert "Fortificação" in r.notas[0]
    assert sessao.receber_dano(16, usar_armadura=True).pv_marcados == 0   # maior -> nenhum


# --- Painful (armadura) -------------------------------------------------------------

def test_painful_marca_estresse_a_cada_espaco(bardo):
    sessao = armadura(bardo, "runes_of_fortification")
    r = sessao.receber_dano(20, usar_armadura=True)
    assert (r.espacos_marcados, r.estresse_marcado) == (1, 1)
    sessao.marcar_armadura(2)
    assert (sessao.armadura_marcada, sessao.estresse_marcado) == (3, 3)


# --- Resilient ---------------------------------------------------------------------

def test_resilient_com_6_nao_marca_o_ultimo_espaco(bardo):
    sessao = armadura(bardo, "harrowbone_armor")          # 4 espaços
    sessao.marcar_armadura(3)
    r = sessao.receber_dano(10, usar_armadura=True, rolagem_d6=6)
    assert (r.rolagem_d6, r.espacos_marcados, r.pv_marcados, r.usou_armadura) == (6, 0, 1, True)
    assert sessao.armadura_marcada == 3


def test_resilient_sem_6_marca_normalmente(bardo):
    sessao = armadura(bardo, "harrowbone_armor")
    sessao.marcar_armadura(3)
    r = sessao.receber_dano(10, usar_armadura=True, rolagem_d6=2)
    assert (r.espacos_marcados, r.pv_marcados) == (1, 1)
    assert sessao.armadura_marcada == 4


def test_resilient_so_rola_no_ultimo_espaco(bardo):
    sessao = armadura(bardo, "harrowbone_armor")
    assert sessao.receber_dano(10, usar_armadura=True).rolagem_d6 is None


# --- Reinforced ---------------------------------------------------------------------

def test_reinforced_sobe_limiares_com_todos_os_espacos_marcados(bardo):
    sessao = armadura(bardo, "irontree_breastplate_armor")   # 10 / 21, 4 espaços
    sessao.marcar_armadura(3)
    assert bardo.ficha().limiar_maior == 10
    sessao.marcar_armadura(1)
    f = bardo.ficha()
    assert (f.limiar_maior, f.limiar_grave) == (12, 23)
    sessao.descanso_curto([Movimento.REPARAR_ARMADURA, Movimento.PREPARAR], [1, None])
    assert bardo.ficha().limiar_maior == 10


# --- Hopeful ------------------------------------------------------------------------

def test_hopeful_paga_esperanca_com_armadura(bardo):
    sessao = armadura(bardo, "rosewild_armor")
    sessao.gastar_esperanca(3, com_armadura=1)
    assert (sessao.esperanca, sessao.armadura_marcada) == (0, 1)
    with pytest.raises(RegraViolada, match="mais do que o custo"):
        sessao.gastar_esperanca(1, com_armadura=2)


def test_sem_hopeful_nao_paga_com_armadura(bardo):
    sessao = armadura(bardo, "leather_armor")
    with pytest.raises(RegraViolada, match="armadura com Esperança"):
        sessao.gastar_esperanca(1, com_armadura=1)
    assert (sessao.esperanca, sessao.armadura_marcada) == (2, 0)


# --- Impenetrable -----------------------------------------------------------------

def test_impenetrable_uma_vez_por_descanso(bardo):
    sessao = armadura(bardo, "dragonscale_armor")         # 12 / 28
    sessao.marcar_pv(4)
    r = sessao.receber_dano(5, evitar_queda=True)
    assert (r.pv_marcados, r.estresse_marcado, r.caiu) == (0, 1, False)
    assert sessao.receber_dano(5, evitar_queda=True).caiu  # já usado
    sessao.descanso_curto([Movimento.CUIDAR_FERIDAS, Movimento.PREPARAR], [1, None])
    assert not sessao.receber_dano(5, evitar_queda=True).caiu   # volta a valer


def test_impenetrable_e_opcional(bardo):
    sessao = armadura(bardo, "dragonscale_armor")
    sessao.marcar_pv(4)
    assert sessao.receber_dano(5).caiu


# --- Warded, Magic e Physical --------------------------------------------------------

def test_warded_reduz_dano_magico(bardo):
    sessao = armadura(bardo, "elundrian_chain_armor")     # 10 / 22, Pontuação 4
    r = sessao.receber_dano(13, tipo=TipoDano.MAGICO)     # 13 - 4 = 9: menor
    assert (r.dano, r.pv_marcados) == (9, 1)
    assert sessao.receber_dano(13, tipo=TipoDano.FISICO).pv_marcados == 2


def test_physical_nao_reduz_dano_magico(bardo):
    sessao = armadura(bardo, "bladefare_armor")
    with pytest.raises(RegraViolada, match="mágico"):
        sessao.receber_dano(20, usar_armadura=True, tipo=TipoDano.MAGICO)
    assert sessao.pv_marcados == 0
    assert sessao.receber_dano(20, usar_armadura=True, tipo=TipoDano.FISICO).usou_armadura


def test_magic_nao_reduz_dano_fisico(bardo):
    sessao = armadura(bardo, "monetts_cloak")
    with pytest.raises(RegraViolada, match="físico"):
        sessao.receber_dano(20, usar_armadura=True, tipo=TipoDano.FISICO)
    assert sessao.receber_dano(20, usar_armadura=True, tipo=TipoDano.MAGICO).usou_armadura


# --- Healing (arma) -----------------------------------------------------------------

def test_healing_limpa_um_pv_em_todo_descanso(bardo):
    bardo.equipar(principal="core_weapon_blessed_anlace")
    sessao = bardo.sessao
    sessao.marcar_pv(2)
    r = sessao.descanso_curto([Movimento.PREPARAR, Movimento.PREPARAR])
    assert r[-1].fonte == "Healing" and r[-1].recuperado == 1
    assert sessao.pv_marcados == 1


# --- Genérico ---------------------------------------------------------------------

def test_marcar_armadura_sem_espaco(bardo):
    sessao = armadura(bardo, "leather_armor")
    with pytest.raises(RegraViolada, match="insuficientes"):
        sessao.marcar_armadura(4)
    assert sessao.armadura_marcada == 0
