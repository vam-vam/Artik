#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Access to a stepper motor for Raspberry Pi.

CURRENT APPLICATION INFO
200 steps/rev
12V, 350mA (with TB6600 < 4.5A)
Big Easy driver = 1/16 microstep mode
Turn a 200 steps motor * 16 microstep left one full revolution: 3200
"""

from time import sleep
from uuid import uuid4
import logging

import RPi.GPIO as gpio  # https://pypi.python.org/pypi/RPi.gpio

logger = logging.getLogger(__name__)


class Stepper_tb6600:
    """Instantiate the stepper.

    pins = [stepPin, directionPin, enablePin]
    """
    def __init__(
            self,
            pins,
            scale_steps=3200,
            scale=360,
            speed=0.000001,
            left_max=None,
            right_max=None,
        ):
        # setup pins
        self.__stepPin = pins[0]
        self.__directionPin = pins[1]
        self.__enablePin = pins[2]
        self.scale_steps = scale_steps
        self.scale = scale
        self.__steps_count = 0
        self.__speedMinwait = speed
        # steps counter from zero position-> left = steps < 0 ; right = steps > 0
        self.left_max = left_max  # left <= 0, default None = infinity
        self.right_max = right_max  # right >= 0, default None = infinity
        # unique id for step motor
        self.suid = 0
        # use the broadcom layout for the gpio
        gpio.setwarnings(False)
        gpio.setmode(gpio.BCM)

        # set gpio pins
        gpio.setup(self.__stepPin, gpio.OUT)
        gpio.setup(self.__directionPin, gpio.OUT)
        gpio.setup(self.__enablePin, gpio.OUT)

        # set enable to high (i.e. power is NOT going to the motor)
        gpio.output(self.__enablePin, True)
        self.stop()

        logger.debug(
            "Stepper initialized (step pins="
            + str(self.__stepPin)
            + ", direction="
            + str(self.__directionPin)
            + ", enable="
            + str(self.__enablePin)
            + ")"
        )

    # clears gpio settings
    def cleangpio(self):
        gpio.cleanup()

    def map(self, x, in_min, in_max, out_min, out_max):
        return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    @property
    def suid(self):
        return self.__suid

    @suid.setter
    def suid(self, suid):
        if suid == 0 or suid is None:
            self.__suid = uuid4()
        else:
            self.__suid = suid

    # step the motor
    # steps = number of steps to take
    # dir = direction stepper will move
    # speed = defines the denominator in the waitTime equation: waitTime = 0.000001/speed. As "speed" is increased,
    #       the waitTime between steps is lowered
    # stayOn = defines whether or not stepper should stay "on" or not. If stepper will need to receive a new
    #       step command immediately, this should be set to "True." Otherwise, it should remain at "False."
    def __step(self, steps, dir, speed=1, stayOn=True):
        suid = self.suid
        # set enable to low (i.e. power IS going to the motor)
        gpio.output(self.__enablePin, False)

        # set the output to true for left and false for right
        turnLeft = True
        if dir == "right":
            turnLeft = False
        elif dir != "left":
            raise ValueError("STEPPER ERROR: no direction supplied")
        gpio.output(self.__directionPin, turnLeft)

        try:
            waitTime = speed / steps  # waitTime controls speed
        except ZeroDivisionError:
            waitTime = self.__speedMinwait

        if waitTime < self.__speedMinwait:
            waitTime = (
                self.__speedMinwait
            )  # continue or call method self.stop() is end driver
            self.stop()

        stepCounter = 0
        while stepCounter < steps:
            if (
                self.left_max is not None
                and self.left_max >= self.__steps_count
                and turnLeft
            ):
                self.stop()
            if (
                self.right_max is not None
                and self.right_max <= self.__steps_count
                and not turnLeft
            ):
                self.stop()
            # print(suid, self.suid, suid != self.suid)
            if suid != self.suid:
                stepCounter = steps
                break
            # gracefully exit if ctr-c is pressed
            # exitHandler.exitPoint(True) #exitHandler.exitPoint(True, cleangpio)
            # turning the gpio on and off tells the easy driver to take one step
            gpio.output(self.__stepPin, True)
            gpio.output(self.__stepPin, False)
            stepCounter += 1
            self.__steps_count += -1 if turnLeft else 1
            # wait before taking the next step thus controlling rotation speed
            sleep(waitTime)
            if (
                self.left_max is not None
                and self.right_max is not None
                and not (self.left_max <= self.__steps_count <= self.right_max)
            ):
                raise ValueError("Value out of range (min-max).")

        if stayOn == False:
            # set enable to high (i.e. power is NOT going to the motor)
            gpio.output(self.__enablePin, True)

        logger.debug(
            "stepperDriver complete (turned "
            + dir
            + " "
            + str(steps)
            + " steps) and wait= "
            + str(waitTime)
        )

    def distance(self, distance, speed=1):
        if distance is None:
            raise ValueError("Distance ERROR: invalid parameter")
        suid = self.suid
        dir = "left"
        if distance > 0:
            dir = "right"
        steps = int(
            self.map(
                abs(distance),
                in_min=0,
                in_max=self.scale,
                out_min=0,
                out_max=self.scale_steps,
            )
        )
        if steps > 0:
            self.__step(steps=steps, dir=dir, speed=speed)
        return suid == self.suid

    def stop(self, disable=False):
        if disable:
            gpio.output(self.__directionPin, False)
            gpio.output(self.__enablePin, True)

        self.suid = 0
        logger.debug("stop " + str(self.suid))
        return True

    @property
    def pedometer(self):
        return self.__steps_count

    def reset(self):
        correction = 0
        if self.left_max > self.__steps_count:
            correction = self.__steps_count - self.left_max
            self.__steps_count = self.left_max
        elif self.right_max < self.__steps_count:
            correction = self.__steps_count - self.right_max
            self.__steps_count = self.right_max

        # move to zero
        dir = "left"
        if (-1 * self.__steps_count) > 0:
            dir = "right"
        speed = abs(0.00025 * self.__steps_count)
        logger.debug("Speed:" + str(speed) + " Step:" + str(self.__steps_count))
        self.__step(steps=abs(self.__steps_count), dir=dir, speed=speed)

        self.__steps_count = correction
        dir = "left"
        if (-1 * self.__steps_count) > 0:
            dir = "right"
        self.__step(steps=abs(self.__steps_count), dir=dir, speed=speed)

    # vrati true pokud je servomotpr v krajni poloze max, jinak false
    @property
    def IsMaxPosition(self):
        return self.right_max is not None and self.right_max <= self.__steps_count

    # vrati true pokud je servo v krajni poloze min, jinak false
    @property
    def IsMinPosition(self):
        return self.left_max is not None and self.left_max >= self.__steps_count

    # vratit informace o nastaveni motoru a info o dalsich vlastnostech
    def state(self):
        result = {}
        result["stepper_max"] = self.right_max
        result["stepper_min"] = self.left_max
        result["stepper_scale"] = self.scale
        result["stepper_scalestep"] = self.scale_steps
        result["stepper_stepcount"] = self.__steps_count
        result["stepper_suid"] = self.suid
        return result


def main():
    logging.basicConfig(
        format="%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) : %(message)s",
        level=logging.DEBUG,
    )

    # example/test
    # stepper variables pins [stepPin, directionPin, enablePin]
    # 200 steps/rev * 1/16 microstep mode = 3200steps # test gears 360 -> 112/22*3200=5.0901
    testStepper = Stepper_tb6600(
        pins=[5, 13, 6],
        scale_steps=16290,
        scale=360,
        left_max=-16290,
        right_max=16290,
    )

    hash_uuid = testStepper.suid
    m = 90
    cas = 0.3
    testStepper.distance(-m, cas)
    # testStepper.stop()
    if hash_uuid == testStepper.suid:
        testStepper.distance(m * -2, cas)
    if hash_uuid == testStepper.suid:
        testStepper.distance(m * 2, cas)
    testStepper.stop()
    if hash_uuid == testStepper.suid:
        testStepper.distance(-m, cas)

    # testStepper.distance(360, 1)
    testStepper.reset()
    # steps, dir, speed, stayOn
    # testStepper._P_step(1600, "right", 0.00100)
    sleep(10)
    testStepper.stop(disable=True)
    sleep(5)
    logger.info("finished")


if __name__ == "__main__":
    main()
