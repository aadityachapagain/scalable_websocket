from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect

class Client(object):   
    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout
        self.ioloop = IOLoop.current()
        self.state = []
        self.ws = None
        self.connect()
        PeriodicCallback(self.keep_alive, 20000).start()
        self.ioloop.start()

    @gen.coroutine
    def connect(self):
        print( "trying to connect")
        try:
            self.ws = yield websocket_connect(self.url)
        except Exception:
            print ("connection error")
        else:
            print ("connected")
            self.run()

    @gen.coroutine
    def run(self):
        while True:
            msg = yield self.ws.read_message()
            if msg is None:
                print ("connection closed")
                self.ws = None
                break
            self.state.append(msg)

    def keep_alive(self):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message("keep alive")

    @gen.coroutine
    def new_message_check(self):
        pass

    def get_new_message(self):
        return 

    def send_message(self, message):
        self.ws.write_message(message)

if __name__ == "__main__":
    client = Client("ws://localhost:3000/websocket", 5)
