# vcard_read

This program create .png thumbs of vcards from vcf file

usage:

	read_vcard.py [-h] [-m] [-a ADD] [-s SIZE] [-f FONT] [-d DIR] [-w] file

positional arguments:

		file        .vcf file with vcards data

optional arguments:

usage: read_vcard.py [-h] [-m] [-a ADD] [-s SIZE] [-f FONT] [-d DIR] [-w] file

This program create .png thumbs of vcards from .vcf file

positional arguments:
  file        .vcf file with vcards data

optional arguments:
  -h, --help  show this help message and exit
  -m          split .vcf file into many single vcard .vcf files and their .png thumbs
  -a ADD      add extra vcard parameter(s) to parse from .vcf file, default
              parameters are: N FN TITLE ORG ADR TEL EMAIL URL
  -s SIZE     .png image size in pixels, valid sizes are: 350x200(default) and 700x400
  -f FONT     full path of the font file to be used for text in .png images
  -d DIR      directory to write all .png thumbs, default name: <file>.thumbs
  -w          show program messages in window, default: text in the standard output


To run vcard_read.py on Ubuntu:
-------------------------------
1) make sure that python3 and all needed packages are installed: 
	io, os, sys, platform, base64, shutil, re, PIL, chardet, random, tkinter(!)
2) to use tkinter on Ubuntu (if it is not present yet) you  need to install a separate package:
    % sudo apt-get install python3-tk
3) change mode of the file to executable:  chmod +x vcard_read.py
4) copy vcard_read.py into Nautilus scripts folder: ~/.local/share/nautilus/scripts
5) once you have done all this, the script will be accessible from the scripts sub-menu of the right click menu in Nautilus