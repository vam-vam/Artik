#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""Artik's brain.

This module is the main interface for controlling the robot's behaviour.

The robot's web API uses this interface to control the robot remotely; see server.py.

"""

import logging
import time
import threading
import uuid
from collections import namedtuple

import RPi.GPIO as GPIO
import cv2

from artik.sensors import bme280
from artik.sensors import hcsr04
from artik.sensors import mcp3208
from artik.sensors import gas
# from artik.actuators import irda
from artik.arduino import Irda
from artik.sensors import hmc5883l
from artik.sensors import ina219
from artik.actuators import voice
from artik.actuators import lcd_display
from artik.actuators import lcd_projector
from artik.actuators import tb6600
from artik.actuators import relay
from artik.actuators import servo
from artik import chat
from artik import eye


logger = logging.getLogger(__name__)

DistanceMeasurement = namedtuple("DistanceMeasurement", "measurement sensor_position_angle obstacle_if_closer")
PowerVoltage = namedtuple("PowerVoltage", "voltage min_safe_voltage") # mysleno k alivie funkci a senzoru napeti


# config for ARTIK and servos for 50Hz (1=228; 1.5=342;2=458)
LEGSPOSTURE = {
    "channel": 10,
    "min": 305,
    "max": 440,
    "position0": 342,
    "scale": 1,
    "up_pin": 25,
    "down_pin": 4,
}

LEGS_RIGHT = {
    "channel": 8, "min": 228, "max": 458, "position0": 342, "scale": 4, "speed": 0.004, "radius": 0
}

LEGS_LEFT = {
    "channel": 9, "min": 228, "max": 458, "position0": 342, "scale": 4, "speed": 0.004, "radius": 0
}

HEAD = {
    "channel": 6,
    "min": 212,
    "max": 465,
    "position0": 342,
    "scale": 5,
    "radius": 60,
}

HEAD_STEPPER = {
    "stepPin": 24,
    "directionPin": 18,
    "enablePin": 23,
    "min": -16290,
    "max": 16290,
    "scale": 16290,
    "scale_steps": 360,
    "speedMinWait": 0.000001,
}

EYE1_TILT = {
    "channel": 4,
    "min": 248,
    "max": 390,
    "position0": 350,
    "scale": 4,
    "radius": 30,
    "up_position": 390,
    "down_position": 340,
}

PROJECTOR_FOCUS = {
    "channel": 5,
    "min": 230,
    "max": 455,
    "position0": 230,
    "scale": 44,
    "radius": 86,
}

IRDA_SEND_PIN = 18

# Control brain
# 1=manual: no intelligence, do what the user says. For example, hit obstacles (no checking).
# 2=semiautomatic: user submits commands, robots tries to pretect itself, e.g. avoid obstacles.
# 3=automatic: fully autonomous regime, NOT USED
BRAIN = 2

OBSTACLE_DISTANCES = []
sensor_temperature = []
sensor_pressure = []
sensor_humidity = []
SENSOR_VOLTAGE = []
sensor_compass = []
CHAT_BOT_CORPUS = "./data/chat/czech"


class ArtikBrain:
    """Artik's brain. This is the main robot API, as used from the web API or from other programs."""

    def __init__(self):
        logger.info("init server ARTIK")
        self.leg_right = Leg(LEGS_RIGHT)
        self.leg_left = Leg(LEGS_LEFT)
        self.legs_posture = LegsPosture(LEGSPOSTURE, self.leg_right, self.leg_left)
        self.head = Head(HEAD_STEPPER)
        self.eyes = []
        # add raspberry pi camera
        self.eyes.append([eye.Eye(source=-1, tilt_param=EYE1_TILT), None])
        self.eyes[-1][1] = eye.BrainEyeArtik(self.eyes[-1][0])
        # add usb camera
        for i in range(1):
            try:
                self.eyes.append([eye.Eye(source=i), None])
                self.eyes[-1][1] = eye.BrainEyeArtik(self.eyes[-1][0])
            except Exception:
                logger.exception("Is only camer PI and %s.", i - 1)
                break

        # setup GPIO
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)

        # setup relay
        try:
            self.relays = relay.RelayModules(6, 12)
        except Exception:
            self.relays = None

        # setup LCD display
        try:
            self.lcd = lcd_display.ArtikDisplay()
            logger.info('LCD display is ready.')
        except Exception:
            logger.exception("failed to initialize LCD display")
            self.lcd = None

        # setup voice
        try:
            self.voice = voice.ArtikVoice(voice=-1, lcd=self.lcd)
            logger.info("Voice is ready %s", self.voice.voice_output)
        except Exception:
            self.voice = None
            logger.exception("Error start voice ARTIK.")
        self.chat = chat.Chatbot(CHAT_BOT_CORPUS)

        # setup projector
        try:
            self.projectors = lcd_projector.ArtikProjektor(servo_param=PROJECTOR_FOCUS)
            if self.relays is not None:
                assert len(self.relays) > 1
                self.projectors.relay = self.relays[1].relay
        except Exception:
            self.projectors = None
            logger.exception('Error start projector.')

        # init sensors
        self.sensors = ArtikHwInits(voice=self.voice)
        #self.sensors = None  # docasne vypnuti senzoru

        # setup sensor temperature
        try:
            self.sensors.temperature_init()
        except Exception:
            logger.exception('Error starting temperature sensor')

        # setup sensor measurement
        try:
            self.sensors.distance_init()
        except Exception:
            logger.exception('Error starting measurement sensor')

        # setup sensor pressure
        try:
            self.sensors.pressure_init()
        except Exception:
            logger.exception('Error starting pressure sensor')

        # setup sensor humidity
        try:
            self.sensors.humidity_init()
        except Exception:
            logger.exception('Error starting humidity sensor')

        # setup sensor compass
        # try:
        #   self.sensors.compass_init()
        # except Exception:
        #   logger.exception('Error start sensor compass')

        # setup sensor voltage
        try:
            self.sensors.voltage_init()

            # run a background thread to put the robot to sleep when it's out of battery
            self.live = threading.Thread(target=self.alive, name="Thread-live", args=(), daemon=True)
            self.live.start()
        except Exception:
            logger.exception('Error starting voltage sensor')
            self.love = None

        # setup sensor gas CO
        try:
            #self.sensors.gas_sensor(channel=None) #aktualne vypnut
            self.sensors.gas_sensor_init(channel=23)  #pin for digital output
        except Exception:
            logger.exception('Error start sensor GAS.')

        self.voice("ok", 0)

    def speaking(self, text, voice=None):
        """Chatbot - converse with the robot based on a dictionary of answers chosen
        according to user's input query.

        Arguments:
            text {str} -- input query
            voice {int} -- choice of response type

        Returns:
            str -- FIXME

        """
        if isinstance(voice, int):
            if voice >= -1:
                self.voice.voice_output = voice
            voice = self.voice
        else:
            voice = None
        return self.chat.response(text, voice)

    def alive(self):
        """Check the battery state to make sure the robot has enough energy for basic functions, or
        to safely switch itself off.

        """
        logger.info("Init base live.")
        while len(SENSOR_VOLTAGE) > 0:
            voltage0 = SENSOR_VOLTAGE[0][0].voltage()
            if voltage0 < SENSOR_VOLTAGE[0][2]:
                logger.critical("Low voltage, POWEROFF")
                self.projector("OFF")  # poweroff projector
                for i in range(2):
                    self.speak(i, 2)
                    time.sleep(0.6)
                    self.speak("Jdu spaat", 1)
                    time.sleep(3.6)
            # Go to sleep = power off the entire robot.
            # Commented out for now because of testing.
            # sys.exit(0)  # FIXME this is not poweroff; it will just exit the current process.
            elif voltage0 < (SENSOR_VOLTAGE[0][1] / 100 * 90):
                logger.warning("Low voltage")
                self.projector("OFF")  # poweroff projector
                self.speak("Maam hlad, chci jiist", 1)
                time.sleep(3.6)
                self.speak("Maam hlad, chci jiist", 1)
            time.sleep(6)

    def relay(self, relay_id=-1, action=-1):
        """Switch a relay on/off.

        Arguments:
            relay {int} -- id relay; FIXME what does -1 mean?
            action {int} -- desired state; FIXME what does -1 mean?

        Returns:
            {dictionary} -- return current state of selected relay

        """
        result = {}
        result["Relay_no"] = relay_id
        result["Relay_state"] = "NONE"
        if not isinstance(relay_id, int):
            return result
        if action == 0:
            self.relays.off(relay_id)
            result["Relay_state"] = "OFF"
        elif action == 1:
            self.relays.on(relay_id)
            result["Relay_state"] = "ON"
        elif action == -1:
            self.relays.state(relay_id)
            result["Relay_state"] = self.relays.state(relay_id).upper()
        return result

    def projector(self, command, replay=1):
        """Control the LCD projector.

        Arguments:
            command {str} -- commands for the projector
            replay {int} -- number of repetitions for the command

        """
        if not isinstance(replay, int):
            replay = 1
        if not (self.projectors is None or command is None) and isinstance(command, str):
            command = command.upper()
            if command == "ON":
                self.projectors.poweron()
            elif command == "OFF":
                self.projectors.poweroff()
            elif command == "FOCUS":
                self.projectors.focus(replay)
            else:
                self.projectors.keyboard(key=command, replay=replay)

    def irda_send(self):
        """Send infrared signal to the IrDa port."""
        # TODO zasilani kodu
        pass

    def irda_recived(self):
        """Receive infrared signal from the IrDa port
        """
        # TODO prijem kodu z jineho vysilace
        pass

    def display(self, text=None, action=-1):
        """Show text on the built-in LCD display.

        Arguments:
            text {str} -- text to display
            action {int} -- FIXME

        """
        self.lcd.text_thread(text=text or "", action=int(action))

    def speak(self, action, voice=-1):
        """Say the given text or display it on the LCD screen.

        Arguments:
            action {int} -- [description]; FIXME
            voice {int} -- [description]; FIXME
            FIXME and where is the input text to say or display?
        Returns:
            Dictionary-- [description]; FIXME
        """
        result = {}
        result["speak"] = "False"
        if voice == -1:
            result["speak"] = "Stop"
            self.voice.stop123()
        else:
            self.voice(action, voice)
            result["speak"] = "OK"
        return result

    def turn_head(self, direction, speed=2000):
        """Turn the head: what direction and how fast.

        Arguments:
            direction {int} -- Rotation direction, conveyed by a position/negative value.
            speed {int} -- Rotation speed.
        Returns:
            [type] -- [description] FIXNE
        """
        if speed > 0:
            return self.head.direction(direction, speed)
        else:
            return self.head.stop_now()

    def head_answer_no(self):
        """Shake the robot's head."""
        return self.head.answer_no()

    def eye_picture(self, eye_id=0):
        """Return image from the given camera, in JPEG format.

        Arguments:
            eye_id {int} -- camera ID
        Returns:
            [type] -- [description] FIXME

        """
        return self.eyes[eye_id][0].picture(format="jpeg")  # FIXME what is the `[0]`?

    def eye_record(self, eye_id=0, rec_time=0):
        """Return file name from the given camera, to record.

        Arguments:
            eye_id {int} -- camera ID
            time {int} -- duration for record
        Returns:
            status {int} -- status recording
            file {str} -- file name

        """
        status ='READY'
        file = 'output.avi'
        # presuout nahravano do eye souboru pod brain
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(file,fourcc, 20.0, self.eyes[eye_id][0].resolution())
        rec_time = time.time()+rec_time
        while time.time() < rec_time:
            out.write(self.eyes[eye_id][0].read())
            status ='RECORD'
        out.release()
        return status, file


    def eye_detect(self, eye_id=0, detect=0):
        """Detect a face or defined object.
        FIXME why are these two in the same function?

        Arguments:
            eye_id {int} -- camera ID
            detect {int} -- type of detection; FIXME what does this mean?
        Returns:
            [type] -- FIXME
        """
        image = self.eyes[eye_id][0].read()
        image_diag = []
        if detect == 0:
            _, _, image_diag = self.eyes[eye_id][1].face_detect(
                image, facesave=True, diag=True,
            )
        if detect == 1:
            _, _, image_diag = self.eyes[eye_id][1].object_detect_dnn(
                image, imgsave=True, diag=True,
            )
        if detect == 2:
            _ = self.eyes[eye_id][1].object_detect_surf(image, image)  # TODO
        if detect == 3:
            _, _, image_diag = self.eyes[eye_id][1].face_detect(
                image, facesave=True, diag=True,
            )
            _, _, image_diag2 = self.eyes[eye_id][1].object_detect_dnn(
                image, imgsave=True, diag=True,
            )
            image = self.eyes[eye_id][1].picture_merge(image_diag2, image)
        image = self.eyes[eye_id][1].picture_merge(image_diag, image)
        return self.eyes[eye_id][1].picture(image)

    def eye_move(self, eye_id=0, leftright=0, updown=0, leftright_speed=2000, updown_speed=2000):
        """Move the eye in any direction.
        FIXME neodpovida texty prace: oko se ma pohybovat pouze nahoru/dolu.

        Arguments:
            eye_id {int} -- camera ID (default: {0})
            leftright {int} -- move eye to the left/right
            updown {int} -- move up/down
            leftright_speed {int} -- left/right movement speed
            updown_speed {int} -- up/down movement speed

        Returns:
            boolean -- [description] FIXME
        """
        if updown_speed != 0:
            self.eyes[eye_id][0].moveaboutrad(tilt_radius=updown, tilt_speed=updown_speed)
        else:
            self.eyes[eye_id][0].stop_now()
        if leftright_speed != 0:
            self.head.moveaboutrad(leftright, leftright_speed)
        else:
            self.head.stop_now()

    def track_eye(self, eye_id=0, img_object=None):
        """Track a selected object or face.

        Arguments:
            eye_id {int} -- camera ID
            img_object {[type]} -- object to track

        Returns:
            [type] -- return picture in selected format; FIXME what?? why, and what format?

        """
        image = self.eyes[eye_id][0].read()
        distance = (0, 0)
        image_diag = []
        if img_object is None:
            faces, _, image_diag = self.eyes[eye_id][1].face_detect(image)
            image = self.eyes[eye_id][1].picture_merge(image_diag, image)
            for (x, y, w, h) in faces:
                distance = self.eyes[eye_id][1].distance_center(
                    co=(x, y, w, h), inside_rectangle=False
                )
                break
        else:
            img_objects = self.eyes[eye_id][1].object_detect_surf(image, img_object)
            image = self.eyes[eye_id][1].picture_add_rectangle(image, img_objects)
            image = self.eyes[eye_id][1].diagnostic(image)
            for (x, y, w, h) in img_objects:
                distance = self.eyes[eye_id][1].distance_center(
                    co=(x, y, w, h), inside_rectangle=False,
                )
                break
        if distance[2] != 0:
            self.walk(left_speed_direction=1, right_speed_direction=1, go_time=1500)
        else:
            self.walk(left_speed_direction=0, right_speed_direction=0, go_time=1500)
        if distance[1] != 0:
            self.eyes[eye_id][0].moveaboutrad(
                tilt_radius=int(distance[1] * self.eyes[eye_id][0].eye_correction[1]),
                tilt_speed=1,
            )
        else:
            self.eyes[eye_id][0].stop_now()
        if distance[0] != 0:
            head_korekce = 25 / self.eyes[eye_id][0].resolution()[0] * -1
            self.head.moveaboutrad(int(distance[0] * head_korekce), 4)
        else:
            self.head.stop_now()
        if self.head.head_max:
            self.walk(left_speed_direction=-1, right_speed_direction=1, go_time=1500)
            self.head.moveaboutrad(-15, 4)
            self.track_eye(eye_id=eye_id)
        if self.head.head_min:
            self.walk(left_speed_direction=1, right_speed_direction=-1, go_time=1500)
            self.head.moveaboutrad(15, 4)
            self.track_eye(eye_id=eye_id)
        return self.eyes[eye_id][0].picture(image=image, format="jpeg")

    def fold_legs(self, up=0):
        """Fold the robot's legs.

        Keyword Arguments:
            up {int} -- fold direction

        Returns:
            [type] -- [description] FIXME
        """
        result = False
        up = int(up)
        up = 0  # zamezeni skladani FIXME
        result = self.legs_posture.stop()
        if up == 1:
            result = self.legs_posture.up()
        elif up == -1:
            result = self.legs_posture.down()
        elif up == 0:
            result = self.legs_posture.stop()
        return result

    def walk(self, left_speed_direction, right_speed_direction, go_time=None):
        """Define the movement of the entire robot.

        Arguments:
            left_speed_direction {int} -- speed and direction; FIXME how can both be defined in one `int`??
            right_speed_direction {int} -- speed and direction; FIXME how can both be defined in one `int`??
            go_time {int} -- Movement duration (default: {None})

        Returns:
            [type] -- [description] FIXME

        """
        left_speed_direction = int(left_speed_direction)
        right_speed_direction = int(right_speed_direction)
        if go_time is None:
            go_time = 1000
        go_time = int(go_time)
        # control direction
        if (
            BRAIN > 1
            and (left_speed_direction != 0 or right_speed_direction != 0)
            and not self.walking_direction_enable(
                left_speed_direction, right_speed_direction,
            )
        ):
            left_speed_direction = 0
            right_speed_direction = 0
        # forward/backward/left/right
        hash_uuid = str(uuid.uuid4())
        logger.debug(
            "Chuze 1 rotation Left %s, Right %s, cas:%s, run:%s",
            left_speed_direction,
            right_speed_direction,
            go_time,
            time.time(),
        )
        self.leg_left.leg_servo.servo_uuid = hash_uuid
        if left_speed_direction != 0:
            self.jdiL = threading.Thread(
                target=self.leg_left.direction,
                name="Thread-LegGoLeft",
                args=(left_speed_direction, go_time, hash_uuid),
                daemon=True,
            )
            self.jdiL.start()
        else:
            self.jdiL = threading.Thread(
                target=self.leg_left.stop,
                name="Thread-LegStopLeft",
                args=(hash_uuid,),
                daemon=True,
            )
            self.jdiL.start()
        logger.debug(
            "Chuze 2 rotation Left %s, Right %s, cas:%s, run:%s",
            left_speed_direction,
            right_speed_direction,
            go_time,
            time.time(),
        )
        self.leg_right.leg_servo.servo_uuid = hash_uuid
        if right_speed_direction != 0:
            self.jdiR = threading.Thread(
                target=self.leg_right.direction,
                name="Thread-LegGoRight",
                args=(right_speed_direction, go_time, hash_uuid),
                daemon=True,
            )
            self.jdiR.start()
        else:
            self.jdiR = threading.Thread(
                target=self.leg_right.stop,
                name="Thread-LegStopRight",
                args=(hash_uuid,),
                daemon=True,
            )
            self.jdiR.start()
        if BRAIN > 1 and (left_speed_direction != 0 or right_speed_direction != 0):
            logger.info(
                "Chuze 3 hash=%s Left %s, Right %s",
                hash_uuid,
                self.leg_left.leg_servo.servo_uuid,
                self.leg_right.leg_servo.servo_uuid,
            )
            while (
                hash_uuid == self.leg_left.leg_servo.servo_uuid
                and hash_uuid == self.leg_right.leg_servo.servo_uuid
            ):
                logger.info("Chuze XXXXXXXXXX stop")
                if not self.walking_direction_enable(
                    left_speed_direction, right_speed_direction
                ):
                    hash_uuid = str(uuid.uuid4())
                    logger.info("Chuze 1-2 stop")
                    self.jdiL = threading.Thread(
                        target=self.leg_left.stop,
                        name="Thread-LegStopLeft",
                        daemon=True,
                    )
                    self.jdiL.start()
                    self.jdiR = threading.Thread(
                        target=self.leg_right.stop,
                        name="Thread-LegStopRight",
                        daemon=True,
                    )
                    self.jdiR.start()
                time.sleep(0.3)
        return True

    def status(self):
        """Return the robot's status: all sensors, actuators.

        Returns:
            dictionary
        """
        result = {}
        result["LEGSPOSTURE"] = self.legs_posture.state()
        result["LEGS_RIGHT"] = self.leg_right.state()
        result["LEGS_LEFT"] = self.leg_left.state()
        result["HEAD"] = self.head.scale()
        result["OBSTACLE_SENSOR0"] = OBSTACLE_DISTANCES[0].measurement.distance_last
        return result

    def _check_can_walk(self, left_direction=None, right_direction=None):
        """Check whether Artik can walk in the specified direction.

        Arguments
        ---------
        left_direction: int
            negative: Artik is reversing with the left leg.
            positive: Artik is moving forwarding with the left leg.
            0: Artik's left leg is immobile.

        right_direction: int
            negative: Artik is reversing with the right leg.
            positive: Artik is moving forwarding with the right leg.
            0: Artik's right leg is immobile.

        """
        result = True
        i = None
        for i in OBSTACLE_DISTANCES:
            # logger.debug("Enable direction sensor %s: L:%s R:%s, distance %s - limit %s", i, left_direction, right_direction, i[0].distance_last, i[2])
            distance = i.measurement.distance_last
            if distance is not None:
                if distance == 0:  # no measurement, or obstacle too close, or too far away => assume no obstacle
                    continue
                result = distance > i.obstacle_if_closer

                if left_direction is not None:
                    # forward
                    if left_direction > 0 and not (0 < i.sensor_position_angle < 180):
                        result = True
                    # backward
                    elif left_direction < 0 and not (-180 < i.sensor_position_angle < 0):
                        result = True

                if right_direction is not None:
                    # forward
                    if right_direction > 0 and not (0 < i.sensor_position_angle < 180):
                        result = True
                    # backward
                    elif right_direction < 0 and not (-180 < i.sensor_position_angle < 0):
                        result = True

                # Robot is rotating in place or standing completely still => no collision.
                if right_direction is not None and left_direction is not None:
                    if left_direction == -right_direction:
                        result = True
            if not result:
                break
        #            logger.info("Enable direction sensor %s: L:%s R:%s, distance %s - limit %s", i, left_direction, right_direction, i[0].distance_last, i[2])
        return result


class Head:
    """Control the robot's head."""

    def __init__(self, head_param):
        logger.debug("initializing head with %s", head_param)
        pins = [
            head_param["stepPin"],
            head_param["directionPin"],
            head_param["enablePin"],
        ]
        self.head_stepper = tb6600.Stepper_tb6600(
            pins=pins,
            scale_steps=head_param["scale_steps"],
            scale=head_param["scale"],
            speed=head_param["speedMinWait"],
            left_max=head_param["min"],
            right_max=head_param["max"],
        )

    def answer_no(self):
        """Make Artik shake its head."""
        logger.debug("Calling method Head.answer_no")
        self.head_stepper.stop()
        hash_uuid = self.head_stepper.suid
        m = 15
        cas = 0.3
        self.head_stepper.distance(m, cas)
        if hash_uuid == self.head_stepper.suid:
            self.head_stepper.distance(m * -2, cas * 2)
        if hash_uuid == self.head_stepper.suid:
            self.head_stepper.distance(m * 2, cas * 2)
        if hash_uuid == self.head_stepper.suid:
            self.head_stepper.distance(-m, cas)

    def direction(self, direction=0, speed=1):
        """Rotate the head.

        Keyword Arguments:
            direction {int}; FIXME units
            speed {int}; FIXME units
        Returns:
            [type] -- [description] FIXME
        """
        result = False
        if direction != 0:
            result = self.head_stepper.distance(direction, speed)
        elif direction == 0:
            result = self.head_stepper.stop()
        logger.debug("Head rotation speed %s and direction %s", speed, direction)
        return result

    def moveaboutrad(self, radius=0, speed=1):
        """Rotate the head by the given angle.

        Arguments:
            radius {int} -- Movement direction
            speed {int} -- Movement speed
        """
        speed = int(speed)
        if speed > 0:
            if radius != 0:
                move_head = threading.Thread(
                    target=self.__head_moveaboutrad,
                    name="Thread-head",
                    args=(radius, speed),
                    daemon=True,
                )
                move_head.start()
            else:
                self.stop_now()

    def __head_moveaboutrad(self, radius=0, speed=1):
        result = False
        radius = int(radius)
        logger.debug("Rotate head by %s radias at speed %s", radius, speed)
        result = self.head_stepper.distance(distance=radius, speed=speed)
        return result

    def stop_now(self):
        """Stop any head movement."""
        logger.debug("Stop position")
        self.head_stepper.stop()

    @property
    def head_max(self):
        """Return the position of maximum rotation; FIXME what does this mean?

        Returns:
            [int] -- hodnota; FIXME
        """
        return self.head_stepper.IsMaxPosition()

    @property
    def head_min(self):
        """Return the position of minimum rotation; FIXME what does this mean?

        Returns:
            int -- hodnota; FIXME
        """
        return self.head_stepper.IsMinPosition()

    def scale(self):
        """FIXME"""
        return self.head_stepper.scale


class HeadServo:
    def __init__(self, head_param):
        logger.debug("init head")
        self.head_servo = servo.Servo(
            head_param["channel"],
            head_param["position0"],
            head_param["min"],
            head_param["max"],
            head_param["scale"],
            0.004,
            head_param["radius"],
        )
        self.head_servo.stop0()

    def answer_no(self):
        logger.debug("calling method Head.no")
        suid = str(uuid.uuid4())
        self.head_servo.servo_uuid = suid
        self.head_servo.setServo(400, suid)
        self.head_servo.setServo(285, suid)
        self.head_servo.setServo(400, suid)
        self.head_servo.setServo(285, suid)
        self.head_servo.stop(suid)
        self.head_servo.stop0()

    def direction(self, direction=0, speed=0):
        result = False
        direction = int(direction)
        speed = int(speed)
        high = 0
        if speed < 1:
            speed = 1
        if direction > 0:
            high = self.head_servo.map(
                direction,
                0,
                self.head_servo.servo_scale,
                self.head_servo.servo_position0,
                self.head_servo.servo_max,
            )
            result = self.head_servo.setServoMove(high, speed)
        elif direction < 0:
            high = self.head_servo.map(
                direction * -1,
                0,
                self.head_servo.servo_scale,
                self.head_servo.servo_position0,
                self.head_servo.servo_min,
            )
            result = self.head_servo.setServoMove(high, speed)
        elif direction == 0:
            result = self.head_servo.stop()
        logger.debug(
            "Head rotation speed %s and direction %s High: %s", speed, direction, high,
        )
        if result:
            self.head_servo.stop0()
        return result

    def moveaboutrad(self, radius=0, speed=1):
        speed = int(speed)
        if speed > 0:
            if radius != 0:
                move_head = threading.Thread(
                    target=self.head_moveaboutrad,
                    name="Thread-head",
                    args=(radius, speed),
                    daemon=True,
                )
                move_head.start()
            else:
                self.stop_now()
        return False

    def head_moveaboutrad(self, radius=0, speed=1):
        result = False
        radius = int(radius)
        speed = int(speed)
        if speed < 1:
            speed = 1
        hash_uuid = str(uuid.uuid4())
        self.head_servo.servo_uuid = hash_uuid
        logger.debug("Head move about rad %s and speed %s", radius, speed)
        result = self.head_servo.setServoAboutRad(
            aradius=radius, speed=speed, suid=hash_uuid
        )
        # if result:
        #    self.head_servo.stop0(suid=hash_uuid)
        return result

    def stop_now(self):
        logger.error("Stop ted pozice")
        self.head_servo.stop0()

    @property
    def head_max(self):
        return self.head_servo.servoIsMaxPosition()

    @property
    def head_min(self):
        return self.head_servo.servoIsMinPosition()

    def scale(self):
        return self.head_servo.servo_scale


class LegsPosture:
    def __init__(self, posture_param, leg_right, leg_left):
        logger.debug("init LegsPosture")
        self.posture_servo = servo.Servo(
            posture_param["channel"],
            posture_param["position0"],
            posture_param["min"],
            posture_param["max"],
            posture_param["scale"],
        )
        self.posture_servo.stop0()
        self.leg_right = leg_right
        self.leg_left = leg_left
        self.gpio_up_pin = posture_param["up_pin"]
        self.gpio_down_pin = posture_param["down_pin"]
        # set position legs up=True or down=False
        self.posture_up = True
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_up_pin, GPIO.IN)
        GPIO.setup(self.gpio_down_pin, GPIO.IN)

    def up(self):
        return self.posture(1)

    def down(self):
        return self.posture(-1)

    def stop(self):
        return self.posture(0)

    def posture(self, up=0):
        logger.debug("Calling legs posture %s", up)
        result = False
        self.leg_right.stop()
        self.leg_left.stop()
        # hash id
        hash_uuid = str(uuid.uuid4())
        self.posture_servo.servo_uuid = hash_uuid
        end = time.time() + 5
        logger.debug(
            "Running posture up(%s) - %s, pin up=%s, pin down=%s",
            up,
            hash_uuid,
            self.gpio_up_pin,
            self.gpio_down_pin,
        )
        if up == 1 and GPIO.input(self.gpio_up_pin) == 0:
            self.posture_servo.setServo(self.posture_servo.servo_max, hash_uuid)
            while (
                GPIO.input(self.gpio_up_pin) == 0
                and end >= time.time()
                and self.posture_servo.servo_uuid == hash_uuid
            ):
                time.sleep(0.5)
            self.posture_up = True
        elif up == -1 and GPIO.input(self.gpio_down_pin) == 0:
            self.posture_servo.servo_status = self.posture_servo.setServo(
                self.posture_servo.servo_min, hash_uuid
            )
            while (
                GPIO.input(self.gpio_down_pin) == 0
                and end >= time.time()
                and self.posture_servo.servo_uuid == hash_uuid
            ):
                time.sleep(0.5)
            self.posture_up = False
        if self.posture_servo.servo_uuid == hash_uuid:
            result = True
        logger.debug("End running posture %s", self.posture_servo.servo_uuid)
        self.posture_servo.stop()
        time.sleep(1)
        self.posture_servo.stop0()
        return result

    def state(self):
        result = {}
        result = self.posture_servo.state()
        result["up_pin"] = self.gpio_up_pin
        result["down_pin"] = self.gpio_down_pin
        return result


class Leg:
    def __init__(self, leg_param):
        logger.debug("Inititializing leg with %s", leg_param)
        self.leg_servo = servo.Servo(
            channel=leg_param["channel"],
            position0=leg_param["position0"],
            min=leg_param["min"],
            max=leg_param["max"],
            scale=leg_param["scale"],
            speed=leg_param["speed"],
            radius=leg_param["radius"],
        )

    def rotation_map(self, x=0, suid=""):
        if x > 0:
            return self.leg_servo.setServo(
                self.leg_servo.map(
                    x,
                    0,
                    self.leg_servo.servo_scale,
                    self.leg_servo.servo_position0,
                    self.leg_servo.servo_max,
                ),
                suid,
            )
        elif x < 0:
            return self.leg_servo.setServo(
                self.leg_servo.map(
                    x * -1,
                    0,
                    self.leg_servo.servo_scale,
                    self.leg_servo.servo_position0,
                    self.leg_servo.servo_min,
                ),
                suid,
            )
        else:
            return self.leg_servo.stop()

    def direction(self, direction_speed=0, go_time=0, suid=""):
        result = False
        direction_speed = int(direction_speed)
        go_time = int(go_time)
        logger.debug("Leg direction speed %s and time %s", direction_speed, go_time)
        if go_time <= 0:
            return result
        go_time = min(go_time, 30000)
        go_time = max(go_time, 500)
        if direction_speed != 0:
            go_time = int(go_time / 1000)
            result = self.rotation_map(direction_speed, suid)
            suid = self.leg_servo.servo_uuid
            logger.debug(
                "Leg direction servo uuid: %s = uuid: %s",
                self.leg_servo.servo_uuid,
                suid,
            )
            end = time.time() + go_time
            while time.time() <= end:
                result = True
                time.sleep(go_time / 4)
                if self.leg_servo.servo_uuid != suid:
                    result = False
                    break
            # time.sleep(go_time)
            logger.debug(
                "Leg direction servo uuid: %s = uuid: %s",
                self.leg_servo.servo_uuid,
                suid,
            )
            if result and self.leg_servo.servo_uuid == suid:
                self.leg_servo.stop()
        return result

    def forward(self, direction_speed=0, go_time=0, suid=""):
        result = False
        direction_speed = int(direction_speed)
        if direction_speed > 0:
            result = self.direction(direction_speed, go_time, suid)
        return result

    def backward(self, direction_speed=0, go_time=0, suid=""):
        result = False
        direction_speed = int(direction_speed)
        if direction_speed < 0:
            result = self.direction(direction_speed, go_time, suid)
        return result

    def scale(self):
        return self.leg_servo.servo_scale

    def stop(self, suid=""):
        logger.debug("Leg stop uuid: %s", self.leg_servo.servo_uuid)
        self.leg_servo.stop(suid)
        return True

    def state(self):
        result = {}
        result = self.leg_servo.state()
        result["scale"] = self.scale()
        result["status"] = self.leg_servo.servo_status
        return result


class Alarm:
    def __init__(self, oVoice=None, text=None, repeat=1):
        self.oVoice = oVoice
        self.text = text
        self.repeat = repeat

    def __call__(self):
        self.Alarm()

    def Alarm(self):
        if self.oVoice is not None:
            self.oVoice.stop123()
            for i in range(self.repeat):
                print(i)
                self.oVoice(1, 2)
                time.sleep(0.6)
                self.oVoice(self.text, -1)
                self.oVoice(self.text, 1)
                time.sleep(3.6)
                if self.oVoice.voice_stop:
                    break


class ArtikHwInits:

    def __init__(self, voice=None):
        self.voice = voice

    def temperature_init(self):
        sensor_temperature.append(bme280.Temperature(unit="metric"))
        logger.debug(
            "Temperature sensor ARTIK: %s C", sensor_temperature[-1].temperature(1)
        )
        if sensor_temperature[-1].temperature(1) is not None:
            p = threading.Thread(
                target=bme280.SensorTemperature,
                args=(sensor_temperature[-1], 10),
                daemon=True,
            )
            p.start()
        else:
            logger.debug(
                "Temperature ARTIK: %s C", sensor_temperature[-1].temperature(1),
            )

    def distance_init(self):
        assert OBSTACLE_DISTANCES, "requires at least one distance sensor"

        self.distance = {}
        thermometer = 23  # reference temperature 23°Celsium
        if isinstance(sensor_temperature[0], bme280.Temperature):
            thermometer = sensor_temperature[0]
        OBSTACLE_DISTANCES.append(
            DistanceMeasurement(
                hcsr04.Measurement(
                    trig_pin=13, echo_pin=16, temperature=thermometer,
                ),
                85.00,
                10,
            )
        )
        p = threading.Thread(
            target=hcsr04.SensorThDistance,
            args=(OBSTACLE_DISTANCES[-1].measurement,),
            daemon=True,
        )
        p.start()

        OBSTACLE_DISTANCES.append(
            [
                hcsr04.Measurement(
                    trig_pin=26, echo_pin=21, temperature=thermometer
                ),
                95.00,
                10,
            ]
        )
        p = threading.Thread(
            target=hcsr04.SensorThDistance,
            args=(OBSTACLE_DISTANCES[-1][0],),
            daemon=True,
        )
        p.start()

        OBSTACLE_DISTANCES.append(
            [
                hcsr04.Measurement(
                    trig_pin=19, echo_pin=20, temperature=thermometer
                ),
                -90.00,
                10,
            ]
        )
        p = threading.Thread(
            target=hcsr04.SensorThDistance,
            args=(OBSTACLE_DISTANCES[-1][0],),
            daemon=True,
        )
        p.start()

    def pressure_init(self):
        sensor_pressure.append(bme280.Pressure(unit="metric"))
        logger.debug("Pressure sensor ARTIK: %s pa", sensor_pressure[-1].pressure(1))

    def humidity_init(self):
        sensor_humidity.append(bme280.Humidity(unit="metric"))
        logger.debug("Humidity sensor ARTIK: %s %%", sensor_humidity[-1].humidity(1))

    def gas_sensor_init(self, channel=None):
        if not channel is None:
            self.gas = gas.sensorMQ_9(do_pin=channel)
            self.gas.alarm_action = Alarm(self.voice, "Alarm gass! Pozor Plynn!", 2)
            self.gas.alarmset_DO(self.gas.do_pin)

    def compass_init(self):
        # value for Czech->Prague
        sensor_compass.append(
            hmc5883l.HMC5883L(gauss=0xA0, declination=(4, 13))
        )

    def voltage_init(self):
        # [sensor, primary voltage, limit V shutdown]
        SENSOR_VOLTAGE.append(
            [
                ina219.INA219(
                    shunt_ohms=0.1,
                    max_expected_amps=3.0,
                    address=0x44,
                    log_level=logging.WARNING,
                ),
                12,
                9,
            ]
        )
        SENSOR_VOLTAGE[-1][0].configure(
            voltage_range=SENSOR_VOLTAGE[-1][0].RANGE_32V,
            gain=SENSOR_VOLTAGE[-1][0].GAIN_AUTO,
            bus_adc=SENSOR_VOLTAGE[-1][0].ADC_128SAMP,
            shunt_adc=SENSOR_VOLTAGE[-1][0].ADC_128SAMP,
        )

    def read_sensors(self):
        """FIXME"""
        result = {}
        #      '''  for dist in len(OBSTACLE_DISTANCES):
        #            result['distance_'+dist] =
        #        for temp in sensor_temperature:
        #
        #        for pres in sensor_pressure:
        #
        #        for humi in sensor_humidity:
        #
        return result

