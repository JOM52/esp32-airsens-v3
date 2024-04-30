#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file: airsens_host_conf.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-class

v0.4.0 : 05.02.2023 --> first prototype
v0.4.1 : 05.03.2023 --> small changes Venezia
v0.4.2 : renamed to airsens_host_conf.py
v0.4.3 : battery level values adjusted
"""
from ubinascii import hexlify
from machine import unique_id
#SYSTEM
WAIT_TIME_ON_RESET = 10 # seconds to wait before the machine reset in case of error
# MQTT
BROKER_IP = '192.168.1.110'
# BROKER_IP = '192.168.1.108'
# BROKER_IP = '192.168.1.102'
BROKER_TOPIC = 'airsens_v3'
BROKER_CLIENT_ID = hexlify(unique_id())
#TIMEZONE
TIMEZONE = 2
# TTGO
BUTTON_MODE_PIN = 35
BUTTON_PAGE_PIN = 0
DEFAULT_MODE = 3 # Mode auto
DEFAULT_PAGE = 3
DEFAULT_ROW_ON_SCREEN = 5 # given by the display hardware and the font size
CHOICE_TIMER_MS = 1000 # milli seconds
BUTTON_DEBOUNCE_TIMER_MS = 10 # milli seconds
REFRESH_SCREEN_TIMER_MS = 20000 # mode auto: display next location each ... milli seconds

# WIFI
WIFI_SSID = 'jmb-airsens'
WIFI_PW = '54f-614-c3b'
# WIFI_SSID = 'Helix007'
# WIFI_PW = 'Lucky001'
# WIFI_SSID = 'Desrochers2023'
# WIFI_PW = 'Gd489337'

# BATTERY
BAT_MAX = 4.2 # 100%
BAT_MIN = 3.6 # 0%
BAT_OK = BAT_MIN + 0.2 # si ubat plus grand -> ok
BAT_LOW = BAT_MIN + 0.1 # si ubat plus petit -> alarm
BAT_PENTE = (100-0)/(BAT_MAX-BAT_MIN)
BAT_OFFSET = 100 - BAT_PENTE * BAT_MAX
# print('Charge bat % = ' + str(BAT_PENTE) + ' * Ubat' + ' + ' + str(BAT_OFFSET))

