#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""
Chatbot for Artik.
"""

from time import sleep

from chatterbot import ChatBot as module_chatbot
from chatterbot.trainers import ChatterBotCorpusTrainer as corpus_trainer


class Chatbot:
    def __init__(self, corpus):
        self.chatbot = module_chatbot('ARTIK')
        self.trainer = corpus_trainer(self.chatbot)
        try:
            self.trainer.train(corpus)
        except Exception:
            raise ValueError('No such file or directory for corpus.')

    def response(self, question='', voice=None):
        response = self.chatbot.get_response(question)
        if voice is not None:
            voice(str(response))
        return response

    def __call__(self, question, voice=None):
        return self.response(question, voice)


# An example is given below.
if __name__ == "__main__":
    chatbot = Chatbot("./models/chat/czech")
    response = chatbot.response('piješ?')
    print(response)
    """
    response = chatbot.response('piješ?')
    print(response)
    response = chatbot.response('piješ?')
    print(response)
    response = chatbot.response('piješ?')
    print(response)
    """
    import artik_voice as artik_voice
    b = artik_voice.artik_voice(voice=1)
    #b("ookk")
    #sleep(1)
    response = chatbot.response('piješ?',voice=b)
    print(response)
    while b.voice_plaing():
        sleep(0.2)
    # The following loop will execute each time the user enters input
    print('Type something to begin...')
    while True:
        try:
            user_input = input()
            response = chatbot.response(str(user_input),voice=b)
            print(response)
            while b.voice_plaing():
                sleep(0.2)
        # Press ctrl-c or ctrl-d on the keyboard to exit
        except (KeyboardInterrupt, EOFError, SystemExit):
            break
