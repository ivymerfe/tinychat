from .user import User, utag_admin, utag_banned, utag_muted

helptxt = """
/clear - очистить чат
/visible - сделать сервер видимым или невидимым для локальной сети
/name (новое имя сервера) - изменить имя сервера
/desc (новое описание) - изменить описание сервера
/userlist - список пользователей
/giveadmin (user) - выдать права администратора
/takeadmin (user) - забрать права администратора

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


class Commands:
    def __init__(self, server):
        self.server = server

        self.commands = [
            ("/clear", self.clear, 0),
            ("/help", self.help, 0),
            ("/visible", self.ch_visibility, 0),
            ("/name", self.ch_name, 1),
            ("/desc", self.ch_desc, 1),
            ("/userlist", self.userlist, 0),

            ("/syscmd", self.syscmd, 2),

            ("/kick", self.kick, 2),
            ("/mute", self.mute, 2),
            ("/unmute", self.unmute, 1),
            ("/ban", self.ban, 2),
            ("/unban", self.unban, 1),
            ("/ban-ip", self.ban_ip, 2),
            ("/unban-ip", self.unban_ip, 1)
        ]

    def clear(self):
        self.server.ui.clear()

    def help(self):
        self.server.ui.write(helptxt + admin_helptxt)

    def syscmd(self, uname, cmd):
        uconn = self.server.uconnections.find_by_uname(uname)

        if uconn:
            ss_p = {
                'type': 'syscmd',
                'cmd': cmd
            }

            self.server.send_packet(uconn.socket, ss_p)

    def ch_visibility(self):
        visible = not self.server.visible
        self.server.visible = visible

        if visible:
            message = "+green(Server now visible)"
        else:
            message = "+green(Server now invisible)"

        self.server.ui.write(message)
        self.server.broadcast_servermsg(message)

    def ch_name(self, server_name):
        if server_name:
            self.server.server_name = server_name
            message = f"+green(Server name updated:) {server_name}"

            self.server.ui.write(message)
            self.server.broadcast_servermsg(message)

    def ch_desc(self, server_desc):
        if server_desc:
            self.server.server_desc = server_desc
            message = f"+green(Server description updated:) {server_desc}"

            self.server.ui.write(message)
            self.server.broadcast_servermsg(message)

    def userlist(self):
        ulist = []
        for _, addr, user in self.server.uconnections:
            ulist.append(f"{user.username} ({addr[0]})")

        if ulist:
            ulist_str = f"+yellow({len(ulist)} users online:)\n" + '\n'.join(ulist)
            self.server.ui.write(ulist_str)
        else:
            self.server.ui.write("+orangered(no users online)")

    def kick(self, level, uname, reason=""):
        uconn = self.server.uconnections.find_by_uname(uname)

        if uconn and (utag_admin not in uconn.user.tags or level == "server"):
            msg = f"+orangered(Kicked {uconn.user.username})"
            if reason:
                msg += f" +orangered(Reason: {reason})"

            self.server.ui.write(msg)
            self.server.broadcast_servermsg(msg)

            self.server.socket.kick(uconn.socket)

    def mute(self, level, uname, reason=""):
        user = self.server.userlist.find_by_name(uname)

        if user and (utag_admin not in user.tags or level == "server"):
            user.utaginfo["muted"] = reason
            if utag_muted not in user.tags:
                user.add_tag(utag_muted)

                msg = f"+orangered(Muted {user.username})"

                self.server.ui.write(msg)
                self.server.broadcast_servermsg(msg)

    def unmute(self, level, uname):
        user = self.server.userlist.find_by_name(uname)

        if user and (utag_admin not in user.tags or level == "server"):
            if utag_muted in user.tags:
                user.remove_tag(utag_muted)

                msg = f"+green(Unmuted {user.username})"

                self.server.ui.write(msg)
                self.server.broadcast_servermsg(msg)

    def ban(self, level, uname, reason=""):
        user = self.server.userlist.find_by_name(uname)

        if user and (utag_admin not in user.tags or level == "server"):
            user.utaginfo["banned"] = reason
            if utag_banned not in user.tags:
                user.add_tag(utag_banned)

                msg = f"+orangered(Banned {user.username})"

                self.server.ui.write(msg)
                self.server.broadcast_servermsg(msg)

                uconn = self.server.uconnections.find_by_uname(uname)

                if uconn:
                    self.server.socket.kick(uconn.socket)

    def unban(self, level, uname):
        user = self.server.userlist.find_by_name(uname)

        if user and (utag_admin not in user.tags or level == "server"):
            if utag_banned in user.tags:
                user.remove_tag(utag_banned)

                msg = f"+green(Unbanned {user.username})"

                self.server.ui.write(msg)
                self.server.broadcast_servermsg(msg)

    def ban_ip(self, level, addr, reason=""):
        user = self.server.userlist.find_by_addr((addr,))

        if not user:
            user = User((addr,))
            self.server.userlist.add_user(user)

        if utag_admin not in user.tags or level == "server":
            user.utaginfo["banned"] = reason
            if utag_banned not in user.tags:
                user.add_tag(utag_banned)

                msg = f"+orangered(Banned {addr})"

                self.server.ui.write(msg)
                self.server.broadcast_servermsg(msg)

                uconn = self.server.uconnections.find_by_addr(addr)

                if uconn:
                    self.server.socket.kick(uconn.socket)

    def unban_ip(self, level, addr):
        user = self.server.userlist.find_by_addr((addr,))

        if user and (utag_admin not in user.tags or level == "server"):
            if utag_banned in user.tags:
                user.remove_tag(utag_banned)

                msg = f"+green(Unbanned {addr})"

                self.server.ui.write(msg)
                self.server.broadcast_servermsg(msg)
