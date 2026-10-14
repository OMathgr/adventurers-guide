# Publicar na VM gratuita da Oracle (HTTPS com DuckDNS + Caddy)

Resultado: o site em `https://SEU-NOME.duckdns.org`, com HTTPS automático,
o app instalável no celular, login com Google (opcional) e backup diário do
banco. Custo: zero (Oracle Always Free + DuckDNS + Let's Encrypt).

Como fica no servidor (tudo em Docker, pela pasta `deploy/`):

- **app**: a API e a interface num processo só (`api/servidor.py`), com o
  banco SQLite num volume. Aplica as migrações sozinho ao subir.
- **caddy**: recebe o HTTPS (portas 80 e 443) e tira/renova o certificado.
- **backup**: uma cópia do banco por dia (guarda as últimas 14).

## 1. Criar a VM na Oracle

1. Crie a conta em <https://www.oracle.com/cloud/free/> (pede cartão só para
   verificar; o plano gratuito não cobra). Escolha uma região perto (ex.:
   São Paulo ou Vinhedo).
2. Dica: em **Billing > Upgrade to Pay As You Go**, a conta continua de graça
   enquanto você usar só recursos "Always Free", e a Oracle deixa de recolher
   instâncias paradas.
3. **Compute > Instances > Create instance**:
   - Image: **Ubuntu 24.04**.
   - Shape: **Ampere (VM.Standard.A1.Flex)**, 1 OCPU e 6 GB já sobram (o
     gratuito vai até 4 OCPU / 24 GB). Se disser "out of capacity", tente outro
     "availability domain" ou mais tarde; a alternativa é a
     **VM.Standard.E2.1.Micro** (AMD, 1 GB, também gratuita; mais apertada).
   - Rede: deixe criar a VCN com **IP público**.
   - Chaves SSH: baixe a chave privada (ou cole a sua pública).
4. Anote o **IP público** da instância.

## 2. Abrir as portas 80 e 443

São dois firewalls:

1. **Na Oracle**: Networking > Virtual Cloud Networks > (sua VCN) > Security
   Lists > Default > **Add Ingress Rules**: origem `0.0.0.0/0`, TCP, portas
   `80` e `443` (uma regra para cada, ou `80,443`).
2. **Na VM** (o Ubuntu da Oracle vem com iptables fechado). Entre por SSH
   (`ssh -i chave.key ubuntu@IP`) e rode:

   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```

## 3. Endereço no DuckDNS

1. Entre em <https://www.duckdns.org> (login com Google, GitHub...).
2. Crie um subdomínio (ex.: `adventurersguide`) e, em "current ip", coloque o
   **IP público da VM**. Pronto: `adventurersguide.duckdns.org` aponta para ela.
   (O IP público da Oracle não muda enquanto a instância existir.)

## 4. Instalar o Docker e baixar o projeto (na VM)

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && newgrp docker
git clone https://github.com/OMathgr/adventurers-guide.git
cd adventurers-guide/deploy
```

(Repositório privado? Use um "personal access token" do GitHub no lugar da senha.)

## 5. Configurar e subir

```bash
cp .env.exemplo .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # copie o resultado para JWT_SECRET
nano .env      # DOMINIO=adventurersguide.duckdns.org e JWT_SECRET=...
docker compose up -d --build
```

A primeira vez demora alguns minutos (monta a interface e a imagem). Depois:

- `docker compose ps` mostra os três serviços (`app` fica "healthy").
- `docker compose logs -f caddy` mostra o certificado sendo tirado.
- Abra `https://adventurersguide.duckdns.org` e crie sua conta.

### E-mail (esqueci minha senha) e Google (opcionais)

No `.env`:

- **E-mail**: `SMTP_HOST=smtp.gmail.com`, `SMTP_USUARIO` = seu Gmail,
  `SMTP_SENHA` = uma "senha de app" (Conta Google > Segurança > Verificação em
  duas etapas > Senhas de app), `SMTP_REMETENTE` = o mesmo Gmail. Sem isto, o
  link de recuperação aparece no log (`docker compose logs app`).
- **Google**: no Google Cloud Console, crie um "ID do cliente OAuth"
  (Aplicativo da Web) com o URI de redirecionamento
  `https://adventurersguide.duckdns.org/api/auth/google/retorno` e preencha
  `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`.

Depois de mudar o `.env`: `docker compose up -d`.

## Atualizar para uma versão nova

```bash
cd adventurers-guide && git pull && cd deploy && docker compose up -d --build
```

O banco fica no volume `dados` e as migrações rodam sozinhas ao subir. Quem
estiver com o app aberto reconecta sozinho (a tela recarrega os dados).

## Backups

- Ficam no volume, em `/dados/backups` (um por dia, os últimos 14). Para ver:
  `docker compose exec app ls /dados/backups`.
- Copiar um para o seu computador:
  `docker compose cp app:/dados/backups/adventurers-AAAAMMDD-HHMMSS.db .` e,
  do seu computador, `scp -i chave.key ubuntu@IP:~/adventurers-guide/deploy/adventurers-*.db .`
- Backup agora: `docker compose exec app python -m api.backup`.
- **Restaurar**: `docker compose stop app`, copie o backup por cima de
  `/dados/adventurers.db` (`docker compose cp arquivo.db app:/dados/adventurers.db`)
  e `docker compose start app`.

Vale guardar uma cópia fora da VM de vez em quando (se a conta ou a instância
sumir, o volume vai junto).

## Problemas comuns

- **O site não abre / certificado não sai**: confira as portas 80 e 443 (os dois
  firewalls, passo 2) e se o DuckDNS aponta para o IP certo (`ping SEU-NOME.duckdns.org`).
- **`app` reinicia sem parar**: `docker compose logs app`. "Defina JWT_SECRET"
  = falta a chave no `.env`.
- **Ao vivo não atualiza**: o Caddy já está configurado para não segurar o fluxo
  (`flush_interval -1`); se puser outro proxy na frente, ele também precisa não
  usar buffer em `/api/eventos`.
- **Um processo só**: não aumente `--workers` do uvicorn; o ao vivo guarda as
  conexões na memória de um processo (para vários, trocar por Redis).
