// Gera src/api/esquema.d.ts a partir da API (FastAPI), sem precisar subir o servidor:
// 1. o Python do .venv exporta o OpenAPI para web/openapi.json;
// 2. o openapi-typescript transforma isso em tipos TypeScript.
// Rode depois de mudar a API:  npm run api:tipos
import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const raiz = resolve(web, '..')
const python = [join(raiz, '.venv', 'Scripts', 'python.exe'), join(raiz, '.venv', 'bin', 'python')]
  .find(existsSync)
if (!python) throw new Error('Não achei o Python do .venv na raiz do projeto.')

execFileSync(python, ['-m', 'api.exportar_openapi', join(web, 'openapi.json')], { cwd: raiz, stdio: 'inherit' })
execFileSync(process.execPath, [join(web, 'node_modules', 'openapi-typescript', 'bin', 'cli.js'),
  join(web, 'openapi.json'), '-o', join(web, 'src', 'api', 'esquema.d.ts')], { stdio: 'inherit' })
