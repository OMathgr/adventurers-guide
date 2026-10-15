"""Regras de acesso das sessões de jogo.

Uma sessão é de UM mestre, o responsável (quem criou). Os outros mestres só
veem o lado do mestre se ele compartilhar com eles, e mesmo assim só para
leitura. Em andamento ou encerrada, qualquer membro vê o lado dos jogadores
(`api/rotas/jogo.py`): entrar, Medo, revelado, lojas e quem está jogando.

Quem não pode ver recebe 404 (a sessão "não existe" para ele); quem vê mas
não é o responsável recebe 403 ao tentar mudar algo.
"""

from .autenticacao import Acesso
from .mesas import SemPermissao, exigir_mestre, membro
from .repositorio import NaoEncontrado
from .tabelas import SessaoTabela

STATUS = ("planejada", "em_andamento", "encerrada")


def pode_ver(sessao: SessaoTabela, usuario_id: str) -> bool:
    return sessao.responsavel_id == usuario_id or usuario_id in (sessao.compartilhada_com or [])


def sessao_do_mestre(a: Acesso, mesa_id: str, sessao_id: str, editar: bool = False) -> SessaoTabela:
    """A sessão, se o usuário for mestre da mesa e puder vê-la; `editar` exige
    ser o responsável."""
    exigir_mestre(membro(a.banco, mesa_id, a.usuario_id))
    sessao = a.banco.get(SessaoTabela, sessao_id)
    if sessao is None or sessao.mesa_id != mesa_id or not pode_ver(sessao, a.usuario_id):
        raise NaoEncontrado("Sessão não encontrada.")
    if editar and sessao.responsavel_id != a.usuario_id:
        raise SemPermissao("Só o mestre responsável pela sessão pode mudar isso.")
    return sessao


def medo_em_jogo(banco, mesa_id: str) -> list[dict]:
    """Medo das sessões em andamento, para todos os membros (o livro pede que o
    Medo fique visível). Só o nome do mestre, sem o título (pode ter spoiler)."""
    linhas = banco.query(SessaoTabela).filter_by(mesa_id=mesa_id, status="em_andamento")
    return [{"sessao_id": s.id, "mestre": s.responsavel.nome, "medo": s.medo} for s in linhas]