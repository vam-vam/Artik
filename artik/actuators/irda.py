#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Python IR transmitter, supports NEC, RC-5 and raw IR.

 bschwind/ir-slinger is licensed under the The Unlicense
 https://github.com/bschwind/ir-slinger/blob/master/pyslinger.py
Requires pigpio library for Irda_Receiver(). Pigpio is a C library for the Raspberry which
allows control of the General Purpose Input Outputs (GPIO).
Pigpio: https://github.com/joan2937/pigpio or apt-get install pigpio # Danijel Tudek, Aug 2016

"""

import ctypes
import time
import logging
from datetime import datetime

import RPi.GPIO as GPIO

logger = logging.getLogger(__name__)

# This is the struct required by pigpio library.
# We store the individual pulses and their duration here. (In an array of these structs.)
class Pulses_struct(ctypes.Structure):
    _fields_ = [("gpioOn", ctypes.c_uint32),
                ("gpioOff", ctypes.c_uint32),
                ("usDelay", ctypes.c_uint32)]

# Since both NEC and RC-5 protocols use the same method for generating waveform,
# it can be put in a separate class and called from both protocol's classes.
class Wave_generator():
    def __init__(self,protocol):
        self.protocol = protocol
        MAX_PULSES = 12000 # from pigpio.h
        Pulses_array = Pulses_struct * MAX_PULSES
        self.pulses = Pulses_array()
        self.pulse_count = 0

    def add_pulse(self, gpioOn, gpioOff, usDelay):
        self.pulses[self.pulse_count].gpioOn = gpioOn
        self.pulses[self.pulse_count].gpioOff = gpioOff
        self.pulses[self.pulse_count].usDelay = usDelay
        self.pulse_count += 1

    # Pull the specified output pin low
    def zero(self, duration):
        self.add_pulse(0, 1 << self.protocol.master.gpio_pin, duration)

    # Protocol-agnostic square wave generator
    def one(self, duration):
        period_time = 1000000.0 / self.protocol.frequency
        on_duration = int(round(period_time * self.protocol.duty_cycle))
        off_duration = int(round(period_time * (1.0 - self.protocol.duty_cycle)))
        total_periods = int(round(duration/period_time))
        total_pulses = total_periods * 2

        # Generate square wave on the specified output pin
        for i in range(total_pulses):
            if i % 2 == 0:
                self.add_pulse(1 << self.protocol.master.gpio_pin, 0, on_duration)
            else:
                self.add_pulse(0, 1 << self.protocol.master.gpio_pin, off_duration)

# NEC protocol class
class NEC():
    def __init__(
            self,
            master,
            frequency=38000,
            duty_cycle=0.33,
            leading_pulse_duration=9000,
            leading_gap_duration=4500,
            one_pulse_duration=562,
            one_gap_duration=1686,
            zero_pulse_duration=562,
            zero_gap_duration=562,
            trailing_pulse=0
        ):
        self.master = master
        self.wave_generator = Wave_generator(self)
        self.frequency = frequency # in Hz, 38000 per specification
        self.duty_cycle = duty_cycle # duty cycle of high state pulse
        # Durations of high pulse and low "gap".
        # The NEC protocol defines pulse and gap lengths, but we can never expect
        # that any given TV will follow the protocol specification.
        self.leading_pulse_duration = leading_pulse_duration # in microseconds, 9000 per specification
        self.leading_gap_duration = leading_gap_duration # in microseconds, 4500 per specification
        self.one_pulse_duration = one_pulse_duration # in microseconds, 562 per specification
        self.one_gap_duration = one_gap_duration # in microseconds, 1686 per specification
        self.zero_pulse_duration = zero_pulse_duration # in microseconds, 562 per specification
        self.zero_gap_duration = zero_gap_duration # in microseconds, 562 per specification
        self.trailing_pulse = trailing_pulse # trailing 562 microseconds pulse, some remotes send it, some don't

    # Send AGC burst before transmission
    def send_agc(self):
        self.wave_generator.one(self.leading_pulse_duration)
        self.wave_generator.zero(self.leading_gap_duration)

    # Trailing pulse is just a burst with the duration of standard pulse.
    def send_trailing_pulse(self):
        self.wave_generator.one(self.one_pulse_duration)

    # This function is processing IR code. Leaves room for possible manipulation
    # of the code before processing it.
    def process_code(self, ircode):
        if (self.leading_pulse_duration > 0) or (self.leading_gap_duration > 0):
            self.send_agc()
        for i in ircode:
            if i == "0":
                self.zero()
            elif i == "1":
                self.one()
            else:
                logger.error("ERROR! Non-binary digit!")
                return 1
        if self.trailing_pulse == 1:
            self.send_trailing_pulse()
        return 0

    # Generate zero or one in NEC protocol
    # Zero is represented by a pulse and a gap of the same length
    def zero(self):
        self.wave_generator.one(self.zero_pulse_duration)
        self.wave_generator.zero(self.zero_gap_duration)

    # One is represented by a pulse and a gap three times longer than the pulse
    def one(self):
        self.wave_generator.one(self.one_pulse_duration)
        self.wave_generator.zero(self.one_gap_duration)

# RC-5 protocol class
# Note: start bits are not implemented here due to inconsistency between manufacturers.
# Simply provide them with the rest of the IR code.
class RC5():
    def __init__(self,
                master,
                frequency=36000,
                duty_cycle=0.33,
                one_duration=889,
                zero_duration=889):
        self.master = master
        self.wave_generator = Wave_generator(self)
        self.frequency = frequency # in Hz, 36000 per specification
        self.duty_cycle = duty_cycle # duty cycle of high state pulse
        # Durations of high pulse and low "gap".
        # Technically, they both should be the same in the RC-5 protocol, but we can never expect
        # that any given TV will follow the protocol specification.
        self.one_duration = one_duration # in microseconds, 889 per specification
        self.zero_duration = zero_duration # in microseconds, 889 per specification

    # This function is processing IR code. Leaves room for possible manipulation
    # of the code before processing it.
    def process_code(self, ircode):
        for i in ircode:
            if i == "0":
                self.zero()
            elif i == "1":
                self.one()
            else:
                logger.error("ERROR! Non-binary digit!")
                return 1
        return 0

    # Generate zero or one in RC-5 protocol
    # Zero is represented by pulse-then-low signal
    def zero(self):
        self.wave_generator.one(self.zero_duration)
        self.wave_generator.zero(self.zero_duration)

    # One is represented by low-then-pulse signal
    def one(self):
        self.wave_generator.zero(self.one_duration)
        self.wave_generator.one(self.one_duration)

# RAW IR ones and zeroes. Specify length for one and zero and simply bitbang the GPIO.
# The default values are valid for one tested remote which didn't fit in NEC or RC-5 specifications.
# It can also be used in case you don't want to bother with deciphering raw bytes from IR receiver:
# i.e. instead of trying to figure out the protocol, simply define bit lengths and send them all here.
class RAW():
    def __init__(self,
                master,
                frequency=36000,
                duty_cycle=0.33,
                one_duration=520,
                zero_duration=520):
        self.master = master
        self.wave_generator = Wave_generator(self)
        self.frequency = frequency # in Hz
        self.duty_cycle = duty_cycle # duty cycle of high state pulse
        self.one_duration = one_duration # in microseconds
        self.zero_duration = zero_duration # in microseconds

    def process_code(self, ircode):
        for i in ircode:
            if i == "0":
                self.zero()
            elif i == "1":
                self.one()
            else:
                logger.error("ERROR! Non-binary digit!")
                return 1
        return 0

    # Generate raw zero or one.
    # Zero is represented by low (no signal) for a specified duration.
    def zero(self):
        self.wave_generator.zero(self.zero_duration)

    # One is represented by pulse for a specified duration.
    def one(self):
        self.wave_generator.one(self.one_duration)


class Irda:
    def __init__(self, gpio_pin, protocol, protocol_config):
        self.pigpio = ctypes.CDLL('libpigpio.so')
        PI_OUTPUT = 1 # from pigpio.h
        self.pigpio.gpioInitialise()
        self.gpio_pin = gpio_pin
        logger.debug("IRDA gpio pin %d" % self.gpio_pin)
        self.pigpio.gpioSetMode(self.gpio_pin, PI_OUTPUT) # pin 17 is used in LIRC by default
        if protocol == "NEC":
            self.protocol = NEC(self, **protocol_config)
        elif protocol == "RC-5":
            self.protocol = RC5(self, **protocol_config)
        elif protocol == "RAW":
            self.protocol = RAW(self, **protocol_config)
        else:
            raise ValueError(f"Invalid protocol {protocol}")

    # send_code takes care of sending the processed IR code to pigpio.
    # IR code itself is processed and converted to pigpio structs by protocol's classes.
    def send_code(self, ircode):
        logger.debug("Processing IR code: %s", ircode)
        code = self.protocol.process_code(ircode)
        if code != 0:
            logger.error("Error in processing IR code!")
            return False
        clear = self.pigpio.gpioWaveClear()
        if clear != 0:
            logger.error("Error in clearing wave!")
            return False
        pulses = self.pigpio.gpioWaveAddGeneric(self.protocol.wave_generator.pulse_count, self.protocol.wave_generator.pulses)
        if pulses < 0:
            logger.error("Error in adding wave!")
            return False
        wave_id = self.pigpio.gpioWaveCreate()
        # Unlike the C implementation, in Python the wave_id seems to always be 0.
        if wave_id >= 0:
            result = self.pigpio.gpioWaveTxSend(wave_id, 0)
            if result >= 0:
                logger.debug("Success! (result: %d)" % result)
            else:
                logger.error("Error! (result: %d)" % result)
                return False
        else:
            logger.error("Error creating wave: %d" % wave_id)
            return 1
        while self.pigpio.gpioWaveTxBusy():
            time.sleep(0.1)
        self.pigpio.gpioWaveDelete(wave_id)
        self.protocol.wave_generator.pulse_count = 0
        return True

    def __del__(self):
        self.pigpio.gpioTerminate()


class Irda_Receiver:
    def __init__(self, pin):
        self.gpio_pin = int(pin)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.IN)

    def receive(self, timeout=5):
        # Loop until we read a 0
        startTime = datetime.now()
        value = 1
        while value:
            value = GPIO.input(self.gpio_pin)
            if (datetime.now()-startTime).seconds > timeout:
                break

        # Grab the start time of the command
        startTime = datetime.now()
        # Used to buffer the command pulses
        command = []
        # The end of the "command" happens when we read more than
        # a certain number of 1s (1 is off for my IR receiver)
        numOnes = 0
        # Used to keep track of transitions from 1 to 0
        previousVal = 0

        while True:
            if value != previousVal:
                # The value has changed, so calculate the length of this run
                now = datetime.now()
                pulseLength = now - startTime
                startTime = now
                command.append((previousVal, pulseLength.microseconds))
            if value:
                numOnes = numOnes + 1
            else:
                numOnes = 0
            # 10000 is arbitrary, adjust as necessary
            if numOnes > 10000:
                break

            previousVal = value
            value = GPIO.input(self.gpio_pin)

        return command

    def convert_to_binary(self, command, one=1000):
        return "".join(map(lambda x: "1" if x[1] > one else "0", filter(lambda x: x[0] == 1, command)))


# Simply define the GPIO pin, protocol (NEC, RC-5 or RAW) and
# override the protocol defaults with the dictionary if required.
# Provide the IR code to the send_code() method.
# An example is given below.
if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) : %(message)s',
        level=logging.DEBUG,
    )
    protocol = "NEC"
    gpio_pin = 24
    #protocol_config = dict(one_duration = 820,
    #                        zero_duration = 820)
    protocol_config = dict()
    ir = Irda(gpio_pin, protocol, protocol_config)
    print("1")
    ir.send_code("000000001111110101000000101111111")
    print("2")
    ir.send_code("000000001111110101000000101111111")
    print("3")
    ir.send_code("000000001111110101000000101111111")
    print("Exiting IR")
    ir = Irda_Receiver(21)
    a = ir.receive(10)
    print(a)
    print(ir.convert_to_binary(a))
