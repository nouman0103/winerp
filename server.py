from websocket_server import WebsocketServer
from .types import PayloadTypes
import json


class Server:
    def __init__(self, port=13254):
        self.websocket = WebsocketServer(host='127.0.0.1', port=port)
        self.websocket.set_fn_new_client(self.__on_client_connect)
        self.websocket.set_fn_message_received(self.__on_message)
        self.websocket.set_fn_client_left(self.__on_client_disconnect)

        self.active_clients = {}
        self.pending_verification = {}
        
    def __on_client_connect(self, client, server):
        print("new client:", client["address"][1])
        self.pending_verification[client["address"][1]] = client

    def __on_client_disconnect(self, client, server):
        print("client disconnect:", client["address"][1])
        for cid, each_client in self.active_clients.items():
            if each_client["id"] == client["address"][1]:
                del self.active_clients[cid]
                return

        if client["address"][1] in self.pending_verification:
            del self.pending_verification[client["address"][1]]
        
    def __on_message(self, client, server, msg):
        msg = json.loads(msg)
        if msg["type"] == PayloadTypes.verification:
            if msg["id"] in self.active_clients:
                server.send_message(client, {
                    "type": PayloadTypes.error,
                    "details": "Already Authorized"}
                )

            elif client["address"][1] in self.pending_verification:
                print("client verified:", client["address"][1])
                self.active_clients[msg["id"]] = {"client": client, "id": client["address"][1]}
                del self.pending_verification[client["address"][1]]
                server.send_message(client, json.dumps({
                    "type": PayloadTypes.success,
                    "details": "Authorized"})
                )
        if msg["type"] == PayloadTypes.request:
            print(msg, self.active_clients.keys())
            source = msg["id"]
            destination = msg["destination"]
            if source is destination:
                server.send_message(client, json.dumps({
                    "type": PayloadTypes.error,
                    "details": "Source and Destination cannot be same!"})
                )

            elif destination not in self.active_clients:
                server.send_message(client, json.dumps({
                    "type": PayloadTypes.error,
                    "details": "Destination could not be found!"})
                )
            
            


    def start(self):
        print("Started WS")
        self.websocket.run_forever()
        
        """
        server.set_fn_client_left(client_left)
        server.set_fn_message_received(new_msg)
        server.run_forever()"""
        
