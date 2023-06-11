from .const import PACKET_SIZE
from socket import *
from select import select
from threading import Thread, Event
import struct


class ClientSocket:
    def __init__(self, port, queue, exception_handler):
        self.PORT = port

        self.queue = queue
        self.exception = exception_handler

        self._socket = None

        self._running = False
        self._socket_thread = None
        self._sconnected = Event()

    def connect(self, addr):
        self.disconnect()
        server = (addr, self.PORT)

        try:
            self._socket = socket(AF_INET, SOCK_STREAM)
            self._socket.settimeout(1)
            self._socket.connect(server)
            self._socket.settimeout(None)
            self.queue.put(("connected", server, None))

            self._running = True
            self._sconnected.set()

            if not self._socket_thread:
                self._socket_thread = Thread(target=self._threadmain)
                self._socket_thread.start()
        except error as e:
            self.queue.put(("connected", server, e))
            self._socket.close()

    def _threadmain(self):
        while self._running:
            while self._sconnected.wait() and self._running:  # DO NOT CHANGE ORDER
                rd, wt, exc = select([self._socket], [], [])

                if rd:
                    if self._socket.fileno() == -1:  # Do break, do not callback on disconnect command
                        break

                    try:
                        data = self._socket.recv(PACKET_SIZE)
                    except ConnectionResetError:
                        break

                    if not data:
                        break

                    self.receive(data)

            self.queue.put(("disconnected",))
            self._sconnected.clear()
            self._socket.close()

    def send(self, data):
        try:
            size = len(data)

            if size > PACKET_SIZE - 4:
                self.exception("data len > packet size")
                return False

            size_b = struct.pack(">I", size)
            self._socket.send(size_b + data)

            return True
        except error as e:
            self.exception(e)
            return False

    def receive(self, rc):
        try:
            data = rc
            while data:
                size = struct.unpack(">I", data[:4])[0]

                pdata = data[4:size + 4]
                data = data[size + 4:]

                self.queue.put(("packet", pdata))

        except struct.error as e:
            self.exception(e)

    def disconnect(self):
        self._sconnected.clear()

        if self._socket:
            self._socket.close()

    def exit(self):
        self._running = False
        self._sconnected.set()

        if self._socket:
            self._socket.close()

        if self._socket_thread:
            self._socket_thread.join()
            self._socket_thread = None
