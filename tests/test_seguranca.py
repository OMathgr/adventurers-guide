"""Parâmetros do hash de senha (api/seguranca.py)."""

from api.seguranca import gerar_hash, verificar_senha


def test_argon2_com_os_parametros_minimos_da_owasp():
    # 19 MiB, 2 passadas, 1 thread: leve para a VM de 1 GB (o padrão da biblioteca usa 64 MiB e 4 threads)
    hash_ = gerar_hash("senha-forte-123")
    assert hash_.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert verificar_senha("senha-forte-123", hash_) == (True, None)   # já no formato atual: nada a regravar
    assert verificar_senha("errada", hash_)[0] is False
    assert verificar_senha("qualquer", "") == (False, None)   # conta só com o Google
