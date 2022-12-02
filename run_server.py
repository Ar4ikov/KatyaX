from webserver import WebServer
import os
from schemes import engine

if __name__ == '__main__':
    webserver = WebServer('webserver', engine)
    webserver.run(host=os.getenv('FLASK_HOST'), port=os.getenv('FLASK_PORT'), debug=os.getenv('FLASK_DEBUG'))
