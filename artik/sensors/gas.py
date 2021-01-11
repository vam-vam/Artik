'''Measure the gas with sensor MQ-X and a Raspberry Pi.'''
# vam.vam
# MIT License
# TODO - other sensor, function with small code, the most simple function

from time import time, sleep
import RPi.GPIO as GPIO
import math
#change for our A/D converter. Must be exist function read(), return float value.
#from MCP3008 import MCP3008 as adc_driver
from artik.sensors import mcp3208 as adc_driver

import logging

try:
    ADC = adc_driver()
except:
    ADC = None

class sensorMQ_X:

    __LOG_FORMAT = '%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) - sensorMQ_X : %(message)s'

    def __init__(self, do_pin=None, analog_pin=None, ro=10, init=ADC):
        logging.basicConfig(level=logging.ERROR, format=self.__LOG_FORMAT)
        self.Ro = ro
        self.adc = init
        self.ADC_RATE = 1023.0             #10-bit A/D converter
        self.alarm_action = None
        self.alarm = 0
        if self.adc is None:
            logging.error("Error init for adc converter.(MQ-X)")
            raise NameError("Error init for adc converter.(MQ-X)")
        if isinstance(analog_pin, int):
            self.analog_pin = analog_pin
            try:
                self.adc = ADC
                ######################### Hardware Related Macros #########################
                self.RL_VALUE                     = 5        # define the load resistance on the board, in kilo ohms
                self.RO_CLEAN_AIR_FACTOR          = 9.83     # RO_CLEAR_AIR_FACTOR=(Sensor resistance in clean air)/RO,
                ######################### Software Related Macros #########################
                # cablibration phase
                self.CALIBRATION_SAMPLE_TIMES     = 50       # define how many samples you are going to take in the calibration phase
                self.CALIBRATION_SAMPLE_INTERVAL  = 500      # define the time interal(in milisecond) between each samples in the
                # normal operation
                self.READ_SAMPLE_INTERVAL         = 50       # define how many samples you are going to take in normal operation
                self.READ_SAMPLE_TIMES            = 5        # define the time interal(in milisecond) between each samples in 
                logging.debug("Calibrating...")
                self.Ro = self.MQCalibration(self.analog_pin)
                logging.debug("Calibration is done..., Ro=%f kohm", self.Ro)
            except:
                logging.error("Error init for adc converter.(MQ-X)")
                raise NameError("Error init for adc converter.(MQ-X)")
        else:
            self.analog_pin = None
        if isinstance(do_pin, int):
            self.do_pin=do_pin
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.do_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        else:
            self.do_pin = None
        if self.do_pin is None and self.analog_pin is None:
            logging.error("Error init sensor MQ_X, invalid pin value.")
            raise ValueError("Wrong value for MQ-X sensor init pin. Pin value must be integer type.")
    
    def alarm_DO(self, *args):
        do_stav = None
        try:
            sleep(0.2)      #wait for refresh gpio.input
            do_stav = not GPIO.input(self.do_pin)
            if do_stav == 1:
                if self.alarm == 0:
                    logging.warning("Sensor MQ-X has ALARM enabled!!!!! %s", self.alarm_action)
                    if self.alarm_action is not None:
                        self.alarm_action()
                self.alarm = 1
            elif do_stav == 0:
                if self.alarm == 1:
                    logging.warning("Sensor MQ-X has alarm disabled.")
                self.alarm = 0
            else:
                raise ValueError("Sensor MQ-X has unknown init value.")
        except:
            logging.debug("Sensor MQ-X has occurred a error, while reading pin %s", self.do_pin)
        return do_stav
    
    def alarmset_DO(self, mq_pin=None):
        if mq_pin is None:
            logging.debug("Sensor alarmset_DO MQ-X is not implemention.")
        else:
            GPIO.add_event_detect(mq_pin, GPIO.RISING, callback=self.alarm_DO, bouncetime=200)
    
    ######################### MQResistanceCalculation #########################
    # Input:   raw_adc - raw value read from adc, which represents the voltage
    # Output:  the calculated sensor resistance
    # Remarks: The sensor and the load resistor forms a voltage divider. Given the voltage
    #          across the load resistor and its resistance, the resistance of the sensor
    #          could be derived.
    ############################################################################ 
    def MQResistanceCalculation(self, raw_adc):
        return float(self.RL_VALUE*(self.ADC_RATE-raw_adc)/float(raw_adc))
  
    ######################### MQCalibration ####################################
    # Input:   mq_pin - analog channel
    # Output:  Ro of the sensor
    # Remarks: This function assumes that the sensor is in clean air. It use  
    #          MQResistanceCalculation to calculates the sensor resistance in clean air 
    #          and then divides it with RO_CLEAN_AIR_FACTOR. RO_CLEAN_AIR_FACTOR is about 
    #          10, which differs slightly between different sensors.
    ############################################################################ 
    def MQCalibration(self, mq_pin):
        val = 0.0
        for _ in range(self.CALIBRATION_SAMPLE_TIMES):          # take multiple samples
            val += self.MQResistanceCalculation(self.adc.read(mq_pin))
            sleep(self.CALIBRATION_SAMPLE_INTERVAL/1000.0)
        val = val/self.CALIBRATION_SAMPLE_TIMES                 # calculate the average value
        val = val/self.RO_CLEAN_AIR_FACTOR                      # divided by RO_CLEAN_AIR_FACTOR yields the Ro 
                                                                # according to the chart in the datasheet 
        return val
    
    #########################  MQRead ##########################################
    # Input:   mq_pin - analog channel
    # Output:  Rs of the sensor
    # Remarks: This function use MQResistanceCalculation to caculate the sensor resistenc (Rs).
    #          The Rs changes as the sensor is in the different consentration of the target
    #          gas. The sample times and the time interval between samples could be configured
    #          by changing the definition of the macros.
    ############################################################################ 
    def MQRead(self, mq_pin):
        rs = 0.0
        for _ in range(self.READ_SAMPLE_TIMES):
            rs += self.MQResistanceCalculation(self.adc.read(mq_pin))
            sleep(self.READ_SAMPLE_INTERVAL/1000.0)
        rs = rs/self.READ_SAMPLE_TIMES
        return rs
   
    def MQPercentage(self, pcurve):
        # self.LPGCurve = [2.3,0.21,-0.47]     # two points are taken from the curve. 
        # with these two points, a line is formed which is "approximately equivalent"
        # to the original curve. Data format:{x, y, slope}; point1:(lg200, 0.21), point2:(lg10000, -0.59) 
        read = self.MQRead(self.analog_pin)
        if self.Ro != 0:
            data = read/self.Ro
        else:
            data = 0
        return self.MQGetPercentage(data, pcurve)
    
    #########################  MQGetPercentage #################################
    # Input:   rs_ro_ratio - Rs divided by Ro
    #          pcurve      - pointer to the curve of the target gas
    # Output:  ppm of the target gas
    # Remarks: By using the slope and a point of the line. The x(logarithmic value of ppm) 
    #          of the line could be derived if y(rs_ro_ratio) is provided. As it is a 
    #          logarithmic coordinate, power of 10 is used to convert the result to non-logarithmic 
    #          value.
    ############################################################################ 
    def MQGetPercentage(self, rs_ro_ratio, pcurve):
        return (math.pow(10,( ((math.log(rs_ro_ratio)-pcurve[1])/ pcurve[2]) + pcurve[0])))




class sensorMQ_9(sensorMQ_X):
    GAS_LPG                      = 0
    GAS_CO                       = 1
    GAS_SMOKE                    = 2

    def __init__(self, do_pin=None, analog_pin=None, ro=10):
        self.CALIBRATION_SAMPLE_TIMES     = 5       # define how many samples you are going to take in the calibration phase
        self.CALIBRATION_SAMPLE_INTERVAL  = 500      # define the time interal(in milisecond) between each samples in the

        self.LPGCurve = [2.3,0.21,-0.47]    # two points are taken from the curve. 
                                            # with these two points, a line is formed which is "approximately equivalent"
                                            # to the original curve. 
                                            # data format:{ x, y, slope}; point1: (lg200, 0.21), point2: (lg10000, -0.59) 
        self.COCurve = [2.3,0.72,-0.34]     # two points are taken from the curve. 
                                            # with these two points, a line is formed which is "approximately equivalent" 
                                            # to the original curve.
                                            # data format:[ x, y, slope]; point1: (lg200, 0.72), point2: (lg10000,  0.15)
        self.SmokeCurve =[2.3,0.53,-0.44]   # two points are taken from the curve. 
                                            # with these two points, a line is formed which is "approximately equivalent" 
                                            # to the original curve.
                                            # data format:[ x, y, slope]; point1: (lg200, 0.53), point2: (lg10000,  -0.22)  
        super().__init__(do_pin=do_pin, analog_pin=analog_pin, ro=ro)
    
    def MQPercentage(self):
        val = {}
        read = self.MQRead(self.analog_pin)
        val["GAS_LPG"]  = self.MQGetGasPercentage(read/self.Ro, self.GAS_LPG)
        val["CO"]       = self.MQGetGasPercentage(read/self.Ro, self.GAS_CO)
        val["SMOKE"]    = self.MQGetGasPercentage(read/self.Ro, self.GAS_SMOKE)
        return val
    
    #########################  MQGetGasPercentage ##############################
    # Input:   rs_ro_ratio - Rs divided by Ro
    #          gas_id      - target gas type
    # Output:  ppm of the target gas
    # Remarks: This function passes different curves to the MQGetPercentage function which 
    #          calculates the ppm (parts per million) of the target gas.
    ############################################################################ 
    def MQGetGasPercentage(self, rs_ro_ratio, gas_id):
        try:
            if ( gas_id == self.GAS_LPG ):
                return self.MQGetPercentage(rs_ro_ratio, self.LPGCurve)
            elif ( gas_id == self.GAS_CO ):
                return self.MQGetPercentage(rs_ro_ratio, self.COCurve)
            elif ( gas_id == self.GAS_SMOKE ):
                return self.MQGetPercentage(rs_ro_ratio, self.SmokeCurve)
        except:
            pass
        return 0


if __name__ == '__main__':
    b=sensorMQ_9(do_pin=12, analog_pin=0)
    while True:
        print("Status DO for MQ-X: %s", b.alarm_DO())
        #print("ahoj", b.MQPercentage())
        sleep(0.5)
