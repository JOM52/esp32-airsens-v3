# Projet : esp32-airsens 

Version 3

**esp32-airsens** est un projet de domotique qui consiste à créer des capteurs intelligents et connectés pour surveiller l'environnement. Ces capteurs sont basés sur le processeur ESP32 et le langage Micropython. Ils peuvent mesurer différents paramètres tels que la température, l'humidité, la pression atmosphérique et le niveau de charge de batterie. Ils envoient ensuite ces données à une centrale via un réseau sans fil. La centrale est un système Liligo-TTGO qui reçoit les données des capteurs, les publie sur un broker MQTT et les affiche sur un écran. L'écran permet de visualiser les informations pertinentes pour chaque capteur.

La version 3 du projet est basée sur la version 2 et introduit les éléments suivants:

- Association semi-automatique du capteur et de la centrale.
- Lors de l'association du capteur et de la centrale le capteur informe automatiquement la centrale du ou des capteurs connectés, des grandeurs mesurées ainsi que de l'ordre dans lequel ces informations seront transmises à la centrale par chaque capteur. 
- Ajout d'une cellule photovoltaïque pour la recharge en continu de la batterie du capteur.

## Schéma de principe
https://github.com/JOM52/esp32-airsens-v3/blob/main/schema/airsens_v3_0%20schema%20de%20principe.odg

## Elément capteur:

La version V1.0 proto du hardware fonctionne bien. Le hardware sera complétée avec un bouton et une led pour démarrer et contrôler le processus d'association du capteur avec la centrale. 

Pour réduire la consommation d'énergie, cette version hard ne contient que l'essentiel pour faire fonctionner le capteur. La configuration se fait par une interface FTDI (USB to UART) qui se branche au besoin et, si la cellule photovoltaïque ne suffit à maintenir la batterie en charge, les batteries se rechargent à part.

Dans l'exemple ci-après, le capteur est un BME 280 qui permet la mesure de la température, du taux d'humidité et de la pression atmosphérique.

https://github.com/JOM52/esp32-airsens-v3/blob/main/schema/airsens_v3_0.kicad_sch

On peut aussi utiliser des capteurs hdc1080 qui mesurent seulement la température et l'humidité relative.

### Hardware

Le hardware ESP32 est un microcontrôleur qui intègre des fonctionnalités de Wi-Fi et de Bluetooth, ainsi que des modules de gestion de l'alimentation, des filtres et des amplificateurs. Il peut se connecter à différents types de capteurs I2C, un protocole de communication série synchrone. 

### Software

Ce projet implémente les drivers pour les capteurs de type BME280, BME680 et HDV1080. Ces capteurs permettent de mesurer différentes grandeurs liées au climat ou à l'environnement. Dans la version 2 du projet, on peut choisir le type et le nombre de capteurs à utiliser dans le fichier de configuration. Toutefois, il faut tenir compte de l'impact sur la consommation d'énergie et la durée de vie de la batterie. Avec une batterie Li-Ion de 2Ah (type 18650), on peut, avec un seul capteur,  réaliser une mesure toutes les 5 minutes pendant environ un an.

#### Fichier de configuration du capteur

Le fichier de configuration permet de personnaliser le fonctionnement d'un capteur sans avoir à modifier le code source. Il contient des lignes de code en Micropython qui assignent des valeurs à des variables globales. Ces variables sont ensuite utilisées par le programme principal pour paramétrer les différents éléments du système. Le fichier de configuration n'a pas besoin d'une structure particulière, mais il peut être organisé en sections pour faciliter la lecture et la compréhension.

Le code ci-après permet de configurer un capteur connecté à un ESP32 qui utilise le protocole ESP-now pour envoyer des données à un proxy. Le capteur peut être de type hdc1080, bme280 ou bme680 et mesure la température, l'humidité, la pression, le gaz et l'altitude selon le cas. 

Le capteur est alimenté par une batterie et entre en mode deepsleep entre chaque acquisition pour économiser de l'énergie. La tension de la batterie est mesurée par un pont diviseur de tension. 

Le code utilise les constantes définies au début du fichier pour paramétrer les différents éléments du système. Par exemple, SENSOR_LOCATION indique le nom du capteur, T_DEEPSLEEP_MS indique la durée du mode deepsleep en millisecondes, SENSORS indique les types de capteurs disponibles et leurs mesures associées, ON_BATTERY indique si le capteur est alimenté par une batterie ou non, etc. 

L'association capteur-centrale se fait "à la main" en renseignant le champ PROXY_MAC_ADRESS avec la MAC_ADRESS de la centrale dans le fichier de configuration du capteur.

Le code ci-dessous montre un exemple de fichier de configuration pour ce système:

```
# acquisitions
SENSOR_LOCATION = 'domo_2' 
T_DEEPSLEEP_MS = 300000
# sensor
SENSORS = {
    'hdc1080':['temp', 'hum'],
    'bme280':['temp', 'hum', 'pres'],
    'bme680':['temp', 'hum', 'pres', 'gas', 'alt'],
  }
# power supply
TO_PRINT = True
ON_BATTERY = True
UBAT_100 = 4.2
UBAT_0 = 3.2
# I2C hardware config
BME_SDA_PIN = 21
BME_SCL_PIN = 22
# analog voltage measurement
R1 = 977000 # first divider bridge resistor
R2 = 312000 # second divider bridge resistor
DIV = R2 / (R1 + R2)  
ADC1_PIN = 35 # Measure of analog voltage (ex: battery voltage following)
#averaging of measurements
AVERAGING = 1
AVERAGING_BAT = 1
AVERAGING_BME = 1

# ESP-now
PROXY_MAC_ADRESS = '3C:61:05:0D:67:CC'
WIFI_CHANNEL = 1
```



### Messages

Les valeurs mesurées pour chaque grandeur sont regroupées et transmises au broker MQTT dans un seul message. Le format de principe du message est le suivant:

`msg = (topic, location, grandeur 1, grandeur 2, .... , grandeur n, bat, rssi)`

Les grandeurs mesurées sont dépendantes des possibilités du capteur par exemple:

- HDC1080 : température, humidité
- BME280  : température, humidité, pression
- BME680  : température, humidité, pression, qualité de l'air

Les valeurs transmises à MQTT sont fonction de la configuration définie dans le fichier _conf du capteur.

#### Principe du logiciel capteur

Pour économiser l'énergie consommée, le capteur est placé en ***deepsleep*** entre chaque mesure. Le temps de sommeil est défini dans le fichier de configuration, en principe 5 minutes. Lors d'un éveil, le capteur lit le fichier de configuration, initialise les constantes, charge les librairies nécessaire, initialise le capteur, fait la mesure, mesure l'état de la batterie, transmets les valeurs à la centrale puis se met en ***deepsleep***

## Centrale

### Software

La centrale est le cœur du système de domotique. Elle a plusieurs fonctions :

- Elle reçoit et traite les messages valides envoyés par les capteurs sans fil.
- Elle adapte les messages au format de l'application de domotique choisie (domoticz, jeedom, ...).
- Elle transmet les valeurs de mesure à MQTT, un protocole de communication qui permet de diffuser les informations aux abonnés.
- Elle affiche différentes informations sur un écran couleur, comme les mesures et l'état des batteries des capteurs.

Les messages reçus ne sont pas confirmés au capteur. Cela signifie que si la centrale n'est pas disponible au moment où le capteur envoie un nouveau message, celui-ci est perdu. En principe cela ne pose pas de problème pour les mesures de grandeurs physiques qui varient peu dans le temps.

La centrale accepte tous les messages qui ont une structure correcte et qui proviennent d'un capteur dont elle connaît l'adresse MAC. Si le capteur est déjà enregistré dans le fichier de configuration et dans la mémoire programme, les nouvelles valeurs remplacent les anciennes. Sinon, le capteur est automatiquement reconnu et ajouté au fichier de configuration et à la mémoire programme.

La centrale dispose de deux boutons sur la version matérielle des Lilygo-ttgo qui permettent de sélectionner les différents affichages programmés. le choix se fait lorsque aucun bouton n'est pressé pendant 1 seconde.

Pour transmettre les mesures à MQTT, la centrale se connecte au réseau WIFI. Les valeurs de mesure sont formatées selon les besoins de l'application de domotique choisie puis envoyées au broker MQTT qui les publie aux abonnés.

### Fichier de configuration de la centrale

Le fichier de configuration est un fichier standard Micropython. 

```
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file: airsens_central_v2.py 
author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-v2

v0.4.0 : 05.02.2023 --> first prototype
v0.4.1 : 05.03.2023 --> small changes Venezia
v2.0.0 : 11.04.2023 --> adapté pour la version 2
"""
from ubinascii import hexlify
from machine import unique_id

#SYSTEM
WAIT_TIME_ON_RESET = 300 # seconds to wait before the machine reset in case of error

# MQTT
BROKER_IP = '192.168.1.108'
TOPIC = 'airsens_domoticz'
BROKER_CLIENT_ID = hexlify(unique_id())

# TTGO
BUTTON_MODE_PIN = 35
BUTTON_PAGE_PIN = 0
DEFAULT_MODE = 0 # Mode auto
DEFAULT_ROW_ON_SCREEN = 5 # given by the display hardware and the font size
CHOICE_TIMER_MS = 1000 # milli seconds
REFRESH_SCREEN_TIMER_MS = 10000 # mode auto: display next location each ... milli seconds
BUTTON_DEBOUNCE_TIMER_MS = 10 # milli seconds

# WIFI
WIFI_WAN = 'jmb-home'
WIFI_PW = 'lu-mba01'

# BATTERY
BAT_MAX = 4.2 # 100%
BAT_MIN = 3.2 # 0%
BAT_OK = 3.4 # si ubat plus grand -> ok
BAT_LOW = 3.3 # si ubat plus petit -> alarm
BAT_PENTE = (100-0)/(BAT_MAX-BAT_MIN)
BAT_OFFSET = 100 - BAT_PENTE * BAT_MAX
print('% = ' + str(BAT_PENTE) + ' + ' + str(BAT_OFFSET))
```

#### Code de la centrale évolution

*Dans une prochaine version il est prévu de modifier le programme pour:*

- *introduire un processus d'identification et d'enregistrement des capteurs par la centrale. Ainsi seuls des capteurs reconnus, validés et enregistrés seront autorisés à transmettre des mesures à la centrale.*
- *de crypter les message pour empêcher que les messages soient lus par des entités non autorisées.*

### Hardware

La centrale utilise un circuit Lilygo-ttgo qui comprend le processeur, une interface USB, un affichage de 135x240 pixels et deux boutons. Dans la version actuelle, ce circuit est utilisé tel quel. Les boutons sont utilisés comme suit:

- bouton 1 --> next **Mode**

- bouton 2 --> next **Page**

  le choix se fait lorsque aucun bouton n'est pressé pendant 1 seconde

### Connection réseau attribution des canaux

Il faut désactiver l'attribution automatique des canaux sur le routeur Wi-Fi : si le routeur Wi-Fi de votre réseau Wi-Fi est configuré pour attribuer automatiquement le canal Wi-Fi, il peut changer le canal du réseau s'il détecte des interférences provenant d'autres routeurs Wi-Fi. Lorsque cela se produit, les appareils ESP connectés au réseau Wi-Fi changeront également de canal pour correspondre au routeur, mais les appareils ESPNow uniquement resteront sur le canal précédent et la communication sera perdue. Pour atténuer cela, configurez votre routeur Wi-Fi pour qu'il utilise un canal Wi-Fi fixe ou configurez vos appareils pour analyser à nouveau les canaux Wi-Fi s'ils ne parviennent pas à trouver leurs homologues attendus sur le canal actuel.

Il faut configurer le sensor pour utiliser le même canal (channel) que le router wifi. Le canal utilisé par la centrale peut être trouvée dans le menu ABOUT. C'est cette valeur qui doit être introduite dans le fichier de configuration du sensor p. ex.: WIFI_CHANNEL = 1

## MQTT mosquitto

Le logiciel MQTT fonctionne comme un éditeur (*broker*). Il est à l'écoute des auteur (*publishers*) qui publient des données et les diffuse auprès des abonnés (*subscribers*).

MQTT est installé comme un service sur un Raspberry PI. Il reçoit les informations transmises par les auteurs qui publient les données (les capteurs) et les rediffuse vers tous les abonnés sans aucun contrôle de validité. Son rôle se limite à faire transiter les données depuis les auteurs vers les abonnés. La responsabilité de la validation et du contrôle des données est laissé à la centrale.

Pour recevoir les données depuis le broker il suffit souscrire au broker sur le TOPIC concerné.

----------- *description de l'installation et de la configuration de MQTT à placer ici*  ----------

## Programme python airsens_mqtt

C'est un programme Python qui s'abonne à des topics MQTT pour les capteurs dont les données doivent être enregistrées dans une base de données. Ce programme est installé comme un service sur le raspberry PI. 

Il consulte le fichier de configuration de la centrale pour connaitre les mac-adress des capteurs reconnus par la centrale.

Il reçoit les données depuis MQTT, vérifie que le capteur est reconnu et, si oui, les enregistre dans la base de données airsens sur MariaDB (anciennement MySql) sur le Raspberry PI .

Ce programme se charge également d'alarmer l'utilisateur (par un mail, un WhatsApp ou autre) lorsque l'accumulateur d'un capteur doit être rechargé. 

*description de l'installation d'un service sur RPI à placer ici*

## Programme de domotique

Les mesures des capteurs peuvent être transmises à un logiciel de domotique (domoticz, jeedom, ...) pour être représentés graphiquement ou intervenir dans différentes alarmes. 

La gestion des messages à destination des logiciels de domotique se font pour chaque logiciel  (domoticz, jeedom, ...) dans une classe spécifique.

Pour Domoticz, le format des messages est le suivant:

 {  "**command**": "udevice",  "**idx**" : 7,  "**nvalue**" : 0,  "**svalue**" : "90;2975.00", "**parse**": false } avec:

- **command**: udevice pour un capteur
- **idx**: index du capteur dans domoticz
- **nvalue**: sans importance pour un capteur
- **svalue**: valeurs mesurées p.ex. température; humidité; pression, ...

plus de détails: https://piandmore.wordpress.com/2019/02/04/mqtt-out-for-domoticz/

## Corrections à apporter

#### Capteurs

- [ ] Compléter le topic par le type de capteur et un id unique pour pouvoir assurer de différentier chaque capteur donc 
  le TOPIC sera constitué comme suit: SENSOR_LOCATION / SENSOR_TYPE / SENSOR_ID 
- [ ] Adapter le programme airsens_v2_jeedom.py au nouveau TOPIC
- [ ] Adapter la table airsens_v2 dans la base de données airsens sur le RPI 139 pour le nouveau TOPIC
- [ ] Analyser si la possibilité d'avoir plusieurs sensors sur un seul capteur à du sens et si non supprimer le code correspondant
- [ ] Prévoir de désactiver les messages pour le suivi par Jeedom si le sensor est sur batterie (ON_BATTERY = False)
- [ ] Modifier la valeur du condensateur (C3) (tester 10uF) pour que le reset se fasse à l'enclenchement du sensor
- [ ] Etudier si l'implémentation du FTDI sur le capteur à du sens ou s'il rester avec un FTDI externe

#### Central

- [ ] Analyser pourquoi le programme se plante et ne redémarre pas en cas de coupure réseau
- [ ] Corriger : En cas de coupure réseau, le central se perd et ne redémarre pas automatiquement

#### Communications Central-Capteurs

- [ ] Permettre à un capteur et un central de s'identifier mutuellement la première fois qu'ils se mettent en communication. P. ex.: un bouton "Synch" sur le capteur et sur le central qui lance la procédure et la synchro se fait.

#### Jeedom

- [ ] Actuellement c'est le RPI108 qui envoie un message au broker MQTT à destination de Jeedom. Corriger et envoyer le message directement depuis le ESP32 Central.

## GITHUB

Ce projet est maintenu dans GitHub, avec une licence GPL. Il est accessible par le lien 
https://github.com/JOM52/esp32-airsens-v2





Pravidondaz avril 2023
