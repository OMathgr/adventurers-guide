"""Encontros de uma sessão: adversários em combate e o Guia de Batalha.

Todo encontro pertence a uma sessão e segue o acesso dela (`api/sessoes.py`):
só o mestre responsável monta e conduz; mestres com quem ele compartilhou a
sessão só veem; jogador nunca vê (404). Não há ordem entre os encontros: um
pode nunca acontecer, conforme o caminho dos jogadores.
"""

import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, TypeAdapter

from motor import Adversario
from motor.encontro import Combatente, Encontro, ResultadoDanoAdversario
from motor.guia_batalha import GuiaDeBatalha, OpcoesDoGuia, calcular, validar_opcoes

from ..autenticacao import Acesso, acesso
from ..repositorio import NaoEncontrado, biblioteca
from ..sessoes import sessao_do_mestre
from ..tabelas import EncontroTabela, InimigoTabela, MesaTabela, NpcTabela

rotas = APIRouter(prefix="/mesas/{mesa_id}/sessoes/{sessao_id}", tags=["Sessões"])
_COMBATENTES = TypeAdapter(list[Combatente])
_ADVERSARIO = TypeAdapter(Adversario)
_OPCOES = TypeAdapter(OpcoesDoGuia)

class CombatenteSaida(BaseModel):
    id: str
    rotulo: str
    adversario: Adversario
    origem: str
    pv_marcados: int
    pf_marcados: int
    condicoes: list[str]
    derrotado: bool


class EncontroSaida(BaseModel):
    id: str
    nome: str
    combatentes: list[CombatenteSaida]
    guia: GuiaDeBatalha                # Pontos de Batalha: orçamento, ajustes e gastos


class EncontroResumo(BaseModel):
    id: str
    nome: str
    combatentes: int
    derrotados: int


class NomeEncontro(BaseModel):
    nome: str = Field(min_length=1, max_length=120)


class NovosCombatentes(BaseModel):
    origem: str = Field(pattern="^(inimigo|npc|srd)$", description="De onde vem a ficha")
    id: str = Field(description="Id do inimigo da mesa, do NPC ou do adversário do SRD")
    quantidade: int = 1


class DanoAdversario(BaseModel):
    dano: int
    resistente: bool = False


class DanoAdversarioSaida(BaseModel):
    resultado: ResultadoDanoAdversario
    encontro: EncontroSaida


class Marcas(BaseModel):
    pv_marcados: int
    pf_marcados: int


class CondicaoNova(BaseModel):
    condicao: str = Field(min_length=1, max_length=60)


def _linha(a: Acesso, sessao_id: str, encontro_id: str) -> EncontroTabela:
    linha = a.banco.get(EncontroTabela, encontro_id)
    if linha is None or linha.sessao_id != sessao_id:
        raise NaoEncontrado("Encontro não encontrado.")
    return linha


def _montar(linha: EncontroTabela) -> Encontro:
    return Encontro(nome=linha.nome, combatentes=_COMBATENTES.validate_python(linha.combatentes))


def _gravar(a: Acesso, linha: EncontroTabela, encontro: Encontro):
    linha.combatentes = _COMBATENTES.dump_python(encontro.combatentes, mode="json")
    a.banco.commit()


def _opcoes_do_guia(a: Acesso, linha: EncontroTabela) -> OpcoesDoGuia:
    """As escolhas salvas no encontro (ou o padrão: nº de PJs = personagens da
    mesa, 4 se não tiver nenhum). O patamar do grupo vem SEMPRE do nível da mesa:
    se o mestre subir o nível da mesa, o guia acompanha."""
    mesa = a.banco.get(MesaTabela, linha.mesa_id)
    opcoes = _OPCOES.validate_python(linha.guia) if linha.guia else OpcoesDoGuia(pjs=len(mesa.personagens) or 4)
    opcoes.patamar = biblioteca().tier_do_nivel(mesa.nivel_maximo)
    return opcoes


def _saida(a: Acesso, linha: EncontroTabela, encontro: Encontro) -> EncontroSaida:
    guia = calcular(_opcoes_do_guia(a, linha), [(c.adversario.tipo, c.adversario.patamar) for c in encontro.combatentes])
    return EncontroSaida(id=linha.id, nome=linha.nome, guia=guia, combatentes=[
        CombatenteSaida(id=c.id, rotulo=c.rotulo, adversario=c.adversario, origem=c.origem,
                        pv_marcados=c.pv_marcados, pf_marcados=c.pf_marcados,
                        condicoes=c.condicoes, derrotado=c.derrotado)
        for c in encontro.combatentes])


def _agir(a: Acesso, mesa_id: str, sessao_id: str, encontro_id: str, acao) -> EncontroSaida:
    """Só o responsável: carrega o encontro, aplica `acao(encontro)`, salva e devolve."""
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    linha = _linha(a, sessao_id, encontro_id)
    encontro = _montar(linha)
    acao(encontro)
    _gravar(a, linha, encontro)
    return _saida(a, linha, encontro)


def _ficha_de_origem(a: Acesso, mesa_id: str, pedido: NovosCombatentes) -> Adversario:
    if pedido.origem == "srd":
        adversario = biblioteca().adversarios.get(pedido.id)
    elif pedido.origem == "inimigo":
        linha = a.banco.get(InimigoTabela, pedido.id)
        adversario = _ADVERSARIO.validate_python(linha.dados) if linha and linha.mesa_id == mesa_id else None
    else:
        linha = a.banco.get(NpcTabela, pedido.id)
        if linha and linha.mesa_id == mesa_id and linha.ficha_combate is None:
            raise NaoEncontrado(f"{linha.nome} não tem ficha de combate.")
        adversario = (_ADVERSARIO.validate_python(linha.ficha_combate)
                      if linha and linha.mesa_id == mesa_id else None)
    if adversario is None:
        raise NaoEncontrado("Ficha de origem não encontrada.")
    return adversario


def resumos(a: Acesso, sessao_id: str) -> list[EncontroResumo]:
    linhas = a.banco.query(EncontroTabela).filter_by(sessao_id=sessao_id).order_by(EncontroTabela.criado_em)
    saida = []
    for linha in linhas:
        e = _montar(linha)
        saida.append(EncontroResumo(id=linha.id, nome=linha.nome, combatentes=len(e.combatentes),
                                    derrotados=sum(c.derrotado for c in e.combatentes)))
    return saida


@rotas.get("/encontros", response_model=list[EncontroResumo])
def listar_encontros(mesa_id: str, sessao_id: str, a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id)
    return resumos(a, sessao_id)


@rotas.post("/encontros", status_code=201, response_model=EncontroSaida)
def criar_encontro(mesa_id: str, sessao_id: str, dados: NomeEncontro, a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    linha = EncontroTabela(id=str(uuid.uuid4()), mesa_id=mesa_id, sessao_id=sessao_id,
                           nome=dados.nome.strip(), combatentes=[])
    a.banco.add(linha)
    a.banco.commit()
    return _saida(a, linha, _montar(linha))


@rotas.get("/encontros/{encontro_id}", response_model=EncontroSaida)
def ver_encontro(mesa_id: str, sessao_id: str, encontro_id: str, a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id)
    linha = _linha(a, sessao_id, encontro_id)
    return _saida(a, linha, _montar(linha))


@rotas.put("/encontros/{encontro_id}", response_model=EncontroSaida)
def renomear_encontro(mesa_id: str, sessao_id: str, encontro_id: str, dados: NomeEncontro,
                      a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    linha = _linha(a, sessao_id, encontro_id)
    linha.nome = dados.nome.strip()
    a.banco.commit()
    return _saida(a, linha, _montar(linha))


@rotas.put("/encontros/{encontro_id}/guia", response_model=EncontroSaida)
def guia_de_batalha(mesa_id: str, sessao_id: str, encontro_id: str, opcoes: OpcoesDoGuia,
                    a: Acesso = Depends(acesso)):
    """Escolhas do Guia de Batalha (nº de PJs, luta mais fácil ou difícil, dano
    extra). O patamar do grupo vem do nível da mesa (o enviado é ignorado) e os
    ajustes de composição são calculados sozinhos."""
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    validar_opcoes(opcoes)
    linha = _linha(a, sessao_id, encontro_id)
    linha.guia = _OPCOES.dump_python(opcoes, mode="json")
    a.banco.commit()
    return _saida(a, linha, _montar(linha))


@rotas.post("/encontros/{encontro_id}/guia/simular", response_model=GuiaDeBatalha)
def simular_guia(mesa_id: str, sessao_id: str, encontro_id: str, pedido: NovosCombatentes,
                 a: Acesso = Depends(acesso)):
    """Como ficaria o Guia de Batalha se estes inimigos entrassem (nada é salvo):
    a tela mostra quanto a escolha custa antes de adicionar."""
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    ficha = _ficha_de_origem(a, mesa_id, pedido)
    linha = _linha(a, sessao_id, encontro_id)
    encontro = _montar(linha)
    encontro.adicionar(ficha, pedido.quantidade)   # só em memória: valida a quantidade
    return calcular(_opcoes_do_guia(a, linha),
                    [(c.adversario.tipo, c.adversario.patamar) for c in encontro.combatentes])


@rotas.delete("/encontros/{encontro_id}", status_code=204)
def apagar_encontro(mesa_id: str, sessao_id: str, encontro_id: str, a: Acesso = Depends(acesso)):
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    a.banco.delete(_linha(a, sessao_id, encontro_id))
    a.banco.commit()
    return Response(status_code=204)


@rotas.post("/encontros/{encontro_id}/combatentes", response_model=EncontroSaida)
def adicionar_combatentes(mesa_id: str, sessao_id: str, encontro_id: str, pedido: NovosCombatentes,
                          a: Acesso = Depends(acesso)):
    """Põe cópias de um inimigo da mesa, da ficha de combate de um NPC ou de um adversário do SRD."""
    sessao_do_mestre(a, mesa_id, sessao_id, editar=True)
    ficha = _ficha_de_origem(a, mesa_id, pedido)
    return _agir(a, mesa_id, sessao_id, encontro_id,
                 acao=lambda e: e.adicionar(ficha, pedido.quantidade, f"{pedido.origem}:{pedido.id}"))


@rotas.delete("/encontros/{encontro_id}/combatentes/{combatente_id}", response_model=EncontroSaida)
def remover_combatente(mesa_id: str, sessao_id: str, encontro_id: str, combatente_id: str,
                       a: Acesso = Depends(acesso)):
    return _agir(a, mesa_id, sessao_id, encontro_id, acao=lambda e: e.remover(combatente_id))


@rotas.post("/encontros/{encontro_id}/combatentes/{combatente_id}/dano", response_model=DanoAdversarioSaida)
def dano_em_combatente(mesa_id: str, sessao_id: str, encontro_id: str, combatente_id: str,
                       pedido: DanoAdversario, a: Acesso = Depends(acesso)):
    resultado = []
    saida = _agir(a, mesa_id, sessao_id, encontro_id, acao=lambda e: resultado.append(
        e.combatente(combatente_id).receber_dano(pedido.dano, pedido.resistente)))
    return DanoAdversarioSaida(resultado=resultado[0], encontro=saida)


@rotas.put("/encontros/{encontro_id}/combatentes/{combatente_id}/marcas", response_model=EncontroSaida)
def marcar(mesa_id: str, sessao_id: str, encontro_id: str, combatente_id: str, pedido: Marcas,
           a: Acesso = Depends(acesso)):
    """PV e PF marcados (valores absolutos, como clicar nos quadradinhos)."""
    return _agir(a, mesa_id, sessao_id, encontro_id, acao=lambda e: e.combatente(combatente_id).definir_marcas(
        pedido.pv_marcados, pedido.pf_marcados))


@rotas.post("/encontros/{encontro_id}/combatentes/{combatente_id}/condicoes", response_model=EncontroSaida)
def condicao_em_combatente(mesa_id: str, sessao_id: str, encontro_id: str, combatente_id: str,
                           pedido: CondicaoNova, a: Acesso = Depends(acesso)):
    return _agir(a, mesa_id, sessao_id, encontro_id,
                 acao=lambda e: e.combatente(combatente_id).aplicar_condicao(pedido.condicao))


@rotas.delete("/encontros/{encontro_id}/combatentes/{combatente_id}/condicoes/{condicao}",
              response_model=EncontroSaida)
def tirar_condicao(mesa_id: str, sessao_id: str, encontro_id: str, combatente_id: str, condicao: str,
                   a: Acesso = Depends(acesso)):
    return _agir(a, mesa_id, sessao_id, encontro_id,
                 acao=lambda e: e.combatente(combatente_id).remover_condicao(condicao))