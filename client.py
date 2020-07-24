from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
import uuid
import random
import asyncio
import time
import traceback
import gc
from threading import Thread

def _get_id():
    return str(uuid.uuid4())

def select_rand_socket(socs):
    while True:
        soc = random.choice(socs)
        if soc.ws is None:
            continue
        soc.out_state.append('rand msg: {:.3f}'.format(random.random()))
        time.sleep(random.randint(1,8))

def clean_client_timeout_fn(_id):
    for client in clients:
        if client.soc_id == _id:
            del client
            break
    # after deleting the conn object and socket 
    # garbage collect all the resources
    gc.collect()

class Client(object):   
    def __init__(self, url, timeout, conn_timeout_callback, soc_id, signal_ping: False):
        self.url = url
        self.soc_id = soc_id
        self.timeout = timeout
        # set timeout callback to close conn and stop async loop
        self._conn_timeout_callback = conn_timeout_callback
        # recived msg from server
        self.state = []
        # message to send to server
        self.out_state = []

        # timeout_counter
        self.timeout_counter = 0
        self.ws = None
        self.connect()
        # check for new message every 0.1 sec
        self.mesg_check_callback = PeriodicCallback(self.send_new_message, 800)
        self.mesg_check_callback.start()

        self.signal_ping = signal_ping
        if signal_ping:
            self.ping_callback = PeriodicCallback(self.keep_alive, 20000)
            self.ping_callback.start()

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
        self.mesg_check_callback.stop()
        if self.signal_ping:
            self.ping_callback.stop()
        self.ws.close()
        if self._conn_timeout_callback:
            self._conn_timeout_callback(self.soc_id)

    def send_new_message(self):
        if self.ws is None:
            return
        if self.timeout_counter > self.timeout:
            pass
        else:
            if len(self.out_state) > 0:
                self.timeout_counter = 0
                self.send_message(self.out_state.pop(0))
            else:
                self.timeout_counter+= 1

    def send_message(self, message):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message(message)

if __name__ == "__main__":
    port = 10001
    clients = [Client("ws://localhost:{}/websocket".format(10001), 5000, clean_client_timeout_fn,_get_id() ,True) for i in range(10)]
    Thread(target = select_rand_socket, args= (clients, )).start()
    ioloop = IOLoop.current()
    ioloop.start()
