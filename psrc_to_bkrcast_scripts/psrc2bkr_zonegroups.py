#Convert PSRC zones to BKR zones (one to one relation - take the max area)
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 09/14/16

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.


# NOTE:
# Added special generator data manually
# copy pasted thecorresponding zone data in soundacast

import os, shutil
import pandas as pd
import h5py
import numpy as np
import csv

#inputs
transit_dir = r'D:\Soundcast\SC2014\soundcast-2-1\inputs\2014\networks\fares'
puma_dir = r'D:\Soundcast\SC2014\soundcast-2-1\inputs\scenario\supplemental\generation\ensembles'
#transitFileName = "transit_fare_zones.grt"
transitFileName = "parking_gz.txt"
pumaFileName = "puma00.ens"
tazSharesFileName = "psrc_to_bkr.txt"

# read file
tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
tazShares = pd.read_table(tazSharesFileName)
    
def runGroupsPSRCtoBKRZones(wd, zoneGroupsFileName, header_rows):
    print('processing: ' + zoneGroupsFileName )

    # read psrc zone group file
    zoneGroupsFileName = os.path.join(wd, zoneGroupsFileName)
    print zoneGroupsFileName
    zoneGroups = pd.read_table(zoneGroupsFileName, delimiter = " ", skiprows = header_rows, names = ["t","groups","zone"])
    print(zoneGroups.head())

    # merge psrc 2 bkr correspondence with percent
    tazGroups = pd.merge(tazShares,zoneGroups, left_on = "psrc_zone_id", right_on = "zone")
    tazGroups["key"] = tazGroups["bkr_zone_id"].astype(str) + "_" + tazGroups["groups"]

    # group by unique pair of bkr zone and group
    tazGroups_grouped = tazGroups.groupby(["key"])

    # calculate sum of percent by unique pair
    tazGroups_sum = tazGroups_grouped['percent'].sum()
    tazGroups_sum = tazGroups_sum.reset_index() # makes object a data frame by setting the current index to a column

    temp = pd.merge(tazGroups_sum, tazGroups[["key","bkr_zone_id","groups", "t"]], on = ["key"], how = "inner")

    #if one bkr in multiple groups, assign to the one with max percent value
    tazGroups_bkr = temp.loc[temp.groupby(["bkr_zone_id"])['percent'].idxmax()]

    extension = zoneGroupsFileName.split(".")[1]
    print extension
    outfile = os.path.join(wd,zoneGroupsFileName.split(".")[0] + "_bkr." + extension)
    print outfile

    if (header_rows > 0):
        print('here')
        header = pd.read_table(zoneGroupsFileName, delimiter = "#", header = None, nrows = header_rows)
        header.to_csv(outfile, sep = " ", header = False, index = False, quoting=csv.QUOTE_NONE, escapechar = " ")

    with open(outfile, 'a') as file:
        tazGroups_bkr[["t","groups","bkr_zone_id"]].to_csv(file, sep = " ", header = False, index = False)

if __name__== "__main__":
    #runGroupsPSRCtoBKRZones(transit_dir, transitFileName, header_rows = 10)
    runGroupsPSRCtoBKRZones(transit_dir, transitFileName, header_rows = 3)
    runGroupsPSRCtoBKRZones(puma_dir, pumaFileName, header_rows = 1)

