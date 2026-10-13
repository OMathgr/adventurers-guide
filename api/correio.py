"""Envio de e-mail por SMTP (funciona com qualquer provedor: Gmail, Outlook,
Brevo, SendGrid...).

Configuração por variáveis de ambiente:
- SMTP_HOST: servidor. Sem ele, o e-mail vai para o log (desenvolvimento).
- SMTP_PORTA: padrão 587.
- SMTP_SEGURANCA: "starttls" (padrão, porta 587), "ssl" (porta 465) ou "nenhuma".
- SMTP_USUARIO e SMTP_SENHA: login no servidor (se ele pedir).
- SMTP_REMETENTE: endereço "De" (padrão: SMTP_USUARIO).
- APP_URL: endereço da interface, usado nos links (padrão: http://localhost:5173).
"""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

_log = logging.getLogger(__name__)

URL_DO_APP = os.environ.get("APP_URL", "http://localhost:5173").rstrip("/")


def enviar(para: str, assunto: str, texto: str):
    host = os.environ.get("SMTP_HOST")
    if not host:
        _log.warning("SMTP_HOST não definido: e-mail não enviado.\nPara: %s\nAssunto: %s\n\n%s", para, assunto, texto)
        return
    usuario = os.environ.get("SMTP_USUARIO")
    msg = EmailMessage()
    msg["From"] = os.environ.get("SMTP_REMETENTE") or usuario or "nao-responda@localhost"
    msg["To"] = para
    msg["Subject"] = assunto
    msg.set_content(texto)
    seguranca = os.environ.get("SMTP_SEGURANCA", "starttls").lower()
    porta = int(os.environ.get("SMTP_PORTA", "465" if seguranca == "ssl" else "587"))
    contexto = ssl.create_default_context()
    try:
        if seguranca == "ssl":
            servidor = smtplib.SMTP_SSL(host, porta, context=contexto, timeout=20)
        else:
            servidor = smtplib.SMTP(host, porta, timeout=20)
        with servidor:
            if seguranca == "starttls":
                servidor.starttls(context=contexto)
            if usuario:
                servidor.login(usuario, os.environ.get("SMTP_SENHA", ""))
            servidor.send_message(msg)
    except (OSError, smtplib.SMTPException):
        # roda em segundo plano depois da resposta: só registra (quem pediu já recebeu a mesma resposta)
        _log.exception("Falha ao enviar e-mail para %s", para)
