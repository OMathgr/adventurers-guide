"""Repouso do grupo: o mestre abre um descanso curto ou longo, cada jogador
escolhe os movimentos do seu personagem e, no fim, tudo é aplicado de uma vez.

Aplicar no fim (e não a cada escolha) é o que permite:
- **Preparar-se em grupo**: +2 de Esperança para cada um, mas só se mais alguém
  também se preparar em grupo (sozinho, vira o Preparar-se comum, +1);
- **movimentos num aliado** (Tratar Feridas, Reparar Armadura) em quem ainda
  não escolheu;
- tudo ou nada: se uma escolha for inválida, ninguém descansa pela metade.

Descanso curto interrompido não dá nada; longo interrompido dá os benefícios do
curto, mesmo depois de três curtos seguidos (o livro diz assim).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .erros import RegraViolada
from .sessao import Movimento, ResultadoMovimento
from .srd import Efeito


class TipoDeRepouso(str, Enum):
    CURTO = "curto"
    LONGO = "longo"


@dataclass
class MovimentoEscolhido:
    movimento: Movimento
    alvo: str | None = None        # id do aliado (Tratar Feridas, Reparar Armadura); None = em si
    rolagem: int | None = None     # d4 rolado na mesa (só no curto); None = o motor rola


@dataclass
class EscolhaDeRepouso:
    movimentos: list[MovimentoEscolhido]
    movimento_longo: int | None = None   # Efficient (Clank): qual movimento do curto vale como longo


@dataclass
class ResultadoDoRepouso:
    tipo: TipoDeRepouso                                   # o que valeu (longo interrompido vale curto)
    por_personagem: dict[str, list[ResultadoMovimento]] = field(default_factory=dict)
    notas: list[str] = field(default_factory=list)


def concluir(tipo: TipoDeRepouso | str, personagens: dict, escolhas: dict[str, EscolhaDeRepouso],
             interrompido: bool = False) -> ResultadoDoRepouso:
    """Aplica o repouso. `personagens`: id -> Personagem (só quem participa);
    `escolhas`: id -> movimentos escolhidos (todo participante precisa ter os seus).
    Valida tudo antes de mexer em alguém."""
    tipo = TipoDeRepouso(tipo)
    if interrompido and tipo is TipoDeRepouso.CURTO:
        raise RegraViolada("Descanso curto interrompido não dá benefícios: cancele o repouso.")
    efetivo = TipoDeRepouso.CURTO if interrompido else tipo
    vivos = {i: p for i, p in personagens.items() if not p.sessao.morto}
    faltando = [p.criacao.nome or i for i, p in vivos.items() if i not in escolhas]
    if faltando:
        raise RegraViolada(f"Ainda falta escolher os movimentos: {', '.join(faltando)}.")

    for i, p in vivos.items():
        validar_escolha(efetivo, i, p, escolhas[i], set(vivos), interrompido)

    # Preparar-se em grupo só vale com mais alguém se preparando em grupo
    em_grupo = [i for i, e in escolhas.items() if i in vivos
                and any(m.movimento is Movimento.PREPARAR_EM_GRUPO for m in e.movimentos)]
    resultado = ResultadoDoRepouso(efetivo)
    if len(em_grupo) == 1:
        sozinho = vivos[em_grupo[0]].criacao.nome or "Alguém"
        resultado.notas.append(f"{sozinho} se preparou em grupo sozinho: vale o Preparar-se comum (+1).")
    if interrompido:
        resultado.notas.append("Descanso longo interrompido: valeram os benefícios do descanso curto.")

    for i, p in vivos.items():
        e = escolhas[i]
        longos = _longos(p, e, efetivo)
        saida = []
        for k, m in enumerate(e.movimentos):
            movimento = m.movimento
            if movimento is Movimento.PREPARAR_EM_GRUPO and len(em_grupo) < 2:
                movimento = Movimento.PREPARAR
            if movimento is Movimento.PROJETO and k not in longos:
                continue   # longo interrompido: o projeto fica para depois
            alvo = vivos[m.alvo].sessao if m.alvo and m.alvo != i else None
            saida.append(p.sessao.aplicar_movimento(movimento, k in longos, m.rolagem, alvo))
        saida += p.sessao.terminar_repouso(longo=efetivo is TipoDeRepouso.LONGO)
        if efetivo is TipoDeRepouso.LONGO:
            s = p.sessao
            if s.companheiro_fora:   # o companheiro volta, com 1 Estresse limpo
                s.companheiro_fora = False
                s.companheiro_estresse = max(s.companheiro_estresse - 1, 0)
            s.descansos_curtos_seguidos = 0
        elif interrompido:
            pass   # longo interrompido não conta como mais um curto seguido
        else:
            p.sessao.descansos_curtos_seguidos += 1
        resultado.por_personagem[i] = saida
    return resultado


def validar_escolha(tipo: TipoDeRepouso | str, pid: str, p, e: EscolhaDeRepouso, participantes: set[str],
                    interrompido: bool = False):
    """Confere a escolha de um personagem (dá para avisar já quando o jogador
    confirma, não só quando o mestre encerra o repouso)."""
    tipo = TipoDeRepouso(tipo)
    movimentos = [m.movimento for m in e.movimentos]
    p.sessao._validar_movimentos(movimentos, [m.rolagem for m in e.movimentos])
    for m in e.movimentos:
        if m.alvo is not None and m.alvo != pid:
            if m.movimento not in (Movimento.CUIDAR_FERIDAS, Movimento.REPARAR_ARMADURA):
                raise RegraViolada("Só Tratar Feridas e Reparar Armadura podem ser feitos num aliado.")
            if m.alvo not in participantes:
                raise RegraViolada("O aliado escolhido não está neste repouso.")
    longos = _longos(p, e, tipo)
    # (no longo interrompido, o projeto escolhido só fica para depois)
    if not interrompido and any(m.movimento is Movimento.PROJETO and k not in longos
                                for k, m in enumerate(e.movimentos)):
        raise RegraViolada(f"{p.criacao.nome}: trabalhar num projeto só no descanso longo.")
    if tipo is TipoDeRepouso.CURTO and not interrompido:
        limite = p.bib.progressao["descansos_curtos_seguidos"]
        if p.sessao.descansos_curtos_seguidos >= limite:
            raise RegraViolada(f"{p.criacao.nome}: depois de {limite} descansos curtos seguidos, "
                               "o próximo precisa ser longo.")


def _longos(p, e: EscolhaDeRepouso, efetivo: TipoDeRepouso) -> set[int]:
    """Índices dos movimentos feitos na versão de descanso longo."""
    if efetivo is TipoDeRepouso.LONGO:
        return set(range(len(e.movimentos)))
    if e.movimento_longo is None:
        return set()
    if Efeito.EFICIENTE not in p.efeitos_ativos():
        raise RegraViolada("Só Eficiente (Clank) troca um movimento curto por um longo.")
    if not 0 <= e.movimento_longo < len(e.movimentos):
        raise RegraViolada("Índice de movimento inválido.")
    return {e.movimento_longo}
