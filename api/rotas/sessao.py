"""Estado de sessão: dano, PV, Estresse, Esperança, armadura, descansos e
companheiro. Toda ação devolve a ficha atualizada."""

from collections.abc import Callable

from fastapi import APIRouter, Depends

from pydantic import BaseModel, Field

from motor import ImpactoDaCicatriz, MovimentoDeMorte, Personagem, ResultadoMorte, Sessao

from ..autenticacao import Acesso, acesso
from ..esquemas import (CondicaoEntrada, Conforto, Dano, DanoCompanheiro, DanoSaida, Descanso, DescansoSaida,
                        Estresse, FichaSaida, GastarEsperanca, Quantidade, RegrasDaMesa,
                        ficha_saida)
from .personagens import executar

rotas = APIRouter(prefix="/personagens/{personagem_id}/sessao", tags=["Sessão"])


def na_sessao(a: Acesso, personagem_id: str, acao: Callable[[Sessao], object]):
    """Executa uma ação da sessão e devolve a ficha atualizada."""
    def com_ficha(p: Personagem):
        acao(p.sessao)
        return p.ficha()
    return ficha_saida(executar(a, personagem_id, com_ficha))


@rotas.post("/dano", response_model=DanoSaida)
def receber_dano(personagem_id: str, pedido: Dano, a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        return p.sessao.receber_dano(**pedido.model_dump()), p.ficha()
    resultado, ficha = executar(a, personagem_id, acao)
    return DanoSaida(resultado=resultado, ficha=ficha_saida(ficha))


@rotas.post("/pv/marcar", response_model=FichaSaida)
def marcar_pv(personagem_id: str, pedido: Quantidade, a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id, lambda s: s.marcar_pv(pedido.quantidade))


@rotas.post("/pv/limpar", response_model=FichaSaida)
def limpar_pv(personagem_id: str, pedido: Quantidade, a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id, lambda s: s.limpar_pv(pedido.quantidade))


@rotas.post("/estresse/marcar", response_model=FichaSaida)
def marcar_estresse(personagem_id: str, pedido: Estresse,
                    a: Acesso = Depends(acesso)):
    """`como`: "imposto" (sem espaço vira PV) ou "custo" (exige espaço livre)."""
    def acao(s: Sessao):
        if pedido.como == "custo":
            s.pagar_estresse(pedido.quantidade)
        else:
            s.marcar_estresse(pedido.quantidade)
    return na_sessao(a, personagem_id, acao)


@rotas.post("/estresse/limpar", response_model=FichaSaida)
def limpar_estresse(personagem_id: str, pedido: Quantidade,
                    a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id, lambda s: s.limpar_estresse(pedido.quantidade))


@rotas.post("/esperanca/ganhar", response_model=FichaSaida)
def ganhar_esperanca(personagem_id: str, pedido: Quantidade,
                     a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id, lambda s: s.ganhar_esperanca(pedido.quantidade))


@rotas.post("/esperanca/gastar", response_model=FichaSaida)
def gastar_esperanca(personagem_id: str, pedido: GastarEsperanca,
                     a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id,
                     lambda s: s.gastar_esperanca(pedido.quantidade, pedido.com_armadura))


@rotas.post("/armadura/marcar", response_model=FichaSaida)
def marcar_armadura(personagem_id: str, pedido: Quantidade,
                    a: Acesso = Depends(acesso)):
    """Para características ativadas na mesa (Shifting, Timeslowing, Deflecting)."""
    return na_sessao(a, personagem_id, lambda s: s.marcar_armadura(pedido.quantidade))


@rotas.post("/descanso", response_model=DescansoSaida)
def descansar(personagem_id: str, pedido: Descanso, a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        if pedido.tipo == "curto":
            resultados = p.sessao.descanso_curto(pedido.movimentos, pedido.rolagens,
                                                 pedido.movimento_longo)
        else:
            resultados = p.sessao.descanso_longo(pedido.movimentos)
        return resultados, p.ficha()
    resultados, ficha = executar(a, personagem_id, acao)
    return DescansoSaida(resultados=resultados, ficha=ficha_saida(ficha))


class MovimentoDeMorteEntrada(BaseModel):
    movimento: MovimentoDeMorte
    rolagem_esperanca: int | None = Field(None, ge=1, le=12)   # d12 da mesa; sem ele, o app rola
    rolagem_medo: int | None = Field(None, ge=1, le=12)
    pv: int | None = Field(None, ge=0, description="Arriscar Tudo: quanto do Dado de Esperança vai para PV")


class MorteSaida(BaseModel):
    resultado: ResultadoMorte
    ficha: FichaSaida


class CicatrizEntrada(BaseModel):
    impacto: ImpactoDaCicatriz
    descricao: str = Field("", max_length=500)


@rotas.post("/morte", response_model=MorteSaida)
def movimento_de_morte(personagem_id: str, pedido: MovimentoDeMorteEntrada, a: Acesso = Depends(acesso)):
    """Marcou o último PV: o jogador escolhe Sacrifício Glorioso, Evitar a Morte ou Arriscar Tudo."""
    def acao(p: Personagem):
        return p.sessao.movimento_de_morte(**pedido.model_dump()), p.ficha()
    resultado, ficha = executar(a, personagem_id, acao)
    return MorteSaida(resultado=resultado, ficha=ficha_saida(ficha))


@rotas.put("/cicatrizes/{indice}", response_model=FichaSaida)
def definir_cicatriz(personagem_id: str, indice: int, pedido: CicatrizEntrada, a: Acesso = Depends(acesso)):
    """O impacto narrativo da cicatriz (física, memória dolorosa, medo paralisante ou outro)."""
    return na_sessao(a, personagem_id, lambda s: s.definir_cicatriz(indice, pedido.impacto, pedido.descricao))


@rotas.post("/companheiro/dano", response_model=FichaSaida)
def dano_no_companheiro(personagem_id: str, pedido: DanoCompanheiro,
                        a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id,
                     lambda s: s.companheiro_recebe_dano(pedido.usar_armadura))


@rotas.post("/companheiro/conforto", response_model=FichaSaida)
def conforto(personagem_id: str, pedido: Conforto, a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id,
                     lambda s: s.conforto_do_companheiro(pedido.ganhar_esperanca))


@rotas.put("/regras", response_model=FichaSaida)
def regras_da_mesa(personagem_id: str, pedido: RegrasDaMesa,
                   a: Acesso = Depends(acesso)):
    """Regras opcionais. Hoje por personagem; depois virão da mesa."""
    return na_sessao(a, personagem_id, lambda s: setattr(s, "dano_massivo", pedido.dano_massivo))


@rotas.post("/condicoes", response_model=FichaSaida)
def aplicar_condicao(personagem_id: str, pedido: CondicaoEntrada, a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id, lambda s: s.aplicar_condicao(pedido.condicao))


@rotas.delete("/condicoes/{condicao}", response_model=FichaSaida)
def remover_condicao(personagem_id: str, condicao: str, a: Acesso = Depends(acesso)):
    return na_sessao(a, personagem_id, lambda s: s.remover_condicao(condicao))
