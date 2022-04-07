from websocket_server import WebsocketServer
from .lib.message import WsMessage
from .lib.payload import Payloads, MessagePayload
from .lib.errors import *
import json

import logging
logger = logging.getLogger(__name__)


class Server:
    def __init__(self, port=13254):
        logger.setLevel(logging.INFO)
        self.websocket = WebsocketServer(host='127.0.0.1', port=port)
        self.websocket.set_fn_new_client(self.__on_client_connect)
        self.websocket.set_fn_message_received(self.__on_message)
        self.websocket.set_fn_client_left(self.__on_client_disconnect)
        self.console_output = True
        self.active_clients = {}
        self.pending_verification = {}
        
    def __on_client_connect(self, client, server):
        logger.info("Client connected with id %s" % client['address'][1])
        self.pending_verification[client["address"][1]] = client

    def __on_client_disconnect(self, client, server):
        logger.info("Client disconnected with id %s" % client['address'][1])
        for cid, each_client in self.active_clients.items():
            if each_client["id"] == client["address"][1]:
                del self.active_clients[cid]
                return

        if client["address"][1] in self.pending_verification:
            del self.pending_verification[client["address"][1]]
    
    def __send_message(self, client, message):
        if not isinstance(message, dict):
            message = message.to_dict()
        self.websocket.send_message(
            client,
            json.dumps(message)
        )

    def __send_error(self, client, payload):
        if not isinstance(payload, dict):
            payload = payload.to_dict()

        self.websocket.send_message(
            client,
            json.dumps(payload)
        )

    def __on_message(self, client, server, msg):
        msg = WsMessage(json.loads(msg))
        payload = MessagePayload().from_message(msg)
        if msg.type.verification:
            if msg.id in self.active_clients:
                payload.type = Payloads.error
                payload.data = "Already authorized."
                payload.traceback = "Already authorized."
                self.__send_error(client, payload)

            elif client["address"][1] in self.pending_verification:
                logger.info("Client verified with connection id %s and local id %s" % (client['address'][1], msg.id))
                self.active_clients[msg.id] = {"client": client, "id": client["address"][1]}
                del self.pending_verification[client["address"][1]]
                payload.type = Payloads.success
                payload.data = "Authorized."
                self.__send_message(client, payload)
        else:
            if client["address"][1] in self.pending_verification:
                logger.info('Unverified client tried to send message')
                payload.type = Payloads.error
                payload.data = "Not authorized."
                payload.traceback = "Not authorized."
                self.__send_error(client, payload)
                return

        if msg.type.request:
            logger.debug("Received Request Message from client %s" % client['address'][1])
            if msg.id == msg.destination:
                payload.type = Payloads.error
                payload.data = "Source and destination are the same."
                payload.traceback = "Source and destination are the same."
                self.__send_error(client, payload)

            elif msg.destination not in self.active_clients:
                payload.type = Payloads.error
                payload.data = "Destination not found."
                payload.traceback = "Destination not found."
                self.__send_error(client, payload)

            else:
                payload.type = Payloads.request
                payload.id = msg.destination
                payload.destination = msg.id
                self.__send_message(
                    self.active_clients[msg.destination]["client"],
                    payload
                )
                logger.debug("Request Message Forwarded to %s" % self.active_clients[msg.destination]["client"]['address'][1])

        if msg.type.response or msg.type.error:
            logger.debug("Received Response Message from client %s" % client['address'][1])
            if msg.destination not in self.active_clients:
                self.__send_error(client, "Destination could not be found!", uuid=msg.uuid)

            payload.type = Payloads.response if msg.type.response else Payloads.error

            self.__send_message(
                self.active_clients[msg.destination]["client"],
                payload
            )
            logger.debug("Response forwarded to %s" % self.active_clients[msg.destination]["client"]['address'][1])
            
            
    def start(self):
        logger.info("Started Websocket Server")
        self.websocket.run_forever()
