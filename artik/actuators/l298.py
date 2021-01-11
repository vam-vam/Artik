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


class Stepper_L298:
    """Instantiate the stepper.

    pins = [stepPin, directionPin, enablePin]
    """

    def __init__(
            self,
            pins,
            scale_steps=3200,
            scale=360,
            speed=0.0005,
            left_max=None,
            right_max=None,
            steptype="half",
        ):
        # setup pins
        self.__gpiopins = pins
        self.scale_steps = scale_steps
        self.scale = scale
        self.initdelay = 0.001
        self.steptype = steptype
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
        try:
            for pin in self.__gpiopins:
                gpio.setup(pin, gpio.OUT)
                gpio.output(pin, False)
            sleep(self.initdelay)
        except Exception:
            raise RuntimeError("Error intializing stepper.")

        logger.debug("Stepper initialized (step pins=" + str(self.__gpiopins) + ")")

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
    def __step(self, steps, dir, speed=1, stayOn=False, steptype=None):
        suid = self.suid
        if steptype is None:
            steptype = self.steptype
        # set the output to true for left and false for right
        turnLeft = True
        if dir == "right":
            turnLeft = False
        elif dir != "left":
            raise ValueError("STEPPER ERROR: no direction supplied")

        try:
            waitTime = speed / steps  # waitTime controls speed
        except ZeroDivisionError:
            waitTime = self.__speedMinwait

        if waitTime < self.__speedMinwait:
            waitTime = (
                self.__speedMinwait
            )  # continue or call method self.stop() is end driver
            self.stop()

        try:
            # select step based on user input
            # Each step_sequence is a list containing GPIO pins that should be set to High
            if steptype == "half":  # half stepping.
                step_sequence = list(range(0, 8))
                step_sequence[0] = [self.__gpiopins[0]]
                step_sequence[1] = [self.__gpiopins[0], self.__gpiopins[1]]
                step_sequence[2] = [self.__gpiopins[1]]
                step_sequence[3] = [self.__gpiopins[1], self.__gpiopins[2]]
                step_sequence[4] = [self.__gpiopins[2]]
                step_sequence[5] = [self.__gpiopins[2], self.__gpiopins[3]]
                step_sequence[6] = [self.__gpiopins[3]]
                step_sequence[7] = [self.__gpiopins[3], self.__gpiopins[0]]
            elif steptype == "full":  # full stepping.
                step_sequence = list(range(0, 4))
                step_sequence[0] = [self.__gpiopins[0], self.__gpiopins[1]]
                step_sequence[1] = [self.__gpiopins[1], self.__gpiopins[2]]
                step_sequence[2] = [self.__gpiopins[2], self.__gpiopins[3]]
                step_sequence[3] = [self.__gpiopins[0], self.__gpiopins[3]]
            elif steptype == "wave":  # wave driving
                step_sequence = list(range(0, 4))
                step_sequence[0] = [self.__gpiopins[0]]
                step_sequence[1] = [self.__gpiopins[1]]
                step_sequence[2] = [self.__gpiopins[2]]
                step_sequence[3] = [self.__gpiopins[3]]
            else:
                raise RuntimeError(f"Unknown step type '{steptype}'; allowed values are 'half', 'full' or 'wave'.")

            #  To run motor in reverse we flip the sequence order.
            if turnLeft:
                step_sequence.reverse()

        except Exception:
            raise RuntimeError("Failed to set pins in motor L298")
        finally:
            if not stayOn:
                for pin in self.__gpiopins:
                    gpio.output(pin, False)

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
            if suid != self.suid:
                stepCounter = steps
                break

            for pin_list in step_sequence:
                for pin in self.__gpiopins:
                    if pin in pin_list:
                        gpio.output(pin, True)
                    else:
                        gpio.output(pin, False)
            stepCounter += 1
            self.__steps_count += -1 if turnLeft else 1
            # wait before taking the next step thus controlling rotation speed
            sleep(.0005)
            if (
                self.left_max is not None
                and self.right_max is not None
                and not (self.left_max <= self.__steps_count <= self.right_max)
            ):
                raise ValueError("Value out of range (min-max).")

        if not stayOn:
            # set enable to high (i.e. power is NOT going to the motor)
            self.stop()

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

    def stop(self):
        self.suid = 0
        for pin in self.__gpiopins:
            gpio.setup(pin, gpio.OUT)
            gpio.output(pin, False)
        sleep(self.initdelay)
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
    testStepper = Stepper_L298(
        pins=[19, 16, 21, 20],
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
    testStepper.stop()
    sleep(5)
    logger.info("finished")


if __name__ == "__main__":
    main()
