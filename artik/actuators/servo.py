#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""Control of servo motors."""

import logging
from time import sleep, time
import uuid

import Adafruit_GPIO.PCA9685 as PCA9685


logger = logging.getLogger(__name__)


class SimulacePWM:
    """
    simulace pwm signalu pro testovani
    """
    def __init__(self):
        self.__name__ = "Simulace"

    def set_pwm_freq(self, *args):
        logger.debug("calling method simulace set_pwm_freq()  %s", args)
        return True

    def set_pwm(self, *args):
        logger.debug("calling method simulace setPWM()  %s", args)
        return True

    def set_all_pwm(self, *args):
        logger.debug("calling method simulace setAllPWM()  %s", args)
        return True

# Initialise the PWM device using the default address
#pwm = PCA9685.PCA9685(address=0x40, busnum=1)
# Note if you'd like more debug output you can instead run:
try:
    pwm = PCA9685.PCA9685(address=0x40, busnum=1)
    pwm.set_pwm_freq(50)
except Exception:
    pwm = SimulacePWM()
    pwm.set_pwm_freq(50)


class Servo:
    """Setup one servo motor."""

    def __init__(self, channel=-1, position0=0, min=0, max=0, scale=1, speed=0.0065, radius=0):
        # channel serva
        self.servo_channel = channel
        # hash id for one task
        self.servo_uuid = str(uuid.uuid4())
        #status servo run/stop
        self.servo_status = False
        self._servo_pwm = 0
        #set min position
        self.servo_min = min
        #set midl/neutral position
        self.servo_position0 = position0
        #set max
        self.servo_max = max
        #set current position
        self.servo_position_H = -1
        #scale/steps between min=>center == center=>max
        self.servo_scale = scale
        #set 0 - max radius
        self.servo_radius = radius
        #speed servo (speed ms (0-max)°radius/(max-min))
        self.servo_speed = speed
        if self.servo_channel > -1:
            self.__setServo(self.servo_position0)

    def map(self, x, in_min, in_max, out_min, out_max):
        return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    #nastaveni pwm signalu pro servo
    def setServo(self, high=0, suid=''):
        result = False
        if (suid != '' and suid != self.servo_uuid):
            return False
        elif suid == '':
            self.servo_uuid = str(uuid.uuid4())
        high = int(high)
        if (self.servo_channel > -1 and ((self.servo_min <= high <= self.servo_max) or high == 0)):
            self.servo_status = True
            pwm.set_pwm(self.servo_channel, 0, high)
            if self._servo_pwm == 0:
                sleep(0.100)
            self._servo_pwm = high
            servo_wait = round(self.servo_speed*abs(high-self.servo_position_H),3)
            logger.debug("Set setServo()=> channel:%s, low:%s, high:%s, spd:%s, sl:%s, cas:%s", self.servo_channel, 0, high, self.servo_speed, servo_wait, time())
            #reaction time servo
            #melo by se zde spocitat reakcni doba kdyz se servo otoci o dany uhel(60°=0.15, 40°=0.1, 10°=0.05,..)
            sleep(servo_wait)
            if high != 0:
                self.servo_position_H = high
            self.servo_status = False
            result = True
        else:
            logger.error("Set setServo()=> channel:%s, low:%s, high:%s, spd:%s, cas:%s", self.servo_channel, 0, high, self.servo_speed, time())
            raise NameError("Error parameters setServo()")
        return result

    __setServo = setServo

    #posune servo na danou polohu definovanou rychlosti
    def setServoMove(self, high=0, speed=1, suid=''):
        result = False
        if int(high) == 0:
            return False
        speed = int(speed)
        if speed < 1:
            speed = 1
        if (suid != '' and suid != self.servo_uuid):
            return False
        elif suid == '':
            self.servo_uuid = str(uuid.uuid4())
        suid = self.servo_uuid
        tik = round(float((high - self.servo_position_H) / speed), 3)
        start = self.servo_position_H
        logger.debug("Set setServoMove()=> start:%s, tik:%s, high:%s, pozice:%s", start, tik, high, self.servo_position_H)
        for i in range(1, speed+1):
            high = int(i*tik + start)
            if high > self.servo_max:
                high = self.servo_max
            elif high < self.servo_min:
                high = self.servo_min
            if high != self.servo_position_H:
                result = self.setServo(high, suid)
                if not result or high == self.servo_max or high == self.servo_min:
                    break
        return result

    #posune servo o dany uhel vuci aktualni poloze
    def setServoAboutRad(self, aradius=0, speed=1, suid=''):
        logger.debug("Set radius:%s, sevo.rad.:%s, pozice:%s", aradius, self.servo_radius, self.servo_position_H)
        if self.servo_radius <= 0 or not isinstance(aradius, int) or aradius == 0:
            return False
        if (suid != '' and suid != self.servo_uuid):
            return False
        elif suid == '':
            self.servo_uuid = str(uuid.uuid4())
        high = int((((self.servo_max - self.servo_min) / self.servo_radius) * aradius) + self.servo_position_H)
        result = self.setServoMove(high=high, speed=speed, suid=suid)
        return result

    #zastavi vsechna serva v poloze jake jsou pri zavolani prikazu(muze dojit u serv k ruseni)
    def stopAll(self):
        pwm.set_all_pwm(0, 0)
        logger.debug("Stop all servo")
        sleep(0.2)

    #zastavi dane servo a vratiho do neutralni polohy nebo do definovane polohy
    def stop(self, suid='', high=0):
        if (suid != '' and suid != self.servo_uuid):
            return False
        elif suid == '':
            self.servo_uuid = str(uuid.uuid4())
        if high <= 0:
            high = self.servo_position0
        logger.debug("Stop()=> servo channel:%s, high:%s, uuid:%s", self.servo_channel, high, self.servo_uuid)
        self.setServo(high, suid)
        return True

    #vypne pwm modulaci daneho serva(muze dojit u serv k ruseni)
    def stop0(self, suid=''):
        if (suid != '' and suid != self.servo_uuid):
            return False
        elif suid == '':
            self.servo_uuid = str(uuid.uuid4())
        self.setServo(0, suid)
        logger.debug("Stop0()=> servo (off) channel:%s", self.servo_channel)
        return True

    #vrati true pokud je servo v krajni poloze max, jinak false
    def servoIsMaxPosition(self):
        return self.servo_position_H == self.servo_max or self.servo_position_H == 0

    #vrati true pokud je servo v krajni poloze min, jinak false
    def servoIsMinPosition(self):
        return self.servo_position_H == self.servo_min or self.servo_position_H == 0

    #vraci informace o nastaveni serva a pripadne info o dalsich vlastnostech
    def state(self):
        result = {}
        result['servo_suid'] = self.servo_uuid
        result['servo_status'] = self.servo_status
        result['servo_position_H'] = self.servo_position_H
        result['servo_channel'] = self.servo_channel
        result['servo_position0'] = self.servo_position0
        result['servo_max'] = self.servo_max
        result['servo_min'] = self.servo_min
        result['servo_scale'] = self.servo_scale
        result['servo_speed'] = self.servo_speed
        result['servo_radius'] = self.servo_radius
        return result
