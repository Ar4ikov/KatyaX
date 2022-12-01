from sqlmodel import SQLModel, Field
from typing import Optional


# describe user scheme with id, telegram_id, telegram_username, is_operator, enable_echo
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(default=None, index=True)
    telegram_username: str = Field(default=None, index=True)
    is_operator: bool = Field(default=False)
    enable_echo: bool = Field(default=False)


# describe the message scheme with id, user_id, text, date, is_solved
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=None, index=True)
    message_id: int = Field(default=None, index=True)
    text: str = Field(default=None)
    date: str = Field(default=None)
    response: str = Field(default=None)
    is_solved: bool = Field(default=False)
