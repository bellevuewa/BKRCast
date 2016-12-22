#Convert PSRC observed data to BKR
#Nagendra Dhakar, nagendra.dhakar@rsginc.com, 12/16/16

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

screenline_correspondence = r'E:\Projects\Clients\bkr\tasks\screenlines\links_screenline_intersect.csv'
observed_data = r'E:\Projects\Clients\bkr\model\bkrcast_tod\inputs\observed\observed_daily_counts.csv'

def runPSRCtoBKRcounts():
    #readbkr links to screenline id
    screenlines_bkr = pd.read_csv(screenline_correspondence)
    #read psrc observed daily counts
    counts_psrc = pd.read_csv(observed_data)
    #find counts for each unique screenlin - assumption: counts are by screenlines
    screenline_counts = counts_psrc[['ScreenLineID', 'Year_2014']].groupby('ScreenLineID').first().reset_index()
    #assign counts to bkr links using screenline ids
    counts_bkr = pd.merge(screenlines_bkr, screenline_counts, left_on = 'ScreenLine', right_on = 'ScreenLineID')
    #rename columns and output in the same format as psrc observed counts file
    counts_bkr = counts_bkr.rename(columns = {'INODE':'NewINode', 'JNODE':'NewJNode'})
    counts_bkr = counts_bkr[['NewINode', 'NewJNode', 'ScreenLineID', 'Year_2014']]
    counts_bkr.to_csv(r'E:\Projects\Clients\bkr\model\bkrcast_tod\inputs\observed\observed_daily_counts_bkr.csv', index = False)

if __name__== "__main__":
    runPSRCtoBKRcounts()