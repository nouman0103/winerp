from websocket_server import WebsocketServer
from .lib.message import WsMessage
from .lib.payload import Payloads
import json

import logging
logger = logging.getLogger(__name__)
logging.basicConfig()

class Server:
    def __init__(self, port=13254):
        logger.setLevel(logging.DEBUG)
        self.websocket = WebsocketServer(host='127.0.0.1', port=port)
        self.websocket.set_fn_new_client(self.__on_client_connect)
        self.websocket.set_fn_message_received(self.__on_message)
        self.websocket.set_fn_client_left(self.__on_client_disconnect)

        self.active_clients = {}
        self.pending_verification = {}
        
    def __on_client_connect(self, client, server):
        logger.info(f"Client connected with id {client['address'][1]}")
        self.pending_verification[client["address"][1]] = client

    def __on_client_disconnect(self, client, server):
        logger.info(f"Client disconnected with id {client['address'][1]}")
        for cid, each_client in self.active_clients.items():
            if each_client["id"] == client["address"][1]:
                del self.active_clients[cid]
                return

        if client["address"][1] in self.pending_verification:
            del self.pending_verification[client["address"][1]]
    
    def __send_message(self, client, message):
        self.websocket.send_message(
            client,
            message if isinstance(message, dict) else message.to_dict()
        )

    def __send_error(self, client, details):
        self.websocket.send_message(
            client,
            {"type":Payloads.error, "details": details}
        )

    def __on_message(self, client, server, msg):
        msg = WsMessage(json.loads(msg))
        if msg.type.verification:
            if msg.id in self.active_clients:
                self.__send_error(client, "Already Authorized")

            elif client["address"][1] in self.pending_verification:
                logger.info(f"Client verified with id {client['address'][1]}")
                print("client verified:", client["address"][1])
                self.active_clients[msg.id] = {"client": client, "id": client["address"][1]}
                del self.pending_verification[client["address"][1]]
                self.__send_message(client, {
                    "type": Payloads.success,
                    "details": "Authorized"}
                )
        if msg.type.request:
            if msg.id is msg.destination:
                self.__send_error(client, "Source and Destination cannot be same!")

            elif msg.destination not in self.active_clients:
                self.__send_error(client, "Destination could not be found!")

            else:
                self.__send_message(
                    self.active_clients[msg.destination],
                    {
                        "type": Payloads.request,
                        "id": msg.destination,
                        "destination": msg.id,
                        "route": msg.route,
                        "args": msg.args,
                        "kwargs": msg.kwargs,
                        "uuid": msg.uuid,
                    }
                )

        if msg.type.response:
            if msg.destination not in self.active_clients:
                self.__send_error(client, "Destination could not be found!")

            self.__send_message(
                self.active_clients[msg.destination],
                {
                    "type": Payloads.request,
                    "id": msg.destination,
                    "destination": msg.id,
                    "route": msg.route,
                    "data": msg.data,
                    "uuid": msg.uuid
                }
            )
            
            


    def start(self):
        logger.info(f"Started Websocket Server")
        self.websocket.run_forever()
        
        """
        server.set_fn_client_left(client_left)
        server.set_fn_message_received(new_msg)
        server.run_forever()"""
        
