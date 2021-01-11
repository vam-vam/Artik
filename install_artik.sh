#!/bin/bash

set -o xtrace -o errexit -o noclobber -o nounset -o pipefail

SUDO_PREFIX="sudo -n "

# Directory containing Artik's code and data
ARTIK_LOCATION="/home/pi/Artik"

# Update the OS.
# The below is tested with Debian Buster, but hopefully works on later versions too.
${SUDO_PREFIX} apt-get update
${SUDO_PREFIX} apt-get -y upgrade
#${SUDO_PREFIX} apt-get -y install python3-dev
${SUDO_PREFIX} apt-get -y install python3-pip

# Install HW support and dependencies
${SUDO_PREFIX} apt-get -y install i2c-tools
${SUDO_PREFIX} i2cdetect -l
${SUDO_PREFIX} apt-get -y install python3-rpi.gpio
${SUDO_PREFIX} apt-get -y install python3-smbus
${SUDO_PREFIX} apt-get -y install pigpio python3-pigpio
${SUDO_PREFIX} pip3 install Adafruit-PureIO

# Raspberry Pi camera. Enable camera in raspi-conf.
${SUDO_PREFIX} apt-get -y install python3-picamera
#${SUDO_PREFIX} apt-get -y install python3-pygame
${SUDO_PREFIX} pip3 install pygame==1.9.6

# LCD display 128x32 ssd1306.
#${SUDO_PREFIX} pip3 install Adafruit-SSD1306
#download ssd13060.py https://github.com/adafruit/Adafruit_Python_SSD1306
${SUDO_PREFIX} apt-get -y -f install python3-pil

# For TTS
${SUDO_PREFIX} pip3 install psutil
${SUDO_PREFIX} apt-get -y -f install festival
#${SUDO_PREFIX} apt-get -y -f install festival_czech_krb
${SUDO_PREFIX} apt-get -y -f install festvox-czech-krb

# CherryPy web server
${SUDO_PREFIX} pip3 install cherrypy

${SUDO_PREFIX} mkdir /var/log/artik
${SUDO_PREFIX} chown -c pi /var/log/artik
${SUDO_PREFIX} chmod u=rwx,g=rwx,o=rwx /var/log/artik

${SUDO_PREFIX} pip3 install imutils

if [ "$OPENCV" != "" ]; then
    echo "Installing OPENCV"
    # We need opencv >= 3.4.4 < 4.0.0
    ${SUDO_PREFIX} apt-get -y install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev gfortran
    ${SUDO_PREFIX} apt-get -y install libhdf5-100
    ${SUDO_PREFIX} apt-get -y install libatlas3-base libsz2 libharfbuzz0b libtiff5 libjasper1 libilmbase12 libopenexr22 libilmbase12 libgstreamer1.0-0 libavcodec57 libavformat57 libavutil55 libswscale4 libqtgui4 libqt4-test libqtcore4
    ${SUDO_PREFIX} pip3 install opencv-python==3.4.13.47
    ${SUDO_PREFIX} pip3 install opencv-contrib-python==3.4.13.47
    # pip3 install opencv-contrib-python==3.4.13.47 --user
    #${SUDO_PREFIX} apt-get -y install build-essential cmake pkg-config
    #${SUDO_PREFIX} apt-get -y install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
    #${SUDO_PREFIX} apt-get -y install libxvidcore-dev libx264-dev
    ${SUDO_PREFIX} apt-get -y install libgtk2.0-dev libgtk-3-dev
fi
if [ "$OPENVINO" != "" ]; then
    echo "Installing Intel NCS2"
    cd ${ARTIK_LOCATION}/tools/NCS2
    sh ./ncs2_install.sh
fi

# Install chatbot.
cd ${ARTIK_LOCATION}/tools
${SUDO_PREFIX} cp -r ./nltk_data /usr/
${SUDO_PREFIX} pip3 install ChatterBot

# Install voice recognition.
# TODO

# Install Artik itself.
cd ${ARTIK_LOCATION}
pip install -e .

# Launch Artik's API web server.
# PYTHONPATH=${PYTHONPATH}:${ARTIK_LOCATION}/tools ${SUDO_PREFIX} python3 -m artik.server ${ARTIK_LOCATION}/data
