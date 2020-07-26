import json
import uuid
import time
from datetime import datetime, timedelta
import threading
import websocket
from typing import Optional
import os

from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
import gc
from users import users_db


__BALCK_LIST_MSG = ['Welcome to the overworld for the ParlAI messenger chatbot demo. Please type "begin" to start.',
                    'Welcome to the ParlAI Chatbot demo. You are now paired with a bot - feel free to send a message.Type [DONE] to finish the chat.']

__BALCK_LIST_MSG = [x.lower() for x in __BALCK_LIST_MSG]

SECRET_KEY = "9ff99f09e3afe0a7111dd687145d087a314ba895d697efb081fbdd93cf524033"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10


def _get_rand_id():
    """
    :return: The string of a random id using uuid4
    """
    return str(uuid.uuid4())

class Client(object):
    client_pools = {}

    def __init__(self, url, timeout, conn_timeout_callback, soc_id, signal_ping = False):
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
        # check for new message every 0.1 sec
        # self.mesg_check_callback = PeriodicCallback(self.count_tick, 800)
        # self.mesg_check_callback.start()

        def on_message(ws, message):
            """
            Prints the incoming message from the server.

            :param ws: a WebSocketApp
            :param message: json with 'text' field to be printed
            """
            self.state.append(message)
            print('recived msg ... ', self.soc_id)

            # incoming_message = json.loads(message)
            # if incoming_message['text'].lower() not in  __BALCK_LIST_MSG:
            #     self.state.append(incoming_message)


        def on_error(ws, error):
            """
            Prints an error, if occurs.

            :param ws: WebSocketApp
            :param error: An error
            """
            print(error)


        def on_close(ws):
            """
            Cleanup before closing connection.

            :param ws: WebSocketApp
            """
            # Reset color formatting if necessary
            print("\033[0m")
            print("Connection closed")


        def _run(ws):
            """
            Takes user input and sends it to a websocket.

            :param ws: websocket.WebSocketApp
            """
            while self.timeout_counter < self.timeout:
                if len(self.out_state) == 0:
                    continue
                x = self.out_state.pop(0)
                data = {}
                data['id'] = self.soc_id
                data['text'] = x
                json_data = json.dumps(data)
                ws.send(json_data)
                if x == "[DONE]":
                    break
            print('client disconnected :', self.soc_id)
            self._conn_timeout_callback(self.soc_id)
            ws.close()


        def on_open(ws):
            """
            Starts a new thread that loops, taking user input and sending it to the websocket.

            :param ws: websocket.WebSocketApp that sends messages to a websocket server
            """
            threading.Thread(target=_run, args=(ws, )).start()
            threading.Thread(target=self.count_tick, args=()).start()

        self.ws = websocket.WebSocketApp(self.url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self.ws.on_open = on_open

        Client.client_pools[self.soc_id] = self
        print('added to self client_pools ...', self.soc_id)
        self.run_client_forever()
        
    def run_client_forever(self):
        print('running websocket client server ... ', self.soc_id)
        self.ws.run_forever()

    def count_tick(self):
        while True:
            if self.timeout + 1 > self.timeout_counter:
                self.timeout_counter += 1
            else:
                break
            time.sleep(1)


def _signal_done(ws):
    json_data = json.dumps({'text': '[DONE]'})
    ws.send(json_data)

PORT =  os.environ.get('PORT', 10001)
SOK_TIMEOUT = os.environ.get('SOK_TIMEOUT',60 *1)


def _conn_cleanup_fn(_id):
    """
    id of client socket to clean up the resourcses associated with it
    """
    del Client.client_pools[_id]
    gc.collect()

def _get_client_with_id(_id):
    print('checking for ... ', _id)
    while True:
        # print('check ... inside ') 
        if Client.client_pools.get(_id):
            break
    print('checked id ... ',_id)
    return Client.client_pools.get(_id)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = None

class Item(BaseModel):
    text: str
    _id: Optional[str] = None

class UserInDB(User):
    hashed_password: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token/", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
async def hello():
    return {"message": "This is BlenderBot chat service."}


@app.post("/interact/")
async def chat(item: Item, current_user: User = Depends(get_current_active_user)):
    item_dict = item.dict()

    n_id = _get_rand_id()
    if item_dict.get('_id'):
        ws = Client.client_pools.get(item_dict['_id'])
        if item_dict.get('_id') in Client.client_pools:
            n_id = item_dict.get('_id')
        else:
            threading.Thread(target = Client, args = ("ws://localhost:{}/websocket".format(PORT), SOK_TIMEOUT, _conn_cleanup_fn, n_id, )).start()
            ws = _get_client_with_id(n_id)
            item_dict['_id'] = n_id
    else:
        threading.Thread(target = Client, args = ("ws://localhost:{}/websocket".format(PORT), SOK_TIMEOUT, _conn_cleanup_fn, n_id, )).start()
        ws = _get_client_with_id(n_id)
        item_dict['_id'] = n_id
    
    ws.out_state.append(item_dict['text'])

    while True:
        if len(ws.state) > 0:
            item_dict['bot_reply'] = ws.state.pop(0)
            break
        
    return item_dict
