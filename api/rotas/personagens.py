"""Construtor de personagem: criação, level up, equipamento, cartas, ficha
e linha do tempo."""

from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, Response

from motor import CartaDeDominio, Criacao, Personagem, RegraViolada, SubidaDeNivel

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..esquemas import (EquipamentoEntrada, EventoLinhaDoTempo, FichaSaida, OpcoesDeCarta, PersonagemCriado,
                        PersonagemResumo, ProximoNivelSaida, RecuperarCarta, VinculoMesa,
                        ficha_saida)
from ..mesas import membro

rotas = APIRouter(prefix="/personagens", tags=["Personagens"])
T = TypeVar("T")


def executar(a: Acesso, personagem_id: str, acao: Callable[[Personagem], T]) -> T:
    """Carrega, executa a ação do motor e salva. Se o motor recusar
    (RegraViolada), nada é salvo: a exceção sobe antes do salvar()."""
    personagem = repositorio.carregar(a.banco, a.usuario_id, personagem_id)
    resultado = acao(personagem)
    repositorio.salvar(a.banco, a.usuario_id, personagem_id, personagem)
    return resultado


@rotas.post("", status_code=201, response_model=PersonagemCriado)
def criar(criacao: Criacao, a: Acesso = Depends(acesso)):
    personagem_id, personagem = repositorio.criar(a.banco, a.usuario_id, criacao)
    return PersonagemCriado(id=personagem_id, ficha=ficha_saida(personagem.ficha()))


@rotas.get("", response_model=list[PersonagemResumo])
def listar(a: Acesso = Depends(acesso)):
    # resumo direto do banco, sem refazer cada personagem
    return [PersonagemResumo(id=p.id, nome=p.nome, nivel=1 + len(p.subidas),
                             classe=p.criacao["classe"], mesa_id=p.mesa_id)
            for p in repositorio.listar(a.banco, a.usuario_id)]


@rotas.get("/{personagem_id}", response_model=FichaSaida)
def ficha(personagem_id: str, ate_nivel: int | None = None,
          a: Acesso = Depends(acesso)):
    return ficha_saida(repositorio.carregar(a.banco, a.usuario_id, personagem_id).ficha(ate_nivel))


@rotas.delete("/{personagem_id}", status_code=204)
def apagar(personagem_id: str, a: Acesso = Depends(acesso)):
    repositorio.apagar(a.banco, a.usuario_id, personagem_id)
    return Response(status_code=204)


@rotas.get("/{personagem_id}/linha-do-tempo", response_model=list[EventoLinhaDoTempo])
def linha_do_tempo(personagem_id: str, a: Acesso = Depends(acesso)):
    return repositorio.carregar(a.banco, a.usuario_id, personagem_id).linha_do_tempo()


# --- Level up ---------------------------------------------------------------------

@rotas.get("/{personagem_id}/opcoes")
def opcoes(personagem_id: str, a: Acesso = Depends(acesso)) -> list[dict]:
    """Avanços que ainda podem ser marcados no próximo nível."""
    return repositorio.carregar(a.banco, a.usuario_id, personagem_id).opcoes_disponiveis()


@rotas.get("/{personagem_id}/proximo-nivel", response_model=ProximoNivelSaida | None)
def proximo_nivel(personagem_id: str, a: Acesso = Depends(acesso)):
    """O que o próximo nível pede (null no nível máximo): conquista de tier,
    avanços disponíveis, atributos marcados e treinos do companheiro."""
    proximo = repositorio.carregar(a.banco, a.usuario_id, personagem_id).proximo_nivel()
    return None if proximo is None else ProximoNivelSaida.model_validate(proximo, from_attributes=True)


@rotas.post("/{personagem_id}/cartas/opcoes", response_model=list[CartaDeDominio])
def opcoes_de_carta(personagem_id: str, pedido: OpcoesDeCarta,
                    a: Acesso = Depends(acesso)):
    """Cartas que podem ser escolhidas no próximo nível (POST porque leva
    os avanços já marcados no corpo)."""
    p = repositorio.carregar(a.banco, a.usuario_id, personagem_id)
    if pedido.para == "nivel":
        return p.cartas_para_nivel(pedido.escolhas)
    if pedido.para == "avanco":
        return p.cartas_para_avanco(pedido.tier)
    return p.cartas_para_troca(pedido.antiga, pedido.escolhas, pedido.carta_do_nivel)


@rotas.post("/{personagem_id}/niveis", response_model=FichaSaida)
def subir_de_nivel(personagem_id: str, subida: SubidaDeNivel,
                   a: Acesso = Depends(acesso)):
    return ficha_saida(executar(a, personagem_id, lambda p: p.subir_de_nivel(subida)))


@rotas.delete("/{personagem_id}/niveis/ultimo", response_model=FichaSaida)
def desfazer_nivel(personagem_id: str, a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        p.desfazer_ultimo_nivel()
        return p.ficha()
    return ficha_saida(executar(a, personagem_id, acao))


# --- Estado atual: equipamento e cartas ------------------------------------------------

@rotas.put("/{personagem_id}/equipamento", response_model=FichaSaida)
def equipar(personagem_id: str, equipamento: EquipamentoEntrada,
            a: Acesso = Depends(acesso)):
    return ficha_saida(executar(a, personagem_id,
                                lambda p: p.equipar(**equipamento.model_dump())))


@rotas.post("/{personagem_id}/cartas/{carta}/guardar", response_model=FichaSaida)
def guardar_carta(personagem_id: str, carta: str, a: Acesso = Depends(acesso)):
    return ficha_saida(executar(a, personagem_id, lambda p: p.guardar_carta(carta)))


@rotas.post("/{personagem_id}/cartas/{carta}/recuperar", response_model=FichaSaida)
def recuperar_carta(personagem_id: str, carta: str, pedido: RecuperarCarta,
                    a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        p.recuperar_carta(carta, pedido.no_lugar_de, pedido.em_descanso)
        return p.ficha()
    return ficha_saida(executar(a, personagem_id, acao))


# --- Mesa ----------------------------------------------------------------------------------

@rotas.put("/{personagem_id}/mesa", response_model=PersonagemResumo)
def vincular_mesa(personagem_id: str, pedido: VinculoMesa, a: Acesso = Depends(acesso)):
    """Leva o personagem para uma mesa da qual você participa (`mesa_id`), ou
    tira de qualquer mesa (`mesa_id: null`). Uma mesa por vez: para trocar,
    desvincule antes."""
    linha = repositorio.linha_do_dono(a.banco, a.usuario_id, personagem_id)
    if pedido.mesa_id is not None:
        membro(a.banco, pedido.mesa_id, a.usuario_id)   # precisa participar da mesa
        if linha.mesa_id not in (None, pedido.mesa_id):
            raise RegraViolada("O personagem já está em outra mesa; desvincule antes.")
    linha.mesa_id = pedido.mesa_id
    a.banco.commit()
    return PersonagemResumo(id=linha.id, nome=linha.nome, nivel=1 + len(linha.subidas),
                            classe=linha.criacao["classe"], mesa_id=linha.mesa_id)
