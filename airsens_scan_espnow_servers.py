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

        # A WLAN interface must be active to send()/recv()
        sta = WLAN(STA_IF)
        sta.active(False)
        ap = WLAN(AP_IF)
        ap.active(False)
        sta.active(True)
        sta.config(channel=1)
        # instantiation of ESPNow
        espnow = ESPNow()
        espnow.active(True)
        # send the message
        bin_mac_adress = unhexlify('ff:ff:ff:ff:ff:ff'.replace(':',''))
        print(bin_mac_adress)
        espnow.add_peer(bin_mac_adress) #conf.PROXY_MAC_ADRESS)
#         print('espnow.get_peer(bin_mac_adress):',espnow.get_peer(bin_mac_adress))
        msg_received_by_central = espnow.send(bin_mac_adress, 'PAIRING', True)
        print('msg_received_by_central:', msg_received_by_central)

#         print('Espnow servers:')
#         self.write_best_server_in_conf(None)

if __name__ == '__main__':
    
    # instanciation of I2C
    scan_espnow = ScanEspnowServers()
    scan_espnow.main()

