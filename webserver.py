import jwt
import datetime
from flask import Flask, request, jsonify, render_template
from dataclasses import asdict
from schemes import User, Message, UserTicket, ConversationThread, create_conversation_table, add_conversation_message, get_conversation_messages
from sqlmodel import Session, select
import os
from typing import Dict, List
from time import sleep


class WebServer(Flask):
    def __init__(self, name, engine, bot_cls=None):
        super().__init__(name)
        self.secret = os.getenv('SECRET')
        self.engine = engine
        self.bot = bot_cls
        
        self.set_routers()

        self.messages: Dict[str, List[ConversationThread]] = {}

    def set_routers(self):
        self.add_url_rule('/<token>/<ticket_id>', 'chat', self.chat, methods=['GET'])
        self.add_url_rule('/<token>/<ticket_id>/get_messages', 'get_messages', self.chat, methods=['GET'])
        self.add_url_rule('/<token>/<ticket_id>/store_user_message', 'store_user_message', self.store_user_message, methods=['POST'])
        self.add_url_rule('/<token>/<ticket_id>/send_message', 'send_message', self.send_message, methods=['POST'])
        self.add_url_rule('/<token>/<ticket_id>/close_thread', 'close_thread', self.close_thread, methods=['GET'])
        self.add_url_rule('/<token>/<ticket_id>/polling/<timestamp>', 'polling', self.polling, methods=['GET'])
        self.add_url_rule('/<token>/get_timestamp', 'get_timestamp', self.get_timestamp, methods=['GET'])

    def generate_token(self, user_id):
        minutes = int(os.getenv('TOKEN_EXPIRE_MINUTES'))
        token = jwt.encode({'user_id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)}, self.secret, algorithm="HS256")
        return token

    def verify_token(self, token):
        try:
            data = jwt.decode(token, self.secret, algorithms=["HS256"])
            return data
        except:
            return False

    def store_user_message(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        id_ = request.form.get('id')
        message = request.args.get('message')
        user_id = self.verify_token(token)['user_id']
        date = request.args.get('date')

        conv_message = ConversationThread(id=id_, user_id=user_id, message=message, date=date)
        self.messages[ticket_id].append(conv_message)

        return jsonify({'status': 'ok'})

    def send_message(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        # get ticket status from db
        with Session(self.engine) as session:
            ticket = select(UserTicket).where(UserTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket).first()

        # if ticket is closed, return error
        if ticket.is_solved == True:
            return jsonify({'error': 'ticket is closed'}), 400

        message = request.form.get('message')

        # remove chars that notsql can't handle
        message = message.replace("'", '"')

        user_id = self.verify_token(token)['user_id']
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
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        return jsonify({'timestamp': datetime.datetime.now().timestamp()})

    def close_thread(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        # get ticket status from db
        with Session(self.engine) as session:
            ticket = select(UserTicket).where(UserTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket).first()

        # if ticket is closed, return error
        if ticket.is_solved == True:
            return jsonify({'error': 'ticket is closed'}), 400

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

    def polling(self, token, ticket_id, timestamp):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

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
        users = [x for x in users if x.id in [y["user_id"] for y in new_messages]]
        users = [x.as_dict() for x in users]
        users = {x['id']: x for x in users}

        return jsonify({'timestamp': datetime.datetime.now().timestamp(), 'ticket_id': ticket_id, 'messages': new_messages, 'users': users})

    def _get_messages(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

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
    
    def get_messages(self, token, ticket_id):
        messages, users = self._get_messages(token, ticket_id)
        return jsonify({'messages': [asdict(x) for x in messages]})

    def chat(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        messages, users = self._get_messages(token, ticket_id)
        messages = [asdict(x) for x in messages]
        users = [x.as_dict() for x in users]
        users = {x['id']: x for x in users}

        # get ticket status
        with Session(self.engine) as session:
            ticket = select(UserTicket).where(UserTicket.ticket_id == ticket_id)
            ticket = session.exec(ticket).first()

        # render template of index.html
        return render_template('index.html', ticket_id=ticket_id, token=token, messages=messages, users=users, is_solved=ticket.is_solved)

    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        super().run(host, port, debug, load_dotenv, **options)
