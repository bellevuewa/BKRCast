#Convert calibration summary files from PSRC to BKR: TAZ_TAD_County.csv and FAZ_TAZ.xlsx
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 09/30/16

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

zonefiles = ["TAZ_TAD_County.csv","FAZ_TAZ.xlsx"]

def runDistrictsPSRCtoBKRZones():

    # read file
    tazSharesFileName = "psrc_to_bkr.txt" #psrc_zone_id	bkr_zone_id	percent 1.0=100%
    tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
    tazShares = pd.read_table(tazSharesFileName)

    # read zone districts file
    wd = r"E:\Projects\Clients\bkr\model\bkrcast\scripts\summarize\inputs\calibration"
    zoneFileName = "TAZ_TAD_County.csv"

    # read psrc zone group file
    zoneFileName = os.path.join(wd, zoneFileName)
    zoneDistricts = pd.read_csv(zoneFileName)
    colnames = list(zoneDistricts.columns.values)
    #zoneDistricts = zoneDistricts[["TAZ","District","New DistrictName"]]

    # merge psrc 2 bkr correspondence with percent
    tazGroups = pd.merge(tazShares,zoneDistricts, left_on = "psrc_zone_id", right_on = "TAZ")
    tazGroups["key"] = tazGroups["bkr_zone_id"].astype(str) + "_" + tazGroups["District"].astype(str)

    # group by unique pair of bkr zone and group
    tazGroups_grouped = tazGroups.groupby(["key"])

    # calculate sum of percent by unique pair
    tazGroups_sum = tazGroups_grouped['percent'].sum()
    tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

    temp = pd.merge(tazGroups_sum, tazGroups[["key","bkr_zone_id","TAD", "OldDistric", "County","District","New DistrictName"]], on = ["key"], how = "inner")

    #if one bkr in multiple groups, assign to the one with max percent value
    tazGroups_bkr = temp.loc[temp.groupby(["bkr_zone_id"])['percent'].idxmax()]

    #write
    outfile = zoneFileName.split(".")[0]+ "_bkr.csv"
    tazdata_bkr = tazGroups_bkr[["bkr_zone_id", "TAD", "OldDistric", "County","District","New DistrictName"]]
    tazdata_bkr = tazdata_bkr.rename(columns = {"bkr_zone_id":"TAZ"})
    tazdata_bkr.to_csv(outfile, sep = "," , header = True, index = False)

def runDistrictsPSRCtoBKRZones():

    # read file
    tazSharesFileName = "psrc_to_bkr.txt" #psrc_zone_id	bkr_zone_id	percent 1.0=100%
    tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
    tazShares = pd.read_table(tazSharesFileName)

    # read zone districts file
    wd = r"E:\Projects\Clients\bkr\model\bkrcast\scripts\summarize\inputs\calibration"
    zoneFileName = "FAZ_TAZ.xlsx"

    # read psrc zone group file
    zoneFileName = os.path.join(wd, zoneFileName)
    zoneDistricts = pd.read_excel(zoneFileName)
    zoneDistricts = zoneDistricts[["zone_id","large_area_id","large_area_name"]]

    # merge psrc 2 bkr correspondence with percent
    tazGroups = pd.merge(tazShares,zoneDistricts, left_on = "psrc_zone_id", right_on = "zone_id")
    tazGroups["key"] = tazGroups["bkr_zone_id"].astype(str) + "_" + tazGroups["large_area_id"].astype(str)

    # group by unique pair of bkr zone and group
    tazGroups_grouped = tazGroups.groupby(["key"])

    # calculate sum of percent by unique pair
    tazGroups_sum = tazGroups_grouped['percent'].sum()
    tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

    temp = pd.merge(tazGroups_sum, tazGroups[["key","bkr_zone_id","zone_id","large_area_id","large_area_name"]], on = ["key"], how = "inner")

    #if one bkr in multiple groups, assign to the one with max percent value
    tazGroups_bkr = temp.loc[temp.groupby(["bkr_zone_id"])['percent'].idxmax()]

    #write
    outfile = zoneFileName.split(".")[0]+ "_bkr.xlsx"
    tazdata_bkr = tazGroups_bkr[["bkr_zone_id","large_area_id","large_area_name"]]
    tazdata_bkr = tazdata_bkr.rename(columns = {"bkr_zone_id":"zone_id"})
    tazdata_bkr.to_excel(outfile, 'taz4k_to_fazlarge_area', index=False)
    writer.save()

if __name__== "__main__":
    runDistrictsPSRCtoBKRZones()

