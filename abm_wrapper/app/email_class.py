FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "live.com", "msn.com", "me.com", "proton.me", "protonmail.com",
    "yandex.com", "mail.com", "gmx.com", "zoho.com", "rediffmail.com",
}


def classify_email(email):
    """personal / work / unknown, by free-provider domain lookup."""
    if not email or "@" not in email:
        return "unknown"
    domain = email.rsplit("@", 1)[-1].strip().lower()
    if not domain:
        return "unknown"
    return "personal" if domain in FREE_EMAIL_DOMAINS else "work"
