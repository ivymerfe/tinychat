from tinychat.network import BroadcastSocket
from threading import Thread, Event
import json


class ServerMonitor:
    def __init__(self, server):
        self.server = server

        self.udp_socket = BroadcastSocket(self.handle_message, self.handle_exception)

        self._bc_thread = None
        self._bc_event = Event()

    def start(self):
        self.udp_socket.create()

        self._bc_thread = Thread(target=self.broadcast_tf)
        self._bc_thread.start()

        self.udp_socket.listen()

    def broadcast_tf(self):
        while not self._bc_event.wait(4):
            self.broadcast()

    def broadcast(self):
        info_p = {
            'type': 'server_info',
            'name': self.server.server_name,
            'desc': self.server.server_desc
        }
        info_pc = json.dumps(info_p).encode('utf8')
        self.udp_socket.broadcast(info_pc)

    def handle_message(self, addr, data):
        pass  # temporarily

    def close(self):
        if self._bc_thread:
            self._bc_event.set()
            self._bc_thread.join()

        self.udp_socket.close()

    def handle_exception(self, exc):
        pass  # print(exc)
