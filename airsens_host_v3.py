#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_host.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-v2

v0.4.0 : 05.02.2023 --> first prototype
v0.4.1 : 26.02.2023 --> optimisation du fichier conf
v0.4.2 : 27.02.2023 --> amelioration de la boucle Main
v0.4.3 : 28.02.2023 --> grand nettoyage
v0.4.4 : 01.03.2022 --> button_1_action simplified
v0.4.5 :05.03.2023 --> small changes Venezia
v1.0.0 : 11.03.2023 --> first production version
v1.1.0 : 07.04.2023 --> adaptation for domoticz process begin
-----------------------------------------------------------------------
v2.0.0 : 10.04.2023 --> new data structure no more compatible with old versions
v2.0.1 : 21.04.2023 --> small cosmetic changes
v2.0.2 : 21.04.2023 --> added menu ABOUT and modified WLAN MAC adresse format
v2.0.3 : 26.04.2023 --> small cosmetics changes
-----------------------------------------------------------------------
v3.0.0 : 30.05.2023 --> Begin with version3 of hard and soft. News are:
                        - Semi-automatic pairing between capteur and centrale
                        - During the pairing the sensor automatically informs the central of:
                                - the connected sensor(s),
                                - the measured quantities.
v3.0.1 : 10.06.2023 --> automatic pairing in developpement
v3.0.2 : 21.06.2023 --> renamed the program to airsens_host_v3.py
-----------------------------------------------------------------------
v3.1.0 : 23.06.2023 --> new datmessage structure no more compatible with old versions.
v3.1.1 : 30.06.2023 --> mqtt in service again (keepalive=60)
v3.1.2 : 14.11.2023 --> added reset, corrected display of mac and added uPython version on about menu
v3.1.3 : 09.01.2024 --> corrigé affichage de l'adresse capteur sur la page Overview
v3.1.4 : 22.03.2024 --> ajouté l'heure de la dernière acquis sur l'affichage 'AUTO'
v3.1.5 : 22.03.2024 --> désactivé le menu 'RESET'
v3.1.6 : 16.04.2024 --> ajouté la synchronistion RTC et dans le menu "about" la page "last measure"'
v3.1.7 : 19.04.2024 --> synchronise esp32 sur le net (ntptime)
v3.1.8 : 19.04.2024 --> optimized the page "Last measure"
"""
VERSION = '3.1.8'
PROGRAM_NAME = 'airsens_host_v3.py'
PROGRAM_NAME_SHORT = 'airsens'
print('Loading "' + PROGRAM_NAME + '" v' + VERSION + ' this may take a while ...')
import airsens_host_conf_v3 as conf

from ubinascii import hexlify, unhexlify
from machine import Pin, Timer, reset, RTC
from espnow import ESPNow
from utime import sleep_ms, time, gmtime, localtime
from network import WLAN, STA_IF, AP_IF, WIFI_PS_NONE
from ntptime import settime, time as ntptime
from math import ceil
from os import uname

from lib.log_and_count import LogAndCount
from lib.ttgo_display import TtgoTdisplay
from lib.simple import MQTTClient

class GlobalVar:
    data_pointer = None
    current_page = None
    current_mode = None
    mac_wlan = None
    mac_formated = None
    sta = None
    channel = None
    rssi = None
    last_mes = []
    last_mes_time = None
    last_mes_sensor = None


class Show:

    def __init__(self,
                 ttgo_display, # classes
                 datas, data_time  # lists to store the datas
                 ):
        self.ttgo_display = ttgo_display
        self.datas = datas
        self.data_time = data_time
        self.refresh_screen_timer = Timer(0)  # timer to switch to the next ecran
        self.refresh_screen_timer.init(period=conf.REFRESH_SCREEN_TIMER_MS, mode=Timer.PERIODIC,
                                       callback=self.refresh_screen_from_timer)
    
    def get_formated_time(self, time=None, ret_type=None):
        if time is None:
            dt = localtime()
        else:
            dt = time
#         year = int(str(dt[0])[2:])
        year = '{:02d}'.format(int(str(dt[0])[2:]))
        month = '{:02d}'.format(dt[1])
        day = '{:02d}'.format(dt[2])
        hour = '{:02d}'.format(dt[3])
        minute = '{:02d}'.format(dt[4])
        second = '{:02d}'.format(dt[5])
        
        if ret_type == None:
            return day + '.' + month + '.' + year + ' ' + hour + ':' + minute + ':' + second
        elif ret_type == 'd':
            return day + '.' + month + '.' + year 
        elif ret_type == 't':
            return hour + ':' + minute + ':' + second
        else:
            return '-.-.- -:-:-'

    # called by the timer because he give a not usefull param
    # and the procedure refresh_screen don't use it
    def refresh_screen_from_timer(self, z):
        self.refresh_screen()

    # refresh the screen for any mode
    def refresh_screen(self):
            
        self.ttgo_display.cls()
        if GlobalVar.current_mode == 0: # mode auto
            GlobalVar.data_pointer = self.manage_data_pointer(GlobalVar.data_pointer, len(self.datas))
            self.display_auto(self.datas, GlobalVar.data_pointer)
            
        elif GlobalVar.current_mode == 1: # mode overview
            self.display_overview(title='OVERVIEW ', n_row=4, n_col=1, data_list=self.datas,
                                       current_page=GlobalVar.current_page, current_mode=GlobalVar.current_mode)
        elif GlobalVar.current_mode == 2: # mode battery status
            self.display_overview(title='BATTERY ', n_row=4, n_col=1, data_list=self.datas,
                                       current_page=GlobalVar.current_page, current_mode=GlobalVar.current_mode)
        elif GlobalVar.current_mode == 3: # mode About
            if GlobalVar.current_page == 0:
                self.ttgo_display.write_line(0, PROGRAM_NAME_SHORT + ' v' + VERSION + '  p1/4', color=self.ttgo_display.COLOR_WHITE)  
                self.ttgo_display.write_about_line(1,'MAC:', str(hexlify(GlobalVar.mac_wlan, ':').decode().upper()))
                self.ttgo_display.write_about_line(2,'WIFI channel:', str(GlobalVar.sta.config("channel")))
                self.ttgo_display.write_about_line(3,'WAN:', conf.WIFI_SSID)
                self.ttgo_display.write_about_line(4,'host IP:', str(GlobalVar.sta.ifconfig()[0]))
            elif GlobalVar.current_page == 1:
                self.ttgo_display.write_line(0, PROGRAM_NAME_SHORT + ' v' + VERSION + '  p2/4', color=self.ttgo_display.COLOR_WHITE)  
                self.ttgo_display.write_about_line(1,'MQTT topic:', '')
                self.ttgo_display.write_about_line(2,'   ', conf.BROKER_TOPIC)
                self.ttgo_display.write_about_line(3,'MQTT broker IP:', '')
                self.ttgo_display.write_about_line(4,'   ', conf.BROKER_IP)
            elif GlobalVar.current_page == 2:
                v_name = uname()[1]
                v = uname()[3]
                v_all = v.split(' ')
                v_detail = v_all[0].split('-')
                v_version = v_detail[0]
                v_plus = v_detail[1] + '-' + v_detail[2] + '-' + v_detail[3]
                v_date = v_all[2]
                self.ttgo_display.write_line(0, PROGRAM_NAME_SHORT + ' v' + VERSION + '  p3/4', color=self.ttgo_display.COLOR_WHITE)  
                self.ttgo_display.write_about_line(1, 'uPython version:', '')
                self.ttgo_display.write_about_line(2, '', v_name + ' ' + v_version)
                self.ttgo_display.write_about_line(3, '', v_plus)
                self.ttgo_display.write_about_line(4, '', v_date)
            elif GlobalVar.current_page == 3:
                self.ttgo_display.write_line(0, PROGRAM_NAME_SHORT + ' v' + VERSION + '  p4/4', color=self.ttgo_display.COLOR_WHITE)  
                self.ttgo_display.write_line(1,'Last measure', '', '', color=self.ttgo_display.COLOR_ORANGE)
                if GlobalVar.last_mes:
                    row_index = 2
                    i_max = len(GlobalVar.last_mes) # - 1
                    i_min = 0 if i_max < 3 else i_max - 3
                    for i in range(i_max, i_min, -1):
                        list_index = i - 1
                        self.ttgo_display.write_line_lastmes(row_index, GlobalVar.last_mes[list_index][0][:5],
                                                              self.get_formated_time(GlobalVar.last_mes[list_index][1], 'd'),
                                                              self.get_formated_time(GlobalVar.last_mes[list_index][1], 't'),
                                                              txt_color=self.ttgo_display.COLOR_CYAN,
                                                              val_color=self.ttgo_display.COLOR_YELLOW)
                        row_index += 1
                        
                else:
                    self.ttgo_display.write_line(2, 'No datas', color=self.ttgo_display.COLOR_RED)
#         elif GlobalVar.current_mode == 4: # mode Reset
#             reset()


    # display the data for the modes auto
    def display_auto(self, datas, data_pointer):
        if datas:
            location, temp_f, hum_f, pres_f, bat_val, bat_f, bat_pc_f, bat_color = datas[data_pointer]
            self.ttgo_display.write_line(0, location[-8:], color=self.ttgo_display.COLOR_WHITE)
            self.ttgo_display.write_line(1, 'Temp = ' + str(temp_f) + '"C', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_line(2, 'Hum  = ' + str(hum_f) + '%', color=self.ttgo_display.COLOR_CYAN)
            if float(pres_f) > 0:
                self.ttgo_display.write_line(3, 'Pres = ' + str(pres_f) + 'hPa', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_line(4, 'Batt = ' + str(bat_f) + 'V ' + str(bat_pc_f) + '%', color=bat_color)
        else:
            self.ttgo_display.write_line(1, 'No datas', color=self.ttgo_display.COLOR_RED)
            

    def display_overview(self, title, n_row, n_col, data_list, current_page, current_mode):
        self.ttgo_display.cls()
        if data_list:
            len_data_list = len(data_list)
            self.ttgo_display.write_line(0, title + ' p '
                                         + str(current_page+1) + '/'
                                         + '{:.0f}'.format(ceil(len_data_list/n_row)),
                                         color=self.ttgo_display.COLOR_WHITE)
            for i in range(0, len(data_list)):
                if (current_page * n_row) <= i < ((current_page + 1) * n_row):
                    row = i - current_page * n_row + 1
                    location, temp_f, hum_f, pres_f, bat_val, bat_f, bat_pc_f, bat_color = data_list[i]
                    if current_mode == 1:
                        self.ttgo_display.write_line_overview(row, '...' + location[-8:], str(temp_f) + 'C', str(hum_f) + '%',
                                                              txt_color=self.ttgo_display.COLOR_CYAN,
                                                              val_color=self.ttgo_display.COLOR_YELLOW)
                    elif current_mode == 2:
                        self.ttgo_display.write_line_bat(row, '...' + location[-8:], str(bat_f) + 'V', str(bat_pc_f) + '%',
                                                         txt_color=self.ttgo_display.COLOR_CYAN, bat_color=bat_color)
        else:
            self.ttgo_display.write_line(1, 'No datas', color=self.ttgo_display.COLOR_RED)
            
    def manage_data_pointer(self, pointer, len_data_list):
        if pointer < len_data_list - 1:
            pointer += 1
        else:
            pointer = 0
        return pointer


class Menu:

    def __init__(self,
                 show, ttgo_display, # classes
                 datas, data_time  # lists to store the datas
                 ):
        self.interrupt_pin = None
        self.show = show
        self.ttgo_display = ttgo_display
        self.choice_ok_timer = Timer(1)  # timer to valid the mode choice
        self.button_debounce_timer = Timer(2)  # timer to debounce the switches
        self.datas = datas
        self.data_time = data_time

    # callback procedure for any button pressed
    # execute the action corresponding to the pressed button
    def on_button_pressed(self, z):
        if self.interrupt_pin == Pin(conf.BUTTON_MODE_PIN):
            self.button_1_action()
        elif self.interrupt_pin == Pin(conf.BUTTON_PAGE_PIN):
            self.button_2_action()

    # debounce any button pressed 
    def button_debounce(self, pin):
        self.interrupt_pin = pin
        self.button_debounce_timer.init(mode=Timer.ONE_SHOT,
                                        period=conf.BUTTON_DEBOUNCE_TIMER_MS, callback=self.on_button_pressed)

    # execute actions selected by the button 1 (executed from the timer choice_ok_timer)
    def choice_ok(self, z):
        # after any change in the modes reinit the refresh timer
        self.show.refresh_screen_timer.deinit()
        if GlobalVar.current_mode == 0:
            'mode auto'
            GlobalVar.data_pointer = -1
        elif GlobalVar.current_mode == 1 or GlobalVar.current_mode == 2:
            'mode overview'
            GlobalVar.current_page = 0
        elif GlobalVar.current_mode == 3:
            GlobalVar.current_page = 0
            pass
           
        self.show.refresh_screen_timer.init(period=conf.REFRESH_SCREEN_TIMER_MS, mode=Timer.PERIODIC,
                                       callback=self.show.refresh_screen_from_timer)
        self.show.refresh_screen()

    def button_1_action(self):
        MODES = ['AUTO', 'OVERVIEW', 'BATTERY', 'ABOUT']# , 'RESET'] # modes
        self.choice_ok_timer.deinit()
        self.ttgo_display.cls()
        # increment ttgo_curent_mode and reset if too big
        len_modes = len(MODES) # store the length of the list
        GlobalVar.current_mode = (GlobalVar.current_mode + 1) % len_modes # use modulo to wrap around
        # display the menu with the active line in yellow
        # use a list comprehension to create a list of colors based on the current mode
        colors = [self.ttgo_display.COLOR_YELLOW if i == GlobalVar.current_mode else self.ttgo_display.COLOR_CYAN for i in range(len_modes)]
        # loop over the modes and colors and write each line
        for i, (mode, color) in enumerate(zip(MODES, colors)):
            self.ttgo_display.write_line(i, mode, color=color)
        # init timer to do action of the select menu entry
        self.choice_ok_timer.init(mode=Timer.ONE_SHOT, period=conf.CHOICE_TIMER_MS, callback=self.choice_ok)
        # change the current mode

    # change the current page
    def button_2_action(self):
        self.show.refresh_screen_timer.deinit()
        if GlobalVar.current_mode == 0:
            # mode auto
            pass
        elif GlobalVar.current_mode == 1 or GlobalVar.current_mode == 2:
            # mode overview
            current_page_inc = 1
            len_liste = 4
            GlobalVar.current_page = self.get_next_page(self.datas, len_liste, GlobalVar.current_page, current_page_inc)
        elif GlobalVar.current_mode == 3:
            # mode About
            GlobalVar.current_page = (GlobalVar.current_page + 1) % 4
            pass
           
        self.show.refresh_screen_timer.init(period=conf.REFRESH_SCREEN_TIMER_MS, mode=Timer.PERIODIC,
                                       callback=self.show.refresh_screen_from_timer)
        self.show.refresh_screen()

    def get_next_page(self, datas, len_liste, current_page, current_page_inc):
        
        # Calculer le nombre total de pages à afficher
        n_pages = len(datas) // len_liste
        if len(datas) % len_liste > 0:
            n_pages += 1
        # Augmenter ou diminuer la page courante selon l'incrément
        # Si la page courante dépasse le nombre total de pages, revenir à la première page
        current_page = (current_page + current_page_inc) % n_pages
        return current_page


class Host:

    def __init__(self):
        self.log = LogAndCount()
        self.ttgo_display = TtgoTdisplay()
        self.ttgo_display.cls()

        GlobalVar.current_mode = conf.DEFAULT_MODE  # default state
        GlobalVar.current_page = conf.DEFAULT_PAGE # 0
        GlobalVar.data_pointer = -1  # start value

        # initialisation listes
        self.datas = []
        self.data_time = []

        # instantiation classes
        self.show = Show(self.ttgo_display, self.datas, self.data_time)
        self.menu = Menu(self.show, self.ttgo_display, self.datas, self.data_time)
        
        # instantiation ESPNow
        self.espnow = ESPNow()
        self.espnow.active(True)
    
    def init_rtc(self):
        # init RTC
        rtc = RTC()
        settime()
        (year, month, day, weekday, hours, minutes, seconds, subseconds) = rtc.datetime()
        sec = ntptime()
        timezone_hour = conf.TIMEZONE
        timezone_sec = timezone_hour * 3600
        sec = int(sec + timezone_sec)
        (year, month, day, hours, minutes, seconds, weekday, yearday) = localtime(sec)
        rtc.datetime((year, month, day, 0, hours, minutes, seconds, 0))

    
    def mqtt_connect_and_subscribe(self):
        try:
            client = MQTTClient(conf.BROKER_CLIENT_ID, conf.BROKER_IP, keepalive=60)
            client.connect(True)
            return client
        except Exception as err:
            self.log.log_error('MQTT_connect_and_subscribe', self.log.error_detail(err), to_print=True)
            self.reset_esp32()
            
    def add_new_measurement(self, new_data):
        location_exist = False
        for i, d in enumerate(self.datas):
            if d[0] == new_data[0]:
                self.datas[i] = new_data
                self.data_time[i] = time()
                location_exist = True
                break
        # append new location
        if not location_exist:
            self.datas.append(new_data)
            self.data_time.append(time())

    def reset_esp32(self):
        wait_time = conf.WAIT_TIME_ON_RESET
        while wait_time > 0:
            print('rebooting ESP32 in ' + str(wait_time) + 's')
            sleep_ms(1000)
            wait_time -= 1
        reset()

    def record_last_measure(self, last_mes_location, last_mes_time):
        for i, m in enumerate(GlobalVar.last_mes):
            if last_mes_location in m:
                del(GlobalVar.last_mes[i])
        d = [last_mes_location, last_mes_time]
        GlobalVar.last_mes.append([last_mes_location, last_mes_time])
            
    def main(self):
        try:
            self.ttgo_display.cls()
            self.ttgo_display.write_centred_line(0, '... Initialazing ...', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_centred_line(2, PROGRAM_NAME, color=self.ttgo_display.COLOR_YELLOW)
            self.ttgo_display.write_centred_line(3, 'Version:' + VERSION, color=self.ttgo_display.COLOR_YELLOW)
            # connect wifi
            sta = WLAN(STA_IF)
            sta.active(True)
            sta.config(ps_mode=WIFI_PS_NONE) # ..then disable power saving
            sta.connect(conf.WIFI_SSID, conf.WIFI_PW)
            print('------------------------------------------------------------------------------------------------------')
            print('connecting the WLAN ', end='')
            for retry in range(200):
                connected = sta.isconnected()
                if connected:
                    print('.')
                    break
                sleep_ms(100)
                print('.', end='')
            if not connected:
                print('\nFailed. Not Connected to: ' + conf.WIFI_SSID)
                self.log.log_error('Connection to ' + conf.WIFI_SSID + ' not possible', to_print = True)            
                self.reset_esp32()
            sta.active(True)
            # initialise global vars
            GlobalVar.sta = sta
            GlobalVar.mac_wlan = sta.config('mac')
            GlobalVar.mac_formated = hexlify(sta.config('mac'), ':').decode().upper()
            GlobalVar.channel = sta.config("channel")
            GlobalVar.rssi = sta.status("rssi")
            # print welcome message
            print(PROGRAM_NAME + ' v' + VERSION)
            print(self.show.get_formated_time())
            print(" ".join(["WLAN STA:",  str(GlobalVar.mac_formated), 'channel:', str(GlobalVar.channel)]))
            print('Host IP:', sta.ifconfig()[0])
            print('Host WLAN:', conf.WIFI_SSID)
            print('MQTT broker IP: ' + conf.BROKER_IP + ' topic: ' + conf.BROKER_TOPIC)
            print('------------------------------------------------------------------------------------------------------')
            self.show.refresh_screen()
            # Setup the button input pin with a pull-up resistor.
            button_mode = Pin(conf.BUTTON_MODE_PIN, Pin.IN, Pin.PULL_UP)
            button_ecran = Pin(conf.BUTTON_PAGE_PIN, Pin.IN, Pin.PULL_UP)
            # Register an interrupt on rising button input.
            button_ecran.irq(self.menu.button_debounce, Pin.IRQ_RISING)
            button_mode.irq(self.menu.button_debounce, Pin.IRQ_RISING)
            # init RTC
            rtc = RTC()
            self.init_rtc()
            # for ever loop
            while True:
                peer, msg = self.espnow.recv()
                if peer and msg:
                    # pairing demand ?
                    if 'PAIRING' in msg.decode('utf-8'):
                        # the demander peer is not in the peers list
                        peer_exist = False
                        for p in self.espnow.get_peers():
                            if peer in p:
                                peer_exist = True
                                break
                        if not peer_exist:
                            # add peer to peers list
                            self.espnow.add_peer(peer)
                        # ask for pairing
                        response = self.espnow.send(peer, str(hexlify(GlobalVar.mac_wlan, ':').decode().upper()) + '/' + str(sta.status('rssi')), True)
                        if response:
                            print('received pairing demand from :', str(hexlify(peer, ':').decode().upper()))
                            print('returned MAC                 :', str(hexlify(GlobalVar.mac_wlan, ':').decode().upper()))
                            print('Rx RSSI                      :', str(str(sta.status('rssi'))))
                            print()
                    elif 'message de test' in msg.decode('utf-8'):
                        print(msg)
                    elif 'scan channels' in msg.decode('utf-8'):
                        print(msg)
                        self.espnow.send(peer, str(sta.status('rssi')))
                    else:
                        try:
                            if len(msg.decode('utf-8').strip()) > 0:
                                '''New message received'''
                                jmb_validation, sensor_id, sensor_location, sensor_type, rx_measurements = msg.decode('utf-8').split(',')
                                dt = rtc.datetime()
                                self.record_last_measure(sensor_location, (dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]))
                                rx_measurements = rx_measurements.split(';')
                                # format the numbers for the small display
                                mes_list = []
                                mes_dict = {}
                                # structure of dictionary
                                # mes_dict['grandeur'] = [value, format for print, format for small ttgo display]
                                mes_dict['temp'] = [0, '{:.2f}', '{:.1f}']
                                mes_dict['hum'] = [0, '{:.1f}', '{:.0f}']
                                mes_dict['pres'] = [0, '{:.1f}', '{:.0f}']
                                mes_dict['gas'] = [0, '{:.0f}', '{:.0f}']
                                mes_dict['alt'] = [0, '{:.0f}', '{:.0f}']
                                mes_dict['sol'] = [-99, '{:.2f}', '{:.2f}']
                                mes_dict['bat'] = [-99, '{:.2f}', '{:.2f}']
                                # pour chaque grandeur dans rx_measurment
                                for rx_mes in rx_measurements:
                                    if rx_mes:
                                        # separe grandeur and value [0] pour grandeur, [1] pour valeur
                                        rx_mes = rx_mes.split(':')
                                        # read the mes_dict value for this grandeur
                                        dict_record = mes_dict[rx_mes[0]]
                                        # set the new value for this record
                                        dict_record[0] = float(rx_mes[1])
                                        # update the mes_dict 
                                        mes_dict[rx_mes[0]] = dict_record
                                        # append this grandeur to the list of measurements
                                        mes_list.append(rx_mes[0])
                                if float(mes_dict['bat'][0]) != -99:
                                    # append the bat, bat_f, bat_pc, bat_pc_f tp the list of measurements
                                    bat = float(mes_dict['bat'][0])
                                    bat_f = '{:.2f}'.format(bat)
                                    bat_pc = min(((bat * conf.BAT_PENTE) + conf.BAT_OFFSET), 100)  
                                    bat_pc_f = '{:.0f}'.format(bat_pc)
                                    
                                    # change the color for the battery to indicate the charge state
                                    if float(bat) < conf.BAT_LOW:
                                        color_bat = self.ttgo_display.COLOR_RED
                                    elif conf.BAT_LOW <= float(bat) <= conf.BAT_OK:
                                        color_bat = self.ttgo_display.COLOR_ORANGE
                                    elif float(bat) > conf.BAT_OK:
                                        color_bat = self.ttgo_display.COLOR_GREEN
                                    else:
                                        color_bat = self.ttgo_display.COLOR_WHITE
                                else:
                                    bat = 0
                                    bat_f = '{:.2f}'.format(bat)
                                    bat_pc = 0  
                                    bat_pc_f = 0
                                    color_bat = self.ttgo_display.COLOR_WHITE
                                    
                                
                                # prepare the list of éléments for adding a new measurement
                                new_measurement_list = [
                                    sensor_id, #[:8],
                                    mes_dict['temp'][2].format(mes_dict['temp'][0]),
                                    mes_dict['hum'][2].format(mes_dict['hum'][0]),
                                    mes_dict['pres'][2].format(mes_dict['pres'][0]),
                                    mes_dict['bat'][2].format(mes_dict['bat'][0]),
                                    bat_f, bat_pc_f, color_bat
                                    ]
                                self.add_new_measurement(new_measurement_list)
                                
                                # check if connected to Wi-FI and if not reconnect 

                                if not sta.isconnected():
                                    sta = WLAN(STA_IF)
                                    sta.active(True)
                                    sta.config(ps_mode=WIFI_PS_NONE) # ..then disable power saving
                                    sta.connect(conf.WIFI_SSID, conf.WIFI_PW)
                                for retry in range(200):
                                    connected = sta.isconnected()
                                    if connected:
                                        break
                                    sleep_ms(100)
                                    print('.', end='')
                                if not connected:
                                    print('\nFailed. Not Connected to: ' + conf.WIFI_SSID)
                                    self.log.log_error('Connection to ' + conf.WIFI_SSID + ' not possible', to_print = True)            
                                    self.reset_esp32()

                                # has the message the right identificator
                                if jmb_validation == 'jmb':
                                    passe = self.log.counters('passe', True)
#                                     try:
#                                         # create the list of data  to send
#                                         message = [conf.BROKER_TOPIC, sensor_location]
#                                         # append the values in the list
#                                         mes = []
# #                                         print(mes_dict)
#                                         for act_mes in mes_list:
#                                             mes.append(mes_dict[act_mes][0])
#                                         message.append(str(mes).replace(',',':'))
#                                         # add the rssi to the list
#                                         message.append(str(sta.status('rssi')))
#                                         # create the message
#                                         msg = ','.join(message)
# #                                         print('msg:', msg)
#                                         # send the message to MQTT
#                                         client = self.mqtt_connect_and_subscribe()  # conf.BROKER_CLIENT_ID, conf.BROKER_IP, conf.BROKER_TOPIC)
#                                         if client is not None:
#                                             client.publish(conf.BROKER_TOPIC, msg)
#                                             client.disconnect()
#                                         else:
#                                             self.log.log_error('MQTT client is None', to_print = True)
# 
#                                     except Exception as err:
#                                         self.log.log_error('MQTT publish', self.log.error_detail(err), to_print = True)
#                                         self.reset_esp32()
                                        
                                    # init the list of data to print
                                    # add the values with the format
                                    payload = []
                                    for act_mes in mes_list:
                                        payload.append(act_mes + ':' + str(mes_dict[act_mes][1].format(mes_dict[act_mes][0])))
                                    message = []
                                    message = "/".join([conf.BROKER_TOPIC, sensor_id, sensor_location, sensor_type, str(payload) ])
                                    
                                    # send the message to MQTT
                                    client = MQTTClient(conf.BROKER_CLIENT_ID, conf.BROKER_IP, keepalive=60)
                                    client.connect(True)
                                    if client is not None:
                                        client.publish(conf.BROKER_TOPIC, message)
                                        client.disconnect()
                                    else:
                                        self.log.log_error('MQTT client is None', to_print = True)
                                        
                                    # add the RSSI and errors to the list
                                    txt_mes = [str(passe), self.show.get_formated_time()]
                                    txt_mes.append(message)
                                    txt_mes.append('RSSI:' + str(sta.status('rssi')))
                                    txt_mes.append('errors:' + str(self.log.counters('error')))
                                    # create the string to print and print it
                                    txt = ' '.join(txt_mes)
                                    print(txt)
                                        
                                else:
                                    self.log.log_error('wrong message received', to_print = True)
                        except ValueError:
                            print('ValueError', msg)
                            pass
                        except Exception as err:
                            self.log.log_error('Main', self.log.error_detail(err), to_print = True)
                            self.reset_esp32()
        except Exception as err:
            self.log.log_error('Main', self.log.error_detail(err), to_print = True)
            self.reset_esp32()

def main():
    host = Host()
    host.main()

if __name__ == '__main__':
    main()
