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
"""
import airsens_sensor_conf_v3 as conf  # configuration file
from machine import SoftI2C, Pin
from network import WLAN, STA_IF, AP_IF
from espnow import  ESPNow
from ubinascii import hexlify, unhexlify

import lib.bme280 as bme280
import lib.bme680 as bme680
import lib.hdc1080 as hdc1080

class AirSensScan:
    
    def __init__(self, i2c, conf_file_name):
        self.POSSIBLES_SENSORS = {
            'hdc1080':['temp', 'hum', 'bat'],
            'bme280':['temp', 'hum', 'pres', 'bat'],
            'bme680':['temp', 'hum', 'pres', 'gas', 'alt', 'bat'],
          }
        self.i2c = i2c
        self.conf_file_name = conf_file_name
        
    def scan_espnow_servers(self):
        possible_central = []
        rssi_max = - 100
        rssi_best = None
        # A WLAN interface must be active to send()/recv()
        sta = WLAN(STA_IF)
#         ap = WLAN(AP_IF)
#         ap.active(False)
        sta.active(True)
        sta.config(channel=11)
        # instantiation of ESPNow
        espnow = ESPNow()
        espnow.active(True)
        # send the brodcast
        bin_mac_adress = unhexlify('ff:ff:ff:ff:ff:ff'.replace(':',''))
        espnow.add_peer(bin_mac_adress) #conf.PROXY_MAC_ADRESS)
        if espnow.send(bin_mac_adress, 'PAIRING', True):
            while True:
                host, msg = espnow.irecv(timeout_ms=5000)     # Available on ESP32 and ESP8266
                if msg: # msg == None if timeout in irecv()
                    decode_msg = msg.decode().split('/')
                    host = decode_msg[0]
                    rssi = decode_msg[1]
                    possible_central.append([host, rssi])
                    print('host et rssi:', host, rssi)
                else:
                    break
#         print('tx_pkts, tx_responses, tx_failures, rx_packets, rx_dropped_packets', espnow.stats())
        if possible_central:
            for i, central in enumerate(possible_central):
                if int(central[1]) > rssi_max:
                    rssi_best = i
                    rssi_max = int(central[1])
            return possible_central[rssi_best][0]
        else:
            print('No central found')
            return None
    
    def verify_witch_sensor_is_connected(self, i2c):
        connected_sensors = []
#         print('self.POSSIBLES_SENSORS:', self.POSSIBLES_SENSORS)
        for sensor_tested in self.POSSIBLES_SENSORS:
            if sensor_tested == 'bme280':
#                 print('sensor_tested:', sensor_tested)
#                 print('sensor grandeurs:', self.POSSIBLES_SENSORS[sensor_tested])
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
# tbd
# retourner une entrée de dictionnaire avec sensoor et quantity
#
        return connected_sensors, self.POSSIBLES_SENSORS[sensor_tested]
    
    def write_actives_sensors_in_conf(self, sensor_list, sensor_quantity):
        print('sensor, quantity:', sensor_list, sensor_quantity)
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
    
    def write_best_host_in_conf(self, new_mac):
        with open (self.conf_file_name, 'r') as f:
            lines = f.readlines()
        with open (self.conf_file_name, 'w') as f:
            for line in lines:
                if 'HOST_MAC_ADRESS' in line:
                    new_line = 'HOST_MAC_ADRESS="' + new_mac + '"\n'
                    f.write(new_line)
                else:
                    f.write(line)
    
    def main(self):
        connected_sensors, sensor_quantity = self.verify_witch_sensor_is_connected(self.i2c)
        print('sensors detected:', connected_sensors, 'quantity:', sensor_quantity)
        self.write_actives_sensors_in_conf(connected_sensors, sensor_quantity)
        
        best_host = self.scan_espnow_servers()
        print('best host:', best_host)
        self.write_best_host_in_conf(best_host)


if __name__ == '__main__':
    conf_file_name = 'airsens_sensor_conf_v3.py'
    # instanciation of I2C
    i2c = SoftI2C(scl=Pin(conf.BME_SCL_PIN), sda=Pin(conf.BME_SDA_PIN), freq=10000)
    scan = AirSensScan(i2c, conf_file_name)
    scan.main()

