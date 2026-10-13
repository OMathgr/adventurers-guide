"""Limite de nível da mesa, cópia para outra mesa e plano de níveis futuros."""

import pytest

from motor import Escolha, Opcao, RegraViolada, SubidaDeNivel


def nivel_3_diferente():
    """Original no nível 3: Fadiga + PV. Aqui: Fadiga duas vezes."""
    return SubidaDeNivel(3, [Escolha(Opcao.ESTRESSE), Escolha(Opcao.ESTRESSE)], "core_domain_card_troublemaker")


def test_limite_da_mesa_bloqueia_subir(bardo_nivel_4):
    bardo_nivel_4.nivel_limite = 4
    p = bardo_nivel_4.proximo_nivel()
    assert p.limite_mesa == 4 and p.bloqueado_pela_mesa
    with pytest.raises(RegraViolada, match="nível 4"):
        bardo_nivel_4.subir_de_nivel(SubidaDeNivel(5, [Escolha(Opcao.EVASAO), Escolha(Opcao.PV)],
                                                   "core_domain_card_hypnotic_shimmer", nova_experiencia="Y"))
    assert bardo_nivel_4.linha_do_tempo()[4]["bloqueado_pela_mesa"]


def test_copia_para_mesa_menor_vira_plano(bardo_nivel_4):
    copia = bardo_nivel_4.copia(nivel_maximo=2)
    assert copia.ficha().nivel == 2 and bardo_nivel_4.ficha().nivel == 4   # o original não muda
    assert [s.nivel for s in copia.plano] == [3, 4]
    tempo = copia.linha_do_tempo()
    assert tempo[2]["planejado"] and tempo[2]["itens"][0].startswith("Planejado:")
    assert tempo[2]["bloqueado_pela_mesa"]
    p = copia.proximo_nivel()
    assert p.planejado and p.bloqueado_pela_mesa
    with pytest.raises(RegraViolada, match="mesa"):
        copia.aplicar_plano()
    copia.nivel_limite = 3                   # o mestre liberou o nível 3
    assert copia.aplicar_plano().nivel == 3
    assert [s.nivel for s in copia.plano] == [4]


def test_copia_sem_limite_leva_tudo_e_o_estado(bardo_nivel_4):
    bardo_nivel_4.equipar(principal="core_weapon_broadsword")
    bardo_nivel_4.guardar_carta("core_domain_card_inspirational_words")
    bardo_nivel_4.sessao.marcar_pv(2)
    copia = bardo_nivel_4.copia()
    assert copia.ficha().nivel == 4 and copia.plano == []
    assert copia.equipamento.principal == "core_weapon_broadsword"
    assert copia.cofre == ["core_domain_card_inspirational_words"]
    assert copia.ficha().pv_marcados == 0     # sessão começa do zero


def test_descartar_e_subir_na_mao_supera_o_plano(bardo_nivel_4):
    copia = bardo_nivel_4.copia(nivel_maximo=2)
    copia.nivel_limite = 4
    copia.subir_de_nivel(nivel_3_diferente())   # escolheu outra coisa no 3
    assert [s.nivel for s in copia.plano] == [4]
    copia.descartar_plano(4)
    assert copia.plano == []
    with pytest.raises(RegraViolada, match="Não há plano"):
        copia.descartar_plano(4)
    with pytest.raises(RegraViolada, match="Não há plano"):
        copia.aplicar_plano()


def test_plano_que_nao_vale_mais_fica_e_da_erro(bardo_nivel_4):
    copia = bardo_nivel_4.copia(nivel_maximo=2)
    copia.plano[0] = SubidaDeNivel(3, [Escolha(Opcao.EVASAO), Escolha(Opcao.PV)], "core_domain_card_troublemaker")
    with pytest.raises(RegraViolada):            # Evasão do patamar 2 já foi usada no nível 2
        copia.aplicar_plano()
    assert [s.nivel for s in copia.plano] == [3, 4] and copia.ficha().nivel == 2
