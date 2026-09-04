import base64
import smtplib
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import settings


def build_sos_message(owner_name: str, event_id: str, latitude: float | None, longitude: float | None, message: str | None) -> str:
    location = "Location unavailable"
    if latitude is not None and longitude is not None:
        location = f"{latitude:.6f}, {longitude:.6f}"
    return (
        f"Sentinel emergency alert\n\n"
        f"{owner_name} activated an SOS alert.\n"
        f"Event: {event_id}\n"
        f"Location: {location}\n"
        f"Message: {message or 'No additional message provided.'}\n\n"
        f"Open the Sentinel dashboard to review and acknowledge the alert."
    )


def send_email(destination: str, subject: str, body: str) -> tuple[bool, str | None]:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password or not settings.smtp_from_email:
        return False, "SMTP is not configured"
    try:
        email = EmailMessage()
        email["From"] = settings.smtp_from_email
        email["To"] = destination
        email["Subject"] = subject
        email.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(email)
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_sms(destination: str, body: str) -> tuple[bool, str | None]:
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_from_number:
        return False, "Twilio SMS is not configured"
    try:
        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
        payload = urlencode({"To": destination, "From": settings.twilio_from_number, "Body": body}).encode()
        credentials = base64.b64encode(f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()).decode()
        request = Request(endpoint, data=payload, method="POST", headers={"Authorization": f"Basic {credentials}"})
        with urlopen(request, timeout=15) as response:
            if response.status not in range(200, 300):
                return False, f"Twilio returned HTTP {response.status}"
        return True, None
    except Exception as exc:
        return False, str(exc)


def sent_timestamp() -> datetime:
    return datetime.utcnow()
