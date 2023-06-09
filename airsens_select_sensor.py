#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: select_sensor.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens-v3

verify the presense of sensors and update the airsens_sensor_conf.py
v0.1.0 : 08.06.2023 --> first prototype
"""
import airsens_sensor_conf_v3 as conf  # configuration file
from machine import SoftI2C, Pin
import lib.bme280 as bme280
import lib.bme680 as bme680
import lib.hdc1080 as hdc1080

class SelectSensor:
    
    def __init__(self,i2c):
        self.POSSIBLES_SENSORS = {
            'hdc1080':['temp', 'hum'],
            'bme280':['temp', 'hum', 'pres'],
            'bme680':['temp', 'hum', 'pres', 'gas', 'alt'],
          }
        self.i2c = i2c
        self.conf_file_name = 'airsens_sensor_conf_v3.py'
        
    def verify_witch_sensor_is_connected(self, i2c):
        connected_sensors = []
        for sensor_tested in self.POSSIBLES_SENSORS:
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
    
    def main(self):
        connected_sensors = self.verify_witch_sensor_is_connected(self.i2c)
        print('sensors detected:', connected_sensors)
        self.write_actives_sensors_in_conf(connected_sensors)

if __name__ == '__main__':
    
    # instanciation of I2C
    i2c = SoftI2C(scl=Pin(conf.BME_SCL_PIN), sda=Pin(conf.BME_SDA_PIN), freq=10000)
    sel_sens = SelectSensor(i2c)
    sel_sens.main()
