import jwt
import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import Unauthorized, NotAcceptable, Forbidden, BadRequest, NotFound
from dataclasses import asdict
from schemes import User, Message, UserTicket, ConversationThread, create_conversation_table, add_conversation_message, get_conversation_messages
from sqlmodel import Session, select
import os
from typing import Dict, List
from time import sleep


class WebServer(Flask):
    def __init__(self, name, engine, bot_cls=None):
        super().__init__(name)
        self.secret = os.getenv('FLASK_SECRET')
        self.engine = engine
        self.bot = bot_cls
        
        self.set_routers()

        self.messages: Dict[str, List[ConversationThread]] = {}

    def set_routers(self):
        self.add_url_rule('/<token>', 'chat', self.chat, methods=['GET'])
        self.add_url_rule('/<token>/get_messages', 'get_messages', self.chat, methods=['GET'])
        self.add_url_rule('/<token>/store_user_message', 'store_user_message', self.store_user_message, methods=['POST'])
        self.add_url_rule('/<token>/send_message', 'send_message', self.send_message, methods=['POST'])
        self.add_url_rule('/<token>/close_thread', 'close_thread', self.close_thread, methods=['GET'])
        self.add_url_rule('/<token>/polling/<timestamp>', 'polling', self.polling, methods=['GET'])
        self.add_url_rule('/<token>/get_timestamp', 'get_timestamp', self.get_timestamp, methods=['GET'])

    def generate_token(self, user_id, telegram_id, ticket_id):
        minutes = int(os.getenv('TOKEN_EXPIRE_MINUTES'))
        token = jwt.encode({'user_id': user_id, 'telegram_id': telegram_id, 'ticket_id': ticket_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)}, self.secret, algorithm="HS256")
        return token

    def verify_token(self, token):
        try:
            data = jwt.decode(token, self.secret, options={"require": ["user_id", "telegram_id", "ticket_id"]}, algorithms=["HS256"])
            return data
            
        except jwt.ExpiredSignatureError:
            raise Unauthorized(response=jsonify({'error': 'token expired'}))
        
        except jwt.MissingRequiredClaimError:
            raise NotAcceptable(response=jsonify({'error': 'missing required claim'}))

        except jwt.InvalidTokenError:
            raise Forbidden(response=jsonify({'error': 'invalid token'}))

    def store_user_message(self, token):
        token_data = self.verify_token(token)
        
        ticket_id = token_data['ticket_id']
        user_id = token_data['user_id']
        message = request.args.get('message')
        date = request.args.get('date')

        id_ = add_conversation_message(self.engine, ticket_id, user_id, message.date, message.text)
        conv_message = ConversationThread(id=id_, user_id=user_id, message=message, date=date)
        
        self.messages[ticket_id].append(conv_message)

        return jsonify({'status': 'ok'})

    def send_message(self, token):
        token_data = self.verify_token(token)
        ticket_id = token_data['ticket_id']

        # get ticket status from db
        with Session(self.engine) as session:
            ticket = select(UserTicket).where(UserTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket).first()

        # if ticket is closed, return error
        if ticket.is_solved == True:
            raise NotFound(response=jsonify({'error': 'ticket is closed'}))

        message = request.form.get('message')

        if message is None or message == '':
            raise BadRequest(response=jsonify({'error': 'message is required and must be not null'}))

        # remove chars that notsql can't handle
        message = message.replace("'", '"')

        user_id = token_data['user_id']
        date = datetime.datetime.now().timestamp()
        conv_message_id = add_conversation_message(self.engine, ticket_id, user_id, date, message)
        conv_message = ConversationThread(id=conv_message_id, user_id=user_id, date=date, message=message)
        
        self.messages[ticket_id].append(conv_message)

        if self.bot is not None:
            user_id = ticket_id.split('_')[1]

            # get user from db
            with Session(self.engine) as session:
                user = session.exec(select(User).where(User.id == user_id)).one()

            # send message to bot
            self.bot.send_echo_message(int(user.telegram_id), message)

        return jsonify({'status': 'ok'})

    def get_timestamp(self, token):
        self.verify_token(token)

        return jsonify({'timestamp': datetime.datetime.now().timestamp()})

    def close_thread(self, token):
        token_data = self.verify_token(token)
        ticket_id = token_data['ticket_id']

        # get ticket status from db
        with Session(self.engine) as session:
            ticket = select(UserTicket).where(UserTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket).first()

        # if ticket is closed, return error
        if ticket.is_solved == True:
            raise NotFound(response=jsonify({'error': 'ticket is closed'}))

        # close ticket
        with Session(self.engine) as session:
            ticket.is_solved = True
            session.add(ticket)
            session.commit()

        # disable echo bot for user
        if self.bot is not None:
            user_id = ticket_id.split('_')[1]

            with Session(self.engine) as session:
                user = session.exec(select(User).where(User.id == user_id)).one()
            
            # disable echo bot for user
            self.bot.set_echo_status(int(user.telegram_id), False)

            # send message to bot
            self.bot.send_echo_message(int(user.telegram_id), 'Оператор завершил чат, бот снова доступен')

        return jsonify({'status': 'ok'})

    def polling(self, token, timestamp):
        token_data = self.verify_token(token)
        ticket_id = token_data['ticket_id']

        if ticket_id not in self.messages:
            return jsonify({'timestamp': datetime.datetime.now().timestamp(), 'ticket_id': ticket_id, 'messages': []})

        new_messages: List[ConversationThread] = []
        wait_for = request.args.get('wait_for', 20)

        end_time = datetime.datetime.now().timestamp() + int(wait_for)
        
        while len(new_messages) == 0:
            for message in self.messages[ticket_id]:
                if float(message.date) >= float(timestamp):
                    new_messages.append(message)

            if datetime.datetime.now().timestamp() > end_time:
                break

            sleep(.0000001)

        new_messages = [asdict(x) for x in new_messages]
        
        # from user ids in new_messages, get users from database
        with Session(self.engine) as session:
            users = session.exec(select(User)).all()

        # get all users from conversaion
        users = [x for x in users if str(x.id) in [str(y["user_id"]) for y in new_messages]]
        users = [x.as_dict() for x in users]
        users = {x['id']: x for x in users}

        return jsonify({'timestamp': datetime.datetime.now().timestamp(), 'ticket_id': ticket_id, 'messages': new_messages, 'users': users})

    def _get_messages(self, ticket_id):
        # get conversation from db
        conversation = get_conversation_messages(self.engine, ticket_id)

        # get users by user_id from db
        with Session(self.engine) as session:
            users = session.exec(select(User)).all()

        # get all users from conversaion
        users = [x for x in users if x.id in [y.user_id for y in conversation]]
        
        self.messages[ticket_id] = conversation

        # return all messages from conversation
        return conversation, users
    
    def get_messages(self, token):
        token_data = self.verify_token(token)
        ticket_id = token_data['ticket_id']

        messages, users = self._get_messages(token, ticket_id)
        
        return jsonify({'messages': [asdict(x) for x in messages]})

    def chat(self, token):
        token_data = self.verify_token(token)
        ticket_id = token_data["ticket_id"]

        messages, users = self._get_messages(ticket_id)
        messages = [asdict(x) for x in messages]
        users = [x.as_dict() for x in users]
        users = {x['id']: x for x in users}

        # get ticket status
        with Session(self.engine) as session:
            ticket = select(UserTicket).where(UserTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket).first()

        # render template of index.html
        return render_template('index.html', ticket_id=ticket_id, token=token, 
        messages=messages, users=users, is_solved=ticket.is_solved, host=os.getenv('REMOTE_ADDR'), port=os.getenv('FLASK_PORT'))

    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        super().run(host, port, debug, load_dotenv, **options)
