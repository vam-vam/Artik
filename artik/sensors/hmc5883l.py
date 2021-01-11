#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek
# Parts of code adapted from https://github.com/rm-hull/hmc5883l

"""
Wrapper class for the HMC5888L Magnetometer (Digital Compass).
Uses smbus rather than quick2wire and sets different init params.

"""

from time import sleep
import math

import Adafruit_GPIO.smbus as smbus


class HMC5883L:

    def __init__(self, busnum=1, address=0x1E, gauss=0xa0, declination=(4, 13)):
        self.__declDegrees = declination[0]
        self.__declMinutes = declination[1]
        self.__declination = (self.__declDegrees + self.__declMinutes / 60) * math.pi / 180
        self.bus = smbus.SMBus(busnum)
        self.address = address
        self.bus.write_byte_data(self.address, 0x00, 0x70)
        self.bus.write_byte_data(self.address, 0x01, gauss)
        self.bus.write_byte_data(self.address, 0x02, 0x00)
        sleep(0.5)

    def declination(self):
        return (self.__declDegrees, self.__declMinutes)

    def axes(self):
        data = self.bus.read_i2c_block_data(self.address, 0x03, 6)
        # Convert the data
        xMag = data[0] * 256 + data[1]
        if xMag > 32767:
            xMag -= 65536

        zMag = data[2] * 256 + data[3]
        if zMag > 32767:
            zMag -= 65536

        yMag = data[4] * 256 + data[5]
        if yMag > 32767:
            yMag -= 65536
        return (xMag, yMag, zMag)

    def heading(self):
        x, y, z = self.axes()
        headingRad = math.atan2(y, x)
        headingRad += self.__declination
        # Correct for reversed heading
        if headingRad < 0:
            headingRad += 2 * math.pi
        # Check for wrap and compensate
        elif headingRad > 2 * math.pi:
            headingRad -= 2 * math.pi
        return headingRad

    def degrees(self):
        # Convert to degrees from radians
        heading_angle = self.heading() * 180 / math.pi
        degrees = math.floor(heading_angle)
        minutes = round((heading_angle - degrees) * 60)
        return (degrees, minutes)

    def __str__(self):
        (x, y, z) = self.axes()
        return "Axis X: " + str(x) + "\t" \
               "Axis Y: " + str(y) + "\t" \
               "Axis Z: " + str(z) + "\t" \
               "Declination: " + str(self.declination()) + "\t" \
               "Degrees(°): " + str(self.degrees()) + "\t" \
               "Heading(rad): " + str(self.heading()) + "\n"


if __name__ == "__main__":
    # Magnetic declination is different for different places on earth.
    # To find the correct declination, check http://magnetic-declination.com
    compass = HMC5883L(declination=(4, 13))
    while True:
        deg = compass.heading()
        print(f"Heading: {deg} '{compass}'")
        sleep(1)
