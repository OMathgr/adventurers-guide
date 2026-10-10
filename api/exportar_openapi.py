"""Grava o esquema OpenAPI da API num arquivo, sem subir o servidor.

Usado pelo front-end para gerar os tipos TypeScript (npm run api:tipos):
    python -m api.exportar_openapi web/openapi.json
"""

import json
import sys

from .main import app

destino = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
with open(destino, "w", encoding="utf-8") as arquivo:
    json.dump(app.openapi(), arquivo, ensure_ascii=False, indent=2)
print(f"OpenAPI gravado em {destino}")
