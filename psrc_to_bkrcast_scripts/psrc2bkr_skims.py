
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

# 10/25/2021
# modified to be compatible with python 3

import os, shutil
import pandas as pd
import h5py
import numpy as np

#inputs
wd = r"E:/Projects/Clients/bkr/model/soundcast/inputs/"
tods = ['5to6', '6to7', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20', '20to5' ]
num_bkr_zones = 1530

def writeSkimTables(fileName, skims, tod):
    
    #delete columns first and then write
    bkrskim = h5py.File(fileName, "a")
    for field in bkrskim.columns:
        dataset = "Skims/" + field
        del bkrskim[dataset]
        bkrskim.create_dataset(dataset, data = bkrskim[field],compression="gzip")

    bkrskim.close()

def runSkimAdjustment():

    for tod in tods:
        print("processing: " + tod)
        #get matrix names
        psrcFileName = os.path.join(wd, tod + ".h5")
        matFile = h5py.File(wd + tod + ".h5")
        matrices = map(lambda x: x[0], matFile.get("Skims").items())
        
        #write out
        bkrMatFile = os.path.join(wd, tod + "_bkr.h5")
        shutil.copy2(psrcFileName, bkrMatFile)
        bkrskim = h5py.File(bkrMatFile, "a")

        #convert to pandas table of matrices
        for matrix in matrices:
            matData = matFile.get("Skims").get(matrix)[:]
            if matrix == "indices":
                matData = matData[:][:,range(num_bkr_zones)] #crop to bkr zone
            else:
                matData = matData[range(num_bkr_zones),:][:,range(num_bkr_zones)] #crop to bkr zone

            dataset = "Skims/" + matrix
            del bkrskim[dataset]
            bkrskim.create_dataset(dataset, data = matData,compression="gzip")
       
        bkrskim.close()

if __name__== "__main__":
    runSkimAdjustment()
