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

import os, shutil
import pandas as pd
import h5py
import numpy as np
import csv

# inputs
wd = r"Z:\Modeling Group\BKRCast\2035Parcel_fromPSRC\LUV2_2035SCinputs\LUV2_Refined_2035_SCInputs"
parcel_file = 'parcels.dat'

# correspondence file
parcel_bkr_taz_file = "parcel_BKRTAZ.csv"

# get script's directory
script_dir = os.path.dirname(os.path.realpath(__file__))
print(script_dir)

def runPSRCtoBKRZones():
    #read parcel file
    parcel_file_path = os.path.join(wd, parcel_file)
    parcels_psrc = pd.read_csv(parcel_file_path, sep = " ")
    parcels_fields = list(parcels_psrc.columns)

    #read parcel to bkr taz correspondence
    parcel_bkr_taz_file_path = os.path.join(wd, parcel_bkr_taz_file)
    parcel_bkr_taz = pd.read_csv(parcel_bkr_taz_file_path)

    # all parcels in both parcels_psrc and correspondence
    #df_all_parcels = pd.concat([parcels_psrc[['PARCELID']], parcel_bkr_taz[['PARCELID']]]) 
    #print "all parcels {0:.0f}".format(len(df_all_parcels))
    #df_all_parcels.drop_duplicates(keep = 'first', inplace = True)
    #print "all parcels {0:.0f}".format(len(df_all_parcels))
    #df_all_parcels = df_all_parcels.drop(parcel_bkr_taz['PARCELID'])
    #print "parcle_BKR_taz {0:.0f}".format(len(parcel_bkr_taz))
    #print 'parcels_psrc {0:.0f}'.format(len(parcels_psrc))
    #print "all parcels {0:.0f}".format(len(df_all_parcels))
    
    #merge bkr taz to parcel file
    parcels_bkr = pd.merge(parcels_psrc, parcel_bkr_taz, left_on = 'PARCELID', right_on = 'PARCELID')
    parcels_bkr['PSRCTAZ'] = parcels_bkr['TAZ_P']
    parcels_fields.append('PSRCTAZ')
    parcels_bkr['TAZ_P'] = parcels_bkr['TAZNUM'].astype(np.int32)
    parcels_bkr = parcels_bkr[parcels_fields]
    parcels_bkr = parcels_bkr.sort_values(by = ['PARCELID'], ascending=[True])

    if len(parcels_bkr) <> len(parcels_psrc):
        print('ERROR: some parcels do not have a bkr taz assigned')
        print "parcle_BKR {0:.0f}".format(len(parcels_bkr))
        print 'parcels_psrc {0:.0f}'.format(len(parcels_psrc))
   
    #write out the updated parcel file
    parcel_file_out = parcel_file.split(".")[0]+ "_bkr.txt"
    parcel_file_out_path = os.path.join(wd, parcel_file_out)
    parcels_bkr.to_csv(parcel_file_out_path, sep = ' ', index = False)

if __name__== "__main__":
    print('started ...')
    runPSRCtoBKRZones()
    print('finished!')

