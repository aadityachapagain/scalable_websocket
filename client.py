from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
import uuid
import random
import time
from threading import Thread
import traceback

def _get_id():
    return str(uuid.uuid4())

def select_rand_socket(socs):
    while True:
        soc = random.choice(socs)
        if soc.ws is None:
            continue
        soc.out_state.append('rand msg: {:.3f}'.format(random.random()))
        time.sleep(random.randint(1,8))

class Client(object):   
    def __init__(self, url, timeout, signal_ping: False):
        self.url = url
        self.timeout = timeout
        # self.ioloop = IOLoop.current()
        self.state = []
        self.out_state = []
        self.ws = None
        self.connect()
        PeriodicCallback(self.send_new_message, 1000).start()
        if signal_ping:
            PeriodicCallback(self.keep_alive, 20000).start()
        # self.ioloop.start()

    @gen.coroutine
    def connect(self):
        try:
            print( "trying to connect")
            self.ws = yield websocket_connect(self.url)
        except Exception:
            print(traceback.format_exc())
            print ("connection error")
        else:
            print ("connected")
            self.run()
            # self.send_new_message()

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

    def close_conn(self):
        self.ws.close()

    # @gen.coroutine
    def send_new_message(self):
        # while True:
        if self.ws is None:
            return
        if len(self.out_state) > 0:
            self.send_message(self.out_state.pop(0))

    def get_new_message(self):
        return 

    def send_message(self, message):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message(message)

if __name__ == "__main__":
    port = 10001
    clients = [Client("ws://localhost:{}/websocket".format(10001), 5, True) for i in range(10)]
    Thread(target = select_rand_socket, args= (clients, )).start()
    ioloop = IOLoop.current()
    ioloop.start()
