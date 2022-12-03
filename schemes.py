from sqlmodel import SQLModel, Field, select, create_engine
from dataclasses import dataclass
from sqlalchemy import text
from typing import Optional
import os


# describe user scheme with id, telegram_id, telegram_username, is_operator, enable_echo
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(default=None, index=True)
    telegram_username: str = Field(default=None, index=True)
    is_operator: bool = Field(default=False)
    enable_echo: bool = Field(default=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# describe the message scheme with id, user_id, text, date, is_solved
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=None, index=True)
    message_id: int = Field(default=None, index=True)
    text: str = Field(default=None)
    date: str = Field(default=None)
    response: str = Field(default=None)
    is_solved: bool = Field(default=False)


@dataclass
class ConversationThread:
    id: int
    user_id: int
    date: str
    message: str

    @classmethod
    def generate_id(cls, user_id: int):
        import random
        import string
        letters = string.ascii_letters
        result_str = ''.join(random.choice(letters) for i in range(10))
        return result_str + "_" + str(user_id)


class UserTicket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=None, index=True)
    ticket_id: str = Field(default=None, index=True)
    is_solved: bool = Field(default=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def create_conversation_table(user_id, session, engine):
    # get all messages from user from last entry with is_solved = False
    # create table with name = ticket_id
    # insert all messages to table
    messages = select(Message).where(Message.user_id == user_id, Message.is_solved == False)
    case_message = session.exec(messages).all()[-1]

    ticket_id = ConversationThread.generate_id(user_id)
    
    # create table with sql query
    create_table_query = f'CREATE TABLE IF NOT EXISTS "{ticket_id}" ("id" SERIAL PRIMARY KEY, "user_id" INTEGER, "date" TEXT, "message" TEXT);'
    with engine.connect() as conn:
        conn.execute(text(create_table_query))
        conn.commit()

    add_conversation_message(engine, ticket_id, user_id=case_message.user_id, date=case_message.date, message=case_message.text)

    return ticket_id


def add_conversation_message(engine, ticket_id, user_id, date, message):
    query_ = f'''INSERT INTO "{ticket_id}" ("user_id", "date", "message") VALUES ('{user_id}', '{date}', '{message}');'''
    with engine.connect() as conn:
        conn.execute(text(query_))
        conn.commit()

    # get id of this query from table
    query_ = f'''SELECT id FROM "{ticket_id}" WHERE "user_id" = '{user_id}' AND "date" = '{date}' AND "message" = '{message}';'''
    with engine.connect() as conn:
        result = conn.execute(text(query_)).fetchall()

    return result[0][0]


def get_conversation_messages(engine, ticket_id):
    query_ = f'''SELECT * FROM "{ticket_id}";'''
    with engine.connect() as conn:
        result = conn.execute(text(query_)).fetchall()

    return [ConversationThread(id=row[0], user_id=row[1], date=row[2], message=row[3]) for row in result]


engine = create_engine(os.getenv('SQLITE_DB'))