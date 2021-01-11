#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
External display connector to Artik.
"""

import subprocess
import time
import uuid
import threading
import logging

import Adafruit_GPIO.SSD1306 as SSD1306 # MIT License https://github.com/adafruit/Adafruit_Python_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


logger = logging.getLogger(__name__)


class ArtikDisplay:

    def __init__(self):
        self.suuid = str(uuid.uuid4())
        try:
            self.display = SSD1306.SSD1306_128_32(rst=None, i2c_address=0x3C, i2c_bus=1)
            # Initialize library.
            self.display.begin()
            # Clear display.
            self.display_clear()
        except Exception:
            raise RuntimeError("LCD does not exist.")
        self.lcd_stop = False
        self.font = ImageFont.load_default()
        self.display_thread = None
        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self.display_image = Image.new('1', self.display_size())

    def __call__(self, text, action=None):
        self.lcd_stop = False
        if action is None:
            action = 1
        if action == 1:
            self.text(text)
        elif action == 2:
            self.text_animate(text)

    def display_size(self):
        return (self.display.width, self.display.height)

    def display_show(self, image=None):
        if image is None:
            image = self.display_image
        # Display image.
        self.display.image(image)
        self.display.display()

    def display_clear(self):
        self.display.clear()
        self.display.display()

    def draw(self, image=None):
        if image is None:
            image = self.display_image
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)
        # Draw a black filled box to clear the image.
        dimensions = self.display_size()
        draw.rectangle((0,0,dimensions[0],dimensions[1]), outline=0, fill=0)
        return draw

    def text(self, text, font=None):
        self.display_clear()
        if font is None:
            font = self.font
        draw = self.draw()
        x, y = 0, 0
        tt = text.replace('\\n', '\n').split("\n")
        for i, line in enumerate(tt):
            line = line.strip()
            y = i*8-2
            #print(y, self.display_size())
            #maxwidth, unused = draw.textsize(text, font=font)
            #print(maxwidth, unused)
            draw.text((x, y), line, font=font, fill=255)
            if y > 16:
                break
        self.display_show()

    def text_animate(self, text, font=None):
        self.display_clear()
        hash_uuid = self.suuid
        if font is None:
            font = self.font
        draw = self.draw()
        x, y = 0, 0
        tt = text.replace('\\n','\n').split("\n")
        dimensions = self.display_size()
        while hash_uuid == self.suuid:
            draw.rectangle((0,0,dimensions[0],dimensions[1]), outline=0, fill=0)
            pos = -1
            for _, line in enumerate(tt):
                pos += 1
                line = line.strip()
                y = pos*8-2
                draw.text((x, y), line, font=font, fill=255)
                self.display_show()
                time.sleep(0.5)
                if hash_uuid != self.suuid:
                    break
                if pos == 3:
                    pos = -1
                    time.sleep(1.5)
                    draw.rectangle((0, 0, dimensions[0], dimensions[1]), outline=0, fill=0)
            time.sleep(1.5)

    def info_os(self, font=None):
        """Display OS information on the built-in LCD display."""
        self.display_clear()
        hash_uuid = self.suuid
        if font is None:
            font = self.font
        draw = self.draw()
        x, y = 0, 0
        dimensions = self.display_size()
        while hash_uuid == self.suuid:
            draw.rectangle((0, 0, dimensions[0], dimensions[1]), outline=0, fill=0)
            # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
            text = []
            #IP address
            cmd = "hostname -I | cut -d\' \' -f1"
            cmd_result = subprocess.check_output(cmd, shell=True)
            text.append("IP: " + str(cmd_result).replace("b", '').replace("\\n","").replace("\'", ""))
            #CPU
            cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
            cmd_result = subprocess.check_output(cmd, shell=True)
            text.append(str(cmd_result).replace("b", '').replace("\\n", "").replace("\'", ""))
            #Memory
            cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
            cmd_result = subprocess.check_output(cmd, shell=True)
            text.append(str(cmd_result).replace("b", '').replace("\\n", "").replace("\'", ""))
            #Disk size
            cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
            cmd_result = subprocess.check_output(cmd, shell=True)
            text.append(str(cmd_result).replace("b", '').replace("\\n", "").replace("\'", ""))
            # Write two lines of text.
            # draw.text((x, y),    test[0],  font=font, fill=255)
            # draw.text((x, y+7),  test[1],  font=font, fill=255)
            # draw.text((x, y+15), test[2],  font=font, fill=255)
            # draw.text((x, tyop+23), test[3],  font=font, fill=255)
            # self.display_show()
            text.append("========")
            draw.rectangle((0, 0, dimensions[0], dimensions[1]), outline=0, fill=0)
            pos = -1
            for _, line in enumerate(text):
                pos += 1
                line = line.strip()
                y = pos*8-2
                draw.text((x, y), line, font=font, fill=255)
                #self.display_show()
                if hash_uuid != self.suuid:
                    break
                if pos == 3:
                    self.display_show()
                    pos = -1
                    time.sleep(2)
                    draw.rectangle((0, 0, dimensions[0], dimensions[1]), outline=0, fill=0)
            self.display_show()
            time.sleep(2)

    def text_thread(self, text, action=0):
        assert isinstance(text, str)

        self.suuid = str(uuid.uuid4())
        action = int(action)
        if action == 1:
            self.display_thread = threading.Thread(
                target=self.text_animate, name="Thread-DisplayAnimate", args=(text, ), daemon=True,
            )
            self.display_thread.start()
        elif action == 2:
            self.display_thread = threading.Thread(target=self.info_os, name="Thread-DisplayOsInfo", daemon=True)
            self.display_thread.start()
        elif action == 0:
            self.text(text)
        else:
            raise ValueError(f"Unknown action {action}")


if __name__ == '__main__':
    lcd = ArtikDisplay()
    #lcd.info_os()
    lcd.text_animate(text='ahoj dkj \\nvbcvb \\n vcsajkh \\nsadhd \\n fgfdgdg \\n gfgfdgas')
    lcd.text_animate(text=' Ahoj,  \n   jak \nse \n mas \n na \n tomto \n dvore?\nabcd12346789efg123456789')
