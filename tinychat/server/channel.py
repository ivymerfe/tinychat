from collections import namedtuple
from .commands import Commands
import json

channel_user = namedtuple("channel_user", ("uconn", "user", "channels", "channel_rights"))


class Channel:
    def __init__(self, server, name, admin):
        self.server = server
        self.userlist = server.userlist
        self.channels = server.channels

        self.name = name
        self.admin_user = admin
        self.second_admins = list()

        self.userlimit = -1

        self.hidden = False

        self.users = list()

        self.whitelist_enabled = False
        self.whitelist = list()
        self.blacklist = list()

        self.write_right = None

        self.message_log = list()

    def get_connections(self):
        return [user.uconn for user in self.users]

    def find_user(self, user):
        for c_user in self.users:
            if c_user.user == user:
                return c_user
        return None

    def find_user_by_name(self, uname):
        for c_user in self.users:
            if c_user.user.username_p == uname:
                return c_user
        return None

    def send_packet(self, user, packet):
        db = json.dumps(packet).encode('utf8')
        socket = self.server.socket
        socket.send(user.uconn.socket, db)

    def send_servermsg(self, user, msg, channel_data=False):
        if user == "Server":
            self.ui_message(msg, channel_data)
        else:
            if channel_data:
                packet = {
                    'type': 'server_message',
                    'text': msg,
                    'channel': self.name
                }
                self.send_packet(user, packet)
            else:
                packet = {
                    'type': 'server_message',
                    'text': msg,
                    'channel': None
                }
                self.send_packet(user, packet)

    def broadcast_packet(self, packet, excepted=None):
        db = json.dumps(packet).encode('utf8')
        socket = self.server.socket

        if excepted:
            for usock, _, user in self.get_connections():
                if user not in excepted:
                    socket.send(usock, db)
        else:
            for usock, _, _ in self.get_connections():
                socket.send(usock, db)

    def broadcast_servermsg(self, msg, channel_data=False):
        if channel_data:
            self.broadcast_packet({'type': 'server_message', 'text': msg, 'channel': self.name})
        else:
            self.broadcast_packet({'type': 'server_message', 'text': msg, 'channel': None})
        self.ui_message(msg, channel_data)

    def ui_message(self, msg, channel_data=False):
        if self.name == "__global__" or self is self.server.connected_channel:
            if channel_data:
                if self.name == "__global__":
                    self.server.ui.write(f"+black([GLOBAL]) {msg}")
                else:
                    self.server.ui.write(f"+black([{self.name}]) {msg}")
            else:
                self.server.ui.write(msg)

    def user_joined(self, c_user):
        user = c_user.user

        # SEND MESSAGE LOG
        result = True

        if user in self.blacklist:
            self.send_servermsg(c_user, "+orangered(You blocked from this channel!)")
            result = False

        if len(self.users) >= self.userlimit != -1 and c_user not in self.second_admins:
            self.send_servermsg(c_user, "+orangered(Maximum users connected!)")
            result = False

        if self.whitelist_enabled and user not in self.whitelist and c_user not in self.second_admins:
            self.send_servermsg(c_user, "+orangered(You cannot join this channel!)")
            result = False

        if not result:
            if self.name == "__global__":
                self.server.socket.kick(c_user.uconn.socket)
        else:
            self.users.append(c_user)
            c_user.channels.append(self.name)

            self.send_packet(c_user, {'type': 'channel_set', 'channel': self.name})
            self.broadcast_servermsg(f"{user.username} +green(joined)", True)

    def user_rename(self, c_user, old_name):
        self.broadcast_servermsg(f"{old_name} +green(changed his name to {c_user.user.username})", True)

    def user_left(self, c_user):
        self.broadcast_servermsg(f"{c_user.user.username} +orangered(left)", True)
        self.send_packet(c_user, {'type': 'channel_remove', 'channel': self.name})
        self.users.remove(c_user)

        c_user.channels.remove(self.name)

    def destroy(self):
        self.broadcast_servermsg(f"+orangered(Channel deleted)", True)
        self.broadcast_packet({'type': 'channel_remove', 'channel': self.name})

        if self is self.server.connected_channel:
            self.server.connected_channel = self.server.global_channel

        for user in self.users:
            user.channels.remove(self.name)

        self.users.clear()

    def get_userlist(self):
        if len(self.users) == 0:
            return "+orangered(No users connected)"

        userlist = [f"{user.username} ({user.addr})" for _, user, _, _ in self.users]
        return '\n'.join([f"Users ({len(self.users)}):"] + userlist)

    def write_message(self, user, message):
        if user == "Server":
            if self.name == "__global__":
                self.server.ui.write(f"+black([GLOBAL]) +yellow(Server) : {message}")
            else:
                self.server.ui.write(f"+black([{self.name}]) +yellow(Server) : {message}")

            msg = {
                'type': 'message',
                'text': message,
                'user': "+yellow(Server)",
                'channel': self.name
            }

            self.broadcast_packet(msg)
            return

        c_user = self.find_user(user)

        if c_user:
            if self.write_right and self.write_right not in c_user.channel_rights[self.name]:
                if user != self.admin_user and user not in self.second_admins:
                    self.server.send_servermsg(c_user.uconn.socket, "+orangered(You cannot write in this channel!)")
                    return

            self.message_log.append((user, message))

            if self.name == self.server.connected_channel:
                self.server.ui.write(f"{c_user.user.username} : {message}")

            msg = {
                'type': 'message',
                'text': message,
                'user': c_user.user.username,
                'channel': self.name
            }

            self.broadcast_packet(msg, excepted=[user])

            if self is self.server.connected_channel or self.name == "__global__":
                if self.name == "__global__":
                    self.server.ui.write(f"+black([GLOBAL]) {c_user.user.username} : {message}")
                else:
                    self.server.ui.write(f"+black([{self.name}]) {c_user.user.username} : {message}")
        else:
            uconn = self.server.uconnections.find_by_uname(user.username_p)
            if uconn:
                self.server.send_servermsg(uconn.socket, "+orangered(You are not connected to this channel!)")

    def command(self, user, cmd):
        cmd_s = cmd.split()

        if user != "Server":
            user = self.find_user(user)

        if user == self.admin_user:
            if cmd_s[0] == "/giveadmin":
                self.add_second_admin(cmd_s[1])
            elif cmd_s[0] == "/takeadmin":
                self.remove_second_admin(cmd_s[1])

        if user == self.admin_user or user in self.second_admins:
            if cmd_s[0] == "/whitelist":
                if cmd_s[1] == "on":
                    self.whitelist_on()
                elif cmd_s[1] == "off":
                    self.whitelist_off()
                elif cmd_s[1] == "add":
                    self.whitelist_add(cmd_s[2])
            elif cmd_s[0] == "/userlimit" and cmd_s[1].lstrip('-').isdecimal():
                self.set_userlimit(int(cmd_s[1]))
            elif cmd_s[0] == "/right":
                if cmd_s[1] == "add":
                    self.add_user_right(cmd_s[2], cmd_s[3])
                elif cmd_s[1] == "remove":
                    self.remove_user_right(user, cmd_s[2], cmd_s[3])
                elif cmd_s[1] == "write":
                    self.set_write_right(cmd_s[2])
            elif cmd_s[0] == "/clearlog":
                self.message_log.clear()
                self.broadcast_servermsg("+green(Message log cleared)", True)

            if self.name == "__global__":
                if cmd_s[0] == "/senduser":
                    c_user = self.find_user_by_name(cmd_s[1])
                    channel = self.channels.find_channel(cmd_s[2])
                    if c_user and channel:
                        self.send_servermsg(c_user, f"+green(Sending to channel -> {cmd_s[2]})")
                        self.send_servermsg(user, f"{c_user.user.username} +green(-> {cmd_s[2]})")
                        self.channels.send_user(c_user, channel)

            else:
                pass
            # server can delete channel by name
            # dont delete channels, created by server
            # make hide command
            # TODO - make commands
        if cmd_s[0] == "/userlist":
            if user == "Server":
                self.server.ui.write(self.get_userlist())
            else:
                self.send_servermsg(user, self.get_userlist())
        elif cmd_s[0] == "/channel":
            if cmd_s[1] == "list":
                if user == "Server":
                    self.server.ui.write(self.channels.get_channel_table())
                else:
                    self.send_servermsg(user, self.channels.get_channel_table())
            elif cmd_s[1] == "join":
                self.channel_join(user, cmd_s[2])
            elif cmd_s[1] == "delete" and (user == self.admin_user or user == "Server"):  # TODO - check if global
                self.channels.destroy_channel(self)
            elif cmd_s[1] == "create":
                self.channel_create(user, cmd_s[2])

    def channel_join(self, user, channel_name):
        if user == "Server":
            channel = self.channels.find_channel(channel_name)
            if channel:
                self.server.connected_channel = channel
                self.server.ui.write(f"+green(Successfully connected to channel {channel_name})")
        else:
            channel = self.channels.find_channel(channel_name)
            if channel:
                self.channels.send_user(user, channel)

    def channel_create(self, user, channel_name):
        channel = self.channels.create_channel(user, channel_name)
        if channel:
            if user == "Server":
                self.server.connected_channel = channel
                self.ui_message(f"+green(Created channel {channel_name})")
            else:
                self.send_servermsg(user, f"+green(Created channel {channel_name})")
                self.channels.send_user(user, channel)
        else:
            self.send_servermsg(user, "+orangered(Channel already exists!)")

    def set_userlimit(self, limit):
        self.userlimit = limit
        if limit == -1:
            self.broadcast_servermsg("+green(Userlimit removed)", True)
        else:
            self.broadcast_servermsg(f"+green(Userlimit set to {limit})", True)

    def whitelist_on(self):
        self.whitelist_enabled = True
        self.broadcast_servermsg("+green(Whitelist enabled)", True)

    def whitelist_off(self):
        self.whitelist_enabled = False
        self.whitelist.clear()
        self.broadcast_servermsg("+green(Whitelist disabled)", True)

    def whitelist_add(self, uname):
        user = self.find_user_by_name(uname)
        if user:
            self.whitelist.append(user)
            self.broadcast_servermsg(f"+green({user.username} added to whitelist)", True)

    def add_second_admin(self, uname):
        c_user = self.find_user_by_name(uname)

        if c_user:
            self.second_admins.append(c_user)
            self.broadcast_servermsg(f"+green({c_user.user.username} is now an admin of this channel)", True)

    def remove_second_admin(self, uname):
        c_user = self.find_user_by_name(uname)
        if c_user and c_user in self.second_admins:
            self.second_admins.remove(c_user)
            self.broadcast_servermsg(f"+orangered({c_user.user.username} is no longer an admin)", True)

    def add_user_right(self, uname, right):
        c_user = self.find_user_by_name(uname)

        if c_user:
            if right not in c_user.channel_rights[self.name]:
                c_user.channel_rights[self.name].append(right)
            self.broadcast_servermsg(f"+green(+right:{right} for {uname})", True)

    def remove_user_right(self, admin, uname, right):
        c_user = self.find_user_by_name(uname)

        if c_user:
            if right in c_user.channel_rights[self.name]:
                c_user.channel_rights[self.name].remove(right)
                self.broadcast_servermsg(f"+orangered(-right:{right} for {uname})", True)
            else:
                self.send_servermsg(admin, f"+orangered({uname} doesnt have this right!)")

    def set_write_right(self, right):
        if right == "*":
            self.write_right = None
            self.broadcast_servermsg("+green(Now all users can write to this channel!)", True)
        else:
            self.write_right = right
            self.broadcast_servermsg(f"+green(Only users with right:{right} can write to this channel)", True)

    def blacklist_add_user(self, user):
        self.blacklist.append(user)

    def blacklist_remove_user(self, user):
        self.blacklist.remove(user)

    # ADD CLEAR MESSAGES COMMAND


class ChannelList:
    def __init__(self, server):
        self.server = server
        self.userlist = server.userlist

        self.channels = list()
        self.channel_users = list()

    def get_channel_table(self):
        table = list()
        table.append("+green(Channels:)")

        for channel in self.channels:
            if channel.hidden:
                continue

            admin_name = "+yellow(Server)" if channel.admin_user == "Server" else channel.admin_user.user.username
            connected = len(channel.users)

            if channel.userlimit == -1:
                table.append(f"+black({channel.name}) +green(:    admin - {admin_name}    users - {connected})")
            else:
                table.append(f"+black({channel.name}) +green(:    admin - {admin_name}"
                             f"    users - {connected}/{channel.userlimit}")

        return '\n'.join(table)

    def add_channel(self, channel):
        self.channels.append(channel)

    def create_channel(self, admin_user, name):
        if not self.find_channel(name):
            chan = Channel(self.server, name, admin_user)
            self.channels.append(chan)
            return chan

    def destroy_channel(self, channel):
        channel.destroy()
        self.channels.remove(channel)

    def send_user(self, user, channel):
        last_channel = None

        if len(user.channels) == 2:
            last_channel = self.find_channel(user.channels[1])

        if channel:
            if last_channel:
                if user == last_channel.admin_user:
                    last_channel.destroy()
                    self.channels.remove(last_channel)
                else:
                    last_channel.user_left(user)

            if channel.name != "__global__":
                if channel.name not in user.channel_rights:
                    user.channel_rights[channel.name] = list()
                channel.user_joined(user)

    def user_joined(self, uconn, channel_name):
        channel = self.find_channel(channel_name)
        c_user = self.find_user(uconn.user)

        if not channel:
            return

        if c_user:
            self.channel_users.remove(c_user)

        c_user = channel_user(uconn, uconn.user, [], dict())
        self.channel_users.append(c_user)

        c_user.channel_rights[channel_name] = list()

        channel.user_joined(c_user)

    def user_rename(self, user, old_name):
        c_user = self.find_user(user)

        for channel_name in c_user.channels:
            channel = self.find_channel(channel_name)

            channel.user_rename(c_user, old_name)

    def user_left(self, user, channel_name):
        channel = self.find_channel(channel_name)
        c_user = self.find_user(user)

        if channel and c_user:
            if user == channel.admin_user:
                channel.destroy()
                self.channels.remove(channel)
            else:
                channel.user_left(c_user)

    def user_disconnected(self, user):
        c_user = self.find_user(user)

        if c_user:
            for channel_name in c_user.channels:
                channel = self.find_channel(channel_name)
                if c_user.user == channel.admin_user:
                    channel.destroy()
                    self.channels.remove(channel)
                    continue
                channel.user_left(c_user)

    def find_channel(self, name):
        for channel in self.channels:
            if channel.name == name:
                return channel

    def find_user(self, user):
        for c_user in self.channel_users:
            if c_user.user == user:
                return c_user

    def find_user_by_name(self, name):
        for c_user in self.channel_users:
            if c_user.user.username_p == name:
                return c_user


class DirectMessages:
    def __init__(self):
        self.dm_disabled = list()
        self.block_list = dict()

    def enable_dm(self, user):
        if user in self.dm_disabled:
            self.dm_disabled.remove(user)

    def disable_dm(self, user):
        if user not in self.dm_disabled:
            self.dm_disabled.append(user)

    def block_user(self, user, blocked_user):
        if user in self.block_list:
            self.block_list[user].append(blocked_user)
        else:
            self.block_list[user] = [blocked_user]

    def can_send_message(self, sender, receiver):
        if receiver in self.dm_disabled:
            return False
        elif receiver in self.block_list and sender in self.block_list[receiver]:
            return False
        return True
