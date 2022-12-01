from sqlmodel import SQLModel, Field, select, create_table
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


# create scheme with id, user_id, date, message
class ConversationThread(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=user_id, index=True)
    date: str = Field(default=None)
    message: str = Field(default=None)

    @classmethod
    def set_table_name(cls, table_name):
        cls.__tablename__ = table_name

    # generate random string id for ticket
    def generate_id(self):
        import random
        import string
        letters = string.ascii_letters
        result_str = ''.join(random.choice(letters) for i in range(10))
        return result_str


def create_conversation_table(user_id, session):
    # get all messages from user from last entry with is_solved = False
    # create table with name = ticket_id
    # insert all messages to table
    
    messages = select(Message).where(Message.user_id == user_id, Message.is_solved == False)
    case_message = session.exec(messages).all()[-1]

    conversation = ConversationThread()
    conversation.set_table_name(conversation.generate_id())
    create_table(conversation, session.engine)

    conv_message = ConversationThread(user_id=case_message.user_id, date=case_message.date, message=case_message.text)
    session.add(conv_message)
    session.commit()

    return conversation.__tablename__


def get_conversation_table(table_name):
    # get table with name = table_name
    # return table
    conversation = ConversationThread()
    conversation.set_table_name(table_name)
    return conversation
