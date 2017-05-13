#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# version = 'ver 4.2b  May 13, 2017'
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

# Initialize global variables
version = 'ver 4.2b  May 13, 2017'

standard_parameters = ['N', 'FN', 'TITLE', 'ORG', 'ADR', 'TEL', 'EMAIL', 'URL']  # PHOTO processed separately

tk_window_geometry = '620x100+300+200'

small_size = {  # parameters of small thumb
    'thumb_size': (350, 200),
    'pict_size': (146, 196),
    'X_PHOTO': 154,
    'Y_PHOTO': 20,
    'X_NO_PHOTO': 50,
    'Y_NO_PHOTO': 40,
    'OFF': 20,
    'pic_offset': (2, 2),
    'font_size_windows': 12,
    'font_size_linux': 12,
    'windows_font': 'ariali.ttf',
    'linux_font': '/usr/share/fonts/truetype/ubuntu-font-family/Ubuntu-RI.ttf',
    'background': (255, 255, 255, 255),  # white
    'text_color': (0, 0, 0)  # black
}
big_size = {  # parameters of big thumb
    'thumb_size': (700, 400),
    'pict_size': (292, 392),
    'X_PHOTO': 308,
    'Y_PHOTO': 40,
    'X_NO_PHOTO': 100,
    'Y_NO_PHOTO': 80,
    'OFF': 40,
    'pic_offset': (4, 4),
    'font_size_windows': 24,
    'font_size_linux': 24,
    'windows_font': 'ariali.ttf',
    'linux_font': '/usr/share/fonts/truetype/ubuntu-font-family/Ubuntu-RI.ttf',
    'background': (255, 255, 255, 255),  # white
    'text_color': (0, 0, 0)  # black
}
available_thumb_sizes = {'350x200': small_size, '700x400': big_size}
current_thumb_parameters = available_thumb_sizes['350x200']  # default value


class Display:
    def __init__(self, window_mode):
        self._stdout = False
        if not window_mode:
            self._stdout = True
            return
        # create window for program messages
        self.mainWindow = tk.Tk()
        self.mainWindow.title("   VCF file reader  {}".format(version))
        self.mainWindow.geometry(tk_window_geometry)
        self.mainWindow['padx'] = 8
        self.text_box = tk.Text(self.mainWindow, state=tk.NORMAL)
        self.text_box.pack()

    def write(self, text):
        if self._stdout:
            print(text)
            return
        self.text_box.insert("end", "{}\n".format(text))

    def window(self):
        return not self._stdout


def form_file_path(dirname, filename):
    return "{}{}{}".format(dirname, '/', filename)


def get_encoding(fname):  # detect file encoding
    with open(fname, "rb") as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']


def load_vcf_file(display, filename):  # parse VCF file into list of dicts with vcard params
    # patterns to parse the .vcf file
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
            start_photo, end_photo = match_photo.span()
            photo_code = match_photo.group('base64')
            # check if the next text is still base64 code
            off = 0  # offset from beginning of the photo field
            for match_base64 in b64_value.finditer(vcard_text[end_photo:]):
                photo_code = ''.join([photo_code, match_base64.group('base64')])
                off = match_base64.span()[1]
            end_photo += off  # offset from begin photo field
            try:
                image_bytes = base64.b64decode(photo_code)
            except Exception:
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
            if (param in standard_parameters) and (param not in vcard_params.keys()):
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
    return cards_list


def create_thumbnail(display, card_info, font, image_name=None):
    background = Image.new('RGBA', current_thumb_parameters['thumb_size'], current_thumb_parameters['background'])
    draw = ImageDraw.Draw(background)
    if 'PHOTO' in card_info.keys():
        x = current_thumb_parameters['X_PHOTO']
        y = current_thumb_parameters['Y_PHOTO']
    else:
        x = current_thumb_parameters['X_NO_PHOTO']
        y = current_thumb_parameters['Y_NO_PHOTO']
    for param in list(card_info.keys()):
        if param == 'PHOTO':
            smaller_img = card_info['PHOTO'].resize(current_thumb_parameters['pict_size'])
            background.paste(smaller_img, current_thumb_parameters['pic_offset'])
        else:
            draw.text((x, y), '{}: {}'.format(param.lower(), card_info[param]),
                      current_thumb_parameters['text_color'], font=font)
            y += current_thumb_parameters['OFF']
    if image_name is None:
        thumb_file = re.sub(r'[\\/*?:"<>|]', '',
                            card_info['FN'].replace(' ', '_'))  # clean filename from forbidden chars
        if os.path.isfile('{}.png'.format(thumb_file)):
            thumb_file = '{}_{}'.format(thumb_file, random.randint(0, 999))
        thumb_file = '{}.png'.format(thumb_file)
    else:
        thumb_file = image_name
    try:
        background.save(thumb_file)
    except IOError:
        display.write("i/o error during writing thumb file: {}".format(thumb_file))
        error = True
    else:
        error = False
    return error


def split_vcf_file(display, filename, dirname):  # split one VCF file into many single vcard files
    vcard_format = "(?i)BEGIN:VCARD(?P<card>.*?)END:VCARD"
    pattern_vcard = re.compile(vcard_format, re.DOTALL)
    with open(filename, encoding=get_encoding(filename)) as f:
        data = f.read()
    n_vcards = 0
    for n, match_vcard in enumerate(pattern_vcard.finditer(data)):
        single_vcf_file = form_file_path(dirname, "{:0>4}.vcf".format(n + 1))
        vcard_text = "{}\n{}{}\n".format("BEGIN:VCARD", match_vcard.group('card').lstrip(), "END:VCARD")
        try:
            with open(single_vcf_file, 'w', encoding='utf8') as f:
                f.write(vcard_text)
        except IOError:
            display.write("i/o error during writing single vcf file: {}".format(single_vcf_file))
        else:
            n_vcards = n + 1
    return n_vcards


def main(display, vcard_file, thumbs_dir, font, multi):
    if not multi:
        list_of_cards = load_vcf_file(display, vcard_file)
        display.write("loaded {} vcards, from file: {}".format(len(list_of_cards), vcard_file))
        errors = 0
        if list_of_cards:
            os.chdir(thumbs_dir)
            for card in list_of_cards:
                if create_thumbnail(display, card, font):  # returns True if there is an error
                    errors += 1
        display.write("created directory: {} with {} thumbs files".format(thumbs_dir, len(list_of_cards) - errors))
    else:
        display.write("split .vcf file mode activated, output directory: {}".format(thumbs_dir))
        nv = split_vcf_file(display, vcard_file, thumbs_dir)
        display.write("created {} .vcf single vcard files".format(nv))
        list_of_files = os.listdir(thumbs_dir)
        os.chdir(thumbs_dir)
        errors = 0
        for file in list_of_files:
            if file.endswith(".vcf"):
                list_of_cards = load_vcf_file(display, file)
                if list_of_cards:
                    png_file = "{}.png".format(file.split(".")[0])
                    if create_thumbnail(display, list_of_cards[0], font, png_file):
                        errors += 1
        display.write("created {} .png thumb files".format(nv - errors))

    if display.window():
        display.mainWindow.mainloop()


def load_truetype_font(font_file):  # check which OS is running and install proper truetype font
    # initialize local vars
    os_name = platform.system()
    font_size = current_thumb_parameters['font_size_linux']
    temp_file = current_thumb_parameters['linux_font']
    if os_name == 'Linux':
        pass
    elif os_name == "Windows":
        font_size = current_thumb_parameters['font_size_windows']
        temp_file = current_thumb_parameters['windows_font']
    else:
        print("this program can run only on windows or linux")
        exit(1)
    if not font_file:  # font file is not given, use standard fonts
        font_file = temp_file
    try:
        font = ImageFont.truetype(font=font_file, size=font_size, encoding='unic')
    except IOError:
        print("cannot open font file: {}".format(font_file))
        exit(2)
    else:
        return font


def make_dir_name(dirname):
    try:
        temp = os.path.split(dirname)[1]
    except OSError:
        print("invalid directory name: {}".format(dirname))
    else:
        if not temp:
            temp = 'temp'
        return "{}_thumbs".format(temp.replace('.vcf', ''))


if __name__ == '__main__':

    ap = argparse.ArgumentParser(description='This program create .png thumbs of vcards from .vcf file')
    ap.add_argument("-m", dest="multi", action="store_true", default=False,
                    help="split .vcf file into many single vcard .vcf files and their .png thumbs")
    ap.add_argument("-a", dest="add", action="store",
                    help="add extra vcard parameter(s) to parse from .vcf file, default parameters are: {}".format(
                        ' '.join(standard_parameters)))
    ap.add_argument("-s", dest="size", action="store", default='350x200',
                    help=".png image size in pixels, valid sizes are: 350x200(default) and 700x400")
    ap.add_argument("-f", dest="font", action="store", type=argparse.FileType('rb'),
                    help="full path of the font file to be used for text in .png images")
    ap.add_argument("-d", dest="dir", action="store",
                    help="directory to write all .png thumbs, default name: <file>.thumbs")
    ap.add_argument("-w", dest="win", action="store_true", default=False,
                    help="show program messages in window, default: text in the standard output")
    ap.add_argument("file", type=argparse.FileType('rb'), help=".vcf file with vcards data")

    args = ap.parse_args(sys.argv[1:])

    if args.add:  # additional parameters to parse from vcard
        for p in args.add.upper().split():
            if p not in standard_parameters:
                standard_parameters.append(p)
            else:
                print("additional parameter {} is already included in the parser".format(p))
    if args.font:
        user_font = load_truetype_font(args.font)
    else:
        user_font = load_truetype_font(None)

    if args.dir:  # get dir name, delete it and all files, then recreate empty dir
        out_dir = make_dir_name(args.dir)
    else:
        out_dir = make_dir_name(args.file.name)
    shutil.rmtree(out_dir, ignore_errors=True)  # remove old thumb directory and all files in it
    try:
        os.makedirs(out_dir)  # create thumbs directory
    except OSError:
        print("access error: can't create directory: {}".format(out_dir))
        exit(3)

    if args.size not in available_thumb_sizes.keys():
        print('invalid size of thumbs, available are: {}'.format(list(available_thumb_sizes.keys())))
        exit(4)
    else:
        current_thumb_parameters = available_thumb_sizes[args.size]

    main(Display(args.win), args.file.name, out_dir, user_font, args.multi)
