"""
email_service.py — Enviament d'emails transaccionals via Brevo SMTP.
"""
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.environ.get("BREVO_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("BREVO_SMTP_USER", "")
SMTP_KEY = os.environ.get("BREVO_SMTP_KEY", "")
FROM_EMAIL = os.environ.get("EMAIL_FROM", "noreply@masellas.info")
FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Cercador FP España")


def send_email(to: str, subject: str, body: str) -> None:
    """Envia un email de text pla. Llença excepció si falla."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        s.starttls()
        s.login(SMTP_USER, SMTP_KEY)
        s.sendmail(FROM_EMAIL, [to], msg.as_bytes())


def send_verification_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/api/auth/verify?token={token}"
    send_email(
        to,
        "Verifica el teu compte — Cercador FP",
        f"Hola,\n\nClica aquest enllaç per verificar el teu compte:\n{link}\n\n"
        "L'enllaç caduca en 24 hores.\n\nCercador FP España",
    )


def send_password_reset_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/reset-password.html?token={token}"
    send_email(
        to,
        "Restableix la teva contrasenya — Cercador FP",
        f"Hola,\n\nHas sol·licitat restablir la contrasenya:\n{link}\n\n"
        "L'enllaç caduca en 1 hora. Si no has fet cap sol·licitud, ignora aquest email.\n\n"
        "Cercador FP España",
    )
