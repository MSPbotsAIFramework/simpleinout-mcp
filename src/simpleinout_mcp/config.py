from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-credential configuration only. Per SOP §3.1, credentials come
    exclusively from per-request HTTP headers (see server.py's
    GatewayTokenMiddleware) — there is intentionally no env-var field for
    client_id / client_secret / refresh_token here, and no fallback mode
    that would read them from the environment on the HTTP transport path.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_http_port: int = 8080
    mcp_http_host: str = "0.0.0.0"

    # Header names are not credentials — just the (configurable) names the
    # Gateway is expected to send. Actual values are never read from env.
    simpleinout_client_id_header: str = "X-SimpleInOut-Client-Id"
    simpleinout_client_secret_header: str = "X-SimpleInOut-Client-Secret"
    simpleinout_refresh_token_header: str = "X-SimpleInOut-Refresh-Token"


def get_settings() -> Settings:
    return Settings()
