#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Version 2.1.1 April, 10 2017
# "THE BEER-WARE LICENSE" (Revision 42):
# Dmitrii Sokolov <sokolovdp@gmail.com> wrote this code. As long as you retain
# this notice you can do whatever you want with this stuff. If we meet some day,
# and you think this stuff is worth it, you can buy me a beer in return
#   source code: https://github.com/sokolovdp/vcard/blob/master/read_vcard.py
# The idea of "beer license" was borrowed from Terry Yin <terry.yinzhe@gmail.com>
#    https://github.com/terryyin/google-translate-python
# ----------------------------------------------------------------------------

import os
import sys
import io
import re
import shutil
import base64
import platform
import chardet
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

stand_pars = ['N', 'FN', 'TITLE', 'ORG', 'ADR', 'TEL', 'EMAIL', 'URL']  # PHOTO processed separately
X_PHOTO = 154
Y_PHOTO = 20
X_NO_PHOTO = 50
Y_NO_PHOTO = 40
OFF = 20
small_size = (146, 196)
thumb_size = (350, 200)
pic_offset = (2, 2)
text_color = (0, 0, 0)
background_color = (255, 255, 255, 255)
windows_font = 'ariali.ttf'
font_size_windows = 12
linux_font = '/usr/share/fonts/truetype/freemono/FreeMono.ttf'
font_size_linux = 10


def get_encoding(fname):
    raw_data = open(fname, "rb").read()
    result = chardet.detect(raw_data)
    return result['encoding']

def load_vcards(filename):  # parse VCF file into list of dicts with vcard params
    with open(filename, encoding=get_encoding(filename)) as f:
        data = f.read()
    vcard_format = "BEGIN:VCARD(?P<card>.*?)END:VCARD\n"
    p_vcard = re.compile(vcard_format, re.DOTALL)
    photo_format = "PHOTO;(?P<photo>.*?)/9k=\n"
    p_photo = re.compile(photo_format, re.DOTALL)
    param_format = "(?P<param>.*?):(?P<value>.*?)\n"
    p_param = re.compile(param_format)
    cards_list = list()

    for match1 in p_vcard.finditer(data):
        vcard_params = dict()
        vcard_text = match1.group('card')
        match2 = re.search(p_photo, vcard_text)
        if match2:  # there is a photo image in the vcard
            span = match2.span()
            photo_value = match2.group('photo').replace('\n', '')
            photo_code = '%s%s' % (photo_value.split(':')[1], '/9k=')
            try:
                image_bytes = base64.b64decode(photo_code)
            except:
                print('error in base64 encoding, image data ignored')
            else:
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                except:
                    print('error in image format, image ignored')
                else:
                    vcard_params["PHOTO"] = image
            vcard_text = vcard_text[:span[0]]
            tail = vcard_text[span[1]:]
            if len(tail):
                vcard_text += tail
        n_given = False
        fn_given = False
        for match3 in p_param.finditer(vcard_text):  # parse other parameters
            params = match3.group('param').split(';')
            values = match3.group('value').split(';')
            param = params[0]
            value = values[0]
            # print(params, params[0], values, values[0])    # debug
            if param == 'N':
                n_given = True
            if param == 'FN':
                fn_given = True
            if (param in stand_pars) and (param not in vcard_params.keys()):
                vcard_params[param] = value
        if vcard_params:
            if (not n_given) and (not fn_given):
                print("no name parameters (N, FN) in data, VCARD ignored")
                continue
            if n_given and fn_given:  # there must only FN parameter in vcard data
                del vcard_params['N']
            elif n_given:
                vcard_params['FN'] = vcard_params['N']
                del vcard_params['N']
            cards_list.append(vcard_params)
        else:
            print("no valid parameters in data, VCARD ignored")
    print("loaded vcards: {} from file: {}".format(len(cards_list), filename))
    #  exit()  # debug
    return cards_list


def create_thumbnail(card_info, font_truetype):
    background = Image.new('RGBA', thumb_size, background_color)
    draw = ImageDraw.Draw(background)
    if 'PHOTO' in card_info.keys():
        x = X_PHOTO
        y = Y_PHOTO
    else:
        x = X_NO_PHOTO
        y = Y_NO_PHOTO
    for param in list(card_info.keys()):
        if param == 'PHOTO':
            smaller_img = card_info['PHOTO'].resize(small_size)
            background.paste(smaller_img, pic_offset)
        else:
            draw.text((x, y), '%s: %s' % (param.lower(), card_info[param]), text_color, font=font_truetype)
            y += OFF
    thumb_file = re.sub(r'[\\/*?:"<>|]', '', card_info['FN'].replace(' ', '_')).replace('\n', ' ')
    thumb_file += '.png'
    if os.path.isfile(thumb_file):
        print('duplicated vcard and thumb file names: {} VCARD ignored'.format(thumb_file))
    else:
        try:
            background.save(thumb_file)
        except IOError:
            print("IO error during writing thumb file:", thumb_file)


def load_truetype_font():  # check which OS is running and install proper truetype font
    font = None
    os_name = platform.system()
    if os_name == 'Windows':
        try:
            font = ImageFont.truetype(font=windows_font, size=font_size_windows, encoding='unic')
        except OSError:
            print("cannot locate Windows font:", windows_font)
            exit()
        except IOError:
            print("cannot open Windows font:", windows_font)
            exit()
    elif os_name == 'Linux':
        try:
            font = ImageFont.truetype(font=linux_font, size=font_size_linux, encoding='unic')
        except OSError:
            print("cannot locate Linux font:", windows_font)
            exit()
        except IOError:
            print("cannot open Linux font:", windows_font)
            exit()
    else:
        print("this programm can run only on Windows or Linux")
        exit()
    return font


def main(vcard_file):
    list_of_cards = load_vcards(vcard_file)
    if list_of_cards:
        dirname = vcard_file.lower().split('.')[0] + ".thumbs"
        shutil.rmtree(dirname, ignore_errors=True)  # remove old directory and files
        try:
            os.makedirs(dirname)  # create new directory
        except OSError:
            print("access error: can't create directory:", dirname)
        else:
            font = load_truetype_font()
            os.chdir(dirname)
            for card in list_of_cards:
                create_thumbnail(card, font)


if __name__ == '__main__':
    if sys.argv[1:]:
        vfile = sys.argv[1]
        if os.path.exists(vfile):
            main(vfile)
        else:
            print("no such vcf file:", vfile)
    else:
        print('no vcard file given')
