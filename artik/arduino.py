#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

from time import sleep

import Adafruit_GPIO.I2C as I2C


# arduino default address.
ARDUINO_I2CADDR = 0x05
#bus = I2C.get_i2c_device(ARDUINO_I2CADDR)


class IrdaProjector:
    def __init__(self, i2c_addr=None):
        try:
            if i2c_addr is None:
                self._bus = I2C.get_i2c_device(ARDUINO_I2CADDR)
            else:
                self._bus = I2C.get_i2c_device(i2c_addr)
        except Exception:
            raise ValueError("Error getting bus address")

    def send_code(self, code):
        if code == "000000001111110101000000101111111":  #0xFD40BF/32 power
            self._bus.writeList(int(ord('p')), [1,int(ord("P"))])
        elif code == "000000001111110100100000110111111":   #0xFD20DF/32 menu
            self._bus.writeList(int(ord('p')), [1,int(ord("M"))])
        elif code == "000000001111110101100000100111111":   #0xFD609F/32 input
            self._bus.writeList(int(ord('p')), [1,int(ord("I"))])
        elif code == "000000001111110110010000011011111":   #0xFD906F/32 ok
            self._bus.writeList(int(ord('p')), [1,int(ord("O"))])
        elif code == "000000001111110110001000011101111":   #0xFD8877/32 esc
            self._bus.writeList(int(ord('p')), [1,int(ord("E"))])
        elif code == "000000001111110100000000111111111":   #0xFD00FF/32 mute
            self._bus.writeList(int(ord('p')), [1,int(ord("m"))])
        elif code == "000000001111110110100000010111111":   #0xFDA05F/32 up
            self._bus.writeList(int(ord('p')), [1,int(ord("U"))])
        elif code == "000000001111110100010000111011111":   #0xFD10EF/32 left
            self._bus.writeList(int(ord('p')), [1,int(ord("L"))])
        elif code == "000000001111110101010000101011111":   #0xFD50AF/32 right
            self._bus.writeList(int(ord('p')), [1,int(ord("R"))])
        elif code == "000000001111110110110000010011111":   #0xFDB04F/32 down
            self._bus.writeList(int(ord('p')), [1,int(ord("D"))])
        elif code == "000000001111110101001000101101111":   #0xFD48B7/32 volume up
            self._bus.writeList(int(ord('p')), [1,int(ord("V"))])
        elif code == "000000001111110101101000100101111":   #0xFD6897/32 volume down
            self._bus.writeList(int(ord('p')), [1,int(ord("v"))])
        sleep(.1)


class Irda:
    def __init__(self, i2c_addr=None):
        try:
            if i2c_addr is None:
                self._bus = I2C.get_i2c_device(ARDUINO_I2CADDR)
            else:
                self._bus = I2C.get_i2c_device(i2c_addr)
        except Exception:
            raise RuntimeError("Error getting I2C device address")

    # TODO also implement IR receiver.

    def send_code(self, code):
        if code == "0000000":  # test
            self._bus.writeList(int(ord('r')), [1, int(ord("O"))])
        sleep(.1)
