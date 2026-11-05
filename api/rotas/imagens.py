"""Fotos de personagens, NPCs e inimigos.

Envio com login (POST /imagens, multipart). A tag <img> do navegador não manda
o token de acesso, então a leitura (GET /imagens/{id}?passe=...) usa um passe
curto (POST /imagens/passe, com login): o link de uma foto para de funcionar em
até 2 horas e o passe não serve para mais nada. O id continua sendo um UUID
aleatório, que a API só entrega a quem pode ver o que usa a foto.

O tipo é conferido pelos primeiros bytes do arquivo (não pelo nome nem pelo
Content-Type que o navegador diz), e o tamanho máximo é 2 MB.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from pydantic import BaseModel

from motor import RegraViolada

from ..autenticacao import Acesso, acesso
from ..db import sessao_do_banco
from ..repositorio import NaoEncontrado
from ..seguranca import TokenInvalido, criar_passe_de_imagens, ler_assinado
from ..tabelas import ImagemTabela, UsuarioTabela

rotas = APIRouter(prefix="/imagens", tags=["Imagens"])

TAMANHO_MAXIMO = 2 * 1024 * 1024


class ImagemEnviada(BaseModel):
    id: str
    url: str


class PasseDeImagens(BaseModel):
    passe: str


def tipo_da_imagem(dados: bytes) -> str | None:
    """JPEG, PNG ou WebP, pela assinatura do arquivo."""
    if dados.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "image/webp"
    return None


def imagem_valida(a: Acesso, imagem_id: str | None) -> str | None:
    """Confere que a foto escolhida existe (None tira a foto)."""
    if imagem_id is not None and a.banco.get(ImagemTabela, imagem_id) is None:
        raise NaoEncontrado("Imagem não encontrada; envie a foto de novo.")
    return imagem_id


@rotas.post("", status_code=201, response_model=ImagemEnviada)
async def enviar(arquivo: UploadFile, a: Acesso = Depends(acesso)):
    dados = await arquivo.read(TAMANHO_MAXIMO + 1)
    if len(dados) > TAMANHO_MAXIMO:
        raise RegraViolada("A imagem passa de 2 MB. Reduza o tamanho e tente de novo.")
    tipo = tipo_da_imagem(dados)
    if tipo is None:
        raise RegraViolada("Envie uma imagem JPG, PNG ou WebP.")
    imagem = ImagemTabela(id=str(uuid.uuid4()), dono_id=a.usuario_id, tipo=tipo, dados=dados)
    a.banco.add(imagem)
    a.banco.commit()
    return ImagemEnviada(id=imagem.id, url=f"/imagens/{imagem.id}")


@rotas.post("/passe", response_model=PasseDeImagens)
def passe(a: Acesso = Depends(acesso)):
    return PasseDeImagens(passe=criar_passe_de_imagens(a.usuario_id))


def _conferir_passe(banco, passe: str | None):
    recusa = HTTPException(status.HTTP_401_UNAUTHORIZED, "O link desta imagem expirou.")
    if passe is None:
        raise recusa
    try:
        dados = ler_assinado("imagens", passe)
    except TokenInvalido:
        raise recusa
    if banco.get(UsuarioTabela, dados.get("sub")) is None:   # conta apagada depois do passe
        raise recusa


@rotas.get("/{imagem_id}")
def ver(imagem_id: str, passe: str | None = None, banco=Depends(sessao_do_banco)):
    _conferir_passe(banco, passe)
    imagem = banco.get(ImagemTabela, imagem_id)
    if imagem is None:
        raise NaoEncontrado("Imagem não encontrada.")
    # só no navegador de quem abriu, pelo tempo que o link pode valer
    return Response(imagem.dados, media_type=imagem.tipo, headers={
        "Cache-Control": "private, max-age=7200, immutable",
        "X-Content-Type-Options": "nosniff",
    })
