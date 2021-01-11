#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Projector for Artik. Includes control for:
* servo (adjust the projector focus)
* relay (turn the project on/off, to save energy)
* IRdA (control the project menu)

"""

from time import sleep
import logging

from artik.arduino import IrdaProjector

from artik.actuators.servo import Servo
#from artik.actuators.relay import RelayModule
#from artik.actuators.irda import Irda

logger = logging.getLogger(__name__)

PROJECTOR_FOCUS = {'channel': 5, 'min': 230, 'max': 455, 'position0': 230, 'scale': 44, 'radius': 86}
RELAY_PIN = 0

class ArtikProjektor:
    def __init__(self, servo_param=None):
        self.servo_focus = None
        self.relay = None
        self.irda = None
        # set servo for focus
        if isinstance(servo_param, dict):
            self.servo_focus = Servo(servo_param['channel'], servo_param['position0'], servo_param['min'], servo_param['max'], servo_param['scale'], 0.004, servo_param['radius'])
        self.servo_focus.stop0()
        # set relay for powerswitch
        #self.relay = RelayModule(RELAY_PIN)
        # set infra remote control
        self.irda = IrdaProjector()
#       protocol_config = dict(frequency=38000,
#                         duty_cycle=0.33,
#                         leading_pulse_duration=9000,
#                         leading_gap_duration=4500,
#                         one_pulse_duration = 562,
#                         one_gap_duration = 1686,
#                         zero_pulse_duration = 562,
#                         zero_gap_duration = 562,
#                         trailing_pulse = 0)
#       self.irda = Irda(irda_param, "NEC", protocol_config)

    def focus(self, setfocus=2):
        if self.servo_focus is None:
            return False
        print(isinstance(setfocus, int))
        self.servo_focus.setServoAboutRad(aradius=setfocus)
        self.servo_focus.stop0()
        return True

    def power_on_off(self, switch=0):
        if (self.relay is None) and (self.irda is None):
            return False
        if not isinstance(switch, int):
            raise ValueError(f"Switch parameter must be an integer, not {type(switch)}.")

        if switch == 1:
            if self.relay is not None:
                self.relay.on()
                sleep(20)   #wait on poweron
            if self.irda is not None:
                self.keyboard("power")
                sleep(10)   #wait on turn on
        else:
            if self.servo_focus is not None:
                self.servo_focus.stop()
            if self.irda is not None:
                #double send is better reaction
                self.keyboard("power")
                self.keyboard("power")
            sleep(3)
            if self.relay is not None:
                self.relay.off()
        return True

    def poweron(self):
        self.power_on_off(switch=1)

    def poweroff(self):
        self.power_on_off(switch=0)

    def keyboard(self, key, replay=1):
        # NEC code Infra /32
        if not isinstance(replay,int) or replay<1:
            replay = 1
        if (not isinstance(key, str)) or (self.irda is None):
            return False
        key = key.upper()
        for i in range(replay):
            if key == "POWER":
                self.irda.send_code("000000001111110101000000101111111")  #0xFD40BF/32
            elif key == "MENU":
                self.irda.send_code("000000001111110100100000110111111")
            elif key == "INPUT":
                self.irda.send_code("000000001111110101100000100111111")
            elif key == "OK":
                self.irda.send_code("000000001111110110010000011011111")
            elif key == "ESC":
                self.irda.send_code("000000001111110110001000011101111")
            elif key == "MUTE":
                self.irda.send_code("000000001111110100000000111111111")
            elif key == "UP":
                self.irda.send_code("000000001111110110100000010111111")
            elif key == "LEFT":
                self.irda.send_code("000000001111110100010000111011111")
            elif key == "RIGHT":
                self.irda.send_code("000000001111110101010000101011111")
            elif key == "DOWN":
                self.irda.send_code("000000001111110110110000010011111")
            elif key == "VOL_UP":
                self.irda.send_code("000000001111110101001000101101111")
            elif key == "VOL_DOWN":
                self.irda.send_code("000000001111110101101000100101111")
            sleep(1)


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) : %(message)s',
        level=logging.DEBUG,
    )
    #ir = irda.Irda(5, "NEC", dict())
    pr = ArtikProjektor(servo_param=PROJECTOR_FOCUS)
    pr.poweron()
    print("pr ready")
    while True:
        data = input("Enter the data to be sent : ")
        pr.focus(int(data))
    #pr.poweroff()
    #pr.irda.send_code("000000001111110101000000101111111")
    #pr.irda.send_code("000000001111110101000000101111111")
    #print("pr on")
    #sleep(10)
    print("pr off")
    #pr.irda.send_code("000000001111110101000000101111111")
    #pr.irda.send_code("000000001111110101000000101111111")
    #pr.poweroff()
    print("exit")
