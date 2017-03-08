
#Convert PSRC matrices to BKR matrices
#Ben Stabler, ben.stabler@rsginc.com, 08/29/16

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
wd = "E:/Projects/Clients/bkr/model/soundcast/inputs/"
seedTripsFileName = "daysim_outputs_seed_trips.h5"
tazSharesFileName = "psrc_to_bkr.txt"

#get taz shares
tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
tazShares = pd.read_table(tazSharesFileName)

def readDaysimTripFields(fileName):
    daysimFile = h5py.File(fileName)
    
    #build pandas data frames
    tripTable = pd.DataFrame()
    tripTable["otaz"] = daysimFile.get("Trip").get("otaz")[:]
    tripTable["dtaz"] = daysimFile.get("Trip").get("dtaz")[:]
    return(tripTable)

def writeDaysimTripFields(fileName, tripFields):
    
    #delete columns first and then write
    daysimFile = h5py.File(fileName, "a")
    for field in tripFields.columns:
        dataset = "Trip/" + field
        del daysimFile[dataset]
        daysimFile.create_dataset(dataset, data = tripFields[field], compression="gzip")
    daysimFile.close()

def pickTaz(table, tazField, zoneWeights):
    psrcZone = table[tazField].tolist()[0]
    print("sampling tazs for PSRC zone " + str(psrcZone))
    bkrZones = zoneWeights[zoneWeights["psrc_zone_id"]==psrcZone]
    if len(bkrZones) == 0:
        print("psrcZone " + str(psrcZone) + " not found so using zone 1 instead - check externals, PNR nodes")
        bkrZones = zoneWeights[zoneWeights["psrc_zone_id"]==1]
        return(bkrZones.sample(len(table), replace=True, weights="percent"))
    else:
        return(bkrZones.sample(len(table), replace=True, weights="percent"))
    
def runDaysimTripsPSRCtoBKRZones(daysimFileName):

    #read daysim trips file
    daysimFileName = os.path.join(wd, daysimFileName)
    trips = readDaysimTripFields(daysimFileName)
    
    #pick a BKR otaz instead
    tripsByPSRCTAZ = trips.groupby("otaz").apply(pickTaz, tazField="otaz", zoneWeights=tazShares)
    tripsByPSRCTAZ = tripsByPSRCTAZ.reset_index(drop=True)
    tripsByPSRCTAZ = tripsByPSRCTAZ.sort_values("psrc_zone_id")

    trips["id"] = range(len(trips))
    trips = trips.sort_values("otaz")
    trips = trips.reset_index(drop=True)
    trips["otaz_new"] = tripsByPSRCTAZ.bkr_zone_id.tolist()
    trips["otaz"] = trips["otaz_new"]
    del trips["otaz_new"]
    trips = trips.sort_values("id")

    #pick a BKR dtaz instead
    tripsByPSRCTAZ = trips.groupby("dtaz").apply(pickTaz, tazField="dtaz", zoneWeights=tazShares)
    tripsByPSRCTAZ = tripsByPSRCTAZ.reset_index(drop=True)
    tripsByPSRCTAZ = tripsByPSRCTAZ.sort_values("psrc_zone_id")

    trips["id"] = range(len(trips))
    trips = trips.sort_values("dtaz")
    trips = trips.reset_index(drop=True)
    trips["dtaz_new"] = tripsByPSRCTAZ.bkr_zone_id.tolist()
    trips["dtaz"] = trips["dtaz_new"]
    del trips["dtaz_new"]
    trips = trips.sort_values("id")

    #write result file by copying input file and writing over arrays
    daysimOutFileName = daysimFileName.split(".")[0]+ "_bkr.csv"
    daysimOutFileName = os.path.join(wd, daysimOutFileName)
    shutil.copy2(daysimFileName, daysimOutFileName)
    writeDaysimTripFields(daysimOutFileName, trips)

if __name__== "__main__":
    runDaysimTripsPSRCtoBKRZones(seedTripsFileName)
