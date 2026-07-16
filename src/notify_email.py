"""Send the digest over SMTP. Credentials come from env / GitHub Secrets:

  SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS,
  EMAIL_FROM (default = SMTP_USER), EMAIL_TO
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send(subject: str, text_body: str, html_body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("EMAIL_TO")
    from_addr = os.environ.get("EMAIL_FROM", user or "")
    port = int(os.environ.get("SMTP_PORT", "587"))

    missing = [k for k, v in {
        "SMTP_HOST": host, "SMTP_USER": user, "SMTP_PASS": password, "EMAIL_TO": to_addr,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"missing email env vars: {', '.join(missing)}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx) as s:
            s.login(user, password)
            s.sendmail(from_addr, [to_addr], msg.as_string())
    else:
        with smtplib.SMTP(host, port) as s:
            s.starttls(context=ctx)
            s.login(user, password)
            s.sendmail(from_addr, [to_addr], msg.as_string())
    print(f"  email sent to {to_addr}")
