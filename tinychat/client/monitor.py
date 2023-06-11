from tinychat.network import BroadcastSocket
from collections import namedtuple
from threading import Thread, Event
import json

server_t = namedtuple("server", ("addr", "name", "desc"))


class ClientMonitor:
    def __init__(self):
        self.local_servers = dict()
        # self.global_servers = dict()  # more timeout

        self.udp_socket = BroadcastSocket(self.handle_message, self.handle_exception)

        self._update_thread = None
        self._update_event = Event()

        self._ping_thread = None
        self._ping_event = Event()

    def start(self):
        self._update_thread = Thread(target=self.update)
        self._update_thread.start()

        self.udp_socket.create()

        # self.ping_thread = Thread(target=self.ping_global)
        # self.ping_thread.start()

        self.udp_socket.listen()

    def get(self):
        return self.local_servers

    def update(self):
        while not self._update_event.wait(1):
            remove_addrs = []
            for addr, (server, time) in self.local_servers.items():
                if time == 5:
                    remove_addrs.append(addr)
                else:
                    self.local_servers[addr] = server, time + 1

            for addr in remove_addrs:
                del self.local_servers[addr]

    def ping_global(self):
        pass  # notimpl

    def handle_message(self, addr, data):
        packet = json.loads(data.decode('utf8'))
        if packet['type'] == 'server_info':
            name = packet['name']
            desc = packet['desc']

            self.local_servers[addr] = server_t(addr, name, desc), 0  # remove servers that stop sending ping

    def close(self):
        if self._update_thread:
            self._update_event.set()
            self._update_thread.join()

        if self._ping_thread:
            self._ping_event.set()
            self._ping_thread.join()

        self.udp_socket.close()

    def handle_exception(self, exc):
        pass  # print(exc)
