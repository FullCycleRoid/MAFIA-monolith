from pydantic_settings import BaseSettings


class SettingsExtensions(BaseSettings):
    TOKEN_TICKER: str = "MAFIA"
    MAFIA_PRICE_USD: float = 0.001
    TON_PRICE_USD: float | None = None
