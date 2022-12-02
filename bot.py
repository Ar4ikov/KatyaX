import os
from telebot import TeleBot
from telebot.types import Message, CallbackQuery
from telebot import types
from schemes import User, Message, engine, create_conversation_table
from webserver import WebServer
from sqlmodel import SQLModel, create_engine, Session, select
from sentence_transformers import SentenceTransformer, util
import pathlib
from typing import List


class EchoBot:
    def __init__(self, engine):
        self.bot = TeleBot(os.getenv('BOT_TOKEN'))

        self.model_id = 'clips/mfaq'
        self.model: SentenceTransformer = None

        self.answers: List[str] = []

        self.engine = engine
        self.webserver = WebServer('webserver', self.engine, bot_cls=self)

    def load_and_parse_md_answers(self, filename: str):
        """
        Load and parse markdown file with answers

        :param filename: path to markdown file

        :returns: list of answers
        """
        basement = pathlib.Path(__file__).parent.absolute()
        answers = basement / filename
        with open(answers, 'r') as f:
            lines = f.readlines()
        
        # split answers by ---
        answers = []
        answer = []
        for line in lines:
            if line == '---\n':
                answers.append(answer)
                answer = []
            else:
                answer.append(line)
        
        answers.append(answer)

        answers = [x[0] for x in answers]

        return answers
    
    def setup_pipeline(self):
        """
        Setup pipeline for model and tokenizer

        :returns: None
        """
        self.answers = self.load_and_parse_md_answers(os.getenv('ANSWERS_FILE'))
        self.model = SentenceTransformer(self.model_id)

    def get_answer_pipeline(self, question: str):
        """
        Get answer from pipeline
        
        :param question: question to answer
        
        :returns: answer
        """
        if not self.model:
            self.setup_pipeline()

        question = '<Q>' + question
        answers = ['<A>' + x for x in self.answers]

        query_embedding = self.model.encode(question)
        corpus_embeddings = self.model.encode(answers)

        result = util.semantic_search(query_embedding, corpus_embeddings)
        response = sorted([(x['corpus_id'], x['score']) for x in result[0]], key=lambda y: y[1], reverse=True)

        return self.answers[response[0][0]]

    def create_or_get(self, user_id: int):
        """
        Create or get user from db

        :param user_id: telegram user id

        :returns: user
        """
        with Session(self.engine) as session:
            user = select(User).where(User.telegram_id == user_id)
            user = session.exec(user).first()
            if not user:
                user = User(telegram_id=user_id, telegram_username='@' + self.bot.get_chat(user_id).username)
                session.add(user)
                session.commit()

        return user

    def stack_message(self, message: Message):
        """
        Stack message to db

        :param message: message from user

        :returns: Nonez
        """
        with Session(self.engine) as session:
            user = self.create_or_get(message.from_user.id)
            session.add(Message(user_id=user.id, message_id=message.id, text=message.text, date=message.date))
            session.commit()

    # set message response in db
    def set_message_response(self, message: Message, text: str):
        """
        Set message response in db

        :param message: message from user

        :param text: text of message

        :returns: None
        """
        # select message from db by id
        # set response
        message = select(Message).where(Message.message_id == message.id)
        with Session(self.engine) as session:
            message = session.exec(message).first()
            message.response = text
            session.add
            session.commit()

    # solve question in db
    def set_solve(self, message: Message):
        """
        Solve question in db

        :param message: message from user

        :returns: answer
        """
        # select message from db by id
        # set solved
        message = select(Message).where(Message.message_id == message.id)
        with Session(self.engine) as session:
            message = session.exec(message).first()
            message.is_solved = True
            session.add(message)
            session.commit()

    def set_routers(self):
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(func=lambda m: m.text.startswith("/newtoken"))(self.regenerate_token)
        self.bot.message_handler(content_types=['text'])(self.conversation)
        self.bot.callback_query_handler(func=lambda call: call.data == 'helpful')(self.helpful)
        self.bot.callback_query_handler(func=lambda call: call.data == 'not_helpful')(self.not_helpful)

    def helpful(self, call: CallbackQuery):
        """
        Helpful button handler

        :param call: callback query

        :returns: None
        """
        self.bot.answer_callback_query(call.id, 'Thank you for your feedback')
        message: Message = call.message

        # set solved status for answered message
        self.set_solve(message.reply_to_message)

        # get response from message in db
        _message = select(Message).where(Message.message_id == message.reply_to_message.id)
        with Session(self.engine) as session:
            _message = session.exec(_message).first()
            response = _message.response

        # edit message, remove keyboard
        self.bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=response)

    def not_helpful(self, call: CallbackQuery):
        """
        Not helpful button handler

        :param call: callback query

        :returns: None
        """
        self.bot.answer_callback_query(call.id, 'Thank you for your feedback')
        message: Message = call.message

        # set solved status for answered message
        # self.set_solve(message.reply_to_message)

        # get response from message in db
        _message = select(Message).where(Message.message_id == message.reply_to_message.id)
        with Session(self.engine) as session:
            _message = session.exec(_message).first()
            response = _message.response

        # edit message, remove keyboard
        self.bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=response)

        # find operators in db
        operators = select(User).where(User.is_operator == True)
        with Session(self.engine) as session:
            operators = session.exec(operators).all()

        user_id = call.message.reply_to_message.from_user.id

        with Session(self.engine) as session:
            user = select(User).where(User.telegram_id == user_id)
            user = session.exec(user).first()

        # create table
        with Session(self.engine) as session:
            ticket_id = create_conversation_table(user.id, session, self.engine)

        for operator in operators:
            token = self.webserver.generate_token(operator.id)
            chat_url = f'http://{os.getenv("FLASK_HOST")}:{os.getenv("FLASK_PORT")}/{token}/{ticket_id}'
            self.bot.send_message(operator.telegram_id, f'New ticket from {user_id} \n\n {chat_url}')

    def regenerate_token(self, message: Message):
        args = message.text.split(' ')
        if len(args) < 2:
            self.bot.reply_to(message, "Пожалуйста, укажите ID тикета, к которому необходимо получить новый токен")
            return

        ticket_id = args[1]

        with Session(self.engine) as session:
            user = select(User).where(User.telegram_id == message.from_user.id)
            user = session.exec(user).first()

        if not user.is_operator:
            self.bot.reply_to(message, "Вы не являетесь оператором")
            return

        token = self.webserver.generate_token(user.id)
        url = f'http://{os.getenv("FLASK_HOST")}:{os.getenv("FLASK_PORT")}/{token}/{ticket_id}'
        self.bot.reply_to(message, f'Новая ссылка для чата: \n\n {url}')

    def send_echo_message(self, user_id, message):
        """
        Send echo message to user

        :param user_id: telegram user id

        :param message: message from user

        :returns: None
        """
        self.bot.send_message(user_id, message)

    def conversation(self, message: Message):
        """
        Conversation handler

        :param message: message from user

        :returns: None
        """
        self.stack_message(message)
        self.create_or_get(message.from_user.id)

        # answer the question
        answer = self.get_answer_pipeline(message.text)

        # stack answer to db
        self.set_message_response(message, answer)

        # create keyboard with buttons: 1) Мне помогло, 2) Мне не помогло
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton('Мне помогло', callback_data='helpful'),
                        types.InlineKeyboardButton('Мне не помогло', callback_data='not_helpful'))
        
        # send message with keyboard
        self.bot.reply_to(message, answer + "\n\nВам помог ответ?", reply_markup=keyboard)

    def start(self, message: Message):
        """
        Start command handler

        :param message: message from user

        :returns: None
        """
        self.create_or_get(message.from_user.id)
        self.bot.send_message(message.chat.id, 'Hello, I am EchoBot')

    def run(self):
        """
        Run bot
        """
        SQLModel.metadata.create_all(self.engine)
        self.set_routers()
        self.bot.infinity_polling(timeout=999999)

if __name__ == '__main__':
    bot = EchoBot(engine=engine)
    bot.run()
