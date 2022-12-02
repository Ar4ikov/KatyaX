import jwt
import datetime
from flask import Flask, request, jsonify, render_template
from dataclasses import asdict
from schemes import User, Message, ConversationThread, create_conversation_table, add_conversation_message, get_conversation_messages
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
        self.add_url_rule('/<token>/<ticket_id>/send_message', 'send_message', self.send_message, methods=['POST'])
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

    def send_message(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        message = request.form.get('message')
        print(message)
        user_id = self.verify_token(token)['user_id']
        date = datetime.datetime.now().timestamp()
        conv_message_id = add_conversation_message(self.engine, ticket_id, user_id, date, message)
        conv_message = ConversationThread(id=conv_message_id, user_id=user_id, date=date, message=message)
        
        self.messages[ticket_id].append(conv_message)

        if self.bot is not None:
            user_id = ticket_id.split('_')[1]
            self.bot.send_echo_message(int(user_id), message)

        return jsonify({'status': 'ok'})

    def get_timestamp(self, token):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        return jsonify({'timestamp': datetime.datetime.now().timestamp()})

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

        return jsonify({'timestamp': datetime.datetime.now().timestamp(), 'ticket_id': ticket_id, 'messages': new_messages})

    def _get_messages(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        # get conversation from db
        conversation = get_conversation_messages(self.engine, ticket_id)
        
        self.messages[ticket_id] = conversation

        # return all messages from conversation
        return conversation

    def get_messages(self, token, ticket_id):
        return jsonify({'messages': [x.as_dict() for x in self._get_messages(token, ticket_id)]})

    def chat(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        messages = [asdict(x) for x in self._get_messages(token, ticket_id)]

        # render template of index.html
        return render_template('index.html', ticket_id=ticket_id, token=token, messages=messages)

    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        super().run(host, port, debug, load_dotenv, **options)
