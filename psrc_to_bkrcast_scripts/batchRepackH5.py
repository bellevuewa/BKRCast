
# Batch repack HDF5 files
# python.exe batchRepackH5.py
# Ben.Stabler@rsginc.com, 10/20/16
# 10/25/2021
# modified to be compatible with python 3

import os
import fnmatch

ext = "*.H5"
h5repack = '"C:\\Program Files\\HDF_Group\\HDF5\\1.8.17\\bin\\h5repack.exe"'

matches = []

#find files
for root, dirnames, filenames in os.walk(os.getcwd()):
    for filename in fnmatch.filter(filenames, ext):
        matches.append(os.path.join(root, filename))

#repack files
for item in matches:
    itemOut = item.replace(".h5","_repack.h5")
    cmdLine = h5repack + " %s %s" % (item, itemOut)
    os.system(cmdLine)
    print"cmdLine"