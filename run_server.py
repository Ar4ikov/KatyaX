from webserver import WebServer
from bot import EchoBot
import os
from schemes import engine
from flask_cors import CORS
from wsgiserver import WSGIServer

if __name__ == '__main__':
    bot = EchoBot(engine)
    webserver = WebServer(__name__, engine, bot)
    CORS(webserver, resources={r"/*": {"origins": "*"}})

    if os.getenv('FLAST_DEBUG'):
        webserver.run(host=os.getenv('FLASK_HOST'), port=os.getenv('FLASK_PORT'), debug=True)
    
    else:
        server = WSGIServer(webserver, host=os.getenv('FLASK_HOST'), port=int(os.getenv('FLASK_PORT')))
        server.start()
