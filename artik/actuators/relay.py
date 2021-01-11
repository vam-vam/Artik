#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Control switching of the HL-52S relay module.
"""

from collections import namedtuple

import RPi.GPIO as GPIO


RelayWithNote = namedtuple("RelayWithNote", "relay note")


class RelayModule:
    """A single relay module."""
    def __init__(self, pinrelay):
        self.relay_on = None
        self.relay_pin = None
        if isinstance(pinrelay, int) and pinrelay > 0:
            self.relay_pin = pinrelay
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            self.off()
        else:
            raise NameError('Pinrelay parameter is not a integer.')

    def on(self):
        try:
            GPIO.setup(self.relay_pin, GPIO.OUT)
            self.relay_on = True
        except Exception:
            raise RuntimeError("Can't switch state to 'on'.")

    def off(self):
        try:
            GPIO.setup(self.relay_pin, GPIO.IN)
            self.relay_on = False
        except Exception:
            raise RuntimeError("Can't switch state to 'off'.")

    def state(self):
        return self.relay_on


class RelayModules:
    """Multiple relays, allowing "bulk" control to switch on/off all relays at once."""
    def __init__(self, *args):
        self.relays = [
            RelayWithNote(RelayModule(pinrelay=pin), None)
            for pin in args
            if isinstance(pin, int)
        ]
        self.off(relay_pos=-1)  # switch off all relays on init

    def on(self, relay_pos):
        if relay_pos < 0:
            for relay, note in self.relays:
                relay.on()
        else:
            self.relays[relay_pos].relay.on()

    def off(self, relay_pos):
        if relay_pos < 0:
            for relay, note in self.relays:
                relay.off()
        else:
            self.relays[relay_pos].relay.off()

    def state(self, relay_pos):
        if relay_pos < 0:
            raise ValueError("Cannot get state of all relays")
        return self.relays[relay_pos].relay.state()
