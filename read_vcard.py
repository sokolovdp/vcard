#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# Dmitrii Sokolov <sokolovdp@gmail.com> wrote this file. As long as you retain
# this notice you can do whatever you want with this stuff. If we meet some day,
# and you think this stuff is worth it, you can buy me a beer in return
#   source code: https://github.com/sokolovdp/vcard/blob/master/read_vcard.py
# The idea of "beer license" was borrowed from Terry Yin <terry.yinzhe@gmail.com>
#    https://github.com/terryyin/google-translate-python
# ----------------------------------------------------------------------------

import os
import sys
import base64
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

temp_thumb_file = 'thumbnail_tmp.jpg'
stand_pars = ['FN', 'TITLE', 'ORG', 'ADR', 'TEL', 'EMAIL', 'URL', 'PHOTO']
max_param_length = 24
X = 154
Y = 20
OFF = 20
small_size = (146, 196)
thumb_size = (350, 200)
pic_offset = (2, 2)
text_color = (0, 0, 0)
background_color = (255, 255, 255, 255)
font_size = 10
font_file = "Roboto-Regular.ttf"  # can be used instead of default font


def load_vcards(lines):  # form list of lines for each vcard, begin line excluded
    all_cards = list()
    card_lines = list()
    inside_card = False
    for line in lines:
        if ":" in line:  # parameter line 
            param, value = line.strip().split(':')
            if "BEGIN" in param:
                if not inside_card:
                    inside_card = True
                else:
                    print("invalid vcard format: END line missing")
                    return None
            elif "END" in param:
                if inside_card:
                    card_lines.append(line)
                    all_cards.append(card_lines)
                    card_lines = list()
                    inside_card = False
                else:
                    print("invalid vcard format: END line before BEGIN line")
                    return None
            else:
                card_lines.append(line)
        elif inside_card:
            card_lines.append(line)
        else:
            continue
    return all_cards


def decode_data(index, lines, value):
    photo_data = value
    for line in lines[index + 1:]:
        if "END:VCARD" in line:
            break
        else:
            photo_data += line.strip()
    # ignore parameters of encoding in pars list
    try:
        imgdata = base64.b64decode(photo_data)
    except:
        print('error in base64 encoding, data ignored')
        return ''
    else:
        with open(temp_thumb_file, 'wb') as f:
            f.write(imgdata)
        return temp_thumb_file


def get_photo(card_lines):
    photo_file = ''
    for index, line in enumerate(card_lines):
        if ":" in line:  # parameter line 
            param, value = line.strip().split(':')
            p, *p_var = param.split(';')
            if p == 'PHOTO':
                if 'http' in value.lower():
                    # download photo from inet
                    break
                else:
                    # data is in the list, so we have to decode them
                    photo_file = decode_data(index, card_lines, value)
                    break
    return photo_file


def create_thumbnail(card_info):
    background = Image.new('RGBA', thumb_size, background_color)
    draw = ImageDraw.Draw(background)
    # font = ImageFont.truetype(font_file, font_size)
    font = ImageFont.load_default()
    params_list = list(card_info.keys())
    if ('PHOTO' in params_list) and (card_info['PHOTO'] != ''):
        img = Image.open(card_info['PHOTO'], 'r')
        small_img = img.resize(small_size)
        background.paste(small_img, pic_offset)
    offset = Y
    for par in params_list:
        if par != 'PHOTO':
            draw.text((X, offset), par + ': ' + card_info[par], text_color, font=font)
            offset += OFF
    background.save((card_info['FN'].lower() + '.png').replace(' ', '_'))


def card_to_thumbnail(card_lines):
    card_data = dict()
    if 'PHOTO' in stand_pars:  # process PHOTO par if present standard parameters
        result = get_photo(card_lines)
        if result != '':
            card_data['PHOTO'] = result
    for line in card_lines:  # process others parameters
        if ":" in line:  # parameter line 
            param, value = line.strip().split(':')
            p1, *_ = param.split(';')
            if (p1 in stand_pars) and (p1 not in card_data):
                temp = " ".join(value.split(';')).strip()
                if len(temp) > max_param_length:  # cut long string
                    temp = temp[:max_param_length]
                card_data[p1] = temp
    create_thumbnail(card_data)


def main(vcard_file):
    with open(vcard_file, encoding="utf8") as f:
        data = f.readlines()
    dirname = vcard_file.lower().split('.')[0] + ".thumbs"
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    os.chdir(dirname)
    list_of_cards = load_vcards(data)
    if list_of_cards:
        for card in list_of_cards:
            card_to_thumbnail(card)
        os.remove(temp_thumb_file)  # remove temporal jpg file


if __name__ == '__main__':
    if sys.argv[1:]:
        vfile = sys.argv[1]
        if os.path.exists(vfile):
            main(vfile)
        else:
            print("no such file:", vfile)
    else:
        print('no vcard file given')
