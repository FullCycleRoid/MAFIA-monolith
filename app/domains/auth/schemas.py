from pydantic import BaseModel


class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: str = None
    username: str = None
    language_code: str = "en"
    is_bot: bool = False
    allows_write_to_pm: bool = False
    auth_date: int
    hash: str
