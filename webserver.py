import jwt
import datetime
from flask import Flask, request, jsonify, render_template
from functools import wraps
from schemes import User, Message, ConversationThread, create_conversation_table, get_conversation_table
from sqlmodel import Session, select
import os
from typing import Dict, List


class WebServer(Flask):
    def __init__(self, name, engine):
        super().__init__(name)
        self.secret = os.getenv('SECRET')
        self.engine = engine
        
        self.set_routers()

        self.messages: Dict[str, List[ConversationThread]] = {}

    def set_routers(self):
        self.add_url_rule('/<token>/<ticket_id>', 'chat', self.chat, methods=['GET'])
        self.add_url_rule('/<token>/<ticket_id>/get_messages', 'get_messages', self.chat, methods=['GET'])
        self.add_url_rule('/<token>/<ticket_id>/send_message', 'send_message', self.send_message, methods=['POST'])
        self.add_url_rule('/<token>/<ticket_id>/polling/<timestamp>', 'polling', self.polling, methods=['GET'])
        self.add_url_rule('/<token>/get_timestamp', 'get_timestamp', self.get_timestamp, methods=['GET'])

    def generate_token(self, user_id):
        minutes = os.getenv('TOKEN_EXPIRE_MINUTES')
        token = jwt.encode({'user_id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)}, self.secret)
        return token

    def verify_token(self, token):
        try:
            data = jwt.decode(token, self.secret)
            return data
        except:
            return False

    def send_message(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        with Session(self.engine) as session:
            message = request.json['message']
            user_id = self.verify_token(token)['user_id']
            conv_message = ConversationThread(user_id=user_id, date=datetime.datetime.now(), message=message)
            session.add(conv_message)
            session.commit()
            session.refresh(conv_message)

            self.messages[ticket_id].append(conv_message)

        return jsonify({'status': 'ok'})

    def get_timestamp(self, token):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        return jsonify({'timestamp': datetime.datetime.now()})

    def polling(self, token, ticket_id, timestamp):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        if ticket_id not in self.messages:
            return jsonify({'messages': []})

        new_messages: List[ConversationThread] = []
        wait_for = request.json.get('wait_for', 20)
        
        while len(new_messages) == 0 or (datetime.datetime.now() - timestamp).seconds <= wait_for:
            for message in self.messages[ticket_id]:
                if message.date > timestamp:
                    new_messages.append(message)

        return jsonify({'timestamp': datetime.datetime.now(), 'ticket_id': ticket_id, 'messages': new_messages})

    def get_messages(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        # get conversation from db
        with Session(self.engine) as session:
            conversation = select(ConversationThread).where(ConversationThread.ticket_id == ticket_id)
            conversation = session.exec(conversation).all()

        self.messages[ticket_id] = conversation

        # return all messages from conversation
        return jsonify({'messages': conversation})

    def chat(self, token, ticket_id):
        if not self.verify_token(token):
            return jsonify({'error': 'invalid token'}), 401

        messages = self.get_messages(token, ticket_id)

        # render template of index.html
        return render_template('index.html', ticket_id=ticket_id, token=token, messages=messages)