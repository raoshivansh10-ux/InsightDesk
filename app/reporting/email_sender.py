"""Email Sender using smtplib."""

import os
import smtplib
from email.message import EmailMessage
from flask import current_app

def send_email(subject, recipient, html_content):
    """
    Sends an HTML email using SMTP configured in .env.
    If not configured, it will print to console.
    """
    smtp_server = os.environ.get('MAIL_SERVER')
    smtp_port = os.environ.get('MAIL_PORT')
    smtp_user = os.environ.get('MAIL_USERNAME')
    smtp_pass = os.environ.get('MAIL_PASSWORD')
    sender_email = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@insightdesk.com')

    if not all([smtp_server, smtp_port, smtp_user, smtp_pass]):
        # Fallback to console print for local dev
        print(f"\n{'='*50}")
        print(f"📧 [DEV EMAIL INTERCEPTED]")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Body snippet: {html_content[:200]}...")
        print(f"{'='*50}\n")
        return True

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient
    msg.set_content("Please enable HTML to view this report.")
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")
        return False
