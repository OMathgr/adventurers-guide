"""Cartas de domínio com efeito passivo: valem na ficha enquanto estão na mão
(Armorer, Fortified Armor, Bare Bones, Untouchable, as "-Touched"), e as que
pedem escolha ao serem pegas e vão para a reserva para sempre (Vitality,
Master of the Craft)."""

import pytest

from motor import Criacao, Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel, Traco

COURO = "core_armor_leather_armor"   # limiares 6/13, Pontuação 3
ESPADA = "core_weapon_broadsword"


def carta(nome: str) -> str:
    return f"core_domain_card_{nome}"


def criar(bib, classe, subclasse, cartas, **tracos):
    """`tracos` troca valores de lugar (a criação exige +2, +1, +1, 0, 0 e -1)."""
    base = {Traco.PRESENCA: 2, Traco.AGILIDADE: 1, Traco.CONHECIMENTO: 1,
            Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1}
    base.update({Traco[k]: v for k, v in tracos.items()})
    assert sorted(base.values()) == [-1, 0, 0, 1, 1, 2], "distribuição inválida no teste"
    return Personagem(bib, Criacao(
        nome="Teste", classe=classe, subclasse=subclasse, ancestralidade="core_ancestry_faun",
        comunidade="core_community_highborne", tracos=base, experiencias=["A", "B"], cartas=cartas))


def guardiao(bib, cartas=(carta("bare_bones"), carta("get_back_up")), **tracos):
    # Vingança: a fundamental (+1 PF) não mexe em limiares, Evasão nem Pontuação
    return criar(bib, "core_class_guardian", "core_subclass_vengeance", list(cartas), **tracos)


def escolhas_do_nivel(nivel: int) -> list[Escolha]:
    """Avanços que não mexem no que os testes medem (exceto PV/PF, conferidos à parte)."""
    if nivel in (4, 7, 10):
        return [Escolha(Opcao.EVASAO), Escolha(Opcao.EXPERIENCIAS, experiencias=("A", "B"))]
    return [Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)]


def subir_ate(p: Personagem, alvo: int, cartas: dict[int, str] = {}, beneficios: dict[int, dict] = {},
              dominio: str | None = None):
    """Sobe até `alvo`. Em cada nível pega `cartas[nivel]` ou a primeira carta sem
    passivo (do `dominio`, se dado)."""
    while (n := p.ficha().nivel + 1) <= alvo:
        if n in cartas:
            escolhida = cartas[n]
        else:
            escolhida = next(c.id for c in p.cartas_para_nivel()
                             if c.passivo is None and c.escolha is None and (dominio is None or c.dominio == dominio))
        p.subir_de_nivel(SubidaDeNivel(n, escolhas_do_nivel(n), escolhida, beneficios_de_carta=beneficios.get(n, {}),
                                       nova_experiencia=f"E{n}" if n in (2, 5, 8) else None))


# --- Bare Bones e Untouchable ------------------------------------------------------------------

def test_bare_bones_sem_armadura(bib):
    p = guardiao(bib, FORCA=2, AGILIDADE=-1, PRESENCA=1)
    f = p.ficha()
    assert (f.pontuacao_armadura, f.limiar_maior, f.limiar_grave) == (3 + 2, 9 + 1, 19 + 1)
    assert carta("bare_bones") in f.cartas_aplicadas
    f = p.equipar(armadura=COURO)   # com armadura, valem os números dela
    assert (f.pontuacao_armadura, f.limiar_maior, f.limiar_grave) == (3, 6 + 1, 13 + 1)
    assert carta("bare_bones") not in f.cartas_aplicadas


def test_bare_bones_usa_o_patamar_e_some_na_reserva(bib):
    p = guardiao(bib, FORCA=2, AGILIDADE=-1, PRESENCA=1)
    subir_ate(p, 5)   # patamar 3: 13/31 + nível
    assert (p.ficha().limiar_maior, p.ficha().limiar_grave) == (13 + 5, 31 + 5)
    p.guardar_carta(carta("bare_bones"))
    f = p.ficha()
    assert (f.pontuacao_armadura, f.limiar_maior, f.limiar_grave) == (0, 5, 10)   # regra de quem está sem armadura


def test_untouchable_metade_da_agilidade(bib):
    cartas = [carta("untouchable"), carta("get_back_up")]
    outras = [carta("get_back_up"), carta("whirlwind")]
    guerreiro = ("core_class_warrior", "core_subclass_call_of_the_brave")
    sem = criar(bib, *guerreiro, outras, AGILIDADE=1)
    com = criar(bib, *guerreiro, cartas, AGILIDADE=1)
    assert com.ficha().evasao == sem.ficha().evasao + 1   # metade de 1 arredonda para cima
    assert carta("untouchable") in com.ficha().cartas_aplicadas
    negativa = criar(bib, *guerreiro, cartas, AGILIDADE=-1, FORCA=1)
    base = criar(bib, *guerreiro, outras, AGILIDADE=-1, FORCA=1)
    assert negativa.ficha().evasao == base.ficha().evasao   # bônus: Agilidade negativa não tira


# --- com armadura ----------------------------------------------------------------------------------

def test_armorer_e_fortified_armor_so_com_armadura(bib):
    p = guardiao(bib, cartas=[carta("get_back_up"), carta("i_am_your_shield")])
    subir_ate(p, 5, cartas={4: carta("fortified_armor"), 5: carta("armorer")})
    for c in p.ficha().cartas:   # tira da reserva o que caiu nela (mão de 5)
        if c in p.cofre and c in (carta("fortified_armor"), carta("armorer")):
            p.recuperar_carta(c, no_lugar_de=next(x for x in p.ficha().cartas_ativas
                                                  if x not in (carta("fortified_armor"), carta("armorer"))),
                              em_descanso=True)
    sem = p.ficha()
    assert (sem.pontuacao_armadura, sem.limiar_maior) == (0, 5)   # sem armadura: nada
    f = p.equipar(armadura=COURO)
    assert f.pontuacao_armadura == 3 + 1
    assert (f.limiar_maior, f.limiar_grave) == (6 + 5 + 2, 13 + 5 + 2)


# --- "-Touched": 4 cartas do domínio na mão ---------------------------------------------------------

def test_blade_touched_com_quatro_cartas_de_lamina(bib):
    p = guardiao(bib, cartas=[carta("get_back_up"), carta("whirlwind")])   # duas de Lâmina
    subir_ate(p, 7, cartas={7: carta("blade_touched")}, dominio="BLADE")
    lamina = [c for c in p.ficha().cartas if bib.cartas[c].dominio == "BLADE"]
    mao = [carta("blade_touched"), *[c for c in lamina if c != carta("blade_touched")][:3]]
    for c in list(p.ficha().cartas_ativas):
        if c not in mao:
            p.guardar_carta(c)
    for c in mao:
        if c in p.cofre:
            p.recuperar_carta(c, em_descanso=True)
    sem_bonus = Personagem(bib, p.criacao)   # só para comparar a espada sem o passivo
    sem_bonus.equipar(principal=ESPADA)
    f = p.equipar(principal=ESPADA)
    assert carta("blade_touched") in f.cartas_aplicadas
    assert f.ataques[0].bonus == sem_bonus.ficha().ataques[0].bonus + 2
    grave = f.limiar_grave
    p.guardar_carta(mao[1])   # 3 de Lâmina na mão: deixa de valer
    f = p.ficha()
    assert f.limiar_grave == grave - 4 and carta("blade_touched") not in f.cartas_aplicadas
    # a rolagem usa o bônus da ficha: o efeito de rolagem antigo não soma de novo
    assert all(o.id != "blade_touched" for o in p.opcoes_de_rolagem("ataque", ataque=0))


# --- Vitality e Master of the Craft -------------------------------------------------------------------

def test_vitality_escolhe_dois_e_fica_na_reserva(bib):
    p = guardiao(bib, cartas=[carta("get_back_up"), carta("whirlwind")])
    subir_ate(p, 4)
    antes = p.ficha()
    with pytest.raises(RegraViolada, match="dois benefícios diferentes"):
        subir_ate(p, 5, cartas={5: carta("vitality")}, beneficios={5: {carta("vitality"): ["PV", "PV"]}})
    with pytest.raises(RegraViolada, match="Vitality"):
        subir_ate(p, 5, cartas={5: carta("vitality")})
    subir_ate(p, 5, cartas={5: carta("vitality")}, beneficios={5: {carta("vitality"): ["PV", "LIMIARES"]}})
    f = p.ficha()
    assert f.pv_max == antes.pv_max + 1 + 1   # +1 do avanço de PV do nível 5, +1 da carta
    assert f.estresse_max == antes.estresse_max + 1   # só o avanço
    assert (f.limiar_maior, f.limiar_grave) == (5 + 2, 10 + 2)
    assert carta("vitality") in p.cofre
    with pytest.raises(RegraViolada, match="para sempre"):
        p.recuperar_carta(carta("vitality"), em_descanso=True)
    # o bônus é permanente: refazer o personagem (carregar de novo) mantém tudo
    copia = p.copia()
    assert copia.ficha().pv_max == f.pv_max and carta("vitality") in copia.cofre


def test_beneficio_so_para_carta_pega_no_nivel(bib):
    p = guardiao(bib, cartas=[carta("get_back_up"), carta("whirlwind")])
    with pytest.raises(RegraViolada, match="Só cartas pegas neste nível"):
        subir_ate(p, 2, beneficios={2: {carta("vitality"): ["PV", "ESTRESSE"]}})


def test_master_of_the_craft(bib):
    bardo = criar(bib, "core_class_bard", "core_subclass_troubadour",
                  [carta("inspirational_words"), carta("book_of_ava")])
    subir_ate(bardo, 8)
    antes = bardo.ficha().experiencias
    mestre = carta("master_of_the_craft")
    with pytest.raises(RegraViolada, match="Master of the Craft"):
        subir_ate(bardo, 9, cartas={9: mestre}, beneficios={9: {mestre: ["Não tenho"]}})
    subir_ate(bardo, 9, cartas={9: mestre}, beneficios={9: {mestre: ["A", "E2"]}})
    f = bardo.ficha()
    assert (f.experiencias["A"], f.experiencias["E2"]) == (antes["A"] + 2, antes["E2"] + 2)
    assert mestre in bardo.cofre
    bardo.desfazer_ultimo_nivel()
    subir_ate(bardo, 9, cartas={9: mestre}, beneficios={9: {mestre: ["B"]}})
    assert bardo.ficha().experiencias["B"] == antes["B"] + 3


def test_nivel_salvo_antes_da_regra_ainda_abre(bib):
    """Vitality pega antes de existir a escolha: recarrega sem o benefício."""
    p = guardiao(bib, cartas=[carta("get_back_up"), carta("whirlwind")])
    subir_ate(p, 4)
    salvos = list(p.historico) + [SubidaDeNivel(5, escolhas_do_nivel(5), carta("vitality"), nova_experiencia="E5")]
    outro = Personagem(bib, p.criacao)
    outro.refazer_historico(salvos)
    assert outro.ficha().nivel == 5 and carta("vitality") in outro.ficha().cartas
    with pytest.raises(RegraViolada, match="Vitality"):   # uma subida nova continua exigindo
        p.subir_de_nivel(salvos[-1])


# --- Versatilidade (Versatile Fighter) ------------------------------------------------------------

class _Dados:
    """rng falso: devolve os valores na ordem."""
    def __init__(self, *valores):
        self.valores = list(valores)

    def randint(self, a, b):
        return self.valores.pop(0)


def versatil(bib):
    p = guardiao(bib, cartas=[carta("get_back_up"), carta("whirlwind")])   # Presença 2, Agilidade 1
    subir_ate(p, 3, cartas={3: carta("versatile_fighter")})
    return p


def test_versatilidade_troca_o_atributo_do_ataque(bib):
    p = versatil(bib)
    f = p.equipar(principal=ESPADA)   # Espada Larga pede Agilidade
    assert (f.ataques[0].traco, f.ataques[0].traco_da_arma) == (Traco.AGILIDADE, None)
    com_agilidade = f.ataques[0].bonus   # Agilidade + 1 (Confiável)
    f = p.equipar(principal=ESPADA, traco_principal="PRESENCE")
    assert (f.ataques[0].traco, f.ataques[0].traco_da_arma) == (Traco.PRESENCA, Traco.AGILIDADE)
    assert f.ataques[0].bonus == com_agilidade - f.tracos[Traco.AGILIDADE] + f.tracos[Traco.PRESENCA]
    # o mesmo atributo da arma não é troca; secundária vazia não guarda nada
    assert p.equipar(principal=ESPADA, traco_principal="AGILITY", traco_secundaria="PRESENCE").ataques[0].traco_da_arma is None
    assert p.equipamento.traco_secundaria is None
    # na reserva, a carta não vale (a escolha fica guardada para quando voltar)
    p.equipar(principal=ESPADA, traco_principal="PRESENCE")
    p.guardar_carta(carta("versatile_fighter"))
    assert p.ficha().ataques[0].traco is Traco.AGILIDADE and p.equipamento.traco_principal is Traco.PRESENCA
    p.recuperar_carta(carta("versatile_fighter"), no_lugar_de=p.ficha().cartas_ativas[0], em_descanso=True)
    assert p.ficha().ataques[0].traco is Traco.PRESENCA


def test_versatilidade_volta_ao_atributo_da_arma_nova_e_salva(bib, criacao_bardo):
    p = versatil(bib)
    p.equipar(principal=ESPADA, traco_principal="PRESENCE")
    estado = p.estado()
    assert estado["equipamento"]["traco_principal"] == "PRESENCE"   # JSON simples para o banco
    outro = Personagem(bib, p.criacao)
    outro.refazer_historico(p.historico)
    outro.restaurar_estado(estado)
    assert outro.ficha().ataques[0].traco is Traco.PRESENCA
    p.inventario.guardar_arma(bib, "core_weapon_mace")
    f = p.trocar_arma(0, em_perigo=False)   # Maça pede Força: a escolha não passa para ela
    assert f.ataques[0].traco is Traco.FORCA and p.equipamento.traco_principal is None


def test_versatilidade_dano_maximo_num_dado_marcando_pf(bib):
    p = versatil(bib)
    p.equipar(principal=ESPADA)
    p.sessao.rng = _Dados(3, 5)   # sem 1 e 2 (Not Good Enough rerrola esses)
    r = p.rolar_dano(ataque=0)   # 2d8 (Proficiência 2 no nível 3)
    novo = p.reagir(r, "versatile_fighter")
    assert [d.valor for d in novo.dados] == [8, 5] and novo.dados[0].original == 3   # o que mais ganha
    assert novo.total == r.total + 5 and p.sessao.estresse_marcado == 1
    novo = p.reagir(novo, "versatile_fighter")   # de novo: agora o outro
    assert [d.valor for d in novo.dados] == [8, 8]
    with pytest.raises(RegraViolada, match="no máximo"):
        p.reagir(novo, "versatile_fighter")
