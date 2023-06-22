from machine import unique_id
from network import WLAN, STA_IF, AP_IF
from espnow import  ESPNow
from ubinascii import hexlify, unhexlify
from utime import ticks_ms, sleep_ms

# A WLAN interface must be active to send()/recv()
sta = WLAN(STA_IF)
sta.active(True)
sta.config(channel=11)
espnow = ESPNow()
espnow.active(True)

while True:
    peer, msg = espnow.irecv(timeout_ms=250)
    if peer and msg:
        print(peer, msg)
