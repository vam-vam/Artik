#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Access cameras from Raspberry Pi: both built-in and USB cameras.

Code adapted from https://github.com/jrosebr1/imutils/blob/master/imutils/video

Example:
    Camera(source=-1)  # Raspberry Pi camera
    Camera(source=0)  # any USB camera
    Camera(source=-2)  # "mock" camera that does nothing; used for interface compatibility

"""

import logging
from threading import Thread
from time import sleep

import cv2
import picamera
from picamera.array import PiRGBArray
from picamera import PiCamera

logger = logging.getLogger(__name__)


class Camera:
    def __init__(self, source, resolution=(320, 240), framerate=15):
        self.camera = None
        try:
            if source == -1:
                self.camera = PiVideoStream(resolution=resolution, framerate=framerate)
            elif source >= 0:
                self.camera = WebcamVideoStream(src=source, resolution=resolution, framerate=framerate)
            elif source == -2:
                self.camera = EmptycamVideoStream(resolution=resolution, framerate=framerate)
            else:
                raise ValueError("Unknown camera source.")
        except Exception:
            raise RuntimeError("Camera does not exist.")

    def read(self):
        if self.camera.stopped:
            self.camera.start()
        return self.camera.read()

    def __call__(self):
        """FIXME: why is this needed? Who calls this and why?"""
        self.read()

    def stop(self):
        self.camera.stop()

    def picture(self, image=None, format='jpeg'):
        """Return the current camera frame as an image."""
        if image is None:
            image = self.read()
        _, data = cv2.imencode('.' + format, image)
        return data.tostring()

    def resolution(self):
        x, y = self.camera.resolution()
        return (x, y)


class PiVideoStream:
    def __init__(self, resolution=(320, 240), framerate=10):
        # initialize the camera and stream
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True)
        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self.stopped = True

    def start(self):
        # start the thread to read frames from the video stream
        if self.stopped:
            self.stopped = False
            t = Thread(target=self.update, args=(), daemon = True)
            t.start()
            sleep(1)
            return self
        else:
            return None

    def update(self):
        # keep looping infinitely until the thread is stopped
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)
            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True

    def resolution(self):
        x, y = self.camera.resolution
        return (x, y)


class WebcamVideoStream:

    def __init__(self, src=0, resolution=(320, 240), framerate=15):
        # initialize the video camera stream and read the first frame
        # from the stream
        self.stream = cv2.VideoCapture(src, cv2.CAP_V4L)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])		# I have found this to be about the highest-
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.stream.set(cv2.CAP_PROP_FPS, framerate)
        (self.grabbed, self.frame) = self.stream.read()
        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped = True

    def start(self):
        # start the thread to read frames from the video stream
        if self.stopped:
            self.stopped = False
            t = Thread(target=self.update, args=(), daemon = True)
            t.start()
            sleep(1)
            return self
        else:
            return None

    def update(self):
        # keep looping infinitely until the thread is stopped
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                return
            # otherwise, read the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True

    def resolution(self):
        x = self.stream.get(cv2.CAP_PROP_FRAME_WIDTH)
        y = self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
        return (x, y)


class EmptycamVideoStream:
    def __init__(self, resolution=(320, 240), framerate=15):
        self.stream = resolution
        self.framerate = framerate
        self.stopped = True

    def start(self):
        return None

    def update(self):
        pass

    def read(self):
        return None

    def stop(self):
        self.stopped = True

    def resolution(self):
        x = self.stream[0]
        y = self.stream[1]
        return x, y
