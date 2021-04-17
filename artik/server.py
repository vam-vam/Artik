#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Web server with API for Artik's remote HTTP access.

Run as:
    python -m artik.server DATA_DIRECTORY

The server config is read from DATA_DIRECTORY/artik.conf

"""

import os
import sys
import time
from functools import wraps
import logging

import cherrypy
from cherrypy.lib import auth_basic
from cherrypy.process.plugins import PIDFile

import artik
from artik import brain


# HTTP Basic Auth credentials
BASIC_AUTH_USERS = {"vam": "test"}


logger = logging.getLogger(__name__)


def server_exception_wrap(func):
    """Decorator to handle internal server errors."""

    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        try:
            logger.debug("calling server method '%s'", func.__name__)
            cherrypy.response.timeout = 3600 * 24 * 7  # [s]
            if getattr(cherrypy.request, "json", None):  # treat JSON the same as normal GET/POST parameters
                kwargs.update(cherrypy.request.json)
            start = time.time()
            result = func(self, *args, **kwargs)
            if result is None:
                result = {}
            result["success"] = 1
            result["taken"] = time.time() - start
            logger.info("method '%s' succeeded in %ss", func.__name__, result["taken"])
            return result
        except Exception as e:
            logger.exception("exception serving request")
            result = {"error": repr(e), "success": 0}
            cherrypy.response.status = 500
            return result

    return _wrapper


def dump_func(func):
    """Decorator for logging call arguments."""

    def log_func(*args, **kwargs):
        logger.debug("Function = %s", func.__name__)
        logger.debug("parameters args: %s", func.args)
        logger.debug("parameters kwargs: %s", func.kwargs)

    return log_func


class ArtikServer:
    """Web API for Artik the robot."""

    def __init__(self):
        self.artik = brain.ArtikBrain()

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def index(self):
        result = {}
        result["welcome"] = f"Welcome to Artik server {self.artik.__version__}"
        return result

    @dump_func
    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def chat(self, **kwargs):
        """Conversation with the robot.

        The robot reacts by choosing a suitable answer to a query submitted by the user.

        Arguments:
            voice {int} -- desired format of the answer (0=Artik, 1=PC Man, 2=Sound, -1=Print text to return/display)
            txt {str} -- user input text

        Returns:
            {dictionary} -- answer from artik

        """
        result = {}
        text = ""
        voice = None
        if "voice" in kwargs:
            voice = int(kwargs["voice"])
        if "txt" in kwargs:
            text = str(kwargs["txt"])
            result["answer"] = str(self.artik.speaking(text, voice))
        return result

    @dump_func
    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def display(self, **kwargs):
        """Display text on Artik's display actuator.
        Arguments:
            txt {str} -- Display input a text to a display
            os:  -- Show information status from os to a display (using RAM, CPU, HDD)

        Returns:
            {dictionary} -- result

        """
        result = {}
        result["result"] = "Fail"
        if "txt" in kwargs:
            self.artik.display(text=str(kwargs["txt"]), action=0)
            result["result"] = "Ok"
        if "os" in kwargs:
            self.artik.display(action=2)
            result["result"] = "OS Ok"
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def fold_legs(self, **kwargs):
        """Transform the robot into either two or three stable points (extend its extra leg).

        Arguments:
            down: 3 stable points (3rd leg is down)
            up: 2 stable points (3rd leg is up)
            stop: stop / pause transfomation

        Returns:
            {dictionary} -- result

        """
        result = {}
        result["folded"] = "YES"
        if "up" in kwargs:
            result["result"] = self.artik.fold_legs(1)
        if "down" in kwargs:
            result["result"] = self.artik.fold_legs(-1)
        if "stop" in kwargs:
            result["result"] = self.artik.fold_legs(0)
            result["slozeni"] = "NO"
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def relay(self, **kwargs):
        """Turn on / off device controlled by a relay switch.

        Arguments:
            relay {int} -- id of the relay to use
            on:  -- switch on relay
            off:  -- switch off relay

        Returns:
            {dictionary} -- result

        """
        result = {}
        relay = -1
        akce = -1
        if "relay" in kwargs:
            relay = int(kwargs["relay"])
        if "on" in kwargs:
            akce = 1
        if "off" in kwargs:
            akce = 0
        if relay >= 0:
            result["result"] = self.artik.relay(relay_id=relay, action=akce)
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def project(self, **kwargs):
        """Control the LCD projector built into the robot.

        Arguments:
            action {str} - choice of action; one of {"on", "off", "focus"}
            count {int} -- number of repetitions or focus settings

        Returns:
            {dictionary} -- result

        """
        result = {}
        result["result"] = "Fail"
        count = None
        if "count" in kwargs:
            count = int(kwargs["count"])
        if "action" in kwargs:
            self.artik.projector(command=str(kwargs["action"]), replay=count)
            result["result"] = "OK"
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def walk(self, **kwargs):
        """Move robot in the given direction, speed and duration.

        Arguments:
            forward {int} -- move forward at a specified speed
            backward {int} -- move backward at a specified speed
            left {int} -- rotate left at a specified speed
            right {int} -- rotate right at a specified speed
            stop: -- stop moving
            left_leg {int} -- speed for the left leg
            right_leg {int} -- speed for the right leg
            time {int} -- stop movement after this long

        Returns:
            {dictionary} -- result

        """
        result = {}
        direction_left = 0
        direction_right = 0
        time = None
        if "forward" in kwargs:
            x = int(kwargs["forward"])
            if x < 0:
                x *= -1
            direction_right = x
            direction_left = x
        if "backward" in kwargs:
            x = int(kwargs["backward"])
            if x > 0:
                x *= -1
            direction_right = x
            direction_left = x
        if "left" in kwargs:
            x = int(kwargs["left"])
            direction_right = x * -1
            direction_left = x
        if "right" in kwargs:
            x = int(kwargs["right"])
            direction_right = x
            direction_left = x * -1
        if "left_leg" in kwargs:
            x = int(kwargs["left_leg"])
            direction_left = x
        if "right_leg" in kwargs:
            x = int(kwargs["right_leg"])
            direction_right = x
        if "time" in kwargs:
            time = int(kwargs["time"])
        if "stop" in kwargs:
            direction_right = 0
            direction_left = 0
            time = 1
        if (
            0 <= abs(direction_right) <= self.artik.leg_right.scale()
            and 0 <= abs(direction_left) <= self.artik.leg_left.scale()
        ):
            result["status"] = self.artik.walk(direction_left, direction_right, time)
        else:
            raise ValueError("Invalid parameters")
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def turn_head(self, **kwargs):
        """Turn the robot's head.

        Arguments:
            center:  -- move head to base position
            stop:  -- stop moving
            no:  -- shake head as if saying "no"
            time {int} -- stop movement after this long
            left {int} -- how much to move in this direction
            right {int} -- how much to move in this direction

        Returns:
            {dictionary} -- result

        """
        result = {}
        x = None
        time = 1500
        if "left" in kwargs:
            x = int(kwargs["left"])
        if "right" in kwargs:
            x = -int(kwargs["right"])
        if "time" in kwargs:
            time = int(kwargs["time"])
        if "center" in kwargs:
            x, time = 0, 1
        if "stop" in kwargs:
            x, time = 0, 0
        if x is not None:
            result["result"] = self.artik.turn_head(x, time)
        elif "no" in kwargs:
            result["result"] = self.artik.head_answer_no()
        else:
            raise ValueError("Invalid parameters")
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def eye_move(self, **kwargs):
        """Control the camera movement.

        Arguments:
            eye {int} -- choice of id camera
            timex {int} -- movement duration for left-right movement
            timey {int} -- duration for up-down movement
            left {int} -- how much to move to the left in seconds 
            right {int} -- how much to move to the right in seconds 
            up {int} -- how much to move up in seconds 
            down {int} -- how much to move down in seconds 
            center:  -- move camera to base position
            stop:  -- stop all camera movement

        Returns:
            {dictionary} -- result

        """
        result = {}
        eye = 0
        x = None
        y = None
        timex = 1500
        timey = 1500
        if "timex" in kwargs:
            timex = int(kwargs["timex"])
        if "timey" in kwargs:
            timey = int(kwargs["timey"])
        if "left" in kwargs:
            x = int(kwargs["left"])
        elif "right" in kwargs:
            x = int(kwargs["right"]) * -1
        else:
            x, timex = 0, 0
        if "up" in kwargs:
            y = int(kwargs["up"])
        elif "down" in kwargs:
            y = int(kwargs["down"]) * -1
        else:
            y, timey = 0, 0
        if "center" in kwargs:
            y, x, timex, timey = 0, 0, 1, 1
        if "stop" in kwargs:
            y, x, timex, timey = 0, 0, 0, 0

        if x is not None and y is not None:
            result["result"] = self.artik.eye_move(eye, x, y, timex, timey)
        else:
            raise ValueError("Wrong parameters")
        return result

    @cherrypy.expose
    def snapshot(self, **kwargs):
        """Capture image from a selectated camera, or center the camera on detected face.

        Argument:
            eye {int} -- camera id: which camera to use

        Returns:
            {str} -- returns a jpeg image

        """
        eye = 0
        result = None
        cherrypy.response.headers["Content-Type"] = "image/jpeg"
        if "eye" in kwargs:
            try:
                eye = int(kwargs["eye"])
                result = self.artik.eye_picture(eye_id=eye)
            except Exception:
                eye = 0
        return result

    @cherrypy.expose
    def eye(self, **kwargs):
        """Capture image from a selectated camera, or center the camera on detected face.

        Argument:
            eye {int} -- camera id: which camera to use
            picture: -- return image from the selected camera
            followme: -- track a detected face so that it stays in the middle of the selected camera
            face_detection: -- detect face from a specific camera

        Returns:
            {str} -- returns a jpeg image for debug

        """
        eye = 0
        result = None
        cherrypy.response.headers["Content-Type"] = "image/jpeg"
        if "eye" in kwargs:
            try:
                eye = int(kwargs["eye"])
            except Exception:
                eye = 0
        if "picture" in kwargs:
            result = self.artik.eye_picture(eye_id=eye)
        if "followme" in kwargs:
            result = self.artik.oko_nasleduj(0)
        if "face_detection" in kwargs:
            try:
                result = self.artik.eye_detect(eye_id=eye, detect=int(kwargs["face_detection"]))
            except Exception:
                pass
        return result

    @cherrypy.expose
    def eye_all(self):
        """
        Return HTML that displays images from all cameras. The HTML is auto-refreshed every 200ms.

        Returns:
            {str} -- page HTML

        """
        result = """<html>
                <head>
                    <title>RPi Cam Preview</title>
                    <script type="text/javascript">
                        window.onload = function() {
                """
        for i in range(len(self.artik.eyes)):
            result += (
                "var image"
                + str(i)
                + ' = document.getElementById("mjpeg_dest'
                + str(i)
                + '");'
            )
        result += "function updateImage() {"
        for i in range(len(self.artik.eyes)):
            result += (
                "image"
                + str(i)
                + ".src = image"
                + str(i)
                + '.src.split("&t=")[0] + "&t=" + new Date().getTime();'
            )
        result += """
   }
    setInterval(updateImage, 200);
}
                    </script>
                </head>
                <body>
                    <center>
                    ahoj
                     """
        for i in range(len(self.artik.eyes)):
            result += (
                """<div><img id="mjpeg_dest"""
                + str(i)
                + """" src="obr2?oko="""
                + str(i)
                + '"'
            )
            result += "/></div> <br/>"
        result += """  <!-- <div><img id="mjpeg_dest" src="face2"/></div> -->
                    </center>
                </body>
            </html>"""
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def say(self, **kwargs):
        """Convert text to speech.

        Arguments:
            voice {int} -- select the output voice (0=Artik, 1=PC Man, 2=Sound)
            txt {str} -- text to convert
        Returns:
            {dictionary} -- fettle
        """
        result = {}
        voice = -1
        if "voice" in kwargs:
            try:
                voice = int(kwargs["voice"])
            except Exception:
                voice = -1
        if "txt" in kwargs and voice >= 0:
            result["speak"] = self.artik.speak(str(kwargs["txt"]), voice)
        else:
            result["speak"] = self.artik.speak("", -1)
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def play(self, **kwargs):
        """Play a sound from a defined sound list.

        Arguments:
            file {int} -- select sound by audio ID from list in program (should play arbitrary WAV/OGG/MP3).
        Returns:
            {dictionary} -- result
        """
        result = {}
        snd_file = None
        if "file" in kwargs:
            try:
                snd_file = int(kwargs["file"])
            except Exception:
                try:
                    snd_file = str(kwargs["file"])
                except Exception:
                    snd_file = None
        result["sound_file"] = snd_file
        result["speak"] = self.artik.speak(snd_file, 2)
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def record_video(self, **kwargs):
        """Recording video to file.

        Arguments:
            eye {int} -- select id camera
            time {int} -- time to rec
            stop {} -- stop recording
            stopALL {} -- stop all recording
        Returns:
            {dictionary} -- status
        """
        result = {}
        if "eye" in kwargs:
            try:
                eye = int(kwargs["eye"])
            except Exception:
                eye = 0
        if "time" in kwargs:
            try:
                time = int(kwargs["time"])
            except Exception:
                time = 0
        if "stop" in kwargs:
            time = 0
        if "stopALL" in kwargs:
            time = 0
            eye = -1
        
        status, file = self.artik.eye_record(eye, time)
        result["record_status"] = status
        result["record_file"] = file
        return result

    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def swivel_eye(self, **kwargs):
        """Control the camera movement up or down.

        Arguments:
            eye {int} -- choice of id camera
            timex {int} -- movement duration for left-right movement
            timey {int} -- duration for up-down movement
            up {int} -- how much to move up in seconds 
            down {int} -- how much to move down in seconds 
            center:  -- move camera to base position
            stop:  -- stop all camera movement

        Returns:
            {dictionary} -- result

        """
        result = {}
        eye = 0
        x = None
        y = None
        timex = 0
        timey = 1500
        if "timey" in kwargs:
            timey = int(kwargs["timey"])
        if "up" in kwargs:
            y = int(kwargs["up"])
        elif "down" in kwargs:
            y = int(kwargs["down"]) * -1
        else:
            y, timey = 0, 0
        if "center" in kwargs:
            y, x, timex, timey = 0, 0, 1, 1
        if "stop" in kwargs:
            y, x, timex, timey = 0, 0, 0, 0

        if x is not None and y is not None:
            result["result"] = self.artik.eye_move(eye, x, y, timex, timey)
        else:
            raise ValueError("Wrong parameters")
        return result


    @server_exception_wrap
    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def status(self, **kwargs):
        """Return the status of Artik's brain."""
        return self.artik.status()

    ping = status  # alias for status



if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) : %(message)s",
        level=logging.DEBUG,
    )
    logger.info("running %s", " ".join(sys.argv))

    program = os.path.basename(sys.argv[0])

    if len(sys.argv) < 2:
        print(globals()["__doc__"] % locals())
        sys.exit(1)

    data_directory = sys.argv[1]
    conf_file = os.path.join(data_directory, "artik.conf")
    conf = cherrypy.lib.reprconf.Config(conf_file)
    conf['/'] = {
        'tools.auth_basic.on': False,  # Basic Auth disabled until HTTPS on.
        'tools.auth_basic.realm': 'galaxy',
        'tools.auth_basic.checkpassword': auth_basic.checkpassword_dict(BASIC_AUTH_USERS),
    }
    logger.info("web server configuration: %s", conf)

    pid_file = conf['global'].get('pid_file', None)
    if pid_file:
        PIDFile(cherrypy.engine, pid_file).subscribe()

    cherrypy.quickstart(ArtikServer(), "/", config=conf)

    logger.info("finished running %s", program)
