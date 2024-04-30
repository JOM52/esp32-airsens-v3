#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_sensor_multi.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-now

The sensors are made with an ESP32 microcontroller and can be powered by battery or by USB.
They transmit the data to a host also realized with an ESP32 by a ESPnow interface

v0.1.0 : 17.08.2022 --> first prototype based on airsens_ble_sensor.py
----------------------------------------------------------------------
v0.2.0 : 07.09.2022 --> modified for new log_and_count.py version ---> no more compatible with previous versions
v0.2.1 : 07.09.2022 --> espnow and wifi powered off before going to deepsleep
v0.2.2 : 19.12.2022 --> small cosmetices changes
v0.2.3 : 20.12.2022 --> temporary change for develop proxy display
v0.2.4 : 03.01.2022 --> added fake sensor for test
v0.2.5 : 11.01.2023 --> name of the conf file modified to airsens_now_sensor_display_conf.py
v0.3.0 : 17.02.2023 --> new version for long time test (tld)
v0.3.1 : 26.02.2023 --> usage of conf values simplidied
----------------------------------------------------------------------
v1.0.0 : 12.03.2023 --> First production version - one version for bme280 and hdc1080
----------------------------------------------------------------------
v2.0.0 : 02.04.2023 --> New data concept
v2.0.1 : 21.04.2023 --> Small cosmetic changes
v2.0.2 : 22.04.2023 --> improved espnow message sending by fixing the wifi channel
v2.0.3 : 26.04.2023 --> Added TO_PRINT in conf file 
----------------------------------------------------------------------
v3.0.0 : 30.05.2023 --> Begin with version3 of hard and soft. News are:
                        - Semi-automatic pairing between capteur and host
                        - During the pairing the sensor automatically informs the host of:
                                - the connected sensor(s),
                                - the measured quantities.
v3.0.1 : 30.05.2023 --> implémentation logiciel de la led et du bouton pour le pairage (éléments de base)
v3.0.2 : 06.06.2023 --> implémentation lecture tension cellule photovoltaique
v3.0.3 : 18.06.2023 --> MTL essai sur wifi mtl
----------------------------------------------------------------------
v3.1.0 : 23.06.2023 --> new datmessage structure no more compatible with old versions.
v3.1.1 : 23.06.2023 --> correction on count of messages lost
v3.1.2 : 25.06.2023 --> standardised the integration of bat and sol in message
v3.1.3 : 25.06.2023 --> final print improved
v3.2.4 : 30.06.2023 --> battery and solar pannel voltage transmitted only ones (that of the last sensor)
v3.3.0 : 08.07.2023 --> stable version for long time test
v3.3.1 : 23.11.2023 --> added reset if error in main loop
v3.3.2 : 26.11.2023 --> improve main error handling 
"""

from utime import ticks_ms, sleep_ms
start_time = ticks_ms()

# PARAMETERS ========================================
PRG_NAME = 'airsens_sensor_v3_scan'
PRG_VERSION = '3.3.2'
CONF_FILE_NAME = 'airsens_sensor_conf_v3.py'
import airsens_sensor_conf_v3 as conf  # configuration file
# IMPORTATIONS ======================================
from ubinascii import hexlify, unhexlify
from machine import Pin, freq, TouchPad, reset, reset_cause
from machine import ADC, SoftI2C, deepsleep, Timer, DEEPSLEEP_RESET, EXT0_WAKE, HARD_RESET
from machine import unique_id
from sys import exit
from network import WLAN, STA_IF, AP_IF
from espnow import  ESPNow
from lib.log_sensor import LogSensors
log = LogSensors()

# SENSORS ============================================
# if 'bme280' in conf.SENSORS:
#     import lib.bme280 as bme280
if 'bme280' in conf.SENSORS:
    import lib.bme280_float as bme280
if 'bme680' in conf.SENSORS:
    import lib.bme680 as bme680
if 'hdc1080' in conf.SENSORS:
    import lib.hdc1080 as hdc1080
# ADC MEASUREMENTS ===================================
if conf.ON_BATTERY:
    bat_adc_in = ADC(Pin(conf.ADC1_PIN))            
    bat_adc_in.atten(ADC.ATTN_6DB ) # Umax = 2V
    bat_adc_in.width(ADC.WIDTH_12BIT) # 0 ... 4095
if conf.SOLAR_PANEL:
    sol_adc_in = ADC(Pin(conf.SOL_PIN))            
    sol_adc_in.atten(ADC.ATTN_6DB ) # Umax = 2V
    sol_adc_in.width(ADC.WIDTH_12BIT) # 0 ... 4095
# LED AND BUTTONS =====================================
LED = Pin(conf.LED_PIN, Pin.OUT)
BTN_PAIR = Pin(conf.BUTTON_PAIR_PIN, mode = Pin.IN, pull=Pin.PULL_UP)
PAIR_STATUS = not BTN_PAIR.value()
# I2C ==================================================
i2c = SoftI2C(scl=Pin(conf.BME_SCL_PIN), sda=Pin(conf.BME_SDA_PIN), freq=10000)
# FUNCTIONS ===========================================
# led flash
def blink_led(freq='high', n_repeat=3):
    if freq =='high': t_ms = 100
    elif freq == 'med': t_ms = 250
    elif freq == 'low': t_ms = 500
    elif freq == 'very_low': t_ms = 1000
    if n_repeat != 0:
        for n in range(n_repeat):
            LED.on()
            sleep_ms(t_ms)
            LED.off()
            sleep_ms(t_ms)
    else:
        while True:
            LED.on()
            sleep_ms(t_ms)
            LED.off()
            sleep_ms(t_ms)
        
# print and store infos after the end of the measure
def end_print(total_time, t_deepsleep):
    msg_send = log.counters('passe', True)
    msg_lost = log.counters('lost', False)
    msg_good = msg_send - msg_lost
    if conf.TO_PRINT:
        print('msg send:' + str(msg_send) + ' good:' + str(msg_good) + ' lost:' + str(msg_lost) +
              ' - error:' + str(log.counters('error', False)), '-->' , str(total_time) + 'ms')
        print('going to deepsleep for: ' + str(t_deepsleep) + ' ms')
        print('=================================================')
    else:
        print(str(total_time) + 'ms')
    deepsleep(t_deepsleep)



def main():
    # Green button = pair
    # Yellow button = reset
    # enter pair mode if pair button is pressed during reset
    if PAIR_STATUS:
        blink_led('high', 7)
        import lib.airsens_scan as airsens_scan

        scan = airsens_scan.AirSensScan(i2c, CONF_FILE_NAME)
        scan_result = scan.main()
        
        if scan_result:
            print('in 5s the system will reset the machine with the new parameters')
            print('-----------------------------------------------')
            blink_led('high', 7)
            sleep_ms(5000)
            reset()
        else:
            log.log_error('pairing not succesfull, retry' , to_print = True, record_time = True)
            blink_led('low', 0)
            exit
            
    bat = -9999
            
    # Normal measurement (no button pressed on boot)
    try:
        host_mac = unhexlify(conf.HOST_MAC_ADRESS.replace(':',''))
        sensor_mac = hexlify(unique_id(),':').decode().upper()
        if conf.TO_PRINT:
            print('=================================================')
            print(PRG_NAME + ' v' + PRG_VERSION )
            print('Host mac:  ' + conf.HOST_MAC_ADRESS, 'channel:' + str(conf.WIFI_CHANNEL))
            print('Sensor mac:', sensor_mac)
        
        # A WLAN interface must be active to send()/recv()
        sta = WLAN(STA_IF)
        sta.active(True)
        sta.config(channel=conf.WIFI_CHANNEL)
        # ESPNow
        espnow = ESPNow()
        espnow.active(True)
        espnow.add_peer(host_mac, lmk=None, channel=conf.WIFI_CHANNEL, ifidx=STA_IF, encrypt=False) #conf.PROXY_MAC_ADRESS)
        
        measurements = []
        for i, sensor_type in enumerate(conf.SENSORS):
            if sensor_type == 'bme280':
                sensor = bme280.BME280(i2c=i2c)
            elif sensor_type == 'bme680':
                sensor = bme680.BME680_I2C(i2c=i2c)
            elif sensor_type == 'hdc1080':
                sensor = hdc1080.HDC1080(i2c=i2c)
            
            msg = 'jmb,'  + sensor_mac + ',' + conf.SENSOR_LOCATION + ',' + sensor_type + ','
            measurement_list = conf.SENSORS.get(sensor_type)
            for measurement in measurement_list:
                value = 0
                for l in range(conf.AVERAGING_BME):
                    if measurement == 'temp':
                        value += float(sensor.temperature)
                    elif measurement == 'pres':
                        value += float(sensor.pressure)
                    elif measurement == 'hum':
                        value += float(sensor.humidity)
                    elif measurement == 'gas':
                        value += float(sensor.gas)
                    elif measurement == 'alt':
                        value += float(sensor.altitude)
                    msg += measurement + ':' + str(value / conf.AVERAGING_BME) + ';'
            msg = msg[:-1]          

            q = 1/0

            bat = 0
            sol = 0
            if i == len(conf.SENSORS) - 1: # only 1 measure of bat and solar pannel
                # read the battery voltage
                if conf.ON_BATTERY:
                    for l in range(conf.AVERAGING_BAT):
                        bat += bat_adc_in.read()
                    bat = bat / conf.AVERAGING_BAT * (2 / 4095) / conf.DIV
                    msg += ';bat:' + str(bat) + ''
                    measurements.append(msg)

                # read the solar panel voltage
                if conf.SOLAR_PANEL:
                    for l in range(conf.AVERAGING_BAT):
                        sol += sol_adc_in.read()
                    sol = sol / conf.AVERAGING_BAT * (2 / 4095) / conf.DIV
                    msg += ';sol:' + str(sol) + ''
                    measurements.append(msg)
    
            if conf.TO_PRINT: print(msg)
            
            # send message to host
            msg_received_by_host = espnow.send(host_mac, msg, True)
            if not msg_received_by_host:
                log.counters('lost', True)
                log.log_error('message is gone lost' , to_print = True, record_time = True)
                
        # close the communication canal
        espnow.active(False)
        espnow = None
        sta.active(False)
        sta = None
        # prepare for deepsleep
        total_time = ticks_ms() - start_time
        t_deepsleep = max(conf.T_DEEPSLEEP_MS - total_time, 10)
        # check the level of the battery
        if not conf.ON_BATTERY:
            # not on battery so finish the measure
            end_print(total_time, t_deepsleep)
        else:
            if bat > conf.UBAT_0:
                # battery is ok so finishing tasks
                end_print(total_time, t_deepsleep)
            else:
                # battery is dead so endless sleep to protect the battery
                pass_to_wait = 10
                for i in range(pass_to_wait):
                    if conf.TO_PRINT: print('going to endless deepsleep in ' + str(pass_to_wait - i) + ' s')
                    sleep_ms(1000)
                log.log_error('Endless deepsleep due to low battery Ubat = ' + '{:.2f}'.format(bat) , to_print = True, record_time = True)
                deepsleep()
        
    except Exception as err:
        log.counters('error', True)
        log.log_error('airsens_sensor main error', log.error_detail(err), to_print=True, record_time = True)
        
        if bat > conf.UBAT_0:
            if conf.TO_PRINT: print('going to deepsleep for: ' + str(conf.T_DEEPSLEEP_MS) + 'ms' + '{:.2f}'.format(bat))
            deepsleep(conf.T_DEEPSLEEP_MS)
        elif bat != -9999:
            if conf.TO_PRINT: print('Endless deepsleep due to error and low battery Ubat = ' + '{:.2f}'.format(bat))
            deepsleep()

if __name__ == "__main__":
    main()
