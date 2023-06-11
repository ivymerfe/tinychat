from collections import namedtuple
from tinychat.gui.colors import parse2
import string

uconn_t = namedtuple("uconnection", ("socket", "addr", "user"))


class UserTag:
    def __init__(self, name, level, rights):
        self.name = name
        self.level = level
        self.rights = rights


# pickle error, then
utag_default = UserTag("default", 1, {"serverAccess": 1, "sendMessagesAllowed": 1, "readMessagesAllowed": 1})
utag_muted = UserTag("muted", 2, {"sendMessagesAllowed": 0})
utag_admin = UserTag("admin", 3, {"adminCommandsAccess": 1})
utag_banned = UserTag("banned", 5, {"serverAccess": 0})


class User:
    def __init__(self, addr):
        self.addr = addr[0]
        self.tags = [utag_default]
        self.utaginfo = dict()
        self.rights = set()

        self.username = ""
        self.username_p = ""

    def set_username(self, uname, uname_p):
        self.username = uname
        self.username_p = uname_p

    @staticmethod
    def filter_username(username):
        ru_letters = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        ok_chars = "0123456789+-_#()~" + string.ascii_letters + ru_letters + ru_letters.upper()

        filtered_chars = [ch for ch in username if ch in ok_chars]

        filtered_uname = ''.join(filtered_chars)
        parsed_uname = parse2(filtered_uname).text

        return filtered_uname, parsed_uname

    def add_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag):
        if tag in self.tags:
            self.tags.remove(tag)

    def check_right(self, right, value):
        check_result = False
        check_level = 0

        for tag in self.tags:
            if tag.level > check_level and right in tag.rights:
                check_result = value == tag.rights[right]
                check_level = tag.level
        return check_result


class UserList:
    def __init__(self):
        self.users = list()

    def add_user(self, user):
        self.users.append(user)

    def remove_user(self, user):
        if user in self.users:
            self.users.remove(user)

    def find_by_addr(self, addr):
        for user in self.users:
            if user.addr == addr[0]:
                return user

    def find_by_name(self, username):
        for user in self.users:
            if user.username_p == username:
                return user


class ConnectionList:
    def __init__(self, userlist):
        self._ulist = userlist
        self.connections = list()

        self.temp_connections = list()

    def create_connection(self, socket, addr):
        user = self._ulist.find_by_addr(addr)

        # check if user exists
        if not user:
            return None

        conn = uconn_t(socket, addr, user)
        self.connections.append(conn)
        return conn

    def destroy_connection(self, addr):
        conn = self.find_by_addr(addr)
        if conn:
            self.connections.remove(conn)

    def create_temp_connection(self, socket, addr):
        conn = uconn_t(socket, addr, None)
        self.temp_connections.append(conn)

    def destroy_temp_connection(self, addr):
        for conn in self.temp_connections:
            if conn.addr == addr:
                self.temp_connections.remove(conn)
                break

    def find_by_addr(self, addr, temp=False):
        for conn in self.connections:
            if conn.addr == addr:
                return conn

        if temp:
            for conn in self.temp_connections:
                if conn.addr == addr:
                    return conn

    def find_by_uname(self, username):
        for conn in self.connections:
            if conn.user.username_p == username:
                return conn

    def __iter__(self):
        yield from self.connections
