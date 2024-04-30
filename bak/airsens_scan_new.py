#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_scan.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens-v3

- scan and record connected sensors
- scan and record espnow hosts and record the one with the best rssi
v0.1.0 : 14.06.2023 --> first prototype
v0.1.1 : 23.06.2023 --> modif en cours pour transmission des grandeurs mesurées
v0.1.2 : 26.06.2023 --> ajout de la sélection du meilleur canal sur le wifi
v0.1.3 : 27.06.2023 --> improved version
"""
import airsens_sensor_conf_v3 as conf  # configuration file
from machine import SoftI2C, Pin
from network import WLAN, STA_IF, AP_IF
from espnow import  ESPNow
from ubinascii import unhexlify

import lib.bme280 as bme280
import lib.bme680 as bme680
import lib.hdc1080 as hdc1080
"""
Ce programme fait partie de l'ensemble airsens.

Il permet de scanner les capteurs connectés et de les ajouter au fichier
airsens_sensor_conf.py

Il scanne aussi les serveurs airsens disponible sur tous les canuax wifi (1..14) et
enregistre dans le fichier de configuration l'adresse mac et le canal de celui qui
a le meilleur rssi 

paramètres en entrée:
    - I2C connecté
    - nom du fichier de configuration du capteur
    
en sortie:
    - True si un ou des capteurs et un ou des hosts on été trouvés
    - False dans le cas contraire
"""
class GlobalVar:
    sensor_ok = False
    host_ok = False

class AirSensScan:
    
    def __init__(self, i2c, conf_file_name):
        
        self.POSSIBLES_SENSORS = {
            'hdc1080':['temp', 'hum'],
            'bme280':['temp', 'hum', 'pres'],
            'bme680':['temp', 'hum', 'pres', 'gas', 'alt'],}
        self.i2c = i2c
        self.conf_file_name = conf_file_name
        
        self.best_host = None
        self.rssi = None
        self.channel = None

        self.sta, self.ap = (WLAN(i) for i in (STA_IF, AP_IF))
        self.sta.active(True)

        self.espnow = ESPNow()
        self.espnow.active(True)

    def scan_espnow_servers(self):
        
        hosts_found = []
        rssi_max = - 100
        rssi_best = None
        # send the brodcast
        bin_mac_adress = unhexlify('ff:ff:ff:ff:ff:ff'.replace(':',''))
        try:
            self.espnow.add_peer(bin_mac_adress)  # If user has not already registered peer
        except OSError:
            pass
        # broadcast for all channels
        print('  ', end='')
        for channel in range (1, 14):
            print(str(channel) + '..', end='')
            self.sta.config(channel=channel)
            # send a PAIRING message
            if self.espnow.send(bin_mac_adress, 'PAIRING', True):
                while True:
                    host, msg = self.espnow.irecv(timeout=250)  # ask for pairing
                    if msg: # msg == None if timeout in irecv()
                        decode_msg = msg.decode().split('/')
                        host = decode_msg[0]
                        rssi = decode_msg[1]
                        hosts_found.append([host, rssi, channel])
                    else:
                        break # no or no more message to receive
        if hosts_found:
            print()
            for h in hosts_found:
                print('  - found host: ' +  str(h[0]), 'channel:' + str(h[2]), 'rssi:' + str(h[1]))

        # check if it's possible host
        if hosts_found:
            # host(s) are found look for best rssi
            for i, host in enumerate(hosts_found):
                if int(host[1]) > rssi_max:
                    rssi_best = i
                    rssi_max = int(host[1])
            self.best_host = hosts_found[rssi_best][0]
            self.rssi = hosts_found[rssi_best][1]
            # look for best channel
            hosts_channels = []
            for i, host in enumerate(hosts_found):
                if host[0] == self.best_host and host[2] not in hosts_channels:
                    hosts_channels.append(host[2])
            hosts_channels.sort()
            count = len(hosts_channels)
#             print('count, hosts_channels:', count, hosts_channels)
            index = 0 if count == 1 or (count == 2 and hosts_channels[1] == 1) else 1
#             print('index:', index)
            self.channel = hosts_channels[index]            
            return True
        else:
            print()
            return False


    def verify_witch_sensor_is_connected(self, i2c):
        connected_sensors = []
        for sensor_tested in self.POSSIBLES_SENSORS:
            print(' - ' + sensor_tested + '..', end='')
            if sensor_tested == 'bme280':
                try:
                    sensor = bme280.BME280(i2c=i2c)
                    connected_sensors.append(sensor_tested)
                except:
                    pass
            elif sensor_tested == 'bme680':
                try:
                    sensor = bme680.BME680_I2C(i2c=i2c)
                    connected_sensors.append(sensor_tested)
                except:
                    pass
            elif sensor_tested == 'hdc1080':
                try:
                    sensor = hdc1080.HDC1080(i2c=i2c)
                    connected_sensors.append(sensor_tested)
                except:
                    pass
        if sensor_tested:
            print('\n -> found')
        else:
            print()
        return connected_sensors
    
    def write_actives_sensors_in_conf(self, sensor_list):
        with open (self.conf_file_name, 'r') as f:
            lines = f.readlines()
        with open (self.conf_file_name, 'w') as f:
            for line in lines:
                if 'SENSORS' in line:
                    new_line = 'SENSORS = {'
                    for sensor in sensor_list:
                        new_line += "'" + str(sensor) + "':"
                        new_line += str(self.POSSIBLES_SENSORS[sensor])
                        new_line += ', '
                    new_line += '}\n'
                    f.write(new_line)
                else:
                    f.write(line)
    
    def write_wifi_channel_in_conf(self, new_channel):
        with open (self.conf_file_name, 'r') as f:
            lines = f.readlines()
        with open (self.conf_file_name, 'w') as f:
            for line in lines:
                if 'WIFI_CHANNEL' in line:
                    new_line = 'WIFI_CHANNEL = ' + str(new_channel) + '\n'
                    f.write(new_line)
                else:
                    f.write(line)
    
    def write_best_host_in_conf(self, new_mac):
        with open (self.conf_file_name, 'r') as f:
            lines = f.readlines()
        with open (self.conf_file_name, 'w') as f:
            for line in lines:
                if 'HOST_MAC_ADRESS' in line:
                    new_line = 'HOST_MAC_ADRESS = "' + new_mac + '"\n'
                    f.write(new_line)
                else:
                    f.write(line)
    
    def main(self):
        print('checking sensors:')
        connected_sensors = self.verify_witch_sensor_is_connected(self.i2c)
        if connected_sensors:
            GlobalVar.sensor_ok = True
        for s in connected_sensors:
            print('   -', s, self.POSSIBLES_SENSORS[s])
        self.write_actives_sensors_in_conf(connected_sensors)
        print('scanning hosts on channel:')        
        if self.scan_espnow_servers():
            print('  -> best host: ' + str(self.best_host), 'channel:' + str(self.channel), 'rssi:' + str(self.rssi))
            self.write_best_host_in_conf(self.best_host)
            self.write_wifi_channel_in_conf(self.channel)
            GlobalVar.host_ok = True
        return GlobalVar.sensor_ok and GlobalVar.host_ok            
            


if __name__ == '__main__':
    conf_file_name = 'airsens_sensor_conf_v3.py'
    # instanciation of I2C
    i2c = SoftI2C(scl=Pin(conf.BME_SCL_PIN), sda=Pin(conf.BME_SDA_PIN), freq=10000)
    scan = AirSensScan(i2c, conf_file_name)
    ok = scan.main()
    
    if ok:
        print('All is ok')
    else:
        print('Something goes wrong ...')
        if not GlobalVar.sensor_ok: print('  - no sensor found')
        if not GlobalVar.host_ok: print('  - no host found')

