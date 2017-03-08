
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

#inputs
wd = r"E:/Projects/Clients/bkr/model/bkrcast_tod/inputs/"
parcelFileName = "buffered_parcels.dat"
popsynFileName = 'hh_and_persons.h5'
zone_district_file = 'TAZ_District_CrossWalk.csv'
tod = '9to1530'
num_bkr_zones = 1530

def runSkimCheck():
    
    parcelFileName = os.path.join(wd, parcelFileName)
    parcels = pd.read_table(parcelFileName, sep = " ")

    #get unique tazs
    tazs = parcels.taz_p.unique()

    #get matrix names
    num_bkr_zones = 1530 #user input

    print "processing: " + tod
    
    #get matrix names
    bkrFileName = os.path.join(wd, tod + ".h5")
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

def readSynPopTables(fileName):
    popsyn = h5py.File(fileName)
    hhFields = map(lambda x: x[0], popsyn.get("Household").items())
    perFields = map(lambda x: x[0], popsyn.get("Person").items())
    
    #build pandas data frames
    hhFields.remove('incomeconverted') #not a column attribute
    hhTable = pd.DataFrame()
    for hhField in hhFields:
        hhTable[hhField] = popsyn.get("Household").get(hhField)[:]

    perTable = pd.DataFrame()
    for perField in perFields:
        perTable[perField] = popsyn.get("Person").get(perField)[:]

    return(hhTable, perTable)

def runPopSynCheck():
    
    popsynFileName = os.path.join(wd, popsynFileName)
    households, persons = readSynPopTables(popsynFileName)
    hh_tazs = households['hhtaz'].unique()

    zone_district = pd.read_csv(os.path.join(wd,zone_district_file))
    districts_tazs = zone_district['zone_id'].unique()

    for hh_taz in hh_tazs:
        found=0
        for districts_taz in districts_tazs:
            if hh_taz == districts_taz:
                found =1
                print('found: ' + str(hh_taz))
                break
        if found==0:
            print('hh taz not found: ' + str(hh_taz))

if __name__== "__main__":
    runSkimCheck()
    runPopSynCheck()
