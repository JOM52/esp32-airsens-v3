from machine import unique_id
from network import WLAN, STA_IF, AP_IF
from espnow import  ESPNow
from ubinascii import hexlify, unhexlify
from utime import ticks_ms, sleep_ms

host_mac_adress = unhexlify('3C:61:05:0D:67:CC'.replace(':',''))
msg = 'message de test'
# A WLAN interface must be active to send()/recv()
sta = WLAN(STA_IF)
sta.active(True)
# sta.config(channel=11)
# instantiation of ESPNow
espnow = ESPNow()
espnow.active(True)
espnow.add_peer(host_mac_adress, lmk=None, channel=11, ifidx=STA_IF, encrypt=False) #conf.PROXY_MAC_ADRESS)
msg_send = 0
msg_good = 0
msg_lost = 0
while True:
    msg_x = msg + ' ' + str(msg_send)
    msg_received_by_host = espnow.send(host_mac_adress, msg_x, True)
    msg_send += 1
    if msg_received_by_host:
        msg_good += 1
    msg_lost = msg_send - msg_good
    print(msg_received_by_host, 'send', msg_send, 'good', msg_good, 'lost', msg_lost)
    sleep_ms(1000)
