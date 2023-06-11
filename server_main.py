from tinychat.network import PORT, ServerSocket
from tinychat.server import Server
from tinychat.gui import AppGui

from queue import Queue
from tkinter import Tk


def handle_exception(exc):
    pass  # print(exc)


main_queue = Queue()
socket = ServerSocket(PORT, main_queue, handle_exception)
server = Server(socket, main_queue)


def main():
    root = Tk()
    root.title("Chat - Server")
    ui = AppGui(root, server.userinput, server.exit)
    server.ui = ui

    socket.open()
    server.start()

    root.mainloop()


if __name__ == "__main__":
    main()
