#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""Access an external USB camera.

Allows plugging in arbitrary camera and adds additional functionality to:

* detect objects
* detect faces
* recognize a person using a pre-trained model

"""

import logging
import os
from threading import Thread
from datetime import datetime
from functools import wraps

import cv2
import numpy as np

from artik.actuators import servo
from artik.sensors.camera import Camera
from artik.sensors import eye_config

logger = logging.getLogger(__name__)


def pic_exception_wrap(func):
    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        self.x, self.y = (320, 240)
        # logger.debug("FIX - wrap", self.x, self.y)
        image = args[0]
        if isinstance(image, np.ndarray):
            # center of picture
            cv2.rectangle(
                image,
                (self.x - 1, self.y - 1),
                (self.x + 1, self.y + 1),
                (255, 0, 255),
                2,
            )
            # neutral area
            cv2.rectangle(
                image,
                (int(self.x / 8 * 3), int(self.y / 3)),
                (int(self.x / 4), int(self.y / 3)),
                (255, 150, 255),
                2,
            )
            return image

    return _wrapper


class Eye(Camera):
    """Access a robot's camera.

    Arguments:
        source {int} -- identify the camera: -1=RaspberryPi, 0<=USB kamera(cv2)

    Keyword Arguments:
        tilt_param {dict} -- servo for tilt
        pan_param {dict} -- servo for pan (left/right
        resolution {tuple} -- camera resolution
        framerate {int} -- restrict camera FPS

    """

    def __init__(
            self,
            source,
            tilt_param=None,
            pan_param=None,
            resolution=(320, 240),
            framerate=10,
        ):
        super().__init__(source=source, resolution=resolution, framerate=framerate)
        if self.camera is None:
            raise ValueError("Camera does not exist.")

        # tilt
        self.eye_tilt_servo = servo.Servo()
        if isinstance(tilt_param, dict):
            self.eye_tilt_servo = servo.Servo(
                channel=tilt_param["channel"],
                position0=tilt_param["position0"],
                min=tilt_param["min"],
                max=tilt_param["max"],
                scale=tilt_param["scale"],
                speed=0.004,
                radius=tilt_param["radius"],
            )
            self.eye_tilt_servo.stop0()
        # pan
        self.eye_pan_servo = servo.Servo()
        if isinstance(pan_param, dict):
            self.eye_pan_servo = servo.Servo(
                channel=pan_param["channel"],
                position0=pan_param["position0"],
                min=pan_param["min"],
                max=pan_param["max"],
                scale=pan_param["scale"],
                speed=0.004,
                radius=pan_param["radius"],
            )
            self.eye_pan_servo.stop0()
        # convert degrees according to servos and camera resolution
        resolution = self.resolution()
        self.eye_correction = (
            (self.eye_pan_servo.servo_radius / resolution[1]),
            (self.eye_tilt_servo.servo_radius / resolution[0]),
        )

    def moveaboutrad(self, tilt_radius=0, tilt_speed=0, pan_radius=0, pan_speed=0):
        """Move camera to any side at the given direction and speed.

        Keyword Arguments:
            tilt_radius {int} -- Tilt angle
            tilt_speed {int} -- Tilt speed; FIXME units
            pan_radius {int} -- Pan angle
            pan_speed {int} -- Pan speed; FIXME units
        """
        tilt_speed = int(tilt_speed)
        pan_speed = int(pan_speed)
        if tilt_speed > 0 and self.eye_tilt_servo.servo_channel > -1:
            if tilt_radius != 0:
                posun_tilt = Thread(
                    target=self.eye_tilt_servo.setServoAboutRad,
                    name="Thread-eye-tilt",
                    args=(tilt_radius, tilt_speed),
                    daemon=True,
                )
                posun_tilt.start()
            else:
                self.stop_now_tilt()
        if pan_speed > 0 and self.eye_pan_servo.servo_channel > -1:
            if pan_radius != 0:
                posun_pan = Thread(
                    target=self.eye_pan_servo.setServoAboutRad,
                    name="Thread-eye-pan",
                    args=(pan_radius, pan_speed),
                    daemon=True,
                )
                posun_pan.start()
            else:
                self.stop_now_pan()

    def stop_now(self):
        """Stop all camera movements."""
        self.stop_now_pan()
        self.stop_now_tilt()

    def stop_now_tilt(self):
        """Stop the camera tilting."""
        self.eye_tilt_servo.stop(self.eye_tilt_servo.servo_position_H)

    def stop_now_pan(self):
        """Stop the camera panning"""
        self.eye_pan_servo.stop(self.eye_pan_servo.servo_position_H)


class BrainEyeArtik:
    """Higher-level camera logic.

    Allows preprocessing of identified persons, finding an object or recognizing a face.
    Depends on konfiguration file located at eye_cnfig

    Arguments:
        eye_param {Eye} -- pripojeni oka k mozku pro zpracovani obrazu; FIXME what does this mean???
    """

    # Load a cascade file and model for detecting faces/objects
    face_cascade = cv2.CascadeClassifier(eye_config.HAAR_FACES)
    face_recognizer = eye_config.FACE_RECOGNIZER
    face_trainer_model = eye_config.FACE_MODEL
    object_model = cv2.dnn.readNetFromTensorflow(
        eye_config.OBJECT_MODEL, eye_config.OBJECT_CONFIG
    )

    def __init__(self, eye_param):
        self.eye = eye_param
        self.resolution = self.eye.resolution()
        # focus area
        self.neutral_area = (
            int(self.resolution[0] / 8 * 3),
            int(self.resolution[1] / 3),
            int(self.resolution[0] / 4),
            int(self.resolution[1] / 3),
        )
        if os.path.isfile(self.face_trainer_model):
            self.face_recognizer.read(self.face_trainer_model)

    def inside_axis(self, rectangle, point):
        """Check whether a point is within axes of a rectangle.

        Arguments:
            rectangle {tuple} -- (x, y, w, h), defines the area in given axis; FIXME what does this mean?
            point {tuple} -- (x, y) point to test

        Returns:
            Tuple with a boolean in each axis x, y which denotes whether the point is within the given axis band.
        """
        x, y = (0, 0)
        if rectangle[0] <= point[0] <= rectangle[0] + rectangle[2]:
            x = 1
        if rectangle[1] <= point[1] <= rectangle[1] + rectangle[3]:
            y = 1
        return (x, y)

    def distance_center(
            self, rectangle_input, rectangle_area=None, inside_rectangle=True,
        ):
        """Calculate the distance between centers of two rectangles.

        Arguments:
            rectangle_input {tuple} -- velikost obdelnikove vysece od ktereho se bude merit; FIXME what does this mean?

        Keyword Arguments:
            rectangle_area {tuple} -- velikost obdelnikove vysece nebo rozliseni kamery; FIXME what?
            inside_rectangle {bool} -- testuje je-li bod v obdelnikove vyseci; FIXME what?

        Returns:
            Vraci tuple se vzdalenosti v jednotllivych osach (x,y,z) od stredu vysecu,
            aktualne osa (z) vraci % zabrani obdelnikove vysece v (rectangle_area); FIXME nechapu, nedokazu prelozit.
        """
        if rectangle_area is None:
            rectangle_area = (int(self.resolution[0] / 2), int(self.resolution[1] / 2))
        dw = rectangle_area[0] - int(rectangle_input[0] + rectangle_input[2] / 2)
        dh = rectangle_area[1] - int(rectangle_input[1] + rectangle_input[3] / 2)
        dz = int(
            max(
                (rectangle_input[2] / rectangle_area[0] * 100),
                (rectangle_input[3] / rectangle_area[1] * 100),
            )
        )  # procenta 0%-100%
        if inside_rectangle and self.inside_axis(
            self.neutral_area,
            (
                int(rectangle_input[0] + rectangle_input[2] / 2),
                int(rectangle_input[1] + rectangle_input[3] / 2),
            ),
        ) == (1, 1):
            dw, dh = (0, 0)
        if dz > 80:
            dz = 0
        return (dw, dh, dz)

    def picture(self, image, format="jpeg"):
        _, data = cv2.imencode("." + format, image)
        return data.tostring()

    def picture_add_rectangle(self, image, polygons, colorRGB=(255, 255, 0)):
        """FIXME Pridej obdelnikovou vysec pro zyrazneni objektu v obrazku.

        Arguments:
            image {image} -- obrazek do ktereho se bude vkladat obdelnik
            polygons {tuple} -- souradnice obdelnikove vysece (x, y, w, h)

        Keyword Arguments:
            colorRGB {tuple} -- barva obdelniku pro lepsi orientaci pri vice vysecich (default: {(255, 255, 0)})
        """
        # Draw a rectangle around every found objects
        for (x, y, w, h) in polygons:
            cv2.rectangle(image, (x, y), (x + w, y + h), colorRGB, 2)
        return image

    def picture_resize(
        self,
        image,
        img_width=eye_config.PREDICT_IMAGE_WIDTH,
        img_height=eye_config.PREDICT_IMAGE_HEIGHT,
    ):
        """Resize a image to the proper size for training and detection or any."""
        return cv2.resize(
            image,
            (img_width, img_height),
            interpolation=eye_config.RESIZE_INTERPOLATION,
        )

    def picture_merge(self, mask_fg, image_bg):
        """Add a mask to an image, used in diagnostics."""
        roi = image_bg[0 : image_bg.shape[0], 0 : image_bg.shape[1]]
        img2gray = cv2.cvtColor(mask_fg, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(img2gray, 10, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        img1_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
        img2_fg = cv2.bitwise_and(mask_fg, mask_fg, mask=mask)
        return cv2.add(img1_bg, img2_fg)

    def face_detect(self, image, facesave=False, diag=False):
        """Recognize a face.

        Arguments:
            image {image} -- Input image to analyze.

        Keyword Arguments:
            facesave {bool} -- Pokud je detekovan, tak jestli se ma ulozit; FIXME what? save what, where?
            diag {bool} -- Ma-li vlozit a vratit diagnosticke informace; FIXME what? vlozit kam?

        Returns:
            faces {tuple} - oblast nalezenych obliceju
            face_ids {tuple} - vraci id detekovaneho obliceje a jmeno osoby
            image_diag {image} - vraci masku ve stejne velikosti vstupniho obrazku,
                        s vyseceme nalezenych obliceju.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image_diag = []
        if diag:
            image_diag = np.zeros((image.shape[0], image.shape[1], 3), np.uint8)
        # Look for faces in the image using the loaded cascade file
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=eye_config.HAAR_SCALE_FACTOR,
            minNeighbors=eye_config.HAAR_MIN_NEIGHBORS,
            flags=cv2.CASCADE_SCALE_IMAGE,
            minSize=eye_config.HAAR_MIN_SIZE,
        )
        face_ids = []
        logger.debug("Found %s face(s).", len(faces))
        for (x, y, w, h) in faces:
            if facesave:
                # save face as image
                cv2.imwrite(
                    eye_config.FACE_SAVE_AS_IMG
                    + str(datetime.now()).replace(" ", "_").replace(":", "-")
                    + ".jpg",
                    image[y : y + h, x : x + w],
                )
            imgface = self.picture_resize(gray[y : y + h, x : x + w])
            face_name = "No Match"
            face_id = -1
            try:
                face_detect_id, confidence = self.face_recognizer.predict(imgface)
                if confidence < eye_config.POSITIVE_THRESHOLD:
                    face_id = face_detect_id
                    face_name = eye_config.id_object_name(face_id, eye_config.FacesName)
                if diag:
                    cv2.rectangle(
                        image_diag,
                        (int(x), int(y)),
                        (int(x + w), int(y + h)),
                        (100, 230, 60),
                        thickness=1,
                    )
                    cv2.putText(
                        image_diag,
                        str(face_name),
                        (x + 2, y + h - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (150, 255, 0),
                        2,
                    )
                logger.debug(
                    "ID face: "
                    + str(face_detect_id)
                    + " Confidence face: "
                    + str(confidence)
                )
            except Exception:
                # tohle zatim nevim jak vyresit, nechci aby chyba shodila cely program
                face_id = -2
                face_name = "Error"
            face_ids.append((face_id, face_name))
        return faces, face_ids, image_diag

    def object_detect_dnn(self, image, imgsave=False, diag=False):
        """Detect objects of predefined classes using DNN.

        Args:
            image (object image): Input image to analyze
            imgsave (bool, optional): FIXME Pokud je detekovan, tak jestli se ma ulozit.
            diag (bool, optional): FIXME Ma-li vlozit a vratit diagnosticke informace.

        Returns:
            FIXME

        """
        objects = []
        object_ids = []
        image_diag = []
        image_height, image_width, _ = image.shape
        if diag:
            image_diag = np.zeros((image_height, image_width, 3), np.uint8)
        self.object_model.setInput(
            cv2.dnn.blobFromImage(image, size=(300, 300), swapRB=True)
        )
        output = self.object_model.forward()
        for detection in output[0, 0, :, :]:
            confidence = detection[2]
            class_label = "No Match"
            if confidence > 0.5:
                class_id = detection[1]
                class_label = eye_config.id_object_name(class_id, eye_config.classNames)
                logger.debug(
                    str(str(class_id) + " " + str(detection[2]) + " " + class_label)
                )
                x = int(detection[3] * image_width)
                y = int(detection[4] * image_height)
                width = int(detection[5] * image_width)
                height = int(detection[6] * image_height)
                if diag:
                    cv2.rectangle(
                        image_diag, (x, y), (width, height), (23, 230, 210), thickness=1
                    )
                    cv2.putText(
                        image_diag,
                        class_label,
                        (x, int(y + 0.05 * image_height)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 255),
                        2,
                    )
                objects.append((x, y, width - x, height - y))
                object_ids.append((class_id, class_label))
                if imgsave:
                    # save found object from image
                    cv2.imwrite(
                        eye_config.DNN_SAVE_AS_IMG
                        + str(class_label)
                        + "_"
                        + str(datetime.now()).replace(" ", "_").replace(":", "-")
                        + ".jpg",
                        image[y:height, x:width],
                    )
        return objects, object_ids, image_diag

    # @pic_exception_wrap
    def object_detect_surf(self, image, image_object):
        """Search for an object in an image using SUFT/SIFT method.

        Arguments:
            image {image} -- input image for detection
            image_object {image} -- searched object

        Returns:
            Returns the coordinates of the found object.
        """
        objects = []
        min_match_count = 10
        # detector=cv2.xfeatures2d.SIFT_create()
        detector = cv2.xfeatures2d.SURF_create(400)
        flann_index_kditree = 0
        flann_param = dict(algorithm=flann_index_kditree, tree=5)
        flann = cv2.FlannBasedMatcher(flann_param, {})
        # training_img=cv2.imread("img/oko/training/solevita.jpg",cv2.IMREAD_GRAYSCALE)
        training_img = cv2.cvtColor(image_object, cv2.COLOR_BGR2GRAY)
        trainKP, trainDesc = detector.detectAndCompute(training_img, None)
        query_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        queryKP, queryDesc = detector.detectAndCompute(query_img, None)
        matches = flann.knnMatch(queryDesc, trainDesc, k=2)
        good_match = []
        good_match = [m for m, n in matches if m.distance < 0.75 * n.distance]
        if len(good_match) > min_match_count:
            tp = []
            qp = []
            for m in good_match:
                tp.append(trainKP[m.trainIdx].pt)
                qp.append(queryKP[m.queryIdx].pt)
            # tp,qp=np.float32((tp,qp))
            H, = cv2.findHomography(tp, qp, cv2.RANSAC, 3.0)
            h, w = training_img.shape
            trainBorder = np.float32([[[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]])
            queryBorder = cv2.perspectiveTransform(trainBorder, H)
            cv2.polylines(image, [np.int32(queryBorder)], True, (0, 255, 0), 5)
            objects = [(np.int32(queryBorder))]
        return objects


def main():
    eye = Eye(-1)
    image = eye.read()
    cv2.imwrite("image_box_text.jpg", image)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s : %(levelname)s : %(module)s:%(lineno)d : %(funcName)s(%(threadName)s) : %(message)s",
        level=logging.DEBUG,
    )
    main()
