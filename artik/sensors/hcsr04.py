#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek
# Parts of code adapted from https://github.com/alaudet/hcsr04sensor (MIT license)

"""
Measure the distance or depth with an HCSR04 Ultrasonic sound
sensor and a Raspberry Pi.

Supports both imperial and metric measurements.

"""

from threading import Thread
import logging
from time import time, sleep
#import math
from random import uniform

import RPi.GPIO as GPIO


logger = logging.getLogger(__name__)


class Measurement:
    '''Create a measurement using a HC-SR04 Ultrasonic Sensor connected to
    the GPIO pins of a Raspberry Pi. = sensor.Measurement(17, 27, 20, 'metric', 1)'''
    def __init__(self, trig_pin, echo_pin, temperature=None, unit='metric', round_to=2):
        #GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.temperature = temperature
        self.temperature_function = None
        self.unit = unit
        self.round_to = round_to
        self.distance_last = None
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trig_pin, False)
        sleep(2)

    def _temperature(self):
        if self.temperature is None:
            #reference temperature
            teplota = 20.0
        elif isinstance(self.temperature, dict):
            teplota = self.temperature.get('temperature', None)
        elif isinstance(self.temperature, (int, float)):
            teplota = self.temperature
        elif isinstance(self.temperature, str):
            teplota = float(self.temperature)
        elif isinstance(self.temperature, object):
            teplota = self.temperature.temperature_last
        if teplota is None:
            #reference temperature
            teplota = 20.0
        if self.unit == 'imperial':
            teplota = (teplota - 32) * 5/9
        return float(round(teplota, 2))

    def raw_distance(self, sample_size=5):
        '''Return an error corrected unrounded distance, in cm, of an object
        adjusted for temperature in Celsius.  The distance calculated
        is the median value of a sample of `sample_size` readings.
        Example: To use a sample size of 5 instead of 11;
        r = value.raw_distance(sample_size=5)'''
        #logger.debug("Collecting %s sample raw_distance", sample_size)
        teplota = self._temperature()
        # logger.debug("Thermometer %s ", teplota)
        if self.unit == 'sim':
            return uniform(1, 100)
        speed_of_sound = 331.57 + (0.607 * teplota)
        #speed_of_sound = 331.3 * math.sqrt(1+(teplota / 273.15))
        sample = []
        for distance_reading in range(sample_size):
            sonar_signal_on = 0
            sonar_signal_off = 0
            sonar_start = time() + 5   # break signal
            GPIO.output(self.trig_pin, True)
            sleep(0.00001)
            GPIO.output(self.trig_pin, False)
            while GPIO.input(self.echo_pin) == 0:
                sonar_signal_off = time()
                if sonar_start <= sonar_signal_off:
                    sonar_signal_off = 0
                    break
            while GPIO.input(self.echo_pin) == 1 and sonar_signal_off > 0:
                sonar_signal_on = time()
                if sonar_start+5 <= sonar_signal_on:
                    sonar_signal_on = 0
                    break
            if sonar_signal_off == 0 or sonar_signal_on == 0:
                sample_size = distance_reading
                break
            time_passed = sonar_signal_on - sonar_signal_off
            distance_cm = time_passed * ((speed_of_sound * 100) / 2)
            if (distance_cm) > 601.00:
                distance_cm = 0.00
            sample.append(distance_cm)
            sleep(0.07)
        sorted_sample = sorted(sample)
        return sorted_sample[sample_size // 2]

    def depth_metric(self, median_reading, hole_depth):
        '''Calculate the rounded metric depth of a liquid. hole_depth is the
        distance, in cm's, from the sensor to the bottom of the hole.'''
        return round(hole_depth - self.distance_metric(median_reading), self.round_to)

    def depth_imperial(self, median_reading, hole_depth):
        '''Calculate the rounded imperial depth of a liquid. hole_depth is the
        distance, in inches, from the sensor to the bottom of the hole.'''
        return round(hole_depth - self.distance_imperial(median_reading), self.round_to)

    def distance_metric(self, median_reading):
        '''Calculate the rounded metric distance, in cm's, from the sensor
        to an object'''
        return round(median_reading, self.round_to)

    def distance_imperial(self, median_reading):
        '''Calculate the rounded imperial distance, in inches, from the sensor
        to an oject.'''
        return round(median_reading * 0.0002953, self.round_to)

    def distance(self, median=3):
        try:
            self.distance_last = self.raw_distance(median)
            if self.unit == 'imperial':
                self.distance_last = self.distance_imperial(self.distance_last)
            elif self.unit == 'metric' or self.unit == 'sim':
                self.distance_last = self.distance_metric(self.distance_last)
            else:
                raise ValueError('Wrong unit type: must be either "imperial" or "metric".')
        except Exception:
            logger.error("Error measuring distance.")
            self.distance_last = None
        return self.distance_last


def SensorThDistance(senzor, distance=None):
    logger.info("New sensorTh trig_pin=%s, echo_pin=%s, type temperature=%s", senzor.trig_pin, senzor.echo_pin, type(senzor.temperature))
    if isinstance(senzor, Measurement):
        while True:
            distance = senzor.distance(3)
            if distance is None:
                sleep(1)
            logger.debug("Update measurment =%s ", distance)
    else:
        logger.info("Is not object sensor for Thread %s and %s", type(senzor), type(distance))


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) : %(message)s',
        level=logging.DEBUG,
    )

    # asd2 = sensor_humi.Temperature(unit='sim')
    # pa = Thread(target=sensor_humi.SensorThDistance, args=(asd2, 2), daemon=True)
    # pa.start()
    distance = 0
    # #asd = Measurement(trig_pin=13, echo_pin=16, unit='metric', temperature="asd2.temperature_last")
    #asd = Measurement(trig_pin=13, echo_pin=16, unit='metric', temperature=25)
    asd = Measurement(trig_pin=13, echo_pin=16, unit='metric')
    #teplota = {}
    #teplota['temperature'] = 20
    p = Thread(target=SensorThDistance, args=(asd,distance), daemon=True)
    p.start()
    a = 0
    while True:
        a = a+1
        sleep(2)
        print(a)
    #s = Measurement(trig_pin=26, echo_pin=21)
    #p = Thread(target=measurement_distance, args=(distance,), daemon=True)
    #p.start()
