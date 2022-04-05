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
            json.dumps(message if isinstance(message, dict) else message.to_dict())
        )

    def __send_error(self, client, details):
        self.websocket.send_message(
            client,
            json.dumps({"type":Payloads.error, "error": details})
        )

    def __on_message(self, client, server, msg):
        msg = WsMessage(json.loads(msg))
        if msg.type.verification:
            if msg.id in self.active_clients:
                self.__send_error(client, "Already Authorized")

            elif client["address"][1] in self.pending_verification:
                logger.info(f"Client verified with connection id {client['address'][1]} and local id {msg.id}")
                self.active_clients[msg.id] = {"client": client, "id": client["address"][1]}
                del self.pending_verification[client["address"][1]]
                self.__send_message(client, {
                    "type": Payloads.success,
                    "data": {"details": "Authorized"}}
                )
        else:
            if client["address"][1] in self.pending_verification:
                logger.info('Unverified client tried to send message')
                self.__send_error(client, "Not Authorized")
                return

        if msg.type.request:
            logger.info(f"Received Request Message from client {client['address'][1]}")
            if msg.id is msg.destination:
                self.__send_error(client, "Source and Destination cannot be same!")

            elif msg.destination not in self.active_clients:
                self.__send_error(client, "Destination could not be found!")

            else:
                logger.info("Request Message Forwarding")
                self.__send_message(
                    self.active_clients[msg.destination]["client"],
                    {
                        "type": Payloads.request,
                        "id": msg.destination,
                        "destination": msg.id,
                        "route": msg.route,
                        "data": msg.data,
                        "uuid": msg.uuid,
                    }
                )
                logger.info("Request Message Forwarded")

        if msg.type.response:
            logger.info(f"Received Response Message from client {client['address'][1]}")
            if msg.destination not in self.active_clients:
                self.__send_error(client, "Destination could not be found!")
            logger.info("Forwarding Response to requester")
            self.__send_message(
                self.active_clients[msg.destination]["client"],
                {
                    "type": Payloads.response,
                    "id": msg.id,
                    "destination": msg.destination,
                    "data": msg.data,
                    "uuid": msg.uuid
                }
            )
            logger.info("Response forwarded")
            
            
    def start(self):
        logger.info(f"Started Websocket Server")
        self.websocket.run_forever()
        
        """
        server.set_fn_client_left(client_left)
        server.set_fn_message_received(new_msg)
        server.run_forever()"""
