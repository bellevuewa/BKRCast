#Convert district correspondence in the TAZ Index file
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 09/23/16

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
wd = r"E:/Projects/Clients/bkr/model/soundcast/inputs"
zoneFileName = "TAZIndex.txt"
tazSharesFileName = "psrc_to_bkr.txt"

# read file
tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
tazShares = pd.read_table(tazSharesFileName)
    
def runDistrictsPSRCtoBKRZones():

    # read psrc zone group file
    zoneFile = os.path.join(wd, zoneFileName)
    zoneDistricts = pd.read_table(zoneFile)
    colnames = list(zoneDistricts.columns.values)
    zoneDistricts = zoneDistricts[["Zone_id","External"]]

    # merge psrc 2 bkr correspondence with percent
    tazGroups = pd.merge(tazShares,zoneDistricts, left_on = "psrc_zone_id", right_on = "Zone_id")
    tazGroups["key"] = tazGroups["bkr_zone_id"].astype(str) + "_" + tazGroups["External"].astype(str)

    # group by unique pair of bkr zone and group
    tazGroups_grouped = tazGroups.groupby(["key"])

    # calculate sum of percent by unique pair
    tazGroups_sum = tazGroups_grouped['percent'].sum()
    tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

    temp = pd.merge(tazGroups_sum, tazGroups[["key","bkr_zone_id","External"]], on = ["key"], how = "inner")

    #if one bkr in multiple groups, assign to the one with max percent value
    tazGroups_bkr = temp.loc[temp.groupby(["bkr_zone_id"])['percent'].idxmax()]

    #initialize taz index file
    tazdata_bkr = pd.DataFrame(index = range(1,1531), columns = ["Zone_id", "zone_ordinal", "Dest_eligible"])
    tazdata_bkr = tazdata_bkr.fillna(0)
    dummy_zones = [173,175,265, 411] #zone with no parcel files
    dummy_zones.extend(range(659,680+1)+range(919,930+1) + range(1216,1230+1)) #dummy zones

    for i in range(1,1531):
        tazdata_bkr["Zone_id"][i] = i
        tazdata_bkr["zone_ordinal"][i] = i
        tazdata_bkr["Dest_eligible"][i] = 1
        if (i in dummy_zones) or i>1355:
            tazdata_bkr["Dest_eligible"][i] = 0

    #attach districts information in external columns
    temp = pd.merge(tazdata_bkr, tazGroups_bkr[["bkr_zone_id", "External"]], left_on = "Zone_id", right_on = "bkr_zone_id", how = "left")
    tazdata_bkr = temp[["Zone_id", "zone_ordinal", "Dest_eligible", "External"]].fillna(0)

    #write
    outfile = zoneFileName.split(".")[0]+ "_bkr.txt"
    tazdata_bkr.to_csv(os.path.join(wd,outfile), sep = "\t" , header = True, index = False)

if __name__== "__main__":
    runDistrictsPSRCtoBKRZones()

