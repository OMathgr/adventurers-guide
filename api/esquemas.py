"""Formatos de entrada e saída da API que não são dataclasses do motor.

As entradas de criação e level up usam direto `motor.Criacao` e
`motor.SubidaDeNivel` (o FastAPI valida dataclasses). Aqui ficam a ficha de
saída e os corpos das ações de sessão.
"""

from typing import Literal, get_type_hints

from pydantic import BaseModel, Field, create_model

from motor import Escolha, Ficha, Movimento, Opcao, Traco, ResultadoDano, ResultadoMovimento, TipoDano

# Campos de controle interno do motor, que não interessam a quem usa a API
# (e um deles tem tupla como chave, o que nem cabe em JSON).
_INTERNOS = {"slots_usados", "subclasse_bloqueada_tiers", "multiclasse_bloqueada"}

FichaSaida = create_model(
    "Ficha",
    **{nome: (tipo, ...) for nome, tipo in get_type_hints(Ficha).items() if nome not in _INTERNOS},
)


def ficha_saida(ficha: Ficha) -> BaseModel:
    return FichaSaida.model_validate(ficha, from_attributes=True)


class OpcaoAvanco(BaseModel):
    tier: int
    opcao: Opcao
    restantes: int
    custo: int


class ProximoNivelSaida(BaseModel):
    """O que o próximo nível pede (motor.ProximoNivel com as opções tipadas)."""

    nivel: int
    tier: int
    nova_experiencia: bool
    limpa_marcas_tracos: bool
    experiencia_companheiro: bool
    avancos: int
    opcoes: list[OpcaoAvanco]
    tracos_marcados: list[Traco]
    treinos: int
    treinos_extra_com_subclasse: int


class PersonagemCriado(BaseModel):
    id: str
    ficha: FichaSaida


class DanoSaida(BaseModel):
    resultado: ResultadoDano
    ficha: FichaSaida


class DescansoSaida(BaseModel):
    resultados: list[ResultadoMovimento]
    ficha: FichaSaida


class PersonagemResumo(BaseModel):
    id: str
    nome: str
    nivel: int
    classe: str
    mesa_id: str | None = None


class VinculoMesa(BaseModel):
    mesa_id: str | None


class CondicaoEntrada(BaseModel):
    condicao: str = Field(min_length=1, max_length=60,
                          description="OCULTO, CONTIDO, VULNERAVEL (ou Hidden...) ou o nome "
                                      "de uma condição de característica")


# --- Corpos das ações ------------------------------------------------------------------

class EquipamentoEntrada(BaseModel):
    principal: str | None = None
    secundaria: str | None = None
    armadura: str | None = None


class OpcoesDeCarta(BaseModel):
    """Para quê é a carta: nível (passo 4), avanço CARTA_DOMINIO ou troca."""

    para: Literal["nivel", "avanco", "troca"]
    escolhas: list[Escolha] = Field(default_factory=list)   # avanços já marcados no nível
    tier: int | None = None                  # avanço
    antiga: str | None = None                # troca
    carta_do_nivel: str | None = None        # troca


class RecuperarCarta(BaseModel):
    no_lugar_de: str | None = None
    em_descanso: bool = False


class Dano(BaseModel):
    dano: int
    usar_armadura: bool = False
    tipo: TipoDano | None = None
    evitar_queda: bool = False
    rolagem_d6: int | None = None
    rolagens_vinculo: list[int] | None = None


class Quantidade(BaseModel):
    quantidade: int = Field(1, ge=0)


class Estresse(Quantidade):
    como: Literal["imposto", "custo"] = "imposto"   # imposto transborda para PV; custo exige espaço


class GastarEsperanca(Quantidade):
    com_armadura: int = Field(0, ge=0)   # Hopeful


class Descanso(BaseModel):
    tipo: Literal["curto", "longo"]
    movimentos: list[Movimento]
    rolagens: list[int | None] | None = None   # só no curto
    movimento_longo: int | None = None         # Efficient, só no curto


class DanoCompanheiro(BaseModel):
    usar_armadura: bool = False   # Armored


class Conforto(BaseModel):
    ganhar_esperanca: bool


class RegrasDaMesa(BaseModel):
    dano_massivo: bool
