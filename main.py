from typing import Optional
import os

from pydantic import BaseModel
from fastapi import FastAPI
from client import Client, _get_id
# import websocket
import threading

port =  os.environ.get('PORT', 10001)

class ClientManager(object):
    agent_pool = {}

    @staticmethod
    def create_new_client(_id):
        ws = Client("ws://localhost:{}/websocket".format(port), 5, False)
        ClientManager.agent_pool[_id] = ws
        return ws

class Item(BaseModel):
    text: str
    _id: Optional[str] = None

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "This is BlenderBot chat service."}


@app.post("/interact/")
async def chat(item: Item):
    item_dict = item.dict()

    if item_dict.get('_id'):
        ws = ClientManager.agent_pool.get(item_dict['_id'], ClientManager.create_new_client(item_dict['_id']))
    else:
        _id = _get_id()
        ws = ClientManager.create_new_client(_id)
    ws.out_state.append(item_dict['text'])
    while True:
        if len(ws.state) > 0:
            break
    item_dict['bot_reply'] = ws.state.pop(0)
    return item_dict