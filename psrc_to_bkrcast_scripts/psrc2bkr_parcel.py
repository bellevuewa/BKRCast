#Convert zones in the parcel file
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 12/22/16

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
import csv

# inputs
wd = r"E:\Projects\Clients\bkr\model\bkrcast_tod\inputs\accessibility"
parcel_file = 'parcels_urbansim_psrc.txt'

# correspondence file
parcel_bkr_taz_file = "parcel_updated_bkrtaz.csv"

# get script's directory
script_dir = os.path.dirname(os.path.realpath(__file__))
print(script_dir)

def runPSRCtoBKRZones():
    #read parcel file
    parcel_file_path = os.path.join(wd, parcel_file)
    parcels_psrc = pd.read_csv(parcel_file_path, sep = " ")
    parcels_fields = list(parcels_psrc.columns)

    #read parcel to bkr taz correspondence
    parcel_bkr_taz_file_path = os.path.join(script_dir, parcel_bkr_taz_file)
    parcel_bkr_taz = pd.read_csv(parcel_bkr_taz_file_path)

    #merge bkr taz to parcel file
    parcels_bkr = pd.merge(parcels_psrc, parcel_bkr_taz, left_on = 'PARCELID', right_on = 'parcelid')
    parcels_bkr['TAZ_P'] = parcels_bkr['TAZNUM'].astype(np.int32)
    parcels_bkr = parcels_bkr[parcels_fields]
    parcels_bkr = parcels_bkr.sort_values(by = ['PARCELID'], ascending=[True])

    if len(parcels_bkr) != len(parcels_psrc):
        print('ERROR: some parcels do not have a bkr taz assigned')
    else:
        #write out the updated parcel file
        parcel_file_out = parcel_file.split(".")[0]+ "_bkr.txt"
        parcel_file_out_path = os.path.join(wd, parcel_file_out)
        parcels_bkr.to_csv(parcel_file_out_path, sep = ' ', index = False)

if __name__== "__main__":
    print('started ...')
    runPSRCtoBKRZones()
    print('finished!')

