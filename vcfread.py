#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
#                "THE BEER-WARE LICENSE":
# Dmitrii Sokolov <sokolovdp@gmail.com> wrote this code. As long as you retain
# this notice you can do whatever you want with this stuff. If we meet some day,
# and you think this stuff is worth it, you can buy me a beer in return
#   source code: https://github.com/sokolovdp/vcard/blob/master/vcfread.py
# The idea of "beer license" was borrowed from Terry Yin <terry.yinzhe@gmail.com>
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
import ntpath
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

try:
    import tkinter as tk
except ImportError:
    tk = None

# Initialize global variables
version = '4.4'
standard_parameters = ['N', 'FN', 'TITLE', 'ORG', 'ADR', 'TEL', 'EMAIL', 'URL']  # PHOTO processed separately
tk_window_geometry = '620x100+300+200'
default_output_directory = "thumbs_folder"
active_font = None
UTF = 'utf-8'

small_size = {  # parameters of small thumb image
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
big_size = {  # parameters of big thumb image
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

VCARD_PATTERN = "(?i)BEGIN:VCARD(?P<card>.*?)END:VCARD"  # pattern of VCARD, Case-insensitive
PHOTO_PATTERN = "PHOTO;(?P<pars>[A-Za-z0-9;=]+?):[\s]*?(?P<base64>[A-Za-z0-9+/=]+?)\n"  # pattern of PHOTO Param
BASE64_PATTERN = "^[ ]??(?P<base64>[A-Za-z0-9+/=]+?)\n"  # pattern of BASE64 code
PARAM_PATTERN = "(?P<param>.*?):(?P<value>.*?)\n"  # pattern of any other PARAM
p_vcard = re.compile(VCARD_PATTERN, re.DOTALL)
p_photo = re.compile(PHOTO_PATTERN, re.DOTALL)
b64_value = re.compile(BASE64_PATTERN, re.MULTILINE)
p_param = re.compile(PARAM_PATTERN)


class Display:
    """
    Window object to display program messages, use TKinter window or sys.stdout
    """

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


def get_encoding(filename):
    """
    Defines encoding of the file
    
    filename:  string with file name
    Return the string of encoding format
    """
    with open(filename, "rb") as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']


def parse_vcf_file(display, vcf_file):
    """
    Parse VCF file into list of dicts with vcard params

    display:  display object for messaging
    vcf_file: string with file name
    Return the list of dicts with vcard parameters
    """
    data = vcf_file.read()
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
            except (ValueError, Exception):
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


def create_thumbnail(display, card_info, filename):
    """
    Create image of the vcard and store in the png file with given name

    display:  display object for messaging
    card_info: dict with vcard data
    filename:  string 
    Return nothing
    """
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
                      current_thumb_parameters['text_color'], font=active_font)
            y += current_thumb_parameters['OFF']
    try:
        background.save(filename)
    except IOError:
        display.write("i/o error during writing thumb file: {}".format(filename))


def write_vcf_file(display, filename, vcard_text):
    """
    Write string with single vcard data into the vcf file

    display:  display object for messaging
    filename:  string 
    vcard_text: string with vcard data
    Return nothing
    """
    try:
        vf = open(filename, 'w', encoding=UTF)
        vf.write(vcard_text)
        vf.close()
    except IOError:
        display.write("i/o error during writing single vcf file: {}".format(filename))


def split_vcf_file(display, vfile, to_dir):
    """
    Split vcard file into many single vcard files.
    
    display:  display object for messaging
    vfile:  file object in opened state 
    Return list of strings with created file names
    """
    base_name = ntpath.basename(vfile.name).split('.')[0]
    data = vfile.read()
    list_of_cards = list()
    for match_vcard in p_vcard.finditer(data):
        vcard_data = match_vcard.group('card').lstrip()
        vcard_text = "{}\n{}{}\n".format("BEGIN:VCARD", vcard_data, "END:VCARD")
        list_of_cards.append(vcard_text)
    files_names = list()
    if len(list_of_cards) == 1:
        filename = "{}{}{}.vcf".format(to_dir, '/', base_name)
        files_names.append(filename)
        write_vcf_file(display, filename, list_of_cards[0])
    elif len(list_of_cards) > 1:
        for i, vcard_text in enumerate(list_of_cards):
            filename = "{}{}{}_{:0>4}.vcf".format(to_dir, '/', base_name, i + 1)
            files_names.append(filename)
            write_vcf_file(display, filename, vcard_text)
    return files_names


def convert_vcf_file_to_thumbs(display, vfile, thumbs_dir):
    """
    Convert vcard file into thumbs files.

    display:  display object for messaging
    vfile:  file object in opened state
    thumbs_dir: string with thumbs subdirectory name
    Return number of created thumb files
    """
    list_of_cards = parse_vcf_file(display, vfile)
    base_name = ntpath.basename(vfile.name).split('.')[0]
    current_directory = os.getcwd()
    os.chdir(thumbs_dir)
    if len(list_of_cards) == 1:  # single vcard file
        card = list_of_cards[0]
        create_thumbnail(display, card, "{}.png".format(base_name))
    elif len(list_of_cards) > 1:  # multi vcards file
        for i, card in enumerate(list_of_cards):
            create_thumbnail(display, card, "{}_{:0>4}.png".format(base_name, i))
    os.chdir(current_directory)
    return len(list_of_cards)


def process_vcf_file(display, filename, thumbs_dir, split_mode):
    """
    Convert vcard file into thumbs or single vcards and thumbs files depending on split_mode

    display:  display object for messaging
    filename:  string with vacrd filename
    thumbs_dir: string with thumbs subdirectory name
    Return nothing
    """
    vcf = open(filename, 'r', encoding=get_encoding(filename))
    if not split_mode:
        n = convert_vcf_file_to_thumbs(display, vcf, thumbs_dir)
        display.write("loaded {} vcards, from file: {}".format(n, filename))
    else:
        files = split_vcf_file(display, vcf, thumbs_dir)
        display.write("file {1} was split into {0} single vcard file(s)".format(len(files), filename))
        for file in files:
            f = open(file, 'r', encoding=UTF)
            convert_vcf_file_to_thumbs(display, f, thumbs_dir)
            f.close()
    vcf.close()


def main(vcf_files, display, thumbs_dir, split_mode):
    for filename in vcf_files:
        process_vcf_file(display, filename, thumbs_dir, split_mode)
    if not split_mode:
        display.write("thumbs files were placed into directory: {}".format(thumbs_dir))
    else:
        display.write("single vcard & thumbs files were placed into directory: {}".format(thumbs_dir))

    if display.window():
        display.mainWindow.mainloop()


def load_truetype_font(font_file):
    """
    Load true type font which will be used for thumbs images
    check which OS is running and install proper truetype font
    
    font_file:  string with path to the font file
    Return font object
    """
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


def create_output_directory(dirname):
    """
    (re)Creates and clean subdirectory for thumbs files in the current directory
    
    Return string with directory name
    """
    if not dirname.isalpha():
        dirname = default_output_directory
    try:
        shutil.rmtree(dirname, ignore_errors=True)  # remove old thumb directory and all files in it
        os.makedirs(dirname)  # create thumbs directory
    except OSError:
        print("access error: directory {} is used by another process".format(dirname))
        exit(3)
    return dirname


def check_directory(dirname):
    """
    Check if the args parameter is a valid existing input directory
    
    Return string with directory name
    """
    if dirname == "$(pwd)":
        dirname = os.getcwd()
    else:
        if not os.path.isdir(dirname):
            raise argparse.ArgumentTypeError("invalid directory path {0}".format(dirname))
        elif not os.access(dirname, os.R_OK):
            raise argparse.ArgumentTypeError("unreadable directory {0}".format(dirname))
    return dirname


def check_file(filename):
    """
    Check if the args parameter is a valid existing input file

    Return string with file name
    """
    if filename.endswith('/'):
        raise argparse.ArgumentTypeError("invalid file name with '/' at the end {0}".format(filename))
    try:
        f = open(filename, 'rb')
    except IOError:
        raise argparse.ArgumentTypeError("no such file {0}".format(filename))
    except:
        raise argparse.ArgumentTypeError("can't open file {0}".format(filename))
    f.close()
    return filename


if __name__ == '__main__':

    ap = argparse.ArgumentParser(
        description='vcfread.py v{} creates .png thumbs of vcards from .vcf file'.format(version))

    source = ap.add_mutually_exclusive_group(required=True)  # two main parameters: file.vcf or directory with vcf files
    source.add_argument("--xdir", dest="xdir", action="store", type=check_directory,
                        help="process all .vcf files in the directory, for the current directory use '$(pwd)'")
    source.add_argument("--file", dest="file", action="store", type=check_file,
                        help="process single .vcf file with vcards data")

    ap.add_argument("--split", dest="split", action="store_true", default=False,
                    help="split .vcf file into many single vcard .vcf files and their .png thumbs")
    ap.add_argument("--add", dest="add", action="store",
                    help="add extra vcard parameter(s) to parse from .vcf file, default parameters are: {}".format(
                        ' '.join(standard_parameters)))
    ap.add_argument("--size", dest="size", action="store", default='350x200',
                    help=".png image size in pixels, valid sizes are: 350x200(default) and 700x400")
    ap.add_argument("--font", dest="font", action="store", type=argparse.FileType('rb'),
                    help="full path of the font file to be used for text in .png images")
    ap.add_argument("--todir", dest="todir", action="store", default=default_output_directory,
                    help="subdirectory for .png thumbs, attention!!! all files in this directory will be deleted!"
                         " default output directory is: {}".format(default_output_directory))
    ap.add_argument("--win", dest="win", action="store_true", default=False,
                    help="if given show messages in window, if not - messages will go to the console output")

    args = ap.parse_args(sys.argv[1:])

    if args.add:  # add parameters to list of parameters for parsing
        for p in args.add.upper().split():
            if p not in standard_parameters:
                standard_parameters.append(p)
            else:
                print("vcard parameter {} is already included in the parser".format(p))

    if args.font:  # check and load font file
        active_font = load_truetype_font(args.font)
    else:
        active_font = load_truetype_font(None)

    out_dir = create_output_directory(args.todir)  # get dir name, delete it and all files, then recreate empty dir

    if args.size not in available_thumb_sizes.keys():  # set thumbs size in pixels
        print('invalid size of thumbs, available are: {}'.format(list(available_thumb_sizes.keys())))
        exit(4)
    else:
        current_thumb_parameters = available_thumb_sizes[args.size]

    if args.win and not tk:  # check if window mode is activated
        print("TKinter package is not installed, window mode is not available")
        args.win = False

    files_for_parsing = list()
    if args.file:  # create list of vcf files to processing
        files_for_parsing.append(args.file)
    else:
        files_for_parsing = [os.path.join(args.xdir, file) for file in os.listdir(args.xdir) if file.endswith('.vcf')]
        if not files_for_parsing:
            print('no vcf files in the directory: {}'.format(args.xdir))
            exit()

    main(files_for_parsing, Display(args.win), out_dir, args.split)
