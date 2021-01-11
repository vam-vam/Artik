#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

# Raspberry Pi Face Recognition Treasure Configuration

# Edit the values below to configure the training and usage of the
# face recognition.

import cv2

# Threshold for the confidence of a recognized face before it's considered a
# positive match.  Confidence values below this threshold will be considered
# a positive match because the lower the confidence value, or distance, the
# more confident the algorithm is that the face was correctly detected.
# Start with a value of 3000, but you might need to tweak this value down if
# you're getting too many false positives (incorrectly recognized faces), or up
# if too many false negatives (undetected faces).
# LBPH<60 ; fisher<1460 ; eigen<12000 ;
POSITIVE_THRESHOLD = 1460.0

# File to save and load face recognizer model.
TRAINING_FILE = 'faces_training.xml'

# Directories which contain training image data.
FACES_DIR = '../img/oko/training/faces/'

# Directorie which contain save detected face images data.
FACE_SAVE_AS_IMG = "img/oko/detect/face_"

# Directorie which contain save detected object images data.
DNN_SAVE_AS_IMG = "img/oko/detect/dnn_"

# Size (in pixels) to resize images for training and prediction.
# Don't change this unless you also change the size of the training images.
PREDICT_IMAGE_WIDTH = 300
PREDICT_IMAGE_HEIGHT = 300

# Face detection cascade classifier configuration.
# You don't need to modify this unless you know what you're doing.
# See: http://docs.opencv.org/modules/objdetect/doc/cascade_classification.html
HAAR_FACES =  './models/opencv/haarcascades/haarcascade_frontalface_alt.xml'
HAAR_SCALE_FACTOR = 1.3
HAAR_MIN_NEIGHBORS = 4
HAAR_MIN_SIZE = (30, 30)

#RESIZE_INTERPOLATION = cv2.INTER_LANCZOS4
RESIZE_INTERPOLATION = cv2.INTER_LINEAR

# Face recognizer and model for detection face
#FACE_RECOGNIZER = cv2.face.EigenFaceRecognizer_create()
#FACE_MODEL = "models/faces_training.xml_eig"
#FACE_RECOGNIZER = cv2.face.LBPHFaceRecognizer_create()
#FACE_MODEL = "models/faces_training.xml_lbph"
FACE_RECOGNIZER = cv2.face.FisherFaceRecognizer_create()
FACE_MODEL = "data/models/faces_training.xml_fish"

# Filename to use when saving the most recently captured image for debugging.
DEBUG_IMAGE = 'capture.jpg'
DEBUG_IMAGE2 = 'capture-detect.jpg'
DEBUG_IMAGE3 = 'capture-crop.jpg'


# Pretrained names of faces in the model
FacesName = {1: 'vam', 2: 'eva', 3: 'honza'}

# Object recognizer and model form image
OBJECT_MODEL = 'data/models/frozen_inference_graph.pb'
OBJECT_CONFIG = 'data/models/ssd_mobilenet_v2_coco_2018_03_29.pbtxt'
# Pretrained names of object in the model
classNames = {0: 'background',
              1: 'person', 2: 'bicycle', 3: 'car', 4: 'motorcycle', 5: 'airplane', 6: 'bus',
              7: 'train', 8: 'truck', 9: 'boat', 10: 'traffic light', 11: 'fire hydrant',
              13: 'stop sign', 14: 'parking meter', 15: 'bench', 16: 'bird', 17: 'cat',
              18: 'dog', 19: 'horse', 20: 'sheep', 21: 'cow', 22: 'elephant', 23: 'bear',
              24: 'zebra', 25: 'giraffe', 27: 'backpack', 28: 'umbrella', 31: 'handbag',
              32: 'tie', 33: 'suitcase', 34: 'frisbee', 35: 'skis', 36: 'snowboard',
              37: 'sports ball', 38: 'kite', 39: 'baseball bat', 40: 'baseball glove',
              41: 'skateboard', 42: 'surfboard', 43: 'tennis racket', 44: 'bottle',
              46: 'wine glass', 47: 'cup', 48: 'fork', 49: 'knife', 50: 'spoon',
              51: 'bowl', 52: 'banana', 53: 'apple', 54: 'sandwich', 55: 'orange',
              56: 'broccoli', 57: 'carrot', 58: 'hot dog', 59: 'pizza', 60: 'donut',
              61: 'cake', 62: 'chair', 63: 'couch', 64: 'potted plant', 65: 'bed',
              67: 'dining table', 70: 'toilet', 72: 'tv', 73: 'laptop', 74: 'mouse',
              75: 'remote', 76: 'keyboard', 77: 'cell phone', 78: 'microwave', 79: 'oven',
              80: 'toaster', 81: 'sink', 82: 'refrigerator', 84: 'book', 85: 'clock',
              86: 'vase', 87: 'scissors', 88: 'teddy bear', 89: 'hair drier', 90: 'toothbrush'}

def id_object_name(face_id, classes):
    for key, value in classes.items():
        if face_id == key:
            return value
    return None
