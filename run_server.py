from webserver import WebServer
from bot import EchoBot
import os
from schemes import engine
from flask_cors import CORS

if __name__ == '__main__':
    bot = EchoBot(engine)
    webserver = WebServer(__name__, engine, bot)
    CORS(webserver, resources={r"/*": {"origins": "*"}})
    webserver.run(host=os.getenv('FLASK_HOST'), port=os.getenv('FLASK_PORT'), debug=os.getenv('FLASK_DEBUG'))
