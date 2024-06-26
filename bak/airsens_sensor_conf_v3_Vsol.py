# ESP-now
HOST_MAC_ADRESS="3C:61:05:0D:67:CC"
WIFI_CHANNEL = 11
# acquisitions
SENSOR_LOCATION = 'mtl_1' 
T_DEEPSLEEP_MS = 30000
# sensor
SENSORS = {'bme280':['temp', 'hum', 'pres', 'bat'], }
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
SOL_PIN = 34 # measure of the solar panel voltage
#averaging of measurements
AVERAGING = 1
AVERAGING_BME = 1
# PAIR
LED_PIN = 12
BUTTON_PAIR_PIN = 14 # no du port gpio
# SOLAR
# SOLAR = False


