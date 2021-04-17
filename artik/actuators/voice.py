#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Text-to-speech voice for Artik.

"""

from time import sleep
import os
import signal
import subprocess
import unicodedata

import psutil

try:
    import pygame
    import_pygame = True
except ImportError:
    import_pygame = False

# The voice control software doesn't accept Czech characters, so we "simulate" their
# pronunciation by replacing them by other phonemes.
CHAR_CONVERT = {
    "á": "aa",
    "ä": "a",
    "č": "ch",
    "ď": "dd",
    "é": "ee",
    "ě": "je",
    "í": "ii",
    "ĺ": "l",
    "ľ": "l",
    "ň": "nj",
    "ó": "oo",
    "ô": "o",
    "ő": "o",
    "ö": "o",
    "ŕ": "rzh",
    "š": "sh",
    "ť": "tj",
    "ú": "uu",
    "ů": "uu",
    "ű": "uu",
    "ü": "u",
    "ý": "yy",
    "ř": "rzh",
    "ž": "zh",
}


class ArtikVoice:
    def __init__(self, voice=0, lcd=None):
        self.output = None
        self.voice_output = voice  # 0=Artik, 1=PC Man, 2=Sound, -1=Print text
        self.voice_stop = False
        self.voice_tts_pid = None
        self.lcd = lcd
        self._playing = False
        if import_pygame:
            pygame.init()
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2)

    def __call__(self, action, voice=None):
        self.voice_stop = False
        self.voice_playing()
        if voice is None:
            voice = self.voice_output
        if voice == 2:
            self.sound(action)
        elif voice <= 1 and isinstance(action, str):
            self.text(action, voice)

    def text(self, text, voice=None):
        if voice is None:
            voice = self.voice_output
        self.voice_playing()
        # convert to phonetic
        text = self.text_to_phonetic(text)
        # prevod na text bez diakritiky
        text = unicodedata.normalize("NFKD", text)
        output = ""
        for c in text:
            if not unicodedata.combining(c):
                output += c
        text = output

        if voice == 0:
            for char in text:
                if char == " ":
                    sleep(0.250)
                else:
                    self.spelling_artik(char)
                if self.voice_stop:
                    self.stop123()
                    break
        elif voice == 1:
            self.spelling_man(text)
        elif voice == -1:
            if self.lcd is None:
                print(char)
            else:
                self.lcd(text)

    def text_to_phonetic(self, text):
        text = text.lower()
        for char in CHAR_CONVERT:
            text = text.replace(char, CHAR_CONVERT[char])
        return text

    def spelling_man(self, text):
        if self.voice_tts_pid is not None and self.voice_tts_pid.poll() is not None:
            self.voice_tts_pid = None
        if self.voice_tts_pid is None:
            self._playing = True
            # self.voice_tts_pid = subprocess.Popen('echo '+text+'| festival --tts --language czech', stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
            self.voice_tts_pid = subprocess.Popen(
                "echo " + text + "| festival --tts --language czech",
                shell=True,
                preexec_fn=os.setsid,  # FIXME is this safe in the presence of threads?
            )
            # self.voice_tts_pid = subprocess.call('echo '+text+'| festival --tts --language czech', shell=True)

    def spelling_artik(self, char):
        sounds = [
            {
                "soundName": "a",
                "soundID": "0.wav",
                "md5": "df0977a56762487f9d833d35814a6716.wav",
                "sampleCount": 16744,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "b",
                "soundID": "1.wav",
                "md5": "3a85eb788b27591b3cc5ab39191d4644.wav",
                "sampleCount": 16168,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "c",
                "soundID": "2.wav",
                "md5": "63f5c3dff75658c7c9f075a8d8b1085d.wav",
                "sampleCount": 17320,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "c1",
                "soundID": "3.wav",
                "md5": "a51a7d2a3cd68553a05c56204c4381f1.wav",
                "sampleCount": 12136,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "d",
                "soundID": "4.wav",
                "md5": "da0ed691a12fd7ff368fcfee5efdaf55.wav",
                "sampleCount": 4072,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "e",
                "soundID": "5.wav",
                "md5": "09c62cc8f0ec0246d7becfe993b3aa09.wav",
                "sampleCount": 4072,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "f",
                "soundID": "6.wav",
                "md5": "887af1f36814d89498826835bee5b89c.wav",
                "sampleCount": 4072,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "g",
                "soundID": "7.wav",
                "md5": "96ee06dc6981db237f69fa1330052084.wav",
                "sampleCount": 4072,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "g1",
                "soundID": "8.wav",
                "md5": "1acd6fb39362c914e3a11860e984dbe6.wav",
                "sampleCount": 12712,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "h",
                "soundID": "9.wav",
                "md5": "f5cc128f0a0b83341ec05f471517f493.wav",
                "sampleCount": 4648,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "i",
                "soundID": "10.wav",
                "md5": "bb178208cf234847e27cadc26a08c092.wav",
                "sampleCount": 4648,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "j",
                "soundID": "11.wav",
                "md5": "af429e8a38160da5ae0c16a48c9b5898.wav",
                "sampleCount": 4648,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "k",
                "soundID": "12.wav",
                "md5": "0f69ff0f5565b54eeff8e48e12b83d95.wav",
                "sampleCount": 5224,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "l",
                "soundID": "13.wav",
                "md5": "bc45c076702b9828ad947dd5a047c79b.wav",
                "sampleCount": 5224,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "m",
                "soundID": "14.wav",
                "md5": "8e7a21999198b5a2dfc97d71432352af.wav",
                "sampleCount": 5224,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "n",
                "soundID": "15.wav",
                "md5": "aab3fa6119e1828fe37a313e8fb3ea8e.wav",
                "sampleCount": 5224,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "o",
                "soundID": "16.wav",
                "md5": "2ddb24e3780d84f4b0e1cca7df3cc263.wav",
                "sampleCount": 4072,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "o1",
                "soundID": "17.wav",
                "md5": "4f97fe8bc993ad20343fe8c3ce02e0b4.wav",
                "sampleCount": 14440,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "p",
                "soundID": "18.wav",
                "md5": "b003afd19594d32ba8e701105ab50dd9.wav",
                "sampleCount": 5224,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "q",
                "soundID": "19.wav",
                "md5": "937b627d671bd8917f4cbc9ec09631c4.wav",
                "sampleCount": 5800,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "r",
                "soundID": "20.wav",
                "md5": "99598a2dcb5b0e75eb4be9a24ad15ec0.wav",
                "sampleCount": 5224,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "s",
                "soundID": "21.wav",
                "md5": "858294260e8bf7551a1171d39e1d8b38.wav",
                "sampleCount": 6376,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "s1",
                "soundID": "22.wav",
                "md5": "14db221bee6d185188d800bcd3496d25.wav",
                "sampleCount": 16168,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "t",
                "soundID": "23.wav",
                "md5": "4403be20f51af795c4316992ab655ffd.wav",
                "sampleCount": 6376,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "u",
                "soundID": "24.wav",
                "md5": "9df78b671f4b568b41dff3ecc1cea311.wav",
                "sampleCount": 6376,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "u1",
                "soundID": "25.wav",
                "md5": "3468cb1cd826147bd8bb142511dac884.wav",
                "sampleCount": 15016,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "v",
                "soundID": "26.wav",
                "md5": "4dd346b7990f75028ad45df28992f48d.wav",
                "sampleCount": 6376,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "w",
                "soundID": "27.wav",
                "md5": "b4299f518b3aa50f05cd04ce8d2cdc5a.wav",
                "sampleCount": 6376,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "x",
                "soundID": "28.wav",
                "md5": "517361ee31a2374bc0cb49595bc6364d.wav",
                "sampleCount": 6952,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "y",
                "soundID": "29.wav",
                "md5": "912d9b0dcc69287c7d5871dcb5aaba21.wav",
                "sampleCount": 6952,
                "rate": 22050,
                "format": "adpcm",
            },
            {
                "soundName": "z",
                "soundID": "30.wav",
                "md5": "5b7275df1d7e8301d385619ab4fc863c.wav",
                "sampleCount": 6952,
                "rate": 22050,
                "format": "adpcm",
            },
        ]
        sound_path = "./data/sound/ArtikTranslator/"
        sound_file = ""
        for snd in sounds:
            if snd.get("soundName", "") == char.lower():
                sound_file = snd.get("soundID", "")
                break
        if sound_file != "":
            self.play123(sound_path + sound_file)

    def sound(self, opt_sound=None):
        sound_file = ""
        if isinstance(opt_sound, int):
            sound_opt_file = ["./data/sound/music.ogg"]
            sound_opt_file.append("./data/sound/buzzer.wav")
            if 0 <= opt_sound < len(sound_opt_file):
                sound_file = sound_opt_file[opt_sound]
        if isinstance(opt_sound, str):
            sound_file = opt_sound
        if os.path.isfile(sound_file):
            self.play123(sound_file)

    def stop123(self):
        """Stop playing text """
        self.voice_stop = True
        pygame.mixer.stop()
        if self.voice_tts_pid is not None and self.voice_tts_pid.pid > 0:
            try:
                os.killpg(os.getpgid(self.voice_tts_pid.pid), signal.SIGTERM)
            except Exception:
                pass
            finally:
                self.voice_tts_pid = None
        self._playing = False

    def play123(self, sound=""):
        if isinstance(sound, str) and sound != "":
            self._playing = True
            if sound[0] != "." and sound[0] != "/":
                sound = "./" + sound
            sound_play = pygame.mixer.Sound(sound)
            if not self.voice_tts_pid is None:
                sound_play.set_volume(0.3)
            # sound_play.set_volume(0.3) # nastaveni pro nocni testovani
            while pygame.mixer.get_busy():
                sleep(0.100)
                continue
            sound_play.play()
            sleep(sound_play.get_length() + 0.3)
            self._playing = False

    def voice_playing(self):
        if self.voice_tts_pid is not None and self.voice_tts_pid.pid > 0:
            if psutil.Process(self.voice_tts_pid.pid).status() == psutil.STATUS_ZOMBIE:
                try:
                    os.killpg(os.getpgid(self.voice_tts_pid.pid), signal.SIGTERM)
                    self._playing = False
                    self.voice_tts_pid = None
                except Exception:
                    self._playing = True
        return self._playing


if __name__ == "__main__":
    b = ArtikVoice()
    b.text("Ahoj", 0)
