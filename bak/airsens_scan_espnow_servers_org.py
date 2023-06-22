#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_scan_servers.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens-v3

verify the presense of sensors and update the airsens_sensor_conf.py
v0.1.0 : 08.06.2023 --> first prototype
"""
from network import WLAN, STA_IF, AP_IF
from espnow import  ESPNow
from ubinascii import hexlify, unhexlify

class ScanEspnowServers:
    
    def __init__(self):
        self.conf_file_name = 'airsens_sensor_conf_v3.py'
        
    def scan_espnow_servers(self):
        pass
    
    def write_best_server_in_conf(self, servers_list):
        pass
    
    def main(self):

        possible_central = []
        rssi_max = - 100
        rssi_best = None
        # A WLAN interface must be active to send()/recv()
        sta = WLAN(STA_IF)
        sta.active(False)
        ap = WLAN(AP_IF)
        ap.active(False)
        sta.active(True)
        sta.config(channel=11)
        # instantiation of ESPNow
        espnow = ESPNow()
        espnow.active(True)
        # send the brodcast
        bin_mac_adress = unhexlify('ff:ff:ff:ff:ff:ff'.replace(':',''))
        espnow.add_peer(bin_mac_adress) #conf.PROXY_MAC_ADRESS)
        msg_received_from_central = espnow.send(bin_mac_adress, 'PAIRING', True)
            
        while True:
            host, msg = espnow.irecv(timeout_ms=1000)     # Available on ESP32 and ESP8266
            if msg: # msg == None if timeout in irecv()
                decode_msg = msg.decode().split('/')
                host = decode_msg[0]
                rssi = decode_msg[1]
                possible_central.append([host, rssi])
                print('host et rssi:', host, rssi)
            else:
                break
        for i, central in enumerate(possible_central):
            if int(central[1]) > rssi_max:
                rssi_best = i
                rssi_max = int(central[1])
    
        print('best central:', possible_central[rssi_best][0], possible_central[rssi_best][1])
        
            
        

#         print('Espnow servers:')
#         self.write_best_server_in_conf(None)

if __name__ == '__main__':
    
    # instanciation of I2C
    scan_espnow = ScanEspnowServers()
    scan_espnow.main()

