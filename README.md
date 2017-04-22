# vcard_read

usage: read_vcard.py [-h] [-s SIZE] [-f FONT] [-t DIR] [-w] file

This program create .png thumbs of vcards from vcf file

positional arguments:
  file                  vcf file with vcard data

optional arguments:
  -h, --help                 show this help message and exit
  -s SIZE, --thumb_size SIZE thumbs icons size, valid sizes are: 350x200 (default)
                             and 700x400
  -f FONT, --font FONT       path to directory with font to be used for thumbs
  -t DIR, --todir DIR        directory to write thumb files, default:
                             filename.thumbs
  -w, --window               show program messages in window, default: messages
                             printed to standart output


To run program vcard_read.py on Ubuntu:

1) make sure that python3 and all needed packages are installed: 
	io, os, sys, platform, base64, shutil, re, PIL, chardet, random, tkinter(!)
2) to use tkinter on Ubuntu (if it is not present yet) you  need to install a separate package:
    % sudo apt-get install python3-tk
3) change mode of the file to executable:  chmod +x vcard_read.py
4) copy vcard_read.py into Nautilus scripts folder: ~/.local/share/nautilus/scripts
5) once you have done all this, the script will be accessible from the scripts sub-menu of the right click menu in Nautilus