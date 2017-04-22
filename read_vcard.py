#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
version = 'Ver 3.0b April 22, 2017'
# "THE BEER-WARE LICENSE" (Revision 42):
# Dmitrii Sokolov <sokolovdp@gmail.com> wrote this code. As long as you retain
# this notice you can do whatever you want with this stuff. If we meet some day,
# and you think this stuff is worth it, you can buy me a beer in return
#   source code: https://github.com/sokolovdp/vcard/blob/master/read_vcard_v3.py
# The idea of "beer license" was borrowed from Terry Yin <terry.yinzhe@gmail.com>
#    https://github.com/terryyin/google-translate-python
# ----------------------------------------------------------------------------

import os
import sys
import io
import re
import argparse
import shutil
import base64
import platform
import chardet
import random
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import tkinter as tk

# Initialize  global variables
stand_pars = ['N', 'FN', 'TITLE', 'ORG', 'ADR', 'TEL', 'EMAIL', 'URL']  # PHOTO processed separately

small_size = {
    'thumb_size': (350, 200),
    'pict_size': (146, 196),
    'X_PHOTO': 154,
    'Y_PHOTO': 20,
    'X_NO_PHOTO': 50,
    'Y_NO_PHOTO': 40,
    'OFF': 20,
    'pic_offset': (2, 2),
    'font_size_windows': 12,
    'font_size_linux': 12
}

big_size = {
    'thumb_size': (700, 400),
    'pict_size': (292, 392),
    'X_PHOTO': 308,
    'Y_PHOTO': 40,
    'X_NO_PHOTO': 100,
    'Y_NO_PHOTO': 80,
    'OFF': 40,
    'pic_offset': (4, 4),
    'font_size_windows': 24,
    'font_size_linux': 24
}

available_thumb_sizes = {'350x200': small_size, '700x400': big_size}
thumb_pars = available_thumb_sizes['350x200']

windows_font = 'ariali.ttf'
linux_font = '/usr/share/fonts/truetype/ubuntu-font-family/Ubuntu-RI.ttf'
font_truetype = ''

vcard_file = ''
encoding = 'UTF-8'
thumbs_dir = 'temp.thumbs'

background_color = (255, 255, 255, 255)  # white
text_color = (0, 0, 0)  # black

# time_out = 30000  # 30 secs
tk_window_geometry = '620x100+300+200'


class Display:
    def __init__(self, window_mode):
        self._stdout = False
        if not window_mode:
            self._stdout = True
            return
        # create window for program messages
        self.mainWindow = tk.Tk()
        # self.mainWindow.after(time_out, lambda: self.mainWindow.destroy())
        self.mainWindow.title("   VCF file reader  {}".format(version))
        self.mainWindow.geometry(tk_window_geometry)
        self.mainWindow['padx'] = 8
        self.text_box = tk.Text(self.mainWindow, state=tk.NORMAL)  # DISABLED)
        self.text_box.pack()

    def write(self, text):
        if self._stdout:
            print(text)
            return
        # text_box.config(state=tk.NORMAL)
        self.text_box.insert("end", "{}\n".format(text))
        # text_box.see("end")
        # text_box.config(state=tk.DISABLED)


def get_encoding(fname):
    raw_data = open(fname, "rb").read()
    result = chardet.detect(raw_data)
    return result['encoding']


def load_vcards(filename):  # parse VCF file into list of dicts with vcard params
    # patterns to parse the vcard file
    vcard_format = "(?i)BEGIN:VCARD(?P<card>.*?)END:VCARD"  # pattern of VCARD, Case-insensitive
    p_vcard = re.compile(vcard_format, re.DOTALL)

    photo_format = "PHOTO;(?P<pars>[A-Za-z0-9;=]+?):[\s]*?(?P<base64>[A-Za-z0-9+/=]+?)\n"  # pattern of PHOTO Param
    p_photo = re.compile(photo_format, re.DOTALL)

    base64_format = "^[ ]??(?P<base64>[A-Za-z0-9+/=]+?)\n"  # pattern of BASE64 code
    b64_value = re.compile(base64_format, re.MULTILINE)

    param_format = "(?P<param>.*?):(?P<value>.*?)\n"  # pattern of any other PARAM
    p_param = re.compile(param_format)

    with open(filename, encoding=get_encoding(filename)) as f:
        data = f.read()
    cards_list = list()
    for match_vcard in p_vcard.finditer(data):
        vcard_params = dict()
        vcard_text = match_vcard.group('card')
        match_photo = re.search(p_photo, vcard_text)
        if match_photo:  # there is a photo image in the vcard
            span = match_photo.span()
            start_photo = span[0]
            end_photo = span[1]
            photo_code = match_photo.group('base64')
            # check if the next text is still base64 code
            off = 0  # offset from beginning of the photo field
            for match_base64 in b64_value.finditer(vcard_text[end_photo:]):
                photo_code = ''.join([photo_code, match_base64.group('base64')])
                off = match_base64.span()[1]
            end_photo += off  # offset from begin photo field
            try:
                image_bytes = base64.b64decode(photo_code)
            except:
                display.write('error in base64 encoding, image data ignored')
            else:
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                except TypeError:
                    display.write('error in image data, image ignored')
                else:
                    vcard_params["PHOTO"] = image
            vcard_head = vcard_text[:start_photo]
            vcard_tail = vcard_text[end_photo:]
            if len(vcard_tail):
                vcard_text = ''.join([vcard_head, vcard_tail])
        n_given = False
        fn_given = False
        for match_param in p_param.finditer(vcard_text):  # parse other parameters
            params = match_param.group('param').upper().split(';')
            values = match_param.group('value').split(';')
            param = params[0]
            value = values[0]
            if param == 'N':
                n_given = True
            if param == 'FN':
                fn_given = True
            if (param in stand_pars) and (param not in vcard_params.keys()):
                vcard_params[param] = value
        if vcard_params:
            if (not n_given) and (not fn_given):
                display.write("no name parameters (N or FN) in data, vcard ignored")
                continue
            if n_given and fn_given:  # there must only FN parameter in vcard data
                del vcard_params['N']
            elif n_given:
                vcard_params['FN'] = vcard_params['N']
                del vcard_params['N']
            cards_list.append(vcard_params)
        else:
            print("no valid parameters in data, vcard ignored")
    display.write("loaded {} vcards, from file: {}".format(len(cards_list), filename))
    return cards_list


def create_thumbnail(card_info):
    background = Image.new('RGBA', thumb_pars['thumb_size'], background_color)
    draw = ImageDraw.Draw(background)
    if 'PHOTO' in card_info.keys():
        x = thumb_pars['X_PHOTO']
        y = thumb_pars['Y_PHOTO']
    else:
        x = thumb_pars['X_NO_PHOTO']
        y = thumb_pars['Y_NO_PHOTO']
    for param in list(card_info.keys()):
        if param == 'PHOTO':
            smaller_img = card_info['PHOTO'].resize(thumb_pars['pict_size'])
            background.paste(smaller_img, thumb_pars['pic_offset'])
        else:
            draw.text((x, y), '{}: {}'.format(param.lower(), card_info[param]), text_color, font=font_truetype)
            y += thumb_pars['OFF']
    thumb_file = re.sub(r'[\\/*?:"<>|]', '', card_info['FN'].replace(' ', '_'))
    if os.path.isfile('{}.png'.format(thumb_file)):
        thumb_file = '{}_{}'.format(thumb_file, random.randint(0, 999))
    thumb_file = '{}.png'.format(thumb_file)
    try:
        background.save(thumb_file)
    except IOError:
        display.write("IO error during writing thumb file: {}".format(thumb_file))


def load_truetype_font(font_file):  # check which OS is running and install proper truetype font
    # initialize local vars
    os_name = platform.system()
    size = 'font_size_linux'
    temp_file = linux_font
    if os_name == "Windows":
        size = 'font_size_windows'
        temp_file = windows_font
    elif os_name == 'Linux':
        pass
    else:
        display.write("this programm can run only on Windows or Linux")
        exit()
    font = None
    if not font_file:
        try:
            font = ImageFont.truetype(font=temp_file, size=thumb_pars[size], encoding='unic')
        except IOError:
            display.write("cannot open font:".format(temp_file))
            exit()
    else:  # font file is given
        try:
            font = ImageFont.truetype(font=font_file, size=thumb_pars[size], encoding='unic')
        except IOError:
            display.write("cannot open font: {}".format(font_file))
            exit()
    return font


def make_dir_name(filename):
    temp = os.path.split(filename)[1]
    if '.' in temp:  # check if there is a file extension
        temp = filename.split('.')[0]
    return "{}.thumbs".format(temp)


def main(window_mode):
    list_of_cards = load_vcards(vcard_file)
    if list_of_cards:
        shutil.rmtree(thumbs_dir, ignore_errors=True)  # remove old directory and files
        try:
            os.makedirs(thumbs_dir)  # create new directory
        except OSError:
            display.write("access error: can't create directory: {}".format(thumbs_dir))
        else:
            os.chdir(thumbs_dir)
            for card in list_of_cards:
                create_thumbnail(card)
            display.write("created directory: {} with {} thumbs".format(thumbs_dir, len(list_of_cards)))
    if window_mode:
        display.mainWindow.mainloop()

if __name__ == '__main__':

    ap = argparse.ArgumentParser(description='This program create .png thumbs of vcards from vcf file')
    ap.add_argument("-s", "--thumb_size", dest="size", action="store", default='350x200',
                    help="thumbs icons size, valid sizes are: 350x200 (default) and 700x400")
    ap.add_argument("-f", "--font", dest="font", action="store", type=argparse.FileType('rb'),
                    help="path to directory with font to be used for thumbs")
    ap.add_argument("-t", "--todir", dest="dir", action="store",
                    help="directory to write thumb files, default: filename.thumbs")
    ap.add_argument("-w", "--window", dest="win", action="store_true", default=False,
                    help="show program messages in window, default: messages printed to standart output")
    ap.add_argument("file", type=argparse.FileType('rb'), help="vcf file with vcard data")

    args = ap.parse_args(sys.argv[1:])
    vcard_file = args.file.name
    encoding = get_encoding(vcard_file)
    if args.font:
        font_truetype = load_truetype_font(args.font)
    else:
        font_truetype = load_truetype_font(None)
    if args.dir:
        thumbs_dir = args.dir
    else:
        thumbs_dir = make_dir_name(vcard_file)
    if args.size not in available_thumb_sizes.keys():
        print('invalid size of thumbs, available are: {}'.format(list(available_thumb_sizes.keys())))
        exit()
    else:
        thumb_pars = available_thumb_sizes[args.size]

    display = Display(args.win)
    main(args.win)
