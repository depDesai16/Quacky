from backend.features.send_email.send_email import send_email as send_email_feature


def send_email(email_address: str, subject: str, body: str) -> str:
    """
    Tool wrapper for sending email via feature layer.
    """
    email_address = (email_address or "").strip()
    subject = (subject or "").strip()
    body = (body or "").strip()

    if not email_address:
        return "Missing recipient email address."
    if not subject:
        return "Missing email subject."
    if not body:
        return "Missing email body."

    return send_email_feature(email_address, subject, body)
