from tinychat.network import PORT, ClientSocket
from tinychat.client import ChatClient
from tinychat.gui import AppGui

from queue import Queue
from tkinter import Tk


def handle_exception(exc):
    pass  # print(exc)


main_queue = Queue()
socket = ClientSocket(PORT, main_queue, handle_exception)
client = ChatClient(socket, main_queue)


def main():
    root = Tk()
    root.title("Chat - Client")
    ui = AppGui(root, client.userinput, client.exit)
    client.ui = ui

    client.start()
    root.mainloop()


if __name__ == "__main__":
    main()
