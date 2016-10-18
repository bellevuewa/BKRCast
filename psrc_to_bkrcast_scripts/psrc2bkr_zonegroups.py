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

import os, shutil
import pandas as pd
import h5py
import numpy as np


def runGroupsPSRCtoBKRZones():

    # read file
    tazSharesFileName = "psrc_to_bkr.txt" #psrc_zone_id	bkr_zone_id	percent 1.0=100%
    tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
    tazShares = pd.read_table(tazSharesFileName)

    # read zone groups file (transit or puma)
    #zoneGroupsFileName = "transit_fare_zones.grt"
    #zoneGroupsFileName = "puma00.ens"
    zoneGroupsFileName = "districts19_ga.ens"

    #path = r'E:\Projects\Clients\bkr\model\bkrcast\inputs\Fares'
    #transitZoneGroupsFileName = os.path.join(path, zoneGroupsFileName)

    # read psrc zone group file
    zoneGroupsFileName = os.path.join(os.getcwd(), zoneGroupsFileName)
    zoneGroups = pd.read_table(zoneGroupsFileName, delimiter = " ")

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

    outfile = zoneGroupsFileName.split(".")[0]
    tazGroups_bkr[["t","groups","bkr_zone_id"]].to_csv(outfile + "_bkr.txt", index = False)


if __name__== "__main__":
    runGroupsPSRCtoBKRZones()

