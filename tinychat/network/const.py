import netifaces

PACKET_SIZE = 1400
DATAGRAM_SIZE = 256

PORT = 6489
UDP_PORT = 57803

INTERFACE = netifaces.gateways()['default'][netifaces.AF_INET][1]
netinfo = netifaces.ifaddresses(INTERFACE)[netifaces.AF_INET][0]

LOCAL_IP = netinfo['addr']
MASK = netinfo['netmask']
BROADCAST_ADDR = netinfo['broadcast']
