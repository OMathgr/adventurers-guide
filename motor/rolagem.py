"""Rolagens de dados com as regras do SRD.

- **Teste** (de atributo, de ataque, de conjuração, de reação): os Dados de
  Dualidade, dois d12 (Esperança e Medo), somados aos bônus. Esperança maior:
  "com Esperança" (+1 Esperança); Medo maior: "com Medo" (+1 Medo para o
  mestre); iguais: **crítico** (sucesso automático, +1 Esperança e limpa 1 PF).
  Vantagem soma um d6 e desvantagem subtrai um d6; uma cancela a outra. Cada
  Experiência usada custa 1 Esperança e soma o modificador dela. Teste de
  reação não gera Esperança nem Medo (e o crítico nele não dá os bônus).
- **Dano**: a expressão da arma (Proficiência × dado + modificadores, já na
  ficha) ou da carta; no crítico, soma o máximo dos dados ao rolado.
- **Livre**: qualquer expressão (ex.: 2d8+1d6+3).

Habilidades, características e cartas que mexem nas rolagens estão em
`data/efeitos_de_rolagem.json` (`EfeitoDeRolagem`): o que é automático o motor
aplica; o que é opção aparece para o jogador escolher antes de rolar (com o
custo pago na hora); reações (rerrolar, trocar os dados...) mudam uma rolagem
já feita, desfazendo e refazendo o que ela tinha aplicado (`deltas`).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field, replace
from enum import Enum

from .erros import RegraViolada

MAX_DADOS = 50          # numa expressão, somando todos os termos
FACES_VALIDAS = range(2, 101)
TIPOS_DE_TESTE = ("teste", "ataque", "conjuracao", "reacao")


class PapelDoDado(str, Enum):
    ESPERANCA = "esperanca"
    MEDO = "medo"
    VANTAGEM = "vantagem"
    DESVANTAGEM = "desvantagem"
    COMUM = "comum"         # dano, carta, livre
    EXTRA = "extra"         # dados somados por habilidades (Ataque Furtivo, Alma de Poeta...)


class Dualidade(str, Enum):
    ESPERANCA = "esperanca"
    MEDO = "medo"
    CRITICO = "critico"


@dataclass
class DadoRolado:
    faces: int
    valor: int
    papel: PapelDoDado = PapelDoDado.COMUM
    descartado: bool = False        # Poderoso/Enorme: o menor sai da soma
    original: int | None = None     # valor antes de uma troca (Perfeccionista, Serra, rerrolagem)
    fonte: str = ""                 # de onde veio o dado extra


@dataclass
class Bonus:
    fonte: str      # "Agilidade", "Experiência: Acrobata", "Crítico"...
    valor: int


@dataclass
class ResultadoRolagem:
    titulo: str                         # "Teste de Agilidade", "Dano: Rapieira"...
    dados: list[DadoRolado]
    bonus: list[Bonus]
    total: int
    expressao: str = ""                 # a fórmula rolada, para o registro ("2d12+2")
    tipo: str = "livre"                 # teste, ataque, conjuracao, reacao, dano, livre
    dualidade: Dualidade | None = None  # só nos testes
    reacao: bool = False
    dificuldade: int | None = None
    sucesso: bool | None = None         # só com Dificuldade informada
    efeitos: list[str] = field(default_factory=list)   # o que foi aplicado (para mostrar)
    opcoes: list[str] = field(default_factory=list)    # nomes das opções e efeitos usados
    medo_gerado: int = 0                # o mestre ganha (a API soma no Medo da sessão)
    # o que a rolagem mudou na ficha, para uma reação desfazer: esperanca, fadiga,
    # pv, medo, "marcador:<nome>", "proxima_vantagem"
    deltas: dict[str, int] = field(default_factory=dict)
    # para refazer numa reação (rerrolar etc.)
    traco: str | None = None
    ataque: int | None = None           # índice em ficha.ataques (condições como "dano mágico")
    carta: str | None = None
    experiencias: int = 0
    vantagem: int = 0                   # +1 vantagem, -1 desvantagem, 0 nenhuma
    dado_esperanca: int = 12
    soma_no_dado: dict[str, int] = field(default_factory=dict)   # Contatos: +3 no Dado de Esperança/Medo
    limpa_fadiga_no_sucesso: bool = False
    padroes_estranhos: int | None = None
    reacao_de: str | None = None        # nome da reação que gerou esta versão
    # cartas usadas por causa desta rolagem ("carta" ou "carta:opção"): uma vez cada
    cartas_usadas: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EfeitoDeRolagem:
    """Uma entrada de data/efeitos_de_rolagem.json."""

    id: str
    fonte_tipo: str                     # habilidade, ancestralidade, comunidade, carta, arma, armadura
    fonte: str                          # nome em inglês (ou id da carta)
    momento: str                        # automatico, antes, depois
    rolagens: tuple[str, ...]
    efeitos: tuple[dict, ...]
    atributos: tuple[str, ...] = ()
    auto: str | None = None
    condicao: str = ""
    custo_esperanca: int = 0
    custo_fadiga: int = 0
    custo_por_unidade: bool = False
    limite: str | None = None           # sessao, descanso, descanso_longo
    quantidade: str | int | None = None  # máximo (ou referência: nivel, proficiencia...)
    escolha: tuple[str, ...] = ()
    alvo: str = "proprio"               # quem pode reagir: proprio, aliado, qualquer
    se: str | None = None               # reações: falhou, falhou_com_experiencia, com_medo
    substituido_por: tuple[str, ...] = ()

    @classmethod
    def de_json(cls, d: dict) -> EfeitoDeRolagem:
        custo = d.get("custo") or {}
        fonte = d["fonte"]
        return cls(id=d["id"], fonte_tipo=fonte["tipo"], fonte=fonte.get("nome") or fonte.get("id"),
                   momento=d["momento"], rolagens=tuple(d["rolagens"]), efeitos=tuple(d["efeitos"]),
                   atributos=tuple(d.get("atributos", ())), auto=d.get("auto"), condicao=d.get("condicao", ""),
                   custo_esperanca=custo.get("esperanca", 0), custo_fadiga=custo.get("fadiga", 0),
                   custo_por_unidade=d.get("custo_por_unidade", "quantidade" in d and bool(custo)),
                   limite=d.get("limite"), quantidade=(d.get("quantidade") or {}).get("max"),
                   escolha=tuple(d.get("escolha", ())), alvo=d.get("alvo", "proprio"), se=d.get("se"),
                   substituido_por=tuple(d.get("substituido_por", ())))

    def tem(self, tipo: str) -> dict | None:
        return next((e for e in self.efeitos if e["tipo"] == tipo), None)


# --- Expressões ("2d8+1d6+3") ------------------------------------------------------------

_TERMO = re.compile(r"([+-])\s*(?:(\d*)\s*d\s*(\d+)|(\d+))", re.I)


def ler_expressao(texto: str) -> tuple[list[tuple[int, int, int]], int]:
    """("2d8+1d6-1") -> ([(sinal, n, faces)...], constante). Recusa o que não for dados e números."""
    limpo = texto.strip().replace(" ", "")
    if not limpo:
        raise RegraViolada("Escreva a rolagem, por exemplo 2d8+3.")
    if limpo[0] not in "+-":
        limpo = "+" + limpo
    pos, dados, constante, total = 0, [], 0, 0
    for m in _TERMO.finditer(limpo):
        if m.start() != pos:
            break
        pos = m.end()
        sinal = 1 if m.group(1) == "+" else -1
        if m.group(3):
            n, faces = int(m.group(2) or 1), int(m.group(3))
            if n < 1 or faces not in FACES_VALIDAS:
                raise RegraViolada(f"Dado inválido: {m.group(0).lstrip('+-')}.")
            total += n
            dados.append((sinal, n, faces))
        else:
            constante += sinal * int(m.group(4))
    if pos != len(limpo):
        raise RegraViolada(f"Não entendi a rolagem \"{texto}\". Use algo como 2d8+1d6+3.")
    if total > MAX_DADOS:
        raise RegraViolada(f"No máximo {MAX_DADOS} dados por rolagem.")
    return dados, constante


def rolar_expressao(texto: str, rng: random.Random, titulo: str = "Rolagem",
                    critico: bool = False) -> ResultadoRolagem:
    """Rola a expressão. `critico` (dano): soma o máximo possível dos dados."""
    termos, constante = ler_expressao(texto)
    dados, soma = [], 0
    for sinal, n, faces in termos:
        for _ in range(n):
            valor = rng.randint(1, faces)
            dados.append(DadoRolado(faces, valor))
            soma += sinal * valor
    bonus = [Bonus("Modificador", constante)] if constante else []
    if critico:
        maximo = sum(sinal * n * faces for sinal, n, faces in termos)
        bonus.append(Bonus("Crítico (máximo dos dados)", maximo))
    return ResultadoRolagem(titulo=titulo, dados=dados, bonus=bonus, tipo="livre",
                            total=soma + sum(b.valor for b in bonus), expressao=texto.replace(" ", ""))


# --- Teste (Dados de Dualidade) -----------------------------------------------------------

def rolar_dualidade(r: ResultadoRolagem, rng: random.Random, quais: tuple[str, ...] = ("esperanca", "medo", "vantagem")):
    """(Re)rola os dados do teste em `r` e recalcula o resultado (sem efeitos na ficha)."""
    if not r.dados:
        r.dados = [DadoRolado(r.dado_esperanca, 0, PapelDoDado.ESPERANCA), DadoRolado(12, 0, PapelDoDado.MEDO)]
        if r.vantagem:
            papel = PapelDoDado.VANTAGEM if r.vantagem > 0 else PapelDoDado.DESVANTAGEM
            r.dados.append(DadoRolado(6, 0, papel))
    for d in r.dados:
        if (d.papel is PapelDoDado.ESPERANCA and "esperanca" in quais) or \
           (d.papel is PapelDoDado.MEDO and "medo" in quais) or \
           (d.papel in (PapelDoDado.VANTAGEM, PapelDoDado.DESVANTAGEM) and "vantagem" in quais):
            novo = rng.randint(1, d.faces)
            if d.valor:
                d.original = d.valor
            d.valor = novo
    recalcular_teste(r)


def dado(r: ResultadoRolagem, papel: PapelDoDado) -> DadoRolado | None:
    return next((d for d in r.dados if d.papel is papel), None)


def recalcular_teste(r: ResultadoRolagem, forcar: Dualidade | None = None):
    esp = dado(r, PapelDoDado.ESPERANCA).valor + r.soma_no_dado.get("esperanca", 0)
    med = dado(r, PapelDoDado.MEDO).valor + r.soma_no_dado.get("medo", 0)
    total = esp + med + sum(b.valor for b in r.bonus)
    for d in r.dados:
        if d.papel is PapelDoDado.VANTAGEM or d.papel is PapelDoDado.EXTRA:
            total += d.valor
        elif d.papel is PapelDoDado.DESVANTAGEM:
            total -= d.valor
    r.total = total
    if forcar is not None:
        r.dualidade = forcar
    elif dado(r, PapelDoDado.ESPERANCA).valor == dado(r, PapelDoDado.MEDO).valor:
        r.dualidade = Dualidade.CRITICO      # os dados iguais (o +3 dos Contatos não cria crítico)
    else:
        r.dualidade = Dualidade.ESPERANCA if esp > med else Dualidade.MEDO
    r.sucesso = None
    if r.dificuldade is not None:
        r.sucesso = r.dualidade is Dualidade.CRITICO or r.total >= r.dificuldade
    extras = "".join(f"{b.valor:+d}" for b in r.bonus if b.valor)
    r.expressao = f"d{r.dado_esperanca}+d12" + ("+d6" if r.vantagem > 0 else "-d6" if r.vantagem < 0 else "") + extras


def rolar_teste(titulo: str, bonus: list[Bonus], rng: random.Random, vantagem: bool = False,
                desvantagem: bool = False, dificuldade: int | None = None, reacao: bool = False,
                dado_esperanca: int = 12) -> ResultadoRolagem:
    """Só os dados e o total; os efeitos na ficha são de `aplicar_teste`."""
    r = ResultadoRolagem(titulo=titulo, dados=[], bonus=list(bonus), total=0, tipo="reacao" if reacao else "teste",
                         reacao=reacao, dificuldade=dificuldade, dado_esperanca=dado_esperanca,
                         vantagem=(1 if vantagem else 0) - (1 if desvantagem else 0))
    rolar_dualidade(r, rng)
    return r


def aplicar_teste(r: ResultadoRolagem, sessao, padroes_estranhos: int | None = None) -> ResultadoRolagem:
    """Aplica na sessão do personagem o que o teste dá (e anota em `efeitos` e `deltas`)."""
    r.padroes_estranhos = padroes_estranhos
    if not r.reacao:
        if r.dualidade is Dualidade.ESPERANCA:
            _ganhar_esperanca(r, sessao, "Com Esperança")
        elif r.dualidade is Dualidade.MEDO:
            r.medo_gerado = 1
            _delta(r, "medo", 1)
            r.efeitos.append("Com Medo: o mestre ganha 1 de Medo.")
        else:
            _ganhar_esperanca(r, sessao, "Crítico")
            _limpar_fadiga(r, sessao, "Crítico")
    if padroes_estranhos is not None:
        sorteados = [d.valor for d in r.dados if d.papel in (PapelDoDado.ESPERANCA, PapelDoDado.MEDO)]
        if padroes_estranhos in sorteados:
            motivo = f"Padrões Estranhos ({padroes_estranhos})"
            if sessao.esperanca < sessao._limite_esperanca:
                _ganhar_esperanca(r, sessao, motivo)
            else:
                _limpar_fadiga(r, sessao, motivo)
    if r.limpa_fadiga_no_sucesso and r.sucesso:
        _limpar_fadiga(r, sessao, "Golpe Característico")
    return r


def desfazer(r: ResultadoRolagem, sessao):
    """Volta o que a rolagem tinha aplicado na ficha (antes de uma reação refazê-la).
    O Medo do mestre é a API que devolve (`medo_gerado`)."""
    d = r.deltas
    if d.get("esperanca"):
        sessao.esperanca = max(sessao.esperanca - d["esperanca"], 0)
    if d.get("fadiga"):
        sessao.estresse_marcado = min(sessao.estresse_marcado + d["fadiga"], sessao._ficha().estresse_max)
    if d.get("pv"):
        sessao.pv_marcados = min(sessao.pv_marcados + d["pv"], sessao._ficha().pv_max)
    for chave, valor in d.items():
        if chave.startswith("marcador:"):
            nome = chave.split(":", 1)[1]
            sessao.marcadores_rolagem[nome] = max(sessao.marcadores_rolagem.get(nome, 0) - valor, 0)
    if d.get("proxima_vantagem"):
        sessao.proxima_vantagem = False
    r.deltas, r.medo_gerado, r.efeitos = {}, 0, []


def _delta(r: ResultadoRolagem, chave: str, valor: int):
    r.deltas[chave] = r.deltas.get(chave, 0) + valor


def _ganhar_esperanca(r: ResultadoRolagem, sessao, motivo: str):
    if sessao.esperanca < sessao._limite_esperanca:
        sessao.ganhar_esperanca(1)
        _delta(r, "esperanca", 1)
        r.efeitos.append(f"{motivo}: +1 de Esperança.")
    else:
        r.efeitos.append(f"{motivo}: a Esperança já está cheia.")


def _limpar_fadiga(r: ResultadoRolagem, sessao, motivo: str):
    if sessao.estresse_marcado:
        sessao.limpar_estresse(1)
        _delta(r, "fadiga", 1)
        r.efeitos.append(f"{motivo}: limpou 1 PF.")


# --- Dano --------------------------------------------------------------------------------

@dataclass
class PlanoDeDano:
    """O que a rolagem de dano faz, montado pelo personagem com os efeitos ativos."""

    titulo: str
    expressao: str                      # base: "2d8+3" (arma) ou "1d8+2" (carta)
    principal: bool = True              # o 1º termo é o dado da arma/carta (Proficiência mexe nele)
    proficiencia_extra: int = 0
    faces_do_dado: int | None = None    # Devastador: d20 como dado de dano
    extras: list[tuple[str, str]] = field(default_factory=list)   # (fonte, expressão) dados a mais
    bonus: list[Bonus] = field(default_factory=list)
    critico: bool = False
    rerrola_valores: tuple[int, ...] = ()
    troca_valor: dict[int, int] = field(default_factory=dict)
    explode: bool = False
    descarta_menor: int = 0             # Poderoso/Enorme: dados a mais, descartando os menores
    dobra_iguais: bool = False
    dobra_maior: bool = False
    multiplica: int = 1
    notas_valor: list[tuple[int, str]] = field(default_factory=list)


def rolar_dano(p: PlanoDeDano, rng: random.Random) -> ResultadoRolagem:
    termos, constante = ler_expressao(p.expressao)
    if p.principal and termos:
        sinal, n, faces = termos[0]
        termos[0] = (sinal, max(n + p.proficiencia_extra, 1), p.faces_do_dado or faces)
    dados: list[DadoRolado] = []
    notas: list[str] = []
    for i, (sinal, n, faces) in enumerate(termos):
        for _ in range(n):
            dados.append(DadoRolado(faces, rng.randint(1, faces)))
    if p.rerrola_valores:
        for d in dados:
            if d.valor in p.rerrola_valores:
                d.original, d.valor = d.valor, rng.randint(1, d.faces)
    for d in dados:
        if d.valor in p.troca_valor:
            d.original, d.valor = d.valor, p.troca_valor[d.valor]
    if p.explode:   # Brutal: cada máximo rola mais um dado (que também pode explodir)
        fila = [d for d in dados]
        while fila and len(dados) < MAX_DADOS:
            d = fila.pop(0)
            if d.valor == d.faces and (d.original is None or d.original == d.faces):
                novo = DadoRolado(d.faces, rng.randint(1, d.faces), fonte="Brutal")
                dados.append(novo)
                fila.append(novo)
    if p.descarta_menor and dados:
        faces = dados[0].faces
        for _ in range(p.descarta_menor):
            dados.append(DadoRolado(faces, rng.randint(1, faces), fonte="dado a mais"))
        validos = sorted((d for d in dados if d.faces == faces), key=lambda d: d.valor)
        for d in validos[:p.descarta_menor]:
            d.descartado = True
    for fonte, expressao in p.extras:
        for sinal, n, faces in ler_expressao(expressao)[0]:
            for _ in range(n):
                dados.append(DadoRolado(faces, rng.randint(1, faces), PapelDoDado.EXTRA, fonte=fonte))
    if p.dobra_iguais:   # Ressonância Sagrada: valores repetidos valem o dobro
        valores = [d.valor for d in dados if not d.descartado]
        for d in dados:
            if not d.descartado and valores.count(d.valor) > 1:
                d.original, d.valor = d.valor, d.valor * 2
    if p.dobra_maior:
        maior = max((d for d in dados if not d.descartado), key=lambda d: d.valor, default=None)
        if maior:
            maior.original, maior.valor = maior.valor, maior.valor * 2
    for valor, nota in p.notas_valor:
        if any(d.valor == valor or d.original == valor for d in dados):
            notas.append(nota)
    bonus = ([Bonus("Modificador", constante)] if constante else []) + list(p.bonus)
    if p.critico:
        maximo = sum(n * f for s, n, f in termos if s > 0)
        bonus.append(Bonus("Crítico (máximo dos dados)", maximo))
    soma = sum(d.valor for d in dados if not d.descartado) + sum(b.valor for b in bonus)
    total = soma * p.multiplica
    expressao = "+".join(f"{n}d{f}" for s, n, f in termos) + (f"{constante:+d}" if constante else "")
    expressao += "".join(f"+{e}" for _, e in p.extras)
    r = ResultadoRolagem(titulo=p.titulo, dados=dados, bonus=bonus, total=total, expressao=expressao, tipo="dano")
    if p.multiplica != 1:
        notas.append(f"Dano multiplicado por {p.multiplica}.")
    r.efeitos.extend(notas)
    return r


# --- Referências usadas pelos efeitos ("nivel", "max:FINESSE,AGILITY", "2xSTRENGTHxn") ---

def resolver(ref: str | int, valores: dict[str, int]) -> int:
    """Valor de uma referência do catálogo. `valores` traz nivel, patamar,
    proficiencia, conjuracao, n (quantidade escolhida), marcadores e os atributos."""
    if isinstance(ref, int):
        return ref
    if ref.startswith("max:"):
        return max(valores[x] for x in ref[4:].split(","))
    total = 1
    for parte in ref.split("x"):
        total *= int(parte) if parte.isdigit() else valores[parte]
    return total


def expandir(expr: str, valores: dict[str, int]) -> str:
    """"{patamar}d6" -> "2d6"."""
    return re.sub(r"\{(\w+)\}", lambda m: str(valores[m.group(1)]), expr)


__all__ = ["Bonus", "DadoRolado", "Dualidade", "EfeitoDeRolagem", "PapelDoDado", "PlanoDeDano",
           "ResultadoRolagem", "TIPOS_DE_TESTE", "aplicar_teste", "desfazer", "expandir", "ler_expressao",
           "recalcular_teste", "replace", "resolver", "rolar_dano", "rolar_dualidade", "rolar_expressao",
           "rolar_teste"]
