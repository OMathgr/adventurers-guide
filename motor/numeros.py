"""Convenções numéricas do projeto.

Toda divisão pela metade arredonda PARA CIMA (decisão do projeto, alinhada ao
SRD onde ele diz "rounded up"). Use `metade` em vez de `// 2`.
"""


def metade(valor: int) -> int:
    """Metade arredondada para cima: metade(15) == 8, metade(1) == 1."""
    return -(-valor // 2)
