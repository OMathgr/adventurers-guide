"""Inventário: ouro, itens, consumíveis, relíquias, armas guardadas e lojas."""

import dataclasses

import pytest

from motor import Personagem, RegraViolada, TipoDeItem, Traco
from motor.inventario import Inventario, decompor, em_punhados
from motor.loja import ItemDaLoja, TipoNaLoja, validar, vender

POCAO_VIDA = "core_consumable_minor_health_potion"
POCAO_VIGOR = "core_consumable_minor_stamina_potion"


# --- catálogo -----------------------------------------------------------------------------

def test_catalogo_tem_as_tabelas_do_srd(bib):
    saque = [i for i in bib.itens.values() if i.tipo is TipoDeItem.SAQUE]
    consumiveis = [i for i in bib.itens.values() if i.tipo is TipoDeItem.CONSUMIVEL]
    assert len(saque) == len(consumiveis) == 60
    assert sorted(i.rolagem for i in saque) == list(range(1, 61))
    assert bib.itens["core_loot_premium_bedroll"].texto == "During downtime, you automatically clear a Stress."
    assert bib.classes["core_class_bard"].itens == ("core_class_bard_item_1", "core_class_bard_item_2")
    assert bib.itens["core_class_bard_item_1"].nome == "A romance novel"


def test_efeitos_simples_lidos_do_texto(bib):
    ef = {i.nome_original: i.efeito for i in bib.itens.values() if i.efeito}
    assert ef["Health Potion"].limpa_pv == "1d4+1"
    assert ef["Major Stamina Potion"].limpa_pf == "1d4+2"
    assert ef["Varik Leaves"].ganha_esperanca == "2"
    assert (ef["Snap Powder"].marca_pf, ef["Snap Powder"].limpa_pv) == (1, "1")
    assert ef["Sweet Moss"].escolha
    assert (ef["Feast of Xuria"].limpa_pv, ef["Feast of Xuria"].ganha_esperanca) == ("tudo", "1d4")
    assert ef["Sleeping Sap"].limpa_pf == "tudo"
    assert len(ef) == 11   # o resto só tem texto (o jogador narra)
    assert bib.itens["core_loot_stride_relic"].reliquia is Traco.AGILIDADE
    assert bib.itens["core_loot_honing_relic"].reliquia == "EXPERIENCIA"


# --- ouro -----------------------------------------------------------------------------------

def test_ouro_sobe_de_punhado_para_bolsa_e_bau():
    inv = Inventario(ouro=9)
    inv.ganhar_ouro(1)   # 9 punhados + 1 = 1 bolsa
    assert decompor(inv.ouro) == {"baus": 0, "bolsas": 1, "punhados": 0}
    inv.ganhar_ouro(em_punhados(bolsas=9))
    assert decompor(inv.ouro) == {"baus": 1, "bolsas": 0, "punhados": 0}


def test_no_maximo_um_bau():
    inv = Inventario(ouro=em_punhados(baus=1, bolsas=9, punhados=9))
    with pytest.raises(RegraViolada, match="Não cabe mais ouro"):
        inv.ganhar_ouro(1)
    assert inv.ouro == 199


def test_gastar_troca_bolsa_por_punhados():
    inv = Inventario(ouro=em_punhados(bolsas=1))
    inv.gastar_ouro(3)
    assert decompor(inv.ouro) == {"baus": 0, "bolsas": 0, "punhados": 7}
    with pytest.raises(RegraViolada, match="faltam 1 bolsa"):
        inv.gastar_ouro(17)


# --- itens ---------------------------------------------------------------------------------

def test_no_maximo_cinco_de_cada_consumivel(bib):
    inv = Inventario()
    inv.adicionar(bib, POCAO_VIDA, 5)
    with pytest.raises(RegraViolada, match="No máximo 5"):
        inv.adicionar(bib, POCAO_VIDA)
    inv.adicionar(bib, POCAO_VIGOR, 5)   # o limite é por consumível
    inv.adicionar(bib, "core_loot_manacles", 7)   # saque não tem limite


def test_so_uma_reliquia(bib):
    inv = Inventario()
    inv.adicionar(bib, "core_loot_stride_relic")
    with pytest.raises(RegraViolada, match="uma relíquia"):
        inv.adicionar(bib, "core_loot_charm_relic")
    with pytest.raises(RegraViolada, match="uma relíquia"):
        inv.adicionar(bib, "core_loot_stride_relic")


def test_reliquia_soma_no_atributo_e_na_experiencia(bardo, bib):
    agilidade = bardo.ficha().tracos[Traco.AGILIDADE]
    bardo.inventario.adicionar(bib, "core_loot_stride_relic")
    assert bardo.ficha().tracos[Traco.AGILIDADE] == agilidade + 1
    bardo.inventario.remover(bib, "core_loot_stride_relic")
    bardo.inventario.adicionar(bib, "core_loot_honing_relic")
    bardo.inventario.experiencia_da_reliquia = "Diplomata"
    assert bardo.ficha().experiencias["Diplomata"] == 3


def test_item_livre(bib):
    inv = Inventario()
    mapa = inv.adicionar_livre("Mapa da Cripta", "Rabiscado a carvão", 2)
    inv.remover_livre(mapa.id)
    assert inv.livres[0].quantidade == 1
    inv.remover_livre(mapa.id)
    assert inv.livres == []
    with pytest.raises(RegraViolada, match="nome"):
        inv.adicionar_livre("  ")


# --- consumíveis ----------------------------------------------------------------------------

def test_pocao_limpa_pv_com_o_dado_rolado(bardo, bib):
    bardo.sessao.marcar_pv(4)
    bardo.inventario.adicionar(bib, "core_consumable_health_potion")
    notas = bardo.usar_consumivel("core_consumable_health_potion", rolagem=2)   # 1d4+1 = 3
    assert bardo.sessao.pv_marcados == 1
    assert "Rolagem: 1d4+1 = 3." in notas and "Limpou 3 PV." in notas
    assert "core_consumable_health_potion" not in bardo.inventario.itens


def test_sem_rolagem_o_motor_rola(bardo, bib):
    bardo.sessao.marcar_estresse(5)
    bardo.inventario.adicionar(bib, POCAO_VIGOR)
    bardo.usar_consumivel(POCAO_VIGOR)
    assert 1 <= 5 - bardo.sessao.estresse_marcado <= 4


def test_rolagem_impossivel_nao_muda_nada(bardo, bib):
    bardo.sessao.marcar_pv(3)
    bardo.inventario.adicionar(bib, POCAO_VIDA)
    with pytest.raises(RegraViolada, match="impossível"):
        bardo.usar_consumivel(POCAO_VIDA, rolagem=5)
    assert (bardo.sessao.pv_marcados, bardo.inventario.itens[POCAO_VIDA]) == (3, 1)


def test_musgo_doce_pede_escolha(bardo, bib):
    bardo.sessao.marcar_estresse(3)
    bardo.inventario.adicionar(bib, "core_consumable_sweet_moss")
    with pytest.raises(RegraViolada, match="escolha"):
        bardo.usar_consumivel("core_consumable_sweet_moss", rolagem=2)
    bardo.usar_consumivel("core_consumable_sweet_moss", rolagem=2, escolha="PF")
    assert bardo.sessao.estresse_marcado == 1


def test_po_do_estalo_custa_pf(bardo, bib):
    bardo.sessao.marcar_pv(2)
    bardo.inventario.adicionar(bib, "core_consumable_snap_powder", 2)
    bardo.usar_consumivel("core_consumable_snap_powder")
    assert (bardo.sessao.pv_marcados, bardo.sessao.estresse_marcado) == (1, 1)
    bardo.sessao.marcar_estresse(bardo.sessao.estresse_livre)
    with pytest.raises(RegraViolada, match="Fadiga insuficiente"):
        bardo.usar_consumivel("core_consumable_snap_powder")


def test_ceia_de_xuria_e_consumivel_so_de_texto(bardo, bib):
    bardo.sessao.marcar_pv(3)
    bardo.sessao.marcar_estresse(2)
    bardo.sessao.esperanca = 0
    bardo.inventario.adicionar(bib, "core_consumable_feast_of_xuria")
    bardo.usar_consumivel("core_consumable_feast_of_xuria", rolagem=3)
    assert (bardo.sessao.pv_marcados, bardo.sessao.estresse_marcado, bardo.sessao.esperanca) == (0, 0, 3)
    bardo.inventario.adicionar(bib, "core_consumable_acidpaste")
    assert bardo.usar_consumivel("core_consumable_acidpaste") == ["Usou Acidpaste."]   # só texto
    assert "core_consumable_acidpaste" not in bardo.inventario.itens


def test_usar_o_que_nao_tem(bardo):
    with pytest.raises(RegraViolada, match="não tem"):
        bardo.usar_consumivel(POCAO_VIDA)
    with pytest.raises(RegraViolada, match="não é um consumível"):
        bardo.usar_consumivel("core_loot_manacles")


# --- armas de inventário ---------------------------------------------------------------------

def test_no_maximo_duas_armas_guardadas(bib):
    inv = Inventario()
    inv.guardar_arma(bib, "core_weapon_rapier")
    inv.guardar_arma(bib, "core_weapon_dagger")
    with pytest.raises(RegraViolada, match="Só cabem 2"):
        inv.guardar_arma(bib, "core_weapon_broadsword")


def test_trocar_arma_na_calma_e_em_perigo(guerreiro, bib):
    guerreiro.equipar(principal="core_weapon_broadsword")
    guerreiro.inventario.guardar_arma(bib, "core_weapon_longsword")   # duas mãos
    with pytest.raises(RegraViolada, match="mesma empunhadura"):
        guerreiro.trocar_arma(0, em_perigo=False)   # espada larga (uma mão) x espada longa (duas)
    guerreiro.inventario.armas = ["core_weapon_mace"]   # uma mão
    guerreiro.trocar_arma(0, em_perigo=False)
    assert guerreiro.equipamento.principal == "core_weapon_mace"
    assert guerreiro.inventario.armas == ["core_weapon_broadsword"]
    assert guerreiro.sessao.estresse_marcado == 0
    guerreiro.trocar_arma(0, em_perigo=True)
    assert guerreiro.equipamento.principal == "core_weapon_broadsword"
    assert guerreiro.sessao.estresse_marcado == 1


def test_trocar_arma_com_mao_vazia_so_equipa(guerreiro, bib):
    guerreiro.inventario.guardar_arma(bib, "core_weapon_round_shield")   # secundária
    guerreiro.trocar_arma(0, em_perigo=False)
    assert guerreiro.equipamento.secundaria == "core_weapon_round_shield"
    assert guerreiro.inventario.armas == []


# --- criação ---------------------------------------------------------------------------------

def test_itens_iniciais_na_criacao(bib, criacao_bardo):
    criacao = dataclasses.replace(criacao_bardo, pocao_inicial=POCAO_VIGOR, item_de_classe="core_class_bard_item_2")
    inv = Personagem(bib, criacao).inventario
    assert inv.ouro == 1
    assert inv.itens == {"core_item_torch": 1, "core_item_rope": 1, "core_item_basic_supplies": 1,
                         POCAO_VIGOR: 1, "core_class_bard_item_2": 1}


def test_item_inicial_de_outra_classe(bib, criacao_bardo):
    criacao = dataclasses.replace(criacao_bardo, pocao_inicial=POCAO_VIDA, item_de_classe="core_class_wizard_item_1")
    with pytest.raises(RegraViolada, match="itens da classe"):
        Personagem(bib, criacao)
    with pytest.raises(RegraViolada, match="Poção"):
        Personagem(bib, dataclasses.replace(criacao_bardo, pocao_inicial="core_consumable_stardrop",
                                            item_de_classe="core_class_bard_item_1"))


def test_inventario_vai_no_estado_e_na_copia(bardo, bib):
    bardo.inventario.ganhar_ouro(12)
    bardo.inventario.adicionar(bib, POCAO_VIDA, 2)
    bardo.inventario.adicionar_livre("Mapa")
    estado = bardo.estado()
    outro = Personagem(bib, bardo.criacao)
    outro.restaurar_estado(estado)
    assert outro.inventario == bardo.inventario
    assert bardo.copia().inventario == bardo.inventario


# --- loja ------------------------------------------------------------------------------------

def test_vender_cobra_entrega_e_baixa_estoque(bardo, bib):
    bardo.inventario.ganhar_ouro(10)
    pocao = ItemDaLoja(TipoNaLoja.ITEM, preco=3, ref=POCAO_VIDA, estoque=2)
    vender(bardo, pocao, 2)
    assert (bardo.inventario.ouro, bardo.inventario.itens[POCAO_VIDA], pocao.estoque) == (4, 2, 0)
    with pytest.raises(RegraViolada, match="estoque"):
        vender(bardo, pocao)


def test_venda_recusada_nao_cobra(bardo, bib):
    bardo.inventario.ganhar_ouro(2)
    with pytest.raises(RegraViolada, match="Ouro insuficiente"):
        vender(bardo, ItemDaLoja(TipoNaLoja.ITEM, preco=3, ref=POCAO_VIDA))
    bardo.inventario.adicionar(bib, POCAO_VIDA, 5)
    with pytest.raises(RegraViolada, match="No máximo 5"):
        vender(bardo, ItemDaLoja(TipoNaLoja.ITEM, preco=1, ref=POCAO_VIDA))
    # o motor recusa no meio; quem chama (a API) não salva este personagem


def test_vender_arma_armadura_e_item_livre(guerreiro, bib):
    guerreiro.inventario.ganhar_ouro(50)
    vender(guerreiro, ItemDaLoja(TipoNaLoja.ARMA, preco=5, ref="core_weapon_longsword"))
    assert guerreiro.inventario.armas == ["core_weapon_longsword"]
    guerreiro.sessao.armadura_marcada = 0
    vender(guerreiro, ItemDaLoja(TipoNaLoja.ARMADURA, preco=10, ref="core_armor_chainmail_armor"))
    assert guerreiro.equipamento.armadura == "core_armor_chainmail_armor"
    vender(guerreiro, ItemDaLoja(TipoNaLoja.LIVRE, preco=0, nome="Mapa da Cripta"))
    assert guerreiro.inventario.livres[0].nome == "Mapa da Cripta"
    assert guerreiro.inventario.ouro == 35


def test_validar_loja(bib):
    validar(bib, [ItemDaLoja(TipoNaLoja.ITEM, preco=1, ref=POCAO_VIDA)])
    with pytest.raises(RegraViolada, match="desconhecido"):
        validar(bib, [ItemDaLoja(TipoNaLoja.ARMA, preco=1, ref="core_weapon_nao_existe")])
    with pytest.raises(RegraViolada, match="nome"):
        validar(bib, [ItemDaLoja(TipoNaLoja.LIVRE, preco=1)])


def test_restaurar_nao_mexe_no_estado_salvo(bib):
    """O estado vem do JSON do banco: se o inventário mexesse nele por baixo, o
    banco acharia que nada mudou e não gravaria."""
    salvo = {"ouro": 1, "itens": {POCAO_VIDA: 1}, "livres": [], "armas": []}
    inv = Inventario.de_estado(salvo)
    inv.adicionar(bib, POCAO_VIDA)
    assert salvo["itens"] == {POCAO_VIDA: 1}


# --- regra opcional das moedas ----------------------------------------------------------------

def test_dez_moedas_viram_um_punhado():
    inv = Inventario()
    inv.ganhar_ouro(0, 7)
    inv.ganhar_ouro(0, 5)
    assert (inv.ouro, inv.moedas) == (1, 2)


def test_gastar_moedas_troca_um_punhado():
    inv = Inventario(ouro=2)
    inv.gastar_ouro(0, 3)
    assert (inv.ouro, inv.moedas) == (1, 7)
    with pytest.raises(RegraViolada, match="faltam 1 punhado, 3 moedas"):
        inv.gastar_ouro(3)


def test_moedas_so_com_a_regra_ligada(bardo):
    from motor.inventario import exigir_moedas
    with pytest.raises(RegraViolada, match="moedas"):
        exigir_moedas(bardo.usa_moedas, 3)
    bardo.inventario.usar_moedas = True          # sem mesa: vale a escolha do personagem
    exigir_moedas(bardo.usa_moedas, 3)
    bardo.moedas_da_mesa = False                 # na mesa: vale a da mesa
    assert not bardo.usa_moedas


def test_loja_cobra_em_moedas(bardo, bib):
    bardo.moedas_da_mesa = True
    bardo.inventario.ganhar_ouro(1)
    vender(bardo, ItemDaLoja(TipoNaLoja.LIVRE, preco=0, moedas=4, nome="Pão"), 2)
    assert (bardo.inventario.ouro, bardo.inventario.moedas) == (0, 2)
    bardo.moedas_da_mesa = False
    with pytest.raises(RegraViolada, match="moedas"):
        vender(bardo, ItemDaLoja(TipoNaLoja.LIVRE, preco=0, moedas=1, nome="Pão"))
