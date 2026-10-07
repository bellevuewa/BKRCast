#Copyright [2014] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import pandas as pd
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import h5toDF
import math
import argparse
import tempfile
from input_configuration import *
from accessibility.accessibility_configuration import *

# 1/18/2022
# upgrade to python 3

def get_percent_rmse(urbansim_file, daysim_file, guide_file):
    urbansim_data = pd.read_csv(urbansim_file, sep = ' ') #Read in UrbanSim data
    jobs_by_taz = urbansim_data[['taz_p', 'emptot_p']].groupby('taz_p').sum() #Get number of jobs by TAZ
    daysim_data = h5toDF.convert_single(daysim_file, guide_file, 'Daysim Outputs', 'Person') #Read in person file from DaySim data
    workers_by_taz = daysim_data['Person'][['pwtaz', 'psexpfac']].query('pwtaz > 0').groupby('pwtaz').sum() #Get number of workers by TAZ
    workers_jobs_by_taz = pd.merge(jobs_by_taz, workers_by_taz, left_index = True, right_index = True) #Merge them
    workers_jobs_by_taz['DaySim'] = workers_jobs_by_taz['psexpfac'] #Rename columns...
    workers_jobs_by_taz['UrbanSim'] = workers_jobs_by_taz['emptot_p']
    workers_jobs_by_taz['Difference'] = workers_jobs_by_taz['DaySim'] - workers_jobs_by_taz['UrbanSim']
    workers_jobs_by_taz['Squared Difference'] = workers_jobs_by_taz['Difference']**2
    rms_error = math.sqrt(workers_jobs_by_taz['Squared Difference'].mean())
    percent_rmse = rms_error / workers_jobs_by_taz['DaySim'].mean() * 100
    print('%RMSE: ' + str(round(percent_rmse, 2)) + '%')
    workers_jobs_by_taz.to_csv(os.path.join(report_lu_output_location, 'workers_jobs.csv'), sep = ',', index = True) #Save the results to a CSV file
    return percent_rmse

def convergence_check(rmse_list, convergence_criterion, iteration): #Function not presently in use
    if iteration == 1:
        convergence = False
        return convergence #No comparison on the first iteration
    if abs(rmse_list[iteration - 1] - rmse_list[iteration - 2]) < convergence_criterion:
        convergence = True
    else:
        convergence = False
    return convergence

def write_rmse(output_path, value, append=False):
    """Publish a complete RMSE file without exposing a partial write."""
    if not math.isfinite(value) or value < 0:
        raise ValueError('RMSE must be finite and nonnegative')
    history = ''
    if append and os.path.isfile(output_path):
        with open(output_path, 'r') as existing:
            history = existing.read()
        if history and not history.endswith('\n'):
            history += '\n'
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(os.path.abspath(output_path)),
                                         delete=False) as result:
            temporary_path = result.name
            result.write(history + str(value) + '\n')
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.remove(temporary_path)


def main():
    parser = argparse.ArgumentParser(description='Calculate shadow-pricing RMSE')
    parser.add_argument('--output', help='Write the current RMSE to this file')
    args = parser.parse_args()
    current_percent_rmse = get_percent_rmse(output_parcels, h5_results_file, guidefile)
    write_rmse(args.output or 'inputs/shadow_rmse.txt', current_percent_rmse,
               append=args.output is None)

if __name__ == "__main__":
    main()
