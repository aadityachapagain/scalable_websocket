import logging
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.options
import uuid

from tornado.options import define, options

define("port", default=3000, help="run on the given port", type=int)

def _get_rand_id():
    return str(uuid.uuid4())


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/websocket", MainHandler)]
        settings = dict(debug=True)
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        self.unique_id = _get_rand_id()
        logging.info("A client connected.")

    def on_close(self):
        logging.info("{} client disconnected".format(self.unique_id))
        

    def on_message(self, message):
        logging.info("message from {}: {}".format(self.unique_id, message))
        self.write_message(' {} : {}'.format(self.unique_id, message))


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()