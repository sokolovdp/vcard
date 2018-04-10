#!/usr/bin/env python3

import os
import sys
import io
import re
import argparse
import shutil
import base64
import platform
from chardet.universaldetector import UniversalDetector
import ntpath
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

# Initialize global variables
version = '4.7 beta'
os_name = platform.system()

THUMB_MODE = 1
SPLIT_MODE = 2
UNITY_MODE = 3
modes = {'split': SPLIT_MODE, 'thumb': THUMB_MODE, 'unity': UNITY_MODE}

standard_parameters = ['N', 'FN', 'TITLE', 'ORG', 'ADR', 'TEL', 'EMAIL', 'URL']  # PHOTO processed separately
default_output_directory = "vcfread_folder"
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
p_vcard = re.compile(VCARD_PATTERN, re.DOTALL)
PHOTO_PATTERN = "PHOTO;(?P<pars>[A-Za-z0-9;=]+?):[\s]*?(?P<base64>[A-Za-z0-9+/=]+?)\n"  # pattern of PHOTO Param
p_photo = re.compile(PHOTO_PATTERN, re.DOTALL)
BASE64_PATTERN = "^[ ]??(?P<base64>[A-Za-z0-9+/=]+?)\n"  # pattern of BASE64 code
b64_value = re.compile(BASE64_PATTERN, re.MULTILINE)
PARAM_PATTERN = "(?P<param>.*?):(?P<value>.*?)\n"  # pattern of any other PARAM
p_param = re.compile(PARAM_PATTERN)
INVALID_CHARS = r'[^A-Za-z0-9_-]'
name_valid = re.compile(INVALID_CHARS)


def get_encoding(filename):
    """
    Defines encoding of the file
    filename:  string with file name
    Return the string of encoding format
    """
    detector = UniversalDetector()
    with open(filename, "rb") as f:
        for line in f.readlines():
            detector.feed(line)
            if detector.done:
                break
    detector.close()
    return detector.result['encoding']


def parse_vcf_file(vcf_file: io.TextIOWrapper) -> list:
    """
    Parse VCF file into list of dicts with vcard params
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
                print('error in base64 encoding, image data ignored')
            else:
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                except TypeError:
                    print('error in image data, image ignored')
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
                print("no name parameters (N or FN) in data, vcard ignored")
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


def create_thumbnail(card_info: dict, filename: str) -> str:
    """
    Create image of the vcard and store in the png file with given name
    card_info: dict with vcard data
    filename:  string 
    Returns: file name
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
        return filename
    except IOError:
        print("i/o error during writing thumb file: {}".format(filename))


def write_vcard_to_vcf_file(filename: str, vcard_text: str):
    """
    Write string with single vcard data into the vcf file
    filename:  string 
    vcard_text: string with vcard data
    Return nothing
    """
    try:
        vf = open(filename, 'w', encoding=UTF)
        vf.write(vcard_text)
        vf.close()
    except IOError:
        print("i/o error during writing single vcf file: {}".format(filename))


def get_short_filename(filename: str) -> str:
    return str(ntpath.basename(filename).split('.')[0])


def split_vcf_file(vfile: io.TextIOWrapper) -> list:
    """
    Split vcard file into many single vcard files.
    vfile:  file object in opened state 
    Return list of strings with created vcf file names
    """
    base_name = get_short_filename(vfile.name)
    data = vfile.read()
    list_of_cards = list()
    for match_vcard in p_vcard.finditer(data):
        vcard_data = match_vcard.group('card').lstrip()
        vcard_text = "{}\n{}{}\n".format("BEGIN:VCARD", vcard_data, "END:VCARD")
        list_of_cards.append(vcard_text)
    files_names = list()
    if len(list_of_cards) == 1:
        filename = "{}.vcf".format(base_name).replace(" ", "_")
        files_names.append(filename)
        write_vcard_to_vcf_file(filename, list_of_cards[0])
    elif len(list_of_cards) > 1:
        for i, vcard_text in enumerate(list_of_cards):
            filename = "{0}_{1:0>4}.vcf".format(base_name, i + 1).replace(" ", "_")
            files_names.append(filename)
            write_vcard_to_vcf_file(filename, vcard_text)
    return files_names


def create_thumbs(list_of_cards: list, base_name: str) -> list:
    """
    Convert vcard file into thumbs files.
    vfile:  file object in opened state
    Return list of strings with created thumb file names
    """
    # list_of_cards = parse_vcf_file(vfile)
    # base_name = get_short_filename(vfile.name)
    thumb_files = list()
    if len(list_of_cards) == 1:  # single vcard file
        card = list_of_cards[0]
        thumb = create_thumbnail(card, "{0}.png".format(base_name))
        if thumb:
            thumb_files.append(thumb)
    elif len(list_of_cards) > 1:  # multi vcards file
        for i, card in enumerate(list_of_cards):
            thumb = create_thumbnail(card, "{0}_{1:0>4}.png".format(base_name, i))
            if thumb:
                thumb_files.append(thumb)
    return thumb_files


def create_desktop_file(file: io.TextIOWrapper, vcfname: str, thumbname: str, vcardata: list):
    vcard = vcardata[0]
    line_1 = "[Desktop Entry]\nVersion={0}\nEncoding=UTF-8\nType=Application\nTerminal=false\n".format(version)
    line_2 = "X-MultipleArgs=false\nMimeType=x-scheme-handler/mailto;application/x-xpinstall;\n"
    line_3 = "StartupNotify=true\nGenericName=VCF File Contact Desktop File\nComment=VCF File\nCategories=Contact;\n"
    line_4 = 'Name={0}\nExec=gedit "{1}"\nIcon="{2}"\n'.format(vcard['FN'], vcfname, thumbname)
    line_5 = "Keywords:Contact;VCF file;{0};{1}\n".format(vcard['FN'], vcard.get('ORG', ''))

    email = vcard.get('EMAIL', '')
    tele = vcard.get('TEL', '')

    line_6 = "Actions="
    if email:
        line_6 += "Thunderbird Compose ID1 Email1;"
    if tele:
        line_6 += "Skype Call Tell;"
    line_6 += '\n'

    if email:
        line_7 = "[Desktop Action Thunderbird Compose ID1 Email1]\nName=Thunderbird Compose ID1 Email1\n" \
                 "OnlyShowIn=Messaging Menu;Unity;\n"
        line_8 = "Exec=thunderbird -compose preselectid='id1',to='{0}', subject='Real',body=''," \
                 "attachment='',cc='',bcc=''\n".format(email)
        line_6 += line_7 + line_8

    if tele:
        line_7 = "[Desktop Action Skype Call Tell]\nName=Skype Call Cell\nOnlyShowIn=Messaging Menu;Unity;\n"
        line_8 = "Exec=skype --callto {0}".format(tele.replace(' ', ''))
        line_6 += line_7 + line_8

    file.write(line_1 + line_2 + line_3 + line_4 + line_5 + line_6)


def process_vcf_file(filename: str, thumbs_dir: str, mode: int):
    """
    Convert vcard file into thumbs or single vcards and thumbs files depending on split_mode
    filename:  string with vacrd filename
    thumbs_dir: string with thumbs subdirectory name
    Return nothing
    """
    encoding = get_encoding(filename)
    vcf = open(filename, 'r', encoding=encoding)
    print("input vcf file: '{0}' encoding: {1}".format(filename, encoding))
    current_directory = os.getcwd()
    os.chdir(thumbs_dir)
    if mode == THUMB_MODE:  # thumb mode
        parsed_vcard_list = parse_vcf_file(vcf)
        print("loaded {0} vcards".format(len(parsed_vcard_list)))
        thumb_files = create_thumbs(parsed_vcard_list, vcf.name)
        print("created {0} thumb files".format(len(thumb_files)))
    elif mode == SPLIT_MODE:  # split mode
        vcf_files = split_vcf_file(vcf)
        print("original file {0} was split into {1} single vcard file(s)".format(vcf.name, len(vcf_files)))
    elif mode == UNITY_MODE:  # naut mode
        vcf_files = split_vcf_file(vcf)
        print("created {0} unity desktop folder(s)".format(len(vcf_files)))
        for vcf_file_name in vcf_files:
            with open(vcf_file_name, 'r', encoding=UTF) as tf:
                thumb_file_name = create_thumbs(parse_vcf_file(tf), tf.name)[0]  # create thumb file
            new_dir = get_short_filename(vcf_file_name)
            create_output_directory(new_dir)
            shutil.move(vcf_file_name, new_dir)
            shutil.move(thumb_file_name, new_dir)
            os.chdir(new_dir)
            # create desktop file
            with open(vcf_file_name, 'r', encoding=UTF) as f:
                vcard_data = parse_vcf_file(f)
            with open("{0}.desktop".format(new_dir), 'w', encoding=UTF) as f:
                create_desktop_file(f, vcf_file_name, thumb_file_name, vcard_data)
            os.chdir("..")
    else:
        pass
    os.chdir(current_directory)
    vcf.close()


def main(vcf_files: list, thumbs_dir: str, mode: int):
    for filename in vcf_files:  # process all .vcf files from the list
        process_vcf_file(filename, thumbs_dir, mode)
    if mode == SPLIT_MODE:  # split mode
        print("single vcard files were placed into subdirectory: {0}".format(thumbs_dir))
    elif mode == THUMB_MODE:  # thumb mode
        print("thumbs files were placed into subdirectory: {0}".format(thumbs_dir))
    elif mode == UNITY_MODE:  # nau mode
        print("folders with .desktop files were placed into subdirectory: {0}".format(thumbs_dir))
    else:
        pass


def load_truetype_font(font_file: str) -> ImageFont:
    """
    Load true type font which will be used for thumbs images
    check which OS is running and install proper truetype font
    font_file:  string with path to the font file
    Return font object
    """
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
        print("cannot open font file: {0}".format(font_file))
        exit(2)
    else:
        return font


def create_output_directory(dirname: str) -> str:
    """
    (re)Creates and clean subdirectory for thumbs files in the current directory
    Return string with valid directory name
    """
    dirname = name_valid.sub('_', dirname)  # replace all invalid symbols with '_'
    try:
        shutil.rmtree(dirname, ignore_errors=True)  # remove old thumb directory and all files in it
        os.makedirs(dirname)  # create thumbs directory
    except OSError:
        print("access error: directory {0} is used by another process".format(dirname))
        exit(3)
    return dirname


def check_directory(dirname: str) -> str:
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


def check_file(filename: str) -> str:
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
    except Exception as e:
        raise argparse.ArgumentTypeError("file {0} open error {1}".format(filename, str(e)))
    f.close()
    return filename


def check_mode(mode: str) -> int:
    """
    Check if the args parameter mode has valid value
    Return int value of mode operation
    """
    if mode.lower() not in modes:
        raise argparse.ArgumentTypeError("invalid mode {0}, valid values are {1}".format(mode, ', '.join(modes.keys())))
    return modes[mode.lower()]


if __name__ == '__main__':

    ap = argparse.ArgumentParser(
        description='vcfread.py v{0} processes .vcf files in {1} modes: {2}'.format(version, len(modes),
                                                                                    ', '.join(modes.keys())))

    source = ap.add_mutually_exclusive_group(required=True)  # two main parameters: file.vcf or directory with vcf files
    source.add_argument("--dir", dest="dir", action="store", type=check_directory,
                        help="process all .vcf files in the directory, for the current directory use '$(pwd)'")
    source.add_argument("--file", dest="file", action="store", type=check_file,
                        help="process .vcf file with vcards data")

    ap.add_argument("--mode", dest="mode", action="store", required=True, type=check_mode,
                    help="1) split - create many single vcard files, 2) thumb - create .png images, "
                         "3) unity - create folder with vcf, thumb and .desktop files"
                    )

    ap.add_argument("--add", dest="add", action="store",
                    help="add extra vcard parameter(s) to parse from .vcf file, default parameters are: {}".format(
                        ' '.join(standard_parameters)))
    ap.add_argument("--size", dest="size", action="store", default='350x200',
                    help=".png image size in pixels, valid sizes are: 350x200(default) and 700x400")
    ap.add_argument("--font", dest="font", action="store", type=argparse.FileType('rb'),
                    help="full path of the font file to be used for text in .png images")
    ap.add_argument("--todir", dest="todir", action="store", default=default_output_directory,
                    help="subdirectory for .png thumbs, attention!!! all files in this directory will be deleted!"
                         " default output directory is: {0}".format(default_output_directory))

    args = ap.parse_args(sys.argv[1:])

    if args.add:  # add parameters to list of parameters for parsing
        for p in args.add.upper().split():
            if p not in standard_parameters:
                standard_parameters.append(p)
            else:
                print("vcard parameter {0} is already included in the parser".format(p))

    if args.font:  # check and load font file
        active_font = load_truetype_font(args.font)
    else:
        active_font = load_truetype_font('')

    out_dir = create_output_directory(args.todir)  # get dir name, delete it and all files, then recreate empty dir

    if args.size not in available_thumb_sizes.keys():  # set thumbs size in pixels
        print('invalid size of thumbs, available are: {}'.format(list(available_thumb_sizes.keys())))
        exit(4)
    else:
        current_thumb_parameters = available_thumb_sizes[args.size]

    files_for_parsing = list()
    if args.file:  # create list of vcf files to processing
        files_for_parsing.append(args.file)
    else:
        files_for_parsing = [os.path.join(args.dir, file) for file in os.listdir(args.dir)
                             if file.endswith('.vcf') or file.endswith('.vcard')]
        if not files_for_parsing:
            print('no vcf(vcard) files in the directory: {0}'.format(args.dir))
            exit()

    main(files_for_parsing, out_dir, args.mode)
