
#Convert PSRC skims to BKR skims
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 09/20/16

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os, shutil
import pandas as pd
import h5py
import numpy as np

def runSkimAdjustment():

    parcelFileName = "buffered_parcels.dat" #psrc_zone_id	bkr_zone_id	percent 1.0=100%
    parcelFileName = os.path.join("E:/Projects/Clients/bkr/model/bkrcast/inputs/", parcelFileName)
    parcels = pd.read_table(parcelFileName, sep = " ")

    #get unique tazs
    tazs = parcels.taz_p.unique()

    #get matrix names
    num_bkr_zones = 1530 #user input

    wd = r"E:/Projects/Clients/bkr/model/bkrcast/inputs/"
    #tods = ['5to6', '6to7', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20', '20to5' ]
    tod = '5to6'

    print "processing: " + tod
    #get matrix names
    bkrFileName = os.path.join(r"E:/Projects/Clients/bkr/model/bkrcast/inputs/2014/seed_skims/", tod + ".h5")
    matFile = h5py.File(bkrFileName)
    matData = matFile.get("Skims").get("h2nt2t")[:]

    for taz in tazs:
        #print taz
        value_col = matData[:][taz] # to taz
        value_row = matData[taz][:] # from taz

        if (value_col < 60000).sum() < 2:
            print taz

        if (value_row < 60000).sum() < 2:
            print taz


if __name__== "__main__":
    runSkimAdjustment()
