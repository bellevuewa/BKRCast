import os
from input_configuration import *
import shutil

#1/18/2022
# modified to be compatible with python 3
print('resetting....')

def removeDir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
        print(path + ' is removed.')

def removeFile(path):
    if os.path.isfile(path):
        os.remove(path)
        print(path + ' is removed')


dirs_for_removal = ['inputs/4k', 'inputs/supplemental', 'outputs', 'inputs/bikes', 'inputs/accessibility', 'inputs/trucks', 'inputs/Fares', 'inputs/IntraZonals', 'inputs/vdfs', 'inputs/tolls',
                    'inputs/extra_attributes', 'inputs/observed', 'inputs/networks', 'projects', 'banks', 'daysim', 'working']
files_for_removal = ['inputs/parking_gz.csv', 'inputs/lu_type.csv', 'inputs/p_r_nodes.csv', households_persons_file, 'inputs/6to9.h5', 'inputs/9to1530.h5', 'inputs/1530to1830.h5', 'inputs/1830to6.h5', 'inputs/buffered_parcels.txt', 'inputs/buffered_parcels.csv']

print('Please confirm the model folder: ' + project_folder)
enter = input('Press Y to continue')
if enter != 'Y':
    print('Thanks. Please modify project folder in input_configuration.py.')
    exit()


for file in files_for_removal:
    removeFile(os.path.join(project_folder, file))

for dir in dirs_for_removal:
    removeDir(os.path.join(project_folder,dir))

print('Reset.')