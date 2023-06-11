from .const import UDP_PORT, BROADCAST_ADDR, DATAGRAM_SIZE
from socket import *
from select import select
from threading import Thread
import struct


class BroadcastSocket:
    def __init__(self, network_handler, exception_handler):
        self.handle_network = network_handler
        self.handle_exception = exception_handler

        self.pbuf = bytearray()

        self.listen_socket = None
        self.broadcast_socket = None

        self._listening = True
        self._listen_thread = None

    def create(self):
        self.listen_socket = socket(AF_INET, SOCK_DGRAM)
        self.listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        self.broadcast_socket = socket(AF_INET, SOCK_DGRAM)
        self.broadcast_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    def listen(self):
        if not self.listen_socket or self.listen_socket.fileno() == -1:
            return

        try:
            self.listen_socket.bind(('', UDP_PORT))

            self._listening = True
            self._listen_thread = Thread(target=self._threadmain)
            self._listen_thread.start()

        except error as e:
            self.handle_exception(e)

    def _threadmain(self):
        while self._listening:
            rd, wt, exc = select([self.listen_socket], [], [])

            if rd:
                if self.listen_socket.fileno() == -1:
                    break

                self.receive()

    def broadcast(self, data):
        if not self.broadcast_socket or self.broadcast_socket.fileno() == -1:
            return False

        size = struct.pack(">I", len(data))

        try:
            self.broadcast_socket.sendto(size + data, (BROADCAST_ADDR, UDP_PORT))
            return True
        except error as e:
            self.handle_exception(e)
            return False

    def receive(self):
        try:
            rcdata, addr = self.listen_socket.recvfrom(DATAGRAM_SIZE)
            data = self.pbuf + rcdata

            size = struct.unpack(">I", data[:4])[0]
            packet = data[4:size + 4]

            self.pbuf = data[size + 4:]

            self.handle_network(addr, packet)

        except error as e:
            self.handle_exception(e)

    def close(self):
        self._listening = False

        if self.listen_socket:
            self.listen_socket.close()

        if self.broadcast_socket:
            self.broadcast_socket.close()

        if self._listen_thread:
            self._listen_thread.join()
