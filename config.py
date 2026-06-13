from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")
    RESEND_API_KEY: str = os.environ.get("RESEND_API_KEY", "")
    INVITE_SENDER_EMAIL: str = os.environ.get("INVITE_SENDER_EMAIL", "noreply@example.com")
    INVOICE_FROM_EMAIL: str = os.environ.get("INVOICE_FROM_EMAIL", "invoices@example.com")
    DEV_EMAIL: str = os.environ.get("DEV_EMAIL", "")  # if set, all emails go here instead of the lessee
    APP_BASE_URL: str = os.environ.get("APP_BASE_URL", "http://localhost:8000")
    ALLOWED_ORIGINS: list[str] = [
        o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    ]
    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_BUCKET_NAME: str = os.environ.get("AWS_S3_BUCKET_NAME", "")
    AWS_REGION: str = os.environ.get("AWS_REGION", "eu-west-1")
    # Comma-separated emails that are always treated as platform admins
    ADMIN_EMAILS: list[str] = [
        e.strip().lower()
        for e in os.environ.get("ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]
    TRIAL_DAYS: int = int(os.environ.get("TRIAL_DAYS", "90"))


settings = Settings()
