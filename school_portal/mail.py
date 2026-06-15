"""Sending email over SMTP (Mailpit in development).

In tests nothing is sent: messages are appended to app.extensions["outbox"].
"""

import smtplib
from email.message import EmailMessage

from flask import current_app, render_template

from . import jobs


def send_email(to: str, subject: str, body: str) -> None:
    app = current_app
    message = EmailMessage()
    message["From"] = app.config["MAIL_FROM"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if app.config.get("TESTING"):
        app.extensions.setdefault("outbox", []).append(message)
        return
    with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"], timeout=20) as smtp:
        if app.config["SMTP_TLS"]:
            smtp.starttls()
        if app.config["SMTP_USER"]:
            smtp.login(app.config["SMTP_USER"], app.config["SMTP_PASSWORD"])
        smtp.send_message(message)


def queue_email(to: str, subject: str, template: str, **context) -> None:
    """Render an email now and send it from the worker."""
    body = render_template(template, **context)
    jobs.enqueue("email", {"to": to, "subject": subject, "body": body})


@jobs.handler("email")
def _send_job(payload: dict) -> None:
    send_email(payload["to"], payload["subject"], payload["body"])
