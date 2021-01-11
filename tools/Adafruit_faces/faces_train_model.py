#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Train the model for recognizing faces. Training happens over predefined images,
which are expected to live in

Code adapted from the OpenCV tutorial at
https://docs.opencv.org/2.4/modules/contrib/doc/facerec/facerec_tutorial.html

"""

import fnmatch
import os

import cv2
import numpy as np

import config
import face


MEAN_FILE = 'mean.png'
POSITIVE_EIGENFACE_FILE = 'positive_eigenface.png'


def walk_files(directory, match='*'):
    """Generator function to iterate through all files in a directory recursively
    which match the given filename match parameter.
    """
    for root, dirs, files in os.walk(directory):
        for filename in fnmatch.filter(files, match):
            yield os.path.join(root, filename)

def prepare_image(filename):
    """Read an image as grayscale and resize it to the appropriate size for
    training the face recognition model.
    """
    return face.resize(cv2.imread(filename, cv2.IMREAD_GRAYSCALE))

def normalize(X, low, high, dtype=None):
    """Normalizes a given array in X to a value between low and high.
    Adapted from python OpenCV face recognition example at:
      https://github.com/Itseez/opencv/blob/2.4/samples/python2/facerec_demo.py
    """
    X = np.asarray(X)
    minX, maxX = np.min(X), np.max(X)
    # normalize to [0...1].
    X = X - float(minX)
    X = X / float((maxX - minX))
    # scale to [low...high].
    X = X * (high-low)
    X = X + low
    if dtype is None:
        return np.asarray(X)
    return np.asarray(X, dtype=dtype)

if __name__ == '__main__':
    print ("Reading training images...")
    faces = []
    labels = []
    pos_count = 0
    # Read all positive images
    for filename in walk_files(config.FACES_DIR + "vam", '*'):
        faces.append(prepare_image(filename))
        labels.append(1)
        pos_count += 1
    for filename in walk_files(config.FACES_DIR + "eva", '*'):
        faces.append(prepare_image(filename))
        labels.append(2)
        pos_count += 1
    for filename in walk_files(config.FACES_DIR + "honza", '*'):
        faces.append(prepare_image(filename))
        labels.append(3)
        pos_count += 1
    print ('Read', pos_count, 'positive images.')
    # Train model
    print ('Training model...')
    eig_rec = cv2.face.EigenFaceRecognizer_create()
    eig_rec.train(np.asarray(faces), np.asarray(labels))
    eig_rec.save(config.TRAINING_FILE+"_eig")

    # train fisher model
    fish_rec = cv2.face.FisherFaceRecognizer_create()
    fish_rec.train(np.asarray(faces), np.asarray(labels))
    fish_rec.save(config.TRAINING_FILE+"_fish")

    # train LBPHF model
    lbph_rec = cv2.face.LBPHFaceRecognizer_create()
    lbph_rec.train(np.asarray(faces), np.asarray(labels))
    lbph_rec.save(config.TRAINING_FILE+"_lbph")

    # Save mean and eignface images which summarize the face recognition model.
    mean = eig_rec.getMean().reshape(faces[0].shape)
    cv2.imwrite(MEAN_FILE, normalize(mean, 0, 255, dtype=np.uint8))
    eigenvectors = eig_rec.getEigenVectors()
    pos_eigenvector = eigenvectors[:,0].reshape(faces[0].shape)
    cv2.imwrite(POSITIVE_EIGENFACE_FILE, normalize(pos_eigenvector, 0, 255, dtype=np.uint8))
