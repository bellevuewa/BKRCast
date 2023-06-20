import pandas as pd
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
import datetime
from functools import reduce
import matplotlib.pyplot as plt
import numpy as np
import io
import getopt
import json
import input_configuration as prj
import emme_configuration as emme_config
from data_wrangling import *

basic_link_attr_list = ['i_node', 'j_node', 'length', 'type', 'num_lanes', 'volume_delay_func', '@bkrlink', 'data1', 'data2', 'auto_volume']
def create_columns_dict(base_column_list, screenline_dict):
    '''
        create a dict of tod and column attribute list. tod is defined in screenline_dict.
        return this created dict
    '''
    columns_dict = {}
    for key, value in screenline_dict.items():
        # make a copy of basic_link_attr_list. otherwise it would be overwritten.
        updated_attr_list = base_column_list.copy()
        for slid, attr in value.items():
            if slid not in updated_attr_list: 
                updated_attr_list.append(slid)
            if attr not in updated_attr_list:
                updated_attr_list.append(attr)
        columns_dict[key] = updated_attr_list
    return columns_dict

def create_scatter_plot_image(x, xlabel, y, ylabel, attr, fid, image_to_file = False):
    '''
       Create a scatter plot. Save the plot in image file if image_to_file is True, or in memory if it is False.
        x: data column on x axis
        y: data column on y axis
        xlabel, and ylabel: labels on axis
        attr: name of attribute in comparison
        fid: figure id
    '''
    # calculate regression line
    m, b = np.polyfit(x, y, deg = 1)
    plt.figure(fid)
    plt.scatter(x = x, y = y)
    plt.ylabel(ylabel)
    plt.xlabel(xlabel)

    # draw regression line on scatter plot
    ypred = m * x + b
    plt.plot(x, ypred, label = f'$y = {m:.3f}x {b:+.3f}$')
    plt.grid(True, which = 'both', axis = 'both')
    ax = plt.gca()
    size = max(ax.get_xlim()[1], ax.get_ylim()[1])
    plt.axis([0, size, 0, size], 'square')

    plt.legend()
    plt.title('Scatter Plot by ' + attr)

    # draw a diagnol line
    abline(1, 0)

    # save the plot to Excel tab. side by side with data table
    if image_to_file == False:
        imgdata = io.BytesIO()
        plt.savefig(imgdata, format = 'png')
        imgdata.seek(0)
        return imgdata
    else:
        file_loc = os.path.join(prj.report_net_output_location, prj.scenario_name + '_' + xlabel + '_' + 'ylabel' + '_attr_scatter.png')
        plt.savefig(file_loc, format = 'png')
        return file_loc

def abline(slope, intercept):
    '''
        draw a line on the plot area, with slope and intercept.
    '''
    axes = plt.gca()
    x_vals = np.array(axes.get_xlim())
    y_vals = intercept + slope * x_vals
    plt.plot(x_vals, y_vals, '--')

def help():
    print("This program will save model volumes and counts at screenline locations to external Excel file, and save")
    print("scatter plots and caculate linear regression as well. ")
    print('Screenlines and counts are defined in a json file, which usually resides in the root project folder.')
    print('')
    print('Two predefined json files are for 2014 and 2018 base year.')
    print('')   
    print('  python network_volume_validation.py -h -i <input_json_file>')
    print('    -h: help')
    print('    -i: json file for screenline and count definition. Default is screenline_2014.json.')
    

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hi:')
    except getopt.GetoptError:
        help()
        sys.exit(2)
    
    json_file = 'screenline_2014.json'
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-i':
            json_file = os.path.join(prj.project_folder, arg)

    print(emme_config.network_summary_project)
    my_project = EmmeProject(emme_config.network_summary_project)

    screenline_dict = json.load(open(json_file))
    columns_dict = create_columns_dict(basic_link_attr_list, screenline_dict)
    sum_sl_dict = {} # aggregated by different screenline tags
 
    writer = pd.ExcelWriter(os.path.join(prj.report_net_output_location, prj.network_validation_output_filename), engine = 'xlsxwriter')
    wksheet = writer.book.add_worksheet('readme')
    wksheet.write(0, 0, str(datetime.datetime.now()))
    wksheet.write(1, 0, 'model folder')
    wksheet.write(1, 1, prj.project_folder)
    wksheet.write(2, 0, 'screenline attributes: ')
    pretty_json = json.dumps(screenline_dict, indent = 2)
    wksheet.write(3, 0, pretty_json)

    for key, value in emme_config.sound_cast_net_dict.items():
        my_project.change_active_database(key)
        print(f'loading {value} ...')
        links_df = my_project.emme_links_to_df()
        if value in screenline_dict.keys():
            for slid, attr in screenline_dict[value].items():
                print(f'processing {slid} ...')
                sl_df = links_df.loc[(links_df['isAuto'] == True) & (links_df['isConnector'] == False) & (links_df[slid] > 0) & (links_df[attr] > 0)].copy()
                selected_columns = columns_dict[value]
                sl_df = sl_df[selected_columns]

                # calculate peak hour model volume at different TOD
                # aggregate model volume and counts by various screenlines.
                if value == 'pm':
                    sl_df['pmpkhr'] = sl_df['auto_volume'] * emme_config.pkhrfac_dict[value]
                    sum_sl_df = sl_df[[slid, 'auto_volume', 'pmpkhr', attr]].groupby(slid).sum()
                elif value == 'am':
                    sl_df['ampkhr'] = sl_df['auto_volume'] * emme_config.pkhrfac_dict[value]
                    sum_sl_df = sl_df[[slid, 'auto_volume', 'ampkhr', attr]].groupby(slid).sum()
                elif value == 'md':
                    sl_df['mdpkhr'] = sl_df['auto_volume'] * emme_config.pkhrfac_dict[value]
                    sum_sl_df = sl_df[[slid, 'auto_volume', 'mdpkhr', attr]].groupby(slid).sum()

                sum_sl_df.rename(columns = {'auto_volume': 'auto_volume'+'_'+value}, inplace = True)
                sum_sl_df = sum_sl_df.round(0)
                sum_sl_df.reset_index(inplace = True)

                sheetname = 'hwy_' + key + '_' + slid
                sl_df.to_excel(writer, sheet_name = sheetname, startrow = 1)
                sheet = writer.sheets[sheetname]
                sheet.write(0, 0, 'screenline = ' + slid)

                if slid in sum_sl_dict.keys():
                    sum_sl_dict[slid].append(sum_sl_df)
                else:
                    sum_sl_dict[slid] = [sum_sl_df]
        else:
            print(f'no screenline volume found in {value}')

    fid = 0
    for attr, dfs in sum_sl_dict.items():
        # merge all relevant aggregated screenline dfs together (AM, MD or/and PM)
        final_sl_summary = reduce(lambda left, right: pd.merge(left, right, on = attr, how = 'outer'), dfs)
        columns_to_add = final_sl_summary.filter(like='auto_volume').columns
        final_sl_summary['total_model_vol'] = final_sl_summary[columns_to_add].sum(axis = 1)
        columns_to_add = final_sl_summary.filter(like='pkhr').columns   
        final_sl_summary['total_pkhr_model_vol'] = final_sl_summary[columns_to_add].sum(axis = 1)
        columns_to_add = final_sl_summary.filter(like = '@slcnt').columns
        final_sl_summary['total_pkhr_counts'] = final_sl_summary[columns_to_add].sum(axis = 1)
        imgdata = create_scatter_plot_image(final_sl_summary['total_pkhr_counts'], 'total_pkhr_counts', final_sl_summary['total_pkhr_model_vol'], 'total_pkhr_model_vol', attr, fid)
        fid += 1    

        # calculate total volumes across all screenlines.
        final_sl_summary.loc['Total'] = final_sl_summary.sum()

        final_sl_summary['Diff'] = final_sl_summary['total_pkhr_model_vol'] - final_sl_summary['total_pkhr_counts']
        final_sl_summary['%Diff'] = (final_sl_summary['Diff'] / final_sl_summary['total_pkhr_counts']).map('{:.1%}'.format)
        final_sl_summary.reset_index(inplace = True)
        final_sl_summary.sort_values(by = attr, inplace = True)
        final_sl_summary.to_excel(writer, sheet_name = attr, startrow = 2, index = False)
        wksheet = writer.sheets[attr]
        wksheet.write(1, 0, 'Auto Volume Validation by ' + attr)
        wksheet.insert_image(0, final_sl_summary.shape[1], '', options = {'image_data': imgdata} )

    writer.save()
    my_project.closeDesktop()
    print('done')

if __name__ == '__main__':
    main()