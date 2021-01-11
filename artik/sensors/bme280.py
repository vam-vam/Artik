#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

import logging
from time import sleep
from random import uniform

import Adafruit_BME280.Adafruit_BME280 as BME280

# BME280 default address.
BME280_I2CADDR = 0x76

# Operating Modes
BME280_OSAMPLE_1 = 1
BME280_OSAMPLE_2 = 2
BME280_OSAMPLE_8 = 4
BME280_FILTER_16 = 4

try:
    BME280_INIT = BME280(p_mode=BME280_OSAMPLE_8, t_mode=BME280_OSAMPLE_2, h_mode=BME280_OSAMPLE_1, filter=BME280_FILTER_16, address=BME280_I2CADDR)
except Exception:
    BME280_INIT = None

logger = logging.getLogger(__name__)


class Temperature:

    def __init__(self, unit='metric', round_to=2, init=BME280_INIT):
        self.unit = unit
        self.round_to = round_to
        self.temperature_last = None
        self.sensor = init
        if self.sensor is None:
            raise RuntimeError("BME280 does not exist.")

    def raw_temperature(self, sample_size=1):
        '''Return an error corrected unrounded temperature, in Celsium, of an object
        adjusted for temperature in Celsium.  The temperature calculated
        is the median value of a sample of `sample_size` readings.
        Example: To use a sample size of 1 instead of 5;
        r = value.raw_temperature(sample_size=5)'''
        if self.unit == 'sim':
            return uniform(1, 100)
        sample = []
        for s_reading in range(sample_size):
            sample.append(self.sensor.read_temperature())
            sleep(0.3)
        sorted_sample = sorted(sample)
        return sorted_sample[sample_size // 2]

    def temperature_metric(self, median_reading):
        '''Calculate the rounded metric temperature, in Celsium, from the sensor
        to an object'''
        return round(median_reading, self.round_to)

    def temperature_imperial(self, median_reading):
        '''Calculate the rounded imperial temperature, in Fahrenheit, from the sensor
        to an oject.'''
        return round((9 * median_reading / 5) + 32, self.round_to)

    def temperature(self, median=1):
        try:
            self.temperature_last = self.raw_temperature(median)
            if self.unit == 'imperial':
                self.temperature_last = self.temperature_imperial(self.temperature_last)
            elif self.unit == 'metric' or self.unit == 'sim':
                self.temperature_last = self.temperature_metric(self.temperature_last)
            else:
                raise ValueError('Wrong Unit Type. Unit Must be imperial or metric or sim')
        except Exception:
            logger.exception("error fetching temperature, setting temperature_last to None")
            self.temperature_last = None
        return self.temperature_last


class Pressure:
    def __init__(self, unit='metric', round_to=2, init=BME280_INIT):
        self.unit = unit
        self.round_to = round_to
        self.pressure_last = None
        self.sensor = init
        if self.sensor is None:
            raise RuntimeError("Pressure does not exist.")

    def raw_pressure(self, sample_size=1):
        if self.unit == 'sim':
            return uniform(1, 100)
        sample = []
        for s_reading in range(sample_size):
            sample.append(self.sensor.read_pressure())
            sleep(0.3)
        sorted_sample = sorted(sample)
        return sorted_sample[sample_size // 2]

    def pressure_metric(self, median_reading):
        '''Calculate the rounded metric pressure, in pascal, from the sensor
        to an object'''
        return round(median_reading, self.round_to)

    def pressure_imperial(self, median_reading):
        '''Calculate the rounded imperial pressure, in inches, from the sensor
        to an oject.'''
        return round(median_reading * 0.0002953, self.round_to)

    def pressure(self, median=1):
        try:
            self.pressure_last = self.raw_pressure(median)
            if self.unit == 'imperial':
                self.pressure_last = self.pressure_imperial(self.pressure_last)
            elif self.unit == 'metric' or self.unit == 'sim':
                self.pressure_last = self.pressure_metric(self.pressure_last)
            else:
                raise ValueError('Wrong Unit Type. Unit Must be imperial or metric or sim')
        except Exception:
            logger.exception("error fetching pressure, setting pressure_last to None")
            self.pressure_last = None
        return self.pressure_last


class Humidity:
    def __init__(self, unit='metric', round_to=2, init=BME280_INIT):
        self.unit = unit
        self.round_to = round_to
        self.humidity_last = None
        self.sensor = init
        if self.sensor is None:
            raise RuntimeError("Humidity does not exist.")

    def raw_humidity(self, sample_size=1):
        if self.unit == 'sim':
            return uniform(1, 100)
        sample = []
        for s_reading in range(sample_size):
            sample.append(self.sensor.read_humidity())
            sleep(0.3)
        sorted_sample = sorted(sample)
        return sorted_sample[sample_size // 2]

    def humidity_metric(self, median_reading):
        '''Calculate the rounded metric pressure, in %, from the sensor
        to an object'''
        return round(median_reading, self.round_to)

    def humidity(self, median=1):
        try:
            self.humidity_last = self.raw_humidity(median)
            if self.unit == 'metric' or self.unit == 'sim':
                self.humidity_last = self.humidity_metric(self.humidity_last)
            else:
                raise ValueError('Wrong Unit Type. Unit Must be metric or sim')
        except Exception:
            logger.exception("error fetching humidity, setting humidity_last to None")
            self.humidity_last = None
        return self.humidity_last


def SensorTemperature(senzor, delay=1):
    assert isinstance(senzor, Temperature)
    logger.info("fetching sensor temperature")
    while True:
        teplo = senzor.temperature(delay)
        logger.debug("Updated temperature =%s C", teplo)
        sleep(delay)

def SensorPressure(senzor, delay=1):
    assert isinstance(senzor, Pressure)
    logger.info("fetching sensor pressure")
    while True:
        pressure = senzor.pressure(delay)
        logger.debug("Updated pressure =%s pa", pressure)
        sleep(delay)

def SensorHumidity(senzor, delay=30):
    assert isinstance(senzor, Humidity)
    logger.info("fetching sensor humidity")
    while True:
        humidity = senzor.humidity(delay)
        logger.debug("Updated humidity =%s %%", humidity)
        sleep(delay)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) : %(message)s',
        level=logging.DEBUG,
    )

    from threading import Thread
    temperature = Temperature(unit='sim')
    print(temperature.temperature(1))

    p = Thread(target=SensorTemperature, args=(temperature, 5), daemon=True)
    p.start()
    a = 0
    while True:
        a += 1
        sleep(2)
        print(a)
