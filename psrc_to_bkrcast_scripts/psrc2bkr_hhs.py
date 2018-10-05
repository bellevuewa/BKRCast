
#Convert PSRC matrices to BKR matrices
#Ben Stabler, ben.stabler@rsginc.com, 08/29/16
#updated for 2014 popsyn file

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

#input settings
wd = r"Z:\Modeling Group\BKRCast\2035Parcel_fromPSRC\LUV2_2035SCinputs\LUV2_Refined_2035_SCInputs"
popsynFileName = "hh_and_persons.h5"
parcel_dir = r"Z:\Modeling Group\BKRCast\2035Parcel_fromPSRC\LUV2_2035SCinputs\LUV2_Refined_2035_SCInputs"
parcelFileName = "parcels_urbansim.txt"

def readSynPopTables(fileName):
    print('read synpop file')
    popsyn = h5py.File(fileName)
    hhFields = map(lambda x: x[0], popsyn.get("Household").items())
    perFields = map(lambda x: x[0], popsyn.get("Person").items())
    
    #build pandas data frames
    #hhFields.remove('incomeconverted') #not a column attribute
    hhTable = pd.DataFrame()
    for hhField in hhFields:
        hhTable[hhField] = popsyn.get("Household").get(hhField)[:]

    perTable = pd.DataFrame()
    for perField in perFields:
        perTable[perField] = popsyn.get("Person").get(perField)[:]

    return(hhTable, perTable)

def writeSynPopTables(fileName, households, persons):
    print('write synpop file')
    #delete columns first and then write
    popsyn = h5py.File(fileName, "a")
    for hhField in households.columns:
        dataset = "Household/" + hhField
        print(dataset)
        del popsyn[dataset]
        popsyn.create_dataset(dataset, data = households[hhField],compression="gzip")
    for perField in persons.columns:
        dataset = "Person/" + perField
        print(dataset)
        del popsyn[dataset]
        popsyn.create_dataset(dataset, data = persons[perField], compression="gzip")
    popsyn.close()
    
def runSynPopPSRCtoBKRZones():

    #read popsyn file
    popsynFile = os.path.join(wd, popsynFileName)
    households, persons = readSynPopTables(popsynFile)

    #get parcle-taz correspondence
    parcelFile = os.path.join(parcel_dir, parcelFileName)
    parcels = pd.read_table(parcelFile, sep=" ")
    parcels = parcels[["PARCELID","TAZ_P"]]

    #merge to households
    print('assign bkr tazs')
    households = pd.merge(households, parcels, left_on = "hhparcel", right_on = "PARCELID")
    
    households["hhtaz"] = households["TAZ_P"].astype(np.int32)
    households.drop(["PARCELID","TAZ_P"], inplace=True, axis=1)
    
    households = households.sort_values("hhno")

    # set person fields to default - pwpcl, pwtaz, pspcl, pstaz, pwautime, pwaudist, psautime, psaudist
    #persons["pwpcl"] = -1
    #persons["pwtaz"] = -1
    #persons["pspcl"] = -1
    #persons["pstaz"] = -1
    #persons["pwautime"] = -1
    #persons["pwaudist"] = -1
    #persons["psautime"] = -1
    #persons["psaudist"] = -1
    #persons[["pwpcl","pwtaz","pspcl","pstaz","pwautime","pwaudist","psautime","psaudist"]] = persons[["pwpcl","pwtaz","pspcl","pstaz","pwautime","pwaudist","psautime","psaudist"]].astype(np.int32)

    #write result file by copying input file and writing over arrays
    popsynOutFileName = popsynFileName.split(".")[0]+ "_bkr.h5"
    popsynOutFileName = os.path.join(wd, popsynOutFileName)
    shutil.copy2(popsynFile, popsynOutFileName)
    writeSynPopTables(popsynOutFileName, households, persons)

if __name__== "__main__":
    runSynPopPSRCtoBKRZones()
