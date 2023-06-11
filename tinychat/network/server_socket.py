from .const import PACKET_SIZE, LOCAL_IP
from socket import *
from select import select
from threading import Thread
import struct


class ServerSocket:
    def __init__(self, port, queue, exception_handler):
        self.PORT = port

        self.queue = queue
        self.exception = exception_handler

        self.addr = None
        self._socket = None

        self.clients = list()

        self._running = False
        self._socket_thread = None

    def open(self):
        self._socket = socket(AF_INET, SOCK_STREAM)
        self._socket.setblocking(False)
        self._socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # add reuseaddr socket option

        self.addr = (LOCAL_IP, self.PORT)

        try:
            self._socket.bind(self.addr)
            self._socket.listen()
            self.clients.append(self._socket)
            self.queue.put(("server_start", None))
        except error as e:
            self.queue.put(("server_start", e))
            return

        self._running = True
        self._socket_thread = Thread(target=self._threadmain)
        self._socket_thread.start()

    def _threadmain(self):
        while self._running:
            rd, wt, exc = select(self.clients, [], [])

            if rd:
                for s in rd:
                    if s is self._socket:
                        if s.fileno() == -1:
                            break

                        client, addr = s.accept()
                        self.clients.append(client)
                        self.queue.put(("connection_request", client, addr))
                    else:
                        if s.fileno() == -1:
                            self.clients.remove(s)
                            continue

                        try:
                            data = s.recv(PACKET_SIZE)
                        except ConnectionResetError:
                            self.queue.put(("disconnected", s.getpeername()))
                            self.clients.remove(s)
                            continue

                        if not data:
                            self.queue.put(("disconnected", s.getpeername()))
                            self.clients.remove(s)
                            continue

                        self.receive(s, data)

    def send(self, s, data):
        try:
            size = len(data)

            if size > PACKET_SIZE - 4:
                self.exception("data len > packet size")
                return False

            size_b = struct.pack(">I", size)
            s.send(size_b + data)

            return True
        except error as e:
            self.exception(e)
            return False

    def receive(self, sock, rc):
        try:
            data = rc
            while data:
                size = struct.unpack(">I", data[:4])[0]

                pdata = data[4:size + 4]
                data = data[size + 4:]

                self.queue.put(("packet", sock, sock.getpeername(), pdata))

        except struct.error as e:
            self.exception(e)

    def kick(self, s):
        self.queue.put(("disconnected", s.getpeername()))
        s.close()

    def close(self):
        self._running = False

        if self._socket:
            self._socket.close()

        if self._socket_thread:
            self._socket_thread.join()
            self._socket_thread = None
