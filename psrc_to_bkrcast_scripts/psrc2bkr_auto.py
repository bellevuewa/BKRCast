
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

def expandTazShares(table):
    
    print("expand PSRC to BKR zone crosswalk to full OD percents table")

    #replicate into expanded OD table
    od_table = pd.DataFrame()
    od_table["o"] = np.repeat(table["psrc_zone_id"].tolist(),len(table))
    od_table["bkr_o"] = np.repeat(table["bkr_zone_id"].tolist(),len(table))
    od_table["percent_o"] = np.repeat(table["percent"].tolist(),len(table))
    od_table["d"] = np.tile(table["psrc_zone_id"].tolist(),len(table))
    od_table["bkr_d"] = np.tile(table["bkr_zone_id"].tolist(),len(table))
    od_table["percent_d"] = np.tile(table["percent"].tolist(),len(table))
    
    #calculat the share by OD group
    od_table["od"] = od_table["o"] * 10000 + od_table["d"]
    od_table["percent"] = od_table["percent_o"] * od_table["percent_d"]
    #od_table[(od_table.o==1) & (od_table.d==1)] #for debugging
    #od_table[(od_table.o==1) & (od_table.d==4)] #for debugging
    return(od_table)

def runMatrixAdjustment():

    #get taz shares
    tazSharesFileName = "psrc_to_bkr.txt" #psrc_zone_id	bkr_zone_id	percent 1.0=100%
    tazSharesFileName = os.path.join(os.getcwd(), tazSharesFileName)
    tazShares = pd.read_table(tazSharesFileName)
    odShares = expandTazShares(tazShares)

    #get matrix names
    num_bkr_zones = 1530 #user input

    wd = "E:/Projects/Clients/bkr/model/soundcast/inputs/4k/"
    matFile = h5py.File(wd + "auto.h5")
    todFolders = map(lambda x: x[0], matFile.items())
    for tod in todFolders:
        matrices = map(lambda x: x[0], matFile.get(tod).items())

        #create pandas OD table for operations
        od_table = pd.DataFrame()
        psrc_zones = tazShares.psrc_zone_id.unique()

        od_table["o"] = np.repeat(psrc_zones,len(psrc_zones))
        od_table["d"] = np.tile(psrc_zones,len(psrc_zones))

        #convert to pandas table of matrices
        for matrix in matrices:
            matData = matFile.get(tod).get(matrix)[:]
            matData = matData[range(len(psrc_zones)),:][:,range(len(psrc_zones))] #crop to actual psrc zone
            print("PSRC " + tod + " " + matrix + " sum " + str(matData.sum()))
            od_table[matrix] = matData.flatten() #add as column

        #join BKR zone shares
        print("join BKR zone shares to matrices")
        od_table = pd.merge(od_table, odShares, on=["o","d"], how = "inner")
                
        #apply percents to each matrix and sum by OD group
        print("apply percents to each matrix and sum by OD group")
        for matrix in matrices:
            od_table[matrix] = od_table[matrix] * od_table["percent"]

        od_table["od"] = od_table["bkr_o"] * 10000 + od_table["bkr_d"]
        od_table_grouped = od_table.groupby(["od"])
        od_table_sums = od_table_grouped.sum()
        od_table_sums["bkr_od"] = od_table_sums.index

        #convert back to matrices and write out
        bkrMatFile = h5py.File(wd + "auto_bkr.h5", "a") #append to file since looping by tod
        
        todFolder = bkrMatFile.create_group(tod) #crate tod folder
        for matrix in matrices:
            print("BKR " + tod + " matrix " + " sum " + str(od_table_sums[matrix].sum()))

            od_table_bkr = pd.DataFrame()
            od_table_bkr["bkr_o"] = np.repeat(range(1,num_bkr_zones+1), num_bkr_zones)
            od_table_bkr["bkr_d"] = np.tile(range(1,num_bkr_zones+1), num_bkr_zones)
            od_table_bkr["bkr_od"] = od_table_bkr["bkr_o"] * 10000 + od_table_bkr["bkr_d"]

            #merge bkr od pair data. keep all OD pairs in od_table_bkr, using how = "left"
            od_table_bkr = pd.merge(od_table_bkr, od_table_sums[["bkr_od", matrix]], on=["bkr_od"], how = "left")
            od_table_bkr.fillna(0, inplace = True)
            bkrMatData = np.array(od_table_bkr[matrix])

            #bkrMatData = np.array(od_table_sums[matrix])
            bkrMatData.shape = (num_bkr_zones, num_bkr_zones)
            todFolder.create_dataset(matrix, data = bkrMatData, compression="gzip")
        
        #close file
        bkrMatFile.close()

if __name__== "__main__":
    runMatrixAdjustment()
