"""Construtor de personagem: criação, level up, equipamento, cartas, ficha
e linha do tempo."""

from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from motor import CartaDeDominio, Criacao, Personagem, SubidaDeNivel

from .. import repositorio
from ..db import sessao_do_banco
from ..esquemas import (EquipamentoEntrada, FichaSaida, OpcoesDeCarta, PersonagemCriado,
                        PersonagemResumo, RecuperarCarta, ficha_saida)

rotas = APIRouter(prefix="/personagens", tags=["Personagens"])
T = TypeVar("T")


def executar(banco: Session, personagem_id: str, acao: Callable[[Personagem], T]) -> T:
    """Carrega, executa a ação do motor e salva. Se o motor recusar
    (RegraViolada), nada é salvo: a exceção sobe antes do salvar()."""
    personagem = repositorio.carregar(banco, personagem_id)
    resultado = acao(personagem)
    repositorio.salvar(banco, personagem_id, personagem)
    return resultado


@rotas.post("", status_code=201, response_model=PersonagemCriado)
def criar(criacao: Criacao, banco: Session = Depends(sessao_do_banco)):
    personagem_id, personagem = repositorio.criar(banco, criacao)
    return PersonagemCriado(id=personagem_id, ficha=ficha_saida(personagem.ficha()))


@rotas.get("", response_model=list[PersonagemResumo])
def listar(banco: Session = Depends(sessao_do_banco)):
    # resumo direto do banco, sem refazer cada personagem
    return [PersonagemResumo(id=p.id, nome=p.nome, nivel=1 + len(p.subidas),
                             classe=p.criacao["classe"]) for p in repositorio.listar(banco)]


@rotas.get("/{personagem_id}", response_model=FichaSaida)
def ficha(personagem_id: str, ate_nivel: int | None = None,
          banco: Session = Depends(sessao_do_banco)):
    return ficha_saida(repositorio.carregar(banco, personagem_id).ficha(ate_nivel))


@rotas.delete("/{personagem_id}", status_code=204)
def apagar(personagem_id: str, banco: Session = Depends(sessao_do_banco)):
    repositorio.apagar(banco, personagem_id)
    return Response(status_code=204)


@rotas.get("/{personagem_id}/linha-do-tempo")
def linha_do_tempo(personagem_id: str, banco: Session = Depends(sessao_do_banco)) -> list[dict]:
    return repositorio.carregar(banco, personagem_id).linha_do_tempo()


# --- Level up ---------------------------------------------------------------------

@rotas.get("/{personagem_id}/opcoes")
def opcoes(personagem_id: str, banco: Session = Depends(sessao_do_banco)) -> list[dict]:
    """Avanços que ainda podem ser marcados no próximo nível."""
    return repositorio.carregar(banco, personagem_id).opcoes_disponiveis()


@rotas.post("/{personagem_id}/cartas/opcoes", response_model=list[CartaDeDominio])
def opcoes_de_carta(personagem_id: str, pedido: OpcoesDeCarta,
                    banco: Session = Depends(sessao_do_banco)):
    """Cartas que podem ser escolhidas no próximo nível (POST porque leva
    os avanços já marcados no corpo)."""
    p = repositorio.carregar(banco, personagem_id)
    if pedido.para == "nivel":
        return p.cartas_para_nivel(pedido.escolhas)
    if pedido.para == "avanco":
        return p.cartas_para_avanco(pedido.tier)
    return p.cartas_para_troca(pedido.antiga, pedido.escolhas, pedido.carta_do_nivel)


@rotas.post("/{personagem_id}/niveis", response_model=FichaSaida)
def subir_de_nivel(personagem_id: str, subida: SubidaDeNivel,
                   banco: Session = Depends(sessao_do_banco)):
    return ficha_saida(executar(banco, personagem_id, lambda p: p.subir_de_nivel(subida)))


@rotas.delete("/{personagem_id}/niveis/ultimo", response_model=FichaSaida)
def desfazer_nivel(personagem_id: str, banco: Session = Depends(sessao_do_banco)):
    def acao(p: Personagem):
        p.desfazer_ultimo_nivel()
        return p.ficha()
    return ficha_saida(executar(banco, personagem_id, acao))


# --- Estado atual: equipamento e cartas ------------------------------------------------

@rotas.put("/{personagem_id}/equipamento", response_model=FichaSaida)
def equipar(personagem_id: str, equipamento: EquipamentoEntrada,
            banco: Session = Depends(sessao_do_banco)):
    return ficha_saida(executar(banco, personagem_id,
                                lambda p: p.equipar(**equipamento.model_dump())))


@rotas.post("/{personagem_id}/cartas/{carta}/guardar", response_model=FichaSaida)
def guardar_carta(personagem_id: str, carta: str, banco: Session = Depends(sessao_do_banco)):
    return ficha_saida(executar(banco, personagem_id, lambda p: p.guardar_carta(carta)))


@rotas.post("/{personagem_id}/cartas/{carta}/recuperar", response_model=FichaSaida)
def recuperar_carta(personagem_id: str, carta: str, pedido: RecuperarCarta,
                    banco: Session = Depends(sessao_do_banco)):
    def acao(p: Personagem):
        p.recuperar_carta(carta, pedido.no_lugar_de, pedido.em_descanso)
        return p.ficha()
    return ficha_saida(executar(banco, personagem_id, acao))
