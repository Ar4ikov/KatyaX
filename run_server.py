from webserver import WebServer
from bot import EchoBot
import os
from schemes import engine

if __name__ == '__main__':
    bot = EchoBot(engine)
    webserver = WebServer('webserver', engine, bot)
    webserver.run(host=os.getenv('FLASK_HOST'), port=os.getenv('FLASK_PORT'), debug=os.getenv('FLASK_DEBUG'))
