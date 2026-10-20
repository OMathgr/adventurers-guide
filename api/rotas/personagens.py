"""Construtor de personagem: criação, level up, equipamento, cartas, ficha
e linha do tempo."""

import dataclasses
from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import object_session

from motor import CartaDeDominio, Criacao, Personagem, RegraViolada, SubidaDeNivel

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..concorrencia import conferir, versao_de
from ..esquemas import (AvancosDoNivel, CopiaParaMesa, SessaoEmJogo, EquipamentoAtual, EquipamentoEntrada, EventoLinhaDoTempo, FichaSaida, FotoEntrada,
                        OpcoesDeCarta, PersonagemCriado, PersonagemResumo, ProximoNivelSaida, RecuperarCarta,
                        VinculoMesa, ficha_saida)
from ..mesas import membro
from .imagens import imagem_valida

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
    return [_resumo(p) for p in repositorio.listar(a.banco, a.usuario_id)]


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


@rotas.post("/{personagem_id}/cartas/extras", response_model=int)
def cartas_extras(personagem_id: str, pedido: AvancosDoNivel, a: Acesso = Depends(acesso)):
    """Quantas cartas a mais o próximo nível dá com estes avanços (habilidade
    de subclasse, ex.: Discípulo do Conhecimento). Vão em `cartas_extras`."""
    return repositorio.carregar(a.banco, a.usuario_id, personagem_id).cartas_extras(pedido.escolhas)


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

@rotas.get("/{personagem_id}/equipamento", response_model=EquipamentoAtual)
def equipamento_atual(personagem_id: str, a: Acesso = Depends(acesso)):
    """Ids do que está equipado agora (a ficha só traz os nomes)."""
    p = repositorio.carregar(a.banco, a.usuario_id, personagem_id)
    eq = p.equipamento
    return EquipamentoAtual(principal=eq.principal, secundaria=eq.secundaria, armadura=eq.armadura,
                            versao=versao_de(dataclasses.asdict(eq)),
                            armas_proprias=p.armas_proprias(), armaduras_proprias=p.armaduras_proprias())


@rotas.put("/{personagem_id}/equipamento", response_model=FichaSaida)
def equipar(personagem_id: str, equipamento: EquipamentoEntrada, versao: str | None = None,
            a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        conferir(versao, dataclasses.asdict(p.equipamento))   # só o equipamento: dano no meio não conflita
        return p.equipar(**equipamento.model_dump())
    return ficha_saida(executar(a, personagem_id, acao))


@rotas.post("/{personagem_id}/cartas/{carta}/guardar", response_model=FichaSaida)
def guardar_carta(personagem_id: str, carta: str, a: Acesso = Depends(acesso)):
    return ficha_saida(executar(a, personagem_id, lambda p: p.guardar_carta(carta)))


@rotas.post("/{personagem_id}/cartas/{carta}/recuperar", response_model=FichaSaida)
def recuperar_carta(personagem_id: str, carta: str, pedido: RecuperarCarta,
                    a: Acesso = Depends(acesso)):
    if not pedido.em_descanso:   # o custo de troca marca Fadiga: só dentro da sessão de jogo
        repositorio.exigir_em_jogo(a.banco, personagem_id, a.usuario_id)

    def acao(p: Personagem):
        p.recuperar_carta(carta, pedido.no_lugar_de, pedido.em_descanso)
        return p.ficha()
    return ficha_saida(executar(a, personagem_id, acao))


# --- Mesa ----------------------------------------------------------------------------------

def _resumo(linha) -> PersonagemResumo:
    ativa = repositorio.participacao_ativa(object_session(linha), linha.id)
    return PersonagemResumo(id=linha.id, nome=linha.nome, nivel=1 + len(linha.subidas),
                            classe=linha.criacao["classe"], mesa_id=linha.mesa_id, foto=linha.foto,
                            em_jogo=SessaoEmJogo(sessao_id=ativa.sessao_id, titulo=ativa.sessao.titulo) if ativa else None)


@rotas.put("/{personagem_id}/mesa", response_model=PersonagemResumo)
def vincular_mesa(personagem_id: str, pedido: VinculoMesa, a: Acesso = Depends(acesso)):
    """Leva um personagem SEM mesa para uma mesa da qual você participa. Dali em
    diante ele fica preso a ela: para jogar em outra, faça uma cópia
    (POST /personagens/{id}/copia). Só entra quem está no nível da mesa ou abaixo."""
    linha = repositorio.linha_do_dono(a.banco, a.usuario_id, personagem_id)
    mesa = membro(a.banco, pedido.mesa_id, a.usuario_id).mesa   # precisa participar da mesa
    if linha.mesa_id == mesa.id:
        return _resumo(linha)
    if linha.mesa_id is not None:
        raise RegraViolada("O personagem já pertence a outra mesa. Para jogar nesta, faça uma cópia dele.")
    nivel = 1 + len(linha.subidas)
    if nivel > mesa.nivel_maximo:
        raise RegraViolada(f"{linha.nome or 'O personagem'} está no nível {nivel} e a mesa no "
                           f"{mesa.nivel_maximo}. Faça uma cópia: os níveis acima viram plano.")
    linha.mesa_id = mesa.id
    a.banco.commit()
    return _resumo(linha)


@rotas.post("/{personagem_id}/copia", status_code=201, response_model=PersonagemCriado)
def copiar_para_mesa(personagem_id: str, pedido: CopiaParaMesa, a: Acesso = Depends(acesso)):
    """Cópia do personagem para outra mesa (o original fica onde está). A cópia
    respeita o nível da mesa nova: os níveis acima viram plano, aplicado quando
    o mestre liberar."""
    original = repositorio.linha_do_dono(a.banco, a.usuario_id, personagem_id)
    mesa = membro(a.banco, pedido.mesa_id, a.usuario_id).mesa
    if original.mesa_id == mesa.id:
        raise RegraViolada("O personagem já está nesta mesa.")
    novo_id, copia = repositorio.criar_copia(a.banco, original, mesa.id, mesa.nivel_maximo)
    return PersonagemCriado(id=novo_id, ficha=ficha_saida(copia.ficha()))


# --- Plano (níveis futuros) ---------------------------------------------------------------

@rotas.post("/{personagem_id}/plano/aplicar", response_model=FichaSaida)
def aplicar_plano(personagem_id: str, a: Acesso = Depends(acesso)):
    """Sobe o próximo nível com o que estava planejado (se a mesa já liberou)."""
    return ficha_saida(executar(a, personagem_id, lambda p: p.aplicar_plano()))


@rotas.delete("/{personagem_id}/plano/{nivel}", status_code=204)
def descartar_plano(personagem_id: str, nivel: int, a: Acesso = Depends(acesso)):
    executar(a, personagem_id, lambda p: p.descartar_plano(nivel))
    return Response(status_code=204)


# --- Foto ------------------------------------------------------------------------------------

@rotas.put("/{personagem_id}/foto", response_model=PersonagemResumo)
def definir_foto(personagem_id: str, pedido: FotoEntrada, a: Acesso = Depends(acesso)):
    linha = repositorio.linha_do_dono(a.banco, a.usuario_id, personagem_id)
    linha.foto = imagem_valida(a, pedido.imagem_id)
    a.banco.commit()
    return _resumo(linha)
