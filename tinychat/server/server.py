from .monitor import ServerMonitor
from .user import *
from .channel import *
from tinychat.gui.colors import set_color

from threading import Thread
import json
import re
import os

cmd_pat = r"^/.+ ?(.+)*$"


class Server:
    def __init__(self, socket, queue):
        self.socket = socket
        self.queue = queue

        self.ui = None

        self.visible = True
        self.server_name = "Server1"
        self.server_desc = "A server for testing"

        self.monitor = ServerMonitor(self)

        self.proc_thread = None

        self.userlist = UserList()
        self.uconnections = ConnectionList(self.userlist)

        self.channels = ChannelList(self)

        self.global_channel = Channel(self, "__global__", "Server")
        self.connected_channel = self.global_channel

        self.channels.add_channel(self.global_channel)

        self.dms = DirectMessages()

        self.load_settings()

    settings_path = os.path.abspath(os.path.join(os.pardir, "settings.json"))

    def load_settings(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    settings = json.loads(f.read())
                    server_settings = settings['server']

                    self.visible = server_settings['visible']
                    self.server_name = server_settings['server_name']
                    self.server_desc = server_settings['server_desc']

            except (FileExistsError, json.JSONDecodeError, KeyError):
                pass

    def save_settings(self):
        settings = dict()

        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r') as f:
                    settings = json.loads(f.read())

        except (FileExistsError, json.JSONDecodeError, KeyError):
            pass

        with open(self.settings_path, 'w') as f:
            server_settings = dict()

            server_settings['visible'] = self.visible
            server_settings['server_name'] = self.server_name
            server_settings['server_desc'] = self.server_desc
            settings['server'] = server_settings

            f.write(json.dumps(settings))

    def start(self):
        self.proc_thread = Thread(target=self.event_proc)
        self.proc_thread.start()

        self.monitor.start()
        self.monitor.broadcast()

    def event_proc(self):
        for event in iter(self.queue.get, 'exit'):
            event_type = event[0]
            if event_type == "server_start":
                self.started(event[1])
            elif event_type == "connection_request":
                self.conn_request(event[1], event[2])
            elif event_type == "packet":
                self.handle_network(event[1], event[2], event[3])
            elif event_type == "udp_packet":
                pass  # We dont handle udp
            elif event_type == "disconnected":
                self.disconnected(event[1])
            elif event_type == "server_stop":
                self.stopped()

    # rpc

    def rpc_send_by_addr(self, addr, data):
        uconn = self.uconnections.find_by_addr(addr, True)
        if uconn:
            self.socket.send(uconn.socket, data.encode('utf8'))

    def rpc_send_by_uname(self, uname, data):
        uconn = self.uconnections.find_by_uname(uname)
        if uconn:
            self.socket.send(uconn.socket, data.encode('utf8'))

    def rpc_broadcast_packet(self, data, bc_all=False):
        data = data.encode('utf8')

        for usock, _, _ in self.uconnections:
            self.socket.send(usock, data)

        if bc_all:
            for usock, _, _ in self.uconnections.temp_connections():
                self.socket.send(usock, data)

    def rpc_kick_by_addr(self, addr):
        uconn = self.uconnections.find_by_addr(addr, True)
        if uconn:
            self.socket.kick(uconn.socket)

    def rpc_kick_by_uname(self, uname):
        uconn = self.uconnections.find_by_uname(uname)
        if uconn:
            self.socket.kick(uconn.socket)

    def send_packet(self, socket, packet):
        db = json.dumps(packet).encode('utf8')
        self.socket.send(socket, db)

    def broadcast_packet(self, packet, ignored=None):
        db = json.dumps(packet).encode('utf8')

        for usock, uaddr, _ in self.uconnections:
            if uaddr != ignored:
                self.socket.send(usock, db)

    def send_servermsg(self, socket, msg):
        packet = {
            'type': 'server_message',
            'text': msg
        }
        db = json.dumps(packet).encode('utf8')
        self.socket.send(socket, db)

    def broadcast_servermsg(self, msg):
        packet = {
            'type': 'server_message',
            'text': msg
        }
        db = json.dumps(packet).encode('utf8')

        for usock, _, _ in self.uconnections:
            self.socket.send(usock, db)

    def started(self, err=None):
        if not err:
            self.ui.write(set_color(f"Server running at {self.socket.addr[0]}", 'green'))
        else:
            self.ui.write(set_color(f"Failed to start a server: {err}", 'orangered'))

            self.stop()

    def stopped(self):
        self.broadcast_servermsg("+orangered(Server closed)")

    def conn_request(self, socket, addr):
        # check for username and address
        user = self.userlist.find_by_addr(addr)

        if user:
            if utag_banned in user.tags:
                msg = "+orangered(You are banned!)"
                reason = user.utaginfo['banned']
                if reason:
                    msg += f"\n+orangered(Reason: {reason})"

                self.send_servermsg(socket, msg)
                self.socket.kick(socket)
                return

        self.uconnections.create_temp_connection(socket, addr)

    def handle_message(self, socket, addr, packet):
        try:
            uconn = self.uconnections.find_by_addr(addr)
            if not uconn:
                return
            user = uconn.user

            if utag_muted in user.tags:
                msg = "+orangered(You are muted!)"
                reason = user.utaginfo['muted']
                if reason:
                    msg += f"\n+orangered(Reason: {reason})"

                self.send_servermsg(socket, msg)
                return

            channel = self.channels.find_channel(packet['channel'])

            if not channel:
                return

            text = packet['text']

            if re.match(cmd_pat, text):
                channel.command(user, text)
            else:
                channel.write_message(user, text)

        except (json.JSONDecodeError, KeyError):
            pass

    def handle_auth(self, socket, addr, packet):
        try:
            username, username_p = User.filter_username(packet['username'])

            if not 2 < len(username_p) < 15:
                login_p = {
                    'type': 'authresp',
                    'success': False,
                    'message': 'Bad username'
                }
                self.send_packet(socket, login_p)
                return

            if username_p.lower() == "server":
                login_p = {
                    'type': 'authresp',
                    'success': False,
                    'message': 'Hahah, funny'
                }
                self.send_packet(socket, login_p)
                return

            user = self.userlist.find_by_name(username_p)
            if user and user.addr != addr[0]:
                login_p = {
                    'type': 'authresp',
                    'success': False,
                    'message': 'This user already registered'
                }
                self.send_packet(socket, login_p)
                return

            rename = False
            old_name = ""

            uconn = self.uconnections.find_by_addr(addr)
            if uconn:
                rename = True
                old_name = uconn.user.username

                if old_name == username:
                    return

            user = self.userlist.find_by_addr(addr)
            if user:
                user.set_username(username, username_p)
            else:
                user = User(addr)
                user.set_username(username, username_p)
                self.userlist.add_user(user)

            if not uconn:
                uconn = self.uconnections.create_connection(socket, addr)

            login_p = {
                'type': 'authresp',
                'success': True,
                'username': username
            }
            self.send_packet(socket, login_p)

            if rename:
                self.channels.user_rename(user, old_name)
            else:
                self.channels.user_joined(uconn, "__global__")
        except (json.JSONDecodeError, KeyError):
            pass

    def direct_message(self, socket, addr, packet):
        pass

    def handle_network(self, socket, addr, pdata):
        packet = json.loads(pdata.decode('utf8'))

        try:
            if packet['type'] == 'message':
                self.handle_message(socket, addr, packet)
            elif packet['type'] == 'direct_message':
                self.direct_message(socket, addr, packet)
            elif packet['type'] == 'login':
                self.handle_auth(socket, addr, packet)

        except (json.JSONDecodeError, KeyError):
            pass

    def disconnected(self, addr):
        self.uconnections.destroy_temp_connection(addr)
        uconn = self.uconnections.find_by_addr(addr)

        if uconn:
            self.uconnections.destroy_connection(addr)

            user = uconn.user

            self.channels.user_disconnected(user)

    def userinput(self, text):
        if re.match(cmd_pat, text):
            self.connected_channel.command("Server", text)
        else:
            self.connected_channel.write_message("Server", text)

    def stop(self):
        self.queue.put(('server_stop',))
        self.queue.put('exit')

        if self.proc_thread:
            self.proc_thread.join()
            self.proc_thread = None

        self.socket.close()
        self.monitor.close()

    def exit(self):
        self.stop()
        self.save_settings()
