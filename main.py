from typing import Optional
import os

from pydantic import BaseModel
from fastapi import FastAPI, Response
from client import Client, _get_id
# import websocket
import threading
import gc

agent_pool = {}

PORT =  os.environ.get('PORT', 10001)
# # 3750 = 5 min
# # 1 timeout tick = 0.08 sec 
SOK_TIMEOUT = os.environ.get('SOK_TIMEOUT',3750)


def _conn_cleanup_fn(_id):
    """
    id of client socket to clean up the resourcses associated with it
    """
    # del ClientManager.agent_pool[_id]
    del agent_pool[_id]
    gc.collect()

# class ClientManager(object):
#     agent_pool = {}

#     @staticmethod
#     def create_new_client(_id):
#         ws = Client("ws://localhost:{}/websocket".format(PORT), SOK_TIMEOUT, _conn_cleanup_fn, _id)
#         ClientManager.agent_pool[_id] = ws
#         return ws

class Item(BaseModel):
    text: str
    _id: Optional[str] = None

app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "This is BlenderBot chat service."}


@app.post("/interact/")
async def chat(item: Item, response: Response):
    item_dict = item.dict()

    n_id = _get_id()
    if item_dict.get('_id'):
        ws = agent_pool.get(item_dict['_id'],Client("ws://localhost:{}/websocket".format(PORT), SOK_TIMEOUT, _conn_cleanup_fn, n_id))
        if item_dict.get('_id') in agent_pool:
            n_id = item_dict.get('_id')
        else:
            agent_pool[n_id] = ws
    else:
        ws = Client("ws://localhost:{}/websocket".format(PORT), SOK_TIMEOUT, _conn_cleanup_fn, n_id)
        agent_pool[n_id] = ws
    
    ws.out_state.append(item_dict['text'])

    while True:
        if len(ws.state) > 0:
            item_dict['bot_reply'] = ws.state.pop(0)
            break
        
    return item_dict