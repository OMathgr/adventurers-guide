"""Mesas: criar, entrar por código, membros e papéis, permissões dos
mestres e ações do mestre sobre os personagens da mesa."""

import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import object_session

from motor import Personagem

from .. import repositorio
from ..autenticacao import Acesso, acesso
from ..esquemas import CondicaoEntrada, Dano, DanoSaida, FichaSaida, ficha_saida
from ..mesas import (JOGADOR, MESTRE, PERMISSOES_PADRAO, Permissao, SemPermissao, eh_criador,
                     exigir, exigir_criador, gerar_codigo, membro, pode)
from ..repositorio import NaoEncontrado
from ..eventos import central
from ..sessoes import medo_em_jogo
from ..tabelas import MembroTabela, MesaTabela, PersonagemTabela

rotas = APIRouter(prefix="/mesas", tags=["Mesas"])


# --- Formatos ---------------------------------------------------------------------------

class NovaMesa(BaseModel):
    nome: str = Field(min_length=1, max_length=120)


class MembroSaida(BaseModel):
    usuario_id: str
    nome: str
    papel: str
    criador: bool
    online: bool = False       # está com o app aberto agora (avisos ao vivo conectados)


class PersonagemNaMesa(BaseModel):
    id: str
    nome: str
    nivel: int
    classe: str
    jogador: str
    dono_id: str
    foto: str | None = None
    morto: bool = False          # atravessou o véu da morte


class FichaResumida(BaseModel):
    """O que qualquer membro da mesa vê de um personagem: quem é e PV, PF e
    Esperança. Nada de atributos, cartas, equipamento ou inventário."""

    id: str
    nome: str
    foto: str | None
    jogador: str
    nivel: int
    classe: str
    subclasse: str
    estagio_subclasse: str
    multiclasse: str | None       # nome da classe da multiclasse
    ancestralidade: str           # "Elfo" ou "Elfo / Orc" (mista)
    comunidade: str
    pv_max: int
    pv_marcados: int
    estresse_max: int
    estresse_marcado: int
    esperanca: int
    esperanca_max: int
    inconsciente: bool = False
    morto: bool = False


class MedoEmJogo(BaseModel):
    sessao_id: str
    mestre: str      # nome do mestre responsável (o título da sessão fica com ele)
    medo: int


class MesaSaida(BaseModel):
    id: str
    nome: str
    codigo_convite: str        # exibido na página da mesa; o link usa o mesmo código
    medo_em_jogo: list[MedoEmJogo]   # Medo das sessões em andamento: visível para todos
    nivel_maximo: int          # personagens da mesa sobem até este nível
    usar_moedas: bool          # regra opcional das moedas (10 moedas = 1 punhado)
    meu_papel: str
    sou_criador: bool
    permissoes_mestres: dict[str, bool]
    minhas_permissoes: list[Permissao]
    membros: list[MembroSaida]
    personagens: list[PersonagemNaMesa]


class MesaResumo(BaseModel):
    id: str
    nome: str
    meu_papel: str


class Papel(BaseModel):
    papel: str = Field(pattern=f"^({JOGADOR}|{MESTRE})$")


class PermissoesMestres(BaseModel):
    ver_fichas: bool
    aplicar_dano: bool
    aplicar_condicoes: bool
    preparar: bool = True
    nivel: bool = True
    dar_itens: bool = True


class NivelDaMesa(BaseModel):
    nivel_maximo: int = Field(ge=1, le=10)


class MoedasDaMesa(BaseModel):
    usar_moedas: bool


def _saida(m: MembroTabela) -> MesaSaida:
    mesa = m.mesa
    return MesaSaida(
        id=mesa.id, nome=mesa.nome, codigo_convite=mesa.codigo_convite,
        medo_em_jogo=[MedoEmJogo(**x) for x in medo_em_jogo(object_session(mesa), mesa.id)],
        nivel_maximo=mesa.nivel_maximo, usar_moedas=mesa.usar_moedas, meu_papel=m.papel,
        sou_criador=eh_criador(m), permissoes_mestres=mesa.permissoes_mestres,
        minhas_permissoes=[p for p in Permissao if pode(m, p)],
        membros=[MembroSaida(usuario_id=x.usuario_id, nome=x.usuario.nome, papel=x.papel,
                             criador=x.usuario_id == mesa.criador_id, online=central.online(x.usuario_id))
                 for x in sorted(mesa.membros, key=lambda x: x.entrou_em)],
        personagens=[PersonagemNaMesa(id=p.id, nome=p.nome, nivel=1 + len(p.subidas),
                                      classe=p.criacao["classe"], jogador=p.dono.nome,
                                      dono_id=p.dono_id, foto=p.foto, morto=bool((p.sessao or {}).get("morto")))
                     for p in mesa.personagens],
    )


def _desvincular_personagens(a: Acesso, mesa_id: str, usuario_id: str):
    for p in a.banco.query(PersonagemTabela).filter_by(mesa_id=mesa_id, dono_id=usuario_id):
        p.mesa_id = None


# --- Mesa ---------------------------------------------------------------------------------

@rotas.post("", status_code=201, response_model=MesaSaida)
def criar_mesa(dados: NovaMesa, a: Acesso = Depends(acesso)):
    mesa = MesaTabela(id=str(uuid.uuid4()), nome=dados.nome.strip(), criador_id=a.usuario_id,
                      codigo_convite=gerar_codigo(a.banco), permissoes_mestres=dict(PERMISSOES_PADRAO))
    mesa.membros.append(MembroTabela(usuario_id=a.usuario_id, papel=MESTRE))
    a.banco.add(mesa)
    a.banco.commit()
    return _saida(membro(a.banco, mesa.id, a.usuario_id))


@rotas.get("", response_model=list[MesaResumo])
def minhas_mesas(a: Acesso = Depends(acesso)):
    meus = a.banco.query(MembroTabela).filter_by(usuario_id=a.usuario_id).all()
    return [MesaResumo(id=m.mesa_id, nome=m.mesa.nome, meu_papel=m.papel) for m in meus]


@rotas.get("/{mesa_id}", response_model=MesaSaida)
def ver_mesa(mesa_id: str, a: Acesso = Depends(acesso)):
    return _saida(membro(a.banco, mesa_id, a.usuario_id))


@rotas.put("/{mesa_id}", response_model=MesaSaida)
def renomear(mesa_id: str, dados: NovaMesa, a: Acesso = Depends(acesso)):
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir_criador(m)
    m.mesa.nome = dados.nome.strip()
    a.banco.commit()
    return _saida(m)


@rotas.delete("/{mesa_id}", status_code=204)
def apagar_mesa(mesa_id: str, a: Acesso = Depends(acesso)):
    """Apaga a mesa. Os personagens continuam existindo, só ficam sem mesa."""
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir_criador(m)
    for p in m.mesa.personagens:
        p.mesa_id = None
    a.banco.delete(m.mesa)
    a.banco.commit()
    return Response(status_code=204)


# --- Convite -----------------------------------------------------------------------------

@rotas.post("/entrar/{codigo}", response_model=MesaSaida)
def entrar(codigo: str, a: Acesso = Depends(acesso)):
    """Entra na mesa pelo código (é o mesmo usado no link). Entra como jogador."""
    mesa = a.banco.query(MesaTabela).filter_by(codigo_convite=codigo.strip().upper()).one_or_none()
    if mesa is None:
        raise NaoEncontrado("Código de convite inválido.")
    if a.banco.get(MembroTabela, (mesa.id, a.usuario_id)) is None:
        a.banco.add(MembroTabela(mesa_id=mesa.id, usuario_id=a.usuario_id, papel=JOGADOR))
        a.banco.commit()
    return _saida(membro(a.banco, mesa.id, a.usuario_id))


@rotas.post("/{mesa_id}/convite", response_model=MesaSaida)
def novo_codigo(mesa_id: str, a: Acesso = Depends(acesso)):
    """Gera um código novo; o antigo (e links com ele) deixa de funcionar."""
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir_criador(m)
    m.mesa.codigo_convite = gerar_codigo(a.banco)
    a.banco.commit()
    return _saida(m)


# --- Membros, papéis e permissões ------------------------------------------------------------

@rotas.post("/{mesa_id}/sair", status_code=204)
def sair(mesa_id: str, a: Acesso = Depends(acesso)):
    m = membro(a.banco, mesa_id, a.usuario_id)
    if eh_criador(m):
        raise SemPermissao("Quem criou a mesa não pode sair; apague a mesa se quiser encerrá-la.")
    _desvincular_personagens(a, mesa_id, a.usuario_id)
    a.banco.delete(m)
    a.banco.commit()
    return Response(status_code=204)


@rotas.put("/{mesa_id}/membros/{usuario_id}", response_model=MesaSaida)
def mudar_papel(mesa_id: str, usuario_id: str, dados: Papel, a: Acesso = Depends(acesso)):
    eu = membro(a.banco, mesa_id, a.usuario_id)
    exigir_criador(eu)
    alvo = membro(a.banco, mesa_id, usuario_id)
    if eh_criador(alvo):
        raise SemPermissao("O papel de quem criou a mesa não muda.")
    alvo.papel = dados.papel
    a.banco.commit()
    return _saida(eu)


@rotas.delete("/{mesa_id}/membros/{usuario_id}", response_model=MesaSaida)
def remover_membro(mesa_id: str, usuario_id: str, a: Acesso = Depends(acesso)):
    eu = membro(a.banco, mesa_id, a.usuario_id)
    exigir_criador(eu)
    alvo = membro(a.banco, mesa_id, usuario_id)
    if eh_criador(alvo):
        raise SemPermissao("Quem criou a mesa não pode ser removido.")
    _desvincular_personagens(a, mesa_id, usuario_id)
    a.banco.delete(alvo)
    a.banco.commit()
    a.banco.refresh(eu.mesa)
    return _saida(eu)


@rotas.put("/{mesa_id}/permissoes", response_model=MesaSaida)
def permissoes(mesa_id: str, dados: PermissoesMestres, a: Acesso = Depends(acesso)):
    """Define o que TODOS os mestres (além do criador) podem fazer."""
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir_criador(m)
    m.mesa.permissoes_mestres = dados.model_dump()
    a.banco.commit()
    return _saida(m)


@rotas.put("/{mesa_id}/nivel", response_model=MesaSaida)
def definir_nivel(mesa_id: str, dados: NivelDaMesa, a: Acesso = Depends(acesso)):
    """Nível máximo dos personagens da mesa. Baixar não desfaz níveis de ninguém:
    quem já passou só não sobe mais até a mesa alcançar."""
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir(m, Permissao.NIVEL)
    m.mesa.nivel_maximo = dados.nivel_maximo
    a.banco.commit()
    return _saida(m)


@rotas.put("/{mesa_id}/moedas", response_model=MesaSaida)
def regra_das_moedas(mesa_id: str, dados: MoedasDaMesa, a: Acesso = Depends(acesso)):
    """Regra opcional do SRD (10 moedas = 1 punhado). Quem pode definir o nível
    da mesa decide. Desligar não apaga as moedas de ninguém: só deixam de aparecer."""
    m = membro(a.banco, mesa_id, a.usuario_id)
    exigir(m, Permissao.NIVEL)
    m.mesa.usar_moedas = dados.usar_moedas
    a.banco.commit()
    return _saida(m)


# --- Mestre agindo sobre os personagens da mesa ------------------------------------------------

def _como_mestre(a: Acesso, mesa_id: str, personagem_id: str, permissao: Permissao, acao, em_jogo: bool = True):
    """Confere a permissão, carrega o personagem da mesa, executa e salva."""
    exigir(membro(a.banco, mesa_id, a.usuario_id), permissao)
    linha = repositorio.linha_na_mesa(a.banco, mesa_id, personagem_id)
    if em_jogo:
        repositorio.exigir_em_jogo(a.banco, personagem_id)
    personagem = repositorio.montar(linha)
    resultado = acao(personagem)
    repositorio.gravar(a.banco, linha, personagem)
    return resultado


@rotas.get("/{mesa_id}/personagens/{personagem_id}/resumo", response_model=FichaResumida)
def ficha_resumida(mesa_id: str, personagem_id: str, a: Acesso = Depends(acesso)):
    """Ficha simplificada para qualquer membro da mesa (jogadores veem os
    personagens uns dos outros)."""
    membro(a.banco, mesa_id, a.usuario_id)
    linha = repositorio.linha_na_mesa(a.banco, mesa_id, personagem_id)
    return resumo_de(linha, repositorio.montar(linha).ficha())


def resumo_de(linha: PersonagemTabela, f) -> FichaResumida:
    """Ficha resumida a partir da ficha calculada (de agora ou de uma sessão)."""
    bib = repositorio.biblioteca()
    ancestralidades = [bib.ancestralidades[x].nome for x in (f.ancestralidade, f.segunda_ancestralidade) if x]
    return FichaResumida(
        id=linha.id, nome=f.nome, foto=linha.foto, jogador=linha.dono.nome, nivel=f.nivel,
        classe=bib.classes[f.classe].nome, subclasse=bib.subclasses[f.subclasse].nome,
        estagio_subclasse=f.estagio_subclasse,
        multiclasse=bib.classes[f.multiclasse["classe"]].nome if f.multiclasse else None,
        ancestralidade=" / ".join(ancestralidades), comunidade=bib.comunidades[f.comunidade].nome,
        pv_max=f.pv_max, pv_marcados=f.pv_marcados, estresse_max=f.estresse_max,
        estresse_marcado=f.estresse_marcado, esperanca=f.esperanca, esperanca_max=f.esperanca_max,
        inconsciente=f.inconsciente, morto=f.morto)


@rotas.get("/{mesa_id}/personagens/{personagem_id}", response_model=FichaSaida)
def ficha_na_mesa(mesa_id: str, personagem_id: str, a: Acesso = Depends(acesso)):
    exigir(membro(a.banco, mesa_id, a.usuario_id), Permissao.VER_FICHAS)
    return ficha_saida(repositorio.montar(repositorio.linha_na_mesa(a.banco, mesa_id, personagem_id)).ficha())


@rotas.post("/{mesa_id}/personagens/{personagem_id}/dano", response_model=DanoSaida)
def dano_na_mesa(mesa_id: str, personagem_id: str, pedido: Dano, a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        return p.sessao.receber_dano(**pedido.model_dump()), p.ficha()
    resultado, ficha = _como_mestre(a, mesa_id, personagem_id, Permissao.APLICAR_DANO, acao)
    return DanoSaida(resultado=resultado, ficha=ficha_saida(ficha))


@rotas.post("/{mesa_id}/personagens/{personagem_id}/condicoes", response_model=FichaSaida)
def aplicar_condicao(mesa_id: str, personagem_id: str, pedido: CondicaoEntrada,
                     a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        p.sessao.aplicar_condicao(pedido.condicao)
        return p.ficha()
    return ficha_saida(_como_mestre(a, mesa_id, personagem_id, Permissao.APLICAR_CONDICOES, acao))


@rotas.post("/{mesa_id}/personagens/{personagem_id}/cicatrizes/{indice}/curar", response_model=FichaSaida)
def curar_cicatriz(mesa_id: str, personagem_id: str, indice: int, a: Acesso = Depends(acesso)):
    """A critério do mestre (projeto no repouso, missão...): o espaço de Esperança volta."""
    def acao(p: Personagem):
        p.sessao.curar_cicatriz(indice)
        return p.ficha()
    # cicatriz é do personagem, não da sessão: dá para curar fora de jogo
    return ficha_saida(_como_mestre(a, mesa_id, personagem_id, Permissao.APLICAR_CONDICOES, acao, em_jogo=False))


@rotas.delete("/{mesa_id}/personagens/{personagem_id}/condicoes/{condicao}", response_model=FichaSaida)
def remover_condicao(mesa_id: str, personagem_id: str, condicao: str, a: Acesso = Depends(acesso)):
    def acao(p: Personagem):
        p.sessao.remover_condicao(condicao)
        return p.ficha()
    return ficha_saida(_como_mestre(a, mesa_id, personagem_id, Permissao.APLICAR_CONDICOES, acao))
