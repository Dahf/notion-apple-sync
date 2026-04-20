from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    notion_oauth_client_id: str = ""
    notion_oauth_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8000/oauth/callback"

    fernet_key: str = ""
    session_secret: str = "dev-insecure-change-me"

    resend_api_key: str = ""
    mail_from: str = "Notion Calendar <noreply@localhost>"

    base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./app.db"
    cache_ttl: int = 600

    imprint_name: str = ""
    imprint_address: str = ""
    imprint_email: str = ""


settings = Settings()
