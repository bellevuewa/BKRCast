from enum import auto
import pandas as pd
import os, sys
import datetime
import getopt
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
import input_configuration as prj
from emme_configuration import *
from data_wrangling import *

# 10/25/2021
# modified to be compatible with python 3

# 5/5/2023
# calculate VMT/VHT/VHD by link speed in 5MPH interval.

# file will be exported to default output folder.
outputfilename = 'system_metrics.txt'

def calculate_system_metrics(links_df, tod, groupby):
    links_df[tod+'_VMT'] = links_df['length'] * links_df['auto_volume']
    links_df[tod+'_VHT'] = (links_df['auto_time'] / 60) * links_df['auto_volume']
    links_df[tod+'_VHD'] = links_df['auto_volume'] * (links_df['auto_time'] / 60 - links_df['length'] / links_df['data2'])

    ret = links_df[[groupby, tod+'_VMT', tod+'_VHT', tod+'_VHD']].groupby(groupby).sum()

    return ret

def calculate_for_GHG(links_df, tod, attr):
    links_df['speedau'] = links_df['length'] / (links_df['auto_time'] / 60.0)
    links_df['speed_bins'] = pd.cut(links_df['speedau'], bins = prj.auto_speed_bins)
    links_df[tod+'_VMT'] = links_df['length'] * links_df['auto_volume']
    links_df[tod+'_VHT'] = (links_df['auto_time'] / 60) * links_df['auto_volume']
    links_df[tod+'_VHD'] = links_df['auto_volume'] * (links_df['auto_time'] / 60 - links_df['length'] / links_df['data2'])
    ret = links_df[['speed_bins', attr, tod+'_VMT',tod+'_VHT', tod+'_VHD']].groupby([attr, 'speed_bins']).sum()
    return ret
    


def help():
    print(' This script is used to calculate VMT, VHT and VHD in different time of day and then aggregated to daily metrics.')
    print(' The metrics are aggregated to subareas flagged by an extra link attribute. The default attribute is @bkrlink.')
    print(' User can define own attribute to tag links. ')
    print(' In addition, VMT, VHT and VHD are also aggregated by link speed in 5mph interval, to match emission factors from Move.')
    print(' The output file is saved in outputs/network/system_metrics.txt.')
    print()
    print(' python calculate_daily_VMT.py -h -t extra_link_attribute_tag')
    print('    -h: help')
    print('    -t: customized extra link attribute for link tagging')

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 't:')
    except getopt.GetoptError:
        help()
        sys.exit(2)
    
    attr = '@bkrlink'
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-t':
            attr = arg
    
    print(network_summary_project)
    my_project = EmmeProject(network_summary_project)

    metrics = pd.DataFrame()
    GHG_metrics_list = []
    for key, value in sound_cast_net_dict.items():
        my_project.change_active_database(key)
        print(f'loading {value} ...')
        if value == 'pm':
            extra_attr = my_project.current_scenario.extra_attribute(attr)
            if extra_attr != None:
                groupby_description = extra_attr.description
            else:
                groupby_description = ''

        links_df = my_project.emme_links_to_df()
        print(f'calculating vmt, vht, and vhd in {value}')
        auto_non_connectors_df = links_df.loc[(links_df['isAuto'] == True) & (links_df['isConnector'] == False)].copy()
        ret = calculate_system_metrics(auto_non_connectors_df, value, attr)
        metrics = pd.merge(metrics, ret, how = 'outer', left_index = True, right_index = True)
        ret = calculate_for_GHG(auto_non_connectors_df, value, attr)
        GHG_metrics_list.append(ret)

    metrics.fillna(0)
    my_project.closeDesktop()

    ghg_metric = GHG_metrics_list[0]
    for i in range(1, 4):
        ghg_metric = ghg_metric.merge(GHG_metrics_list[i], how = 'outer', left_index = True, right_index = True)

    ghg_metric.fillna(0, inplace = True)

    # calculate daily VMT, VHT, and VHD
    print(f'calculating daily vmt, vht, and vhd')
    metrics['daily_VMT'] = 0
    metrics['daily_VHT'] = 0
    metrics['daily_VHD'] = 0

    ghg_metric['daily_VMT'] = 0
    ghg_metric['daily_VHT'] = 0
    ghg_metric['daily_VHD'] = 0

    for key, value in sound_cast_net_dict.items():  
        metrics['daily_VMT'] = metrics['daily_VMT'] + metrics[value + '_VMT']
        metrics['daily_VHT'] = metrics['daily_VHT'] + metrics[value + '_VHT']
        metrics['daily_VHD'] = metrics['daily_VHD'] + metrics[value + '_VHD']
        ghg_metric['daily_VMT'] = ghg_metric['daily_VMT'] + ghg_metric[value + '_VMT']
        ghg_metric['daily_VHT'] = ghg_metric['daily_VHT'] + ghg_metric[value + '_VHT']
        ghg_metric['daily_VHD'] = ghg_metric['daily_VHD'] + ghg_metric[value + '_VHD']
    
    for col in metrics.columns:
        metrics[col] = metrics[col].map('{:.1f}'.format)
        ghg_metric[col] = ghg_metric[col].map('{:.1f}'.format)
    outputfile = os.path.join(prj.project_folder, 'outputs/network', outputfilename)

 

    # export to file also calculate daily VMT/VHT/VHD
    with open(outputfile, 'w')  as f:
        f.write(str(datetime.datetime.now()) + '\n')
        f.write(f'Project folder: {prj.project_folder}\n\n')
        f.write('%s\n\n' % metrics.to_string())

        f.write('%s\n\n' % ghg_metric.to_string())
        f.write('Notes\n')
        f.write('1. Auto mode only. Centroid connectors are not included.\n')
        f.write(f'2. {attr}: {groupby_description}')


    print('Done')
if __name__ == '__main__':
    main()
