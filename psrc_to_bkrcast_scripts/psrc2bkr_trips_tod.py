
#Convert PSRC trip matrices of 12 time periods into BKR matrices of 4 time periods
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 10/13/16

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

# 10/25/2021
# modified to be compatible with python 3

import os, shutil
import pandas as pd
import h5py
import numpy as np

def runMatrixAdjustment():
   # before running this script
   # appropriate 4 skims out of 12 tod skims are renamed into 4 tods
   # then run this script on those 4 renamed skims, to rename the group within with correct tod name

    wd = r"E:\Projects\Clients\bkr\model\bkrcast_tod\inputs"
    #tods = ['5to6', '6to7', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20', '20to5' ]
    tods = ['5to9', '9to15', '15to18', '18to5']
    #tods = ['5to9']
    for tod in tods:
        print("updating: " + tod)
        #get matrix names
        infile = os.path.join(wd,tod+".h5")
        matFile = h5py.File(infile, "a")
        groups = matFile.keys()
        matrices = map(lambda x: x[0], matFile.get("Skims").items())

        #delete the existing group with tod name
        if groups[0] == 'Skims':
            del matFile[groups[1]]
        else:
            del matFile[groups[0]]

        # create a group with bkr tod name
        temp = matFile.create_group(tod)

        matFile.close()

if __name__== "__main__":
    runMatrixAdjustment()
