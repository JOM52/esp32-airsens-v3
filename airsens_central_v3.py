#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_central.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-v2

v0.4.0 : 05.02.2023 --> first prototype
v0.4.1 : 26.02.2023 --> optimisation du fichier conf
v0.4.2 : 27.02.2023 --> amelioration de la boucle Main
v0.4.3 : 28.02.2023 --> grand nettoyage
v0.4.4 : 01.03.2022 --> button_1_action simplified
v0.4.5 : 05.03.2023 --> small changes Venezia
v1.0.0 : 11.03.2023 --> first production version
v1.1.0 : 07.04.2023 --> adaptation for domoticz process begin
-----------------------------------------------------------------------
v2.0.0 : 10.04.2023 --> new data structure no more compatible with old versions
v2.0.1 : 21.04.2023 --> small cosmetic changes
v2.0.2 : 21.04.2023 --> added menu ABOUT and modified WLAN MAC adresse format
v2.0.3 : 26.04.2023 --> small cosmetics changes
"""
VERSION = '2.0.3'
PROGRAM_NAME = 'airsens_central_v2.py'
PROGRAM_NAME_SHORT = 'airsens'
print('Loading "' + PROGRAM_NAME + '" v' + VERSION + ' please be patient ...')
import airsens_central_conf_v2 as conf

from ubinascii import hexlify, unhexlify
from machine import Pin, Timer, reset
from espnow import ESPNow
from utime import sleep_ms, localtime, time, gmtime
from network import WLAN, STA_IF, AP_IF, WIFI_PS_NONE
from ntptime import settime
from math import ceil

from lib.log_and_count import LogAndCount
from lib.ttgo_display import TtgoTdisplay
from lib.umqttsimple import MQTTClient


class GlobalVar:
    data_pointer = None
    current_page = None
    current_mode = None
    wlan_mac = None
    sta = None
    


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
                self.ttgo_display.write_line(0, PROGRAM_NAME_SHORT + ' v' + VERSION + '  p1/2', color=self.ttgo_display.COLOR_WHITE)  
                self.ttgo_display.write_about_line(1,'MAC:', str(hexlify(GlobalVar.wlan_mac, ':').decode().upper()))
                self.ttgo_display.write_about_line(2,'WIFI channel:', str(GlobalVar.sta.config("channel")))
                self.ttgo_display.write_about_line(3,'WAN:', conf.WIFI_WAN)
                self.ttgo_display.write_about_line(4,'Central IP:', str(GlobalVar.sta.ifconfig()[0]))
            elif GlobalVar.current_page == 1:
                self.ttgo_display.write_line(0, PROGRAM_NAME_SHORT + ' v' + VERSION + '  p2/2', color=self.ttgo_display.COLOR_WHITE)  
                self.ttgo_display.write_about_line(1,'MQTT topic:', '')
                self.ttgo_display.write_about_line(2,'   ', conf.TOPIC)
                self.ttgo_display.write_about_line(3,'MQTT broker IP:', '')
                self.ttgo_display.write_about_line(4,'   ', conf.BROKER_IP)
            else:
                self.ttgo_display.write_line(1, 'No datas', color=self.ttgo_display.COLOR_RED)


    # display the data for the modes auto
    def display_auto(self, datas, data_pointer):
        if datas:
            location, temp_f, hum_f, pres_f, bat_val, bat_f, bat_pc_f, bat_color = datas[data_pointer]
            self.ttgo_display.write_line(0, location, color=self.ttgo_display.COLOR_WHITE)
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
                        self.ttgo_display.write_line_overview(row, location, str(temp_f) + 'C', str(hum_f) + '%',
                                                              txt_color=self.ttgo_display.COLOR_CYAN,
                                                              val_color=self.ttgo_display.COLOR_YELLOW)
                    elif current_mode == 2:
                        self.ttgo_display.write_line_bat(row, location, str(bat_f) + 'V', str(bat_pc_f) + '%',
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
        MODES = ['AUTO', 'OVERVIEW', 'BATTERY', 'ABOUT'] # modes
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
            GlobalVar.current_page = (GlobalVar.current_page + 1) % 2
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


class Central:

    def __init__(self):
        self.log = LogAndCount()
        self.ttgo_display = TtgoTdisplay()
        self.ttgo_display.cls()

        GlobalVar.current_mode = conf.DEFAULT_MODE  # default state
        GlobalVar.current_page = 0
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
    
    def get_formated_time(self, time=None):
        if time is None:
            dt = localtime()
        else:
            dt = localtime(int(time))
        year = '{:04d}'.format(dt[0])
        month = '{:02d}'.format(dt[1])
        day = '{:02d}'.format(dt[2])
        hour = '{:02d}'.format(dt[3])
        minute = '{:02d}'.format(dt[4])
        second = '{:02d}'.format(dt[5])
        return day + '.' + month + '.' + year + ' ' + hour + ':' + minute + ':' + second

    def wifi_reset(self):  # Reset Wi-FI to AP_IF off, STA_IF on and disconnected
        sta = WLAN(STA_IF)
        sta.active(False)
        ap = WLAN(AP_IF)
        ap.active(False)
        sta.active(True)
        return sta, ap
    
    def mqtt_connect_and_subscribe(self):
        try:
            client = MQTTClient(conf.BROKER_CLIENT_ID, conf.BROKER_IP)
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

            

    def main(self):
        try:
            self.ttgo_display.cls()
            self.ttgo_display.write_centred_line(0, '... Initialazing ...', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_centred_line(2, PROGRAM_NAME, color=self.ttgo_display.COLOR_YELLOW)
            self.ttgo_display.write_centred_line(3, 'Version:' + VERSION, color=self.ttgo_display.COLOR_YELLOW)
            sta, ap = self.wifi_reset()  # Reset Wi-FI to AP off, STA on and disconnected
            sta.config(ps_mode=WIFI_PS_NONE) # ..then disable power saving
            GlobalVar.wlan_mac = sta.config('mac')
            GlobalVar.sta = sta
            sta.connect(conf.WIFI_WAN, conf.WIFI_PW)
            while not sta.isconnected():
                sleep_ms(200)
            txt = " ".join(["WLAN STA:",  str(hexlify(sta.config('mac'), ':').decode().upper()), 'channel:', str(sta.config("channel"))])
            print('---------------------------------------------------------------------------------------------------------------------')
            print(PROGRAM_NAME + ' v' + VERSION)
            print(self.get_formated_time())
            print("Central MAC Address:", hexlify(GlobalVar.wlan_mac, ':').decode().upper()) # Show MAC for peering
            print(txt)
            print('Central IP:', sta.ifconfig()[0])
            print('Central WLAN:', conf.WIFI_WAN)
            print('MQTT broker IP: ' + conf.BROKER_IP + ' topic: ' + conf.TOPIC)
            print("Main running on channel:", sta.config('channel'))
            print('ESPNow active:', self.espnow)
            print('---------------------------------------------------------------------------------------------------------------------')
            # Setup the button input pin with a pull-up resistor.
            button_mode = Pin(conf.BUTTON_MODE_PIN, Pin.IN, Pin.PULL_UP)
            button_ecran = Pin(conf.BUTTON_PAGE_PIN, Pin.IN, Pin.PULL_UP)
            # Register an interrupt on rising button input.
            button_ecran.irq(self.menu.button_debounce, Pin.IRQ_RISING)
            button_mode.irq(self.menu.button_debounce, Pin.IRQ_RISING)
            for peer, msg in self.espnow:
                if peer and msg:
                    if len(msg.decode('utf-8').strip()) > 0:
                        '''New message received'''
#                         print('new message received', msg)
                        jmb_id, location, sensor_type, rx_measurements = msg.decode('utf-8').split(',')
                        rx_measurements = rx_measurements.split(';')
                        # format the numbers for the small display
                        mes_list = []
                        mes_dict = {}
                        # structure of dictionary
                        # mes_dict['grandeur'] = [value, format for print, format for small ttgo display]
                        mes_dict['temp'] = [0, '{:.2f}', '{:.1f}']
                        mes_dict['hum'] = [0, '{:.0f}', '{:.0f}']
                        mes_dict['pres'] = [0, '{:.0f}', '{:.0f}']
                        mes_dict['gas'] = [0, '{:.0f}', '{:.0f}']
                        mes_dict['alt'] = [0, '{:.0f}', '{:.0f}']
                        mes_dict['bat'] = [0, '{:.2f}', '{:.2f}']
                        # pour chaque grandeur dans rx_measurment
                        for rx_mes in rx_measurements:
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
                        
                        # prepare the list of éléments for adding a new measurement
                        new_measurement_list = [
                            sensor_type,
                            mes_dict['temp'][2].format(mes_dict['temp'][0]),
                            mes_dict['hum'][2].format(mes_dict['hum'][0]),
                            mes_dict['pres'][2].format(mes_dict['pres'][0]),
                            mes_dict['bat'][2].format(mes_dict['bat'][0]),
                            bat_f, bat_pc_f, color_bat
                            ]
                        self.add_new_measurement(new_measurement_list)
                        
                        # check if connected to Wi-FI and if not reconnect 
                        if not sta.isconnected():
                            sta, ap = self.wifi_reset()  # Reset Wi-FI to AP off, STA on and disconnected
                            sta.connect(conf.WIFI_WAN, conf.WIFI_PW)
                            while not sta.isconnected():
                                sleep_ms(200)
                            self.log.log_error('WIFI connection lost, reconnecting', to_print = True)
                            sta.config(ps_mode=WIFI_PS_NONE)  # ..then disable power saving

                        # has the message the right identificator
                        if jmb_id == 'jmb':
                            passe = self.log.counters('passe', True)
                            try:
                                # create the list of data  to send
                                txt_mes = [conf.TOPIC, location]
                                # append the values in the list
                                mes = []
                                for act_mes in mes_list:
                                    mes.append(mes_dict[act_mes][0])
                                txt_mes.append(str(mes).replace(',',':'))
                                # add the rssi to the list
                                txt_mes.append(str(sta.status('rssi')))
#                                 print(txt_mes)
                                # create the message
                                msg = ','.join(txt_mes)
                                # send the message to MQTT
                                client = self.mqtt_connect_and_subscribe()  # conf.BROKER_CLIENT_ID, conf.BROKER_IP, conf.TOPIC)
                                if client is not None:
                                    client.publish(conf.TOPIC, msg)
#                                     print('msg sended to mqtt:', msg)
                                    client.disconnect()
                                else:
                                    self.log.log_error('MQTT client is None', to_print = True)

                            except Exception as err:
                                self.log.log_error('MQTT publish', self.log.error_detail(err), to_print = True)
                                self.reset_esp32()
                            # init the list of data to print
                            txt_mes = [str(passe), self.get_formated_time(), conf.TOPIC, location, sensor_type]
                            # add the values with the format
                            mes1 = []
                            for act_mes in mes_list:
#                                 txt_mes.append(act_mes + ':' + str(mes_dict[act_mes][1].format(mes_dict[act_mes][0])))
                                mes1.append(act_mes + ':' + str(mes_dict[act_mes][1].format(mes_dict[act_mes][0])))
                            txt_mes.append(str(mes1))
                            # add the RSSI and errors to the list
                            txt_mes.append('RSSI:' + str(sta.status('rssi')))
                            txt_mes.append('errors:' + str(self.log.counters('error')))
                            # create the string to print and print it
                            txt = ' '.join(txt_mes)
                            print(txt)
                                
                        else:
                            self.log.log_error('wrong message received', to_print = True)
                    else:
                        print('---------------------------------------------------------------------------------------------------------------------')

        except Exception as err:
            self.log.log_error('Main', self.log.error_detail(err), to_print = True)
            self.reset_esp32()

def main():
    central = Central()
    central.main()

if __name__ == '__main__':
    main()
