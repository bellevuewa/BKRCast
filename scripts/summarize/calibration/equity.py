import os
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts\summarize"))
import numpy as np
import pandas as pd
import datetime
from h5toDF import *
import getopt
import input_configuration as prj
from summary_functions import *

def aggregate_by_attribute(df, select_attr_name, group_attr_name, aggregate_attr_name):
    select_attr_name_values = np.sort(df[select_attr_name].unique())
    output_list = []
    for attr in select_attr_name_values:
        agg_by_select_attr = df.loc[df[select_attr_name] == attr].groupby(group_attr_name).sum()[[aggregate_attr_name]]
        agg_by_select_attr[str(attr) + '_%'] = agg_by_select_attr[aggregate_attr_name] / agg_by_select_attr[aggregate_attr_name].sum()
        agg_by_select_attr.rename(columns = {aggregate_attr_name : attr}, inplace = True)
        output_list.append(agg_by_select_attr)

    final_df = output_list[0]
    for item in output_list[1:]:
        final_df = final_df.merge(item, left_index = True, right_index = True, how = 'outer')
    
    return final_df

def create_demographic_hhs_report(df, writer):
    print('  households by income level and jurisdiction')
    hhs_by_jurisdiction = aggregate_by_attribute(df, 'Jurisdiction', 'income_bins', 'hhexpfac')
    hhs_by_jurisdiction.to_excel(writer, sheet_name = 'hhs_by_jurisdiction', index = True, startrow = 1)
    hhs_by_jurisdiction_sheet = writer.sheets['hhs_by_jurisdiction']
    hhs_by_jurisdiction_sheet.write(0,0, 'Households Distribution by Income Level')
    srow = hhs_by_jurisdiction.shape[0] + 3
    hhs_by_jurisdiction_sheet.write(srow,0, 'notes')
    hhs_by_jurisdiction_sheet.write(srow+1,0, '1. federal poverty line for one person household is $' + str(prj.fed_poverty_1st_person)) 
    hhs_by_jurisdiction_sheet.write(srow+2,0, '   add $' + str(prj.fed_poverty_extra_person) + ' for each additional person in the same household.') 

    print('  households by income level and subarea')
    hhs_by_subarea = aggregate_by_attribute(df, 'Subarea', 'income_bins', 'hhexpfac')
    hhs_by_subarea.to_excel(writer, sheet_name = 'hhs_by_subarea', index = True, startrow = 1)
    hhs_by_subarea_sheet = writer.sheets['hhs_by_subarea']
    hhs_by_subarea_sheet.write(0, 0, 'Households Distribution by Income Level')
    srow = hhs_by_subarea.shape[0] + 3
    hhs_by_subarea_sheet.write(srow,0, 'notes')
    hhs_by_subarea_sheet.write(srow+1,0, '1. federal poverty line for one person household is $' + str(prj.fed_poverty_1st_person)) 
    hhs_by_subarea_sheet.write(srow+2,0, '   add $' + str(prj.fed_poverty_extra_person) + ' for each additional person in the same household.') 

    print('  households by jurisdiction and vehicle ownership')
    veh_by_jurisdiction = aggregate_by_attribute(df, 'Jurisdiction', 'veh_bins', 'hhexpfac')
    veh_by_jurisdiction.to_excel(writer, sheet_name = 'veh_by_jurisdiction', index = True, startrow = 1)
    veh_by_jurisdiction_sheet = writer.sheets['veh_by_jurisdiction']
    veh_by_jurisdiction_sheet.write(0, 0, 'Household Distribution by Vehicles')

    print('  households by subarea and vehicle ownership')
    veh_by_subarea = aggregate_by_attribute(df, 'Subarea', 'veh_bins', 'hhexpfac')
    veh_by_subarea.to_excel(writer, sheet_name = 'veh_by_subarea', index = True, startrow = 1)
    veh_by_subarea_sheet = writer.sheets['veh_by_subarea']
    veh_by_subarea_sheet.write(0, 0, 'Household Distribution by Vehicles')

def create_demographic_person_report(df, writer):
    print('  people by age and jurisdiction')
    person_by_jurisdiction = aggregate_by_attribute(df, 'Jurisdiction', 'age_bins', 'psexpfac')
    person_by_jurisdiction.to_excel(writer, sheet_name = 'persons_by_juris', index = True, startrow = 1)
    person_by_jurisdiction_sheet = writer.sheets['persons_by_juris']
    person_by_jurisdiction_sheet.write(0, 0, 'Person Distribution by Age')

    print('  people by age and subarea')
    person_by_subarea = aggregate_by_attribute(df, 'Subarea', 'age_bins', 'psexpfac')
    person_by_subarea.to_excel(writer, sheet_name = 'person_by_subarea', index = True, startrow = 1)
    person_by_subarea_sheet = writer.sheets['person_by_subarea']
    person_by_subarea_sheet.write(0, 0, 'Person Distribution by Age')

    print('  people by person type and jurisdiction')
    persons_by_pptyp_juris = aggregate_by_attribute(df, 'Jurisdiction', 'pptyp', 'psexpfac')
    persons_by_pptyp_juris.to_excel(writer, sheet_name = 'pptyp_by_Juris', index = True, startrow = 1)
    persons_by_pptyp_juris_sheet = writer.sheets['pptyp_by_Juris']
    persons_by_pptyp_juris_sheet.write(0, 0, 'Person Distribution by Type')

    print('  people by person type and subarea')
    persons_by_pptyp_subarea = aggregate_by_attribute(df, 'Subarea', 'pptyp', 'psexpfac')
    persons_by_pptyp_subarea.to_excel(writer, sheet_name = 'pptyp_by_subarea', index = True, startrow = 1)
    persons_by_pptyp_subarea_sheet = writer.sheets['pptyp_by_subarea']
    persons_by_pptyp_subarea_sheet.write(0, 0, 'Person Distribution by Type')

def write_to_sheet(writer, name_of_sheet, dict_dfs, write_index = True, horizontal = True):
    '''
       writer: ExcelWriter variable
       name_of_sheet: the sheet that dfs are to be exported
       dict_dfs: dictionary of dfs: {title1: df1, title2:df2...}
       write_index: write indices if True
       horizontal: export dfs horizontally or vertically. Default is horizontal
    '''    
    srow = 1
    scol = 0
    for title, df in dict_dfs.items():
        df.to_excel(writer, sheet_name = name_of_sheet, index = write_index, startrow = srow, startcol = scol)
        sheet = writer.sheets[name_of_sheet]
        sheet.write(srow - 1, scol, title)
        if horizontal == True:
            srow = srow + df.shape[0] + 3
        else:
            if write_index == True:
                scol = scol + df.shape[1] + len(df.index.names) + 3
            else:
                scol = scol + df.shape[1] + 3

    return srow, scol

def aggregate_trips_by_all_subareas(df, group_attr_name_list, aggregate_dict, column_rename_dict):
    output_df = df.groupby(group_attr_name_list).agg(aggregate_dict).fillna(0)
    output_df.rename(columns = column_rename_dict, inplace = True)
    output_df.columns = output_df.columns.droplevel(1)
    output_df['avg_trip_length'] = (output_df['travdist'] / output_df['total_person_trips'])
    output_df['avg_trip_travel_time'] = (output_df['travtime'] / output_df['total_person_trips'])
    output_df['trips_per_person'] = (output_df['total_person_trips'] / output_df['total_persons'])
    output_df['person_trip_share'] = 0
    lvl1 = output_df.index.levels[0]
    for l1 in lvl1:
        subtotal = output_df.loc[l1, 'total_person_trips'].sum()
        output_df.loc[l1, 'person_trip_share'] = output_df['total_person_trips'] / subtotal

    output_df = output_df.round({'travdist':0, 'travtime':0, 'avg_trip_length':2, 'avg_trip_travel_time':2, 'trips_per_person':2, 'person_trip_share': 3})
    return output_df

def trip_mode_share_residents(df, group_attr_list, aggregate_dict, column_rename_dict):
    mode_share_df = df.groupby(group_attr_list).agg(aggregate_dict).fillna(0)
    mode_share_df.columns = mode_share_df.columns.droplevel(1)
    mode_share_df['avg_trip_length'] = mode_share_df['travdist'] / mode_share_df['trexpfac']
    mode_share_df['avg_trip_travel_time'] = mode_share_df['travtime'] / mode_share_df['trexpfac']
    mode_share_df['trip_mode_share'] = 0

    lv1 = mode_share_df.index.levels[0]
    lv2 = mode_share_df.index.levels[1]

    for l1 in lv1:
        for l2 in lv2:
            subtotal = mode_share_df.loc[(l1, l2), 'trexpfac'].sum()
            mode_share_df.loc[(l1, l2), 'trip_mode_share'] = mode_share_df['trexpfac'] / subtotal
        
    mode_share_df = mode_share_df.round({'travdist':0, 'travtime':0, 'avg_trip_length':2, 'avg_trip_travel_time':2, 'trip_mode_share':3})
    mode_share_df.rename(columns = column_rename_dict, inplace = True)

    return mode_share_df        


def help():
    print(' This script is used to generate demographic report and equity report. Demographic data is saved in demographic_report.xlsx.')
    print(' Equity data is saved in equity_report.xlsx. Both files are located in outputs/summary folder.')
    print('')
    print(' The following files are used in generating reports.')
    print('    _household.tsv')
    print('    _person.tsv')
    print('    _trip.tsv')  
    print('')
    print(' Usage:')    
    print('    python scripts/summarize/calibration/equity.py -h -i trip_file_name')
    print('         -h: help')
    print('         -i: name of an alternative trip file to be used in this tool. Default file path is outputs/daysim.')
 
    
    
def main():
    trip_file = '_trip.tsv'
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hi:')
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit(0)
        elif opt == '-i':
            trip_file = arg

    print('loading files...')
    hhs_df = pd.read_csv(os.path.join(prj.report_output_location, '_household.tsv'), sep = '\t')
    taz_subarea = pd.read_csv(os.path.join(prj.main_inputs_folder, 'subarea_definition','TAZ_Subarea.csv'), sep = ',')
    lookup_parcels_df = pd.read_csv(os.path.join(prj.main_inputs_folder, 'model', 'parcel_TAZ_2014_lookup.csv'), low_memory = False)
    hhs_df = pd.merge(hhs_df, taz_subarea, left_on = 'hhtaz', right_on = 'BKRCastTAZ', how = 'left')
    persons_df = pd.read_csv(os.path.join(prj.report_output_location, '_person.tsv'), sep = '\t')

    #calculate federal poverty line 
    hhs_df['fed_poverty'] = 0
    hhs_df['fed_poverty'] = prj.fed_poverty_1st_person + prj.fed_poverty_extra_person * (hhs_df['hhsize'] - 1)

    hhs_df['income_bins'] = pd.cut(hhs_df['hhincome'] / hhs_df['fed_poverty'], bins = prj.income_bins)
    hhs_df['veh_bins'] = pd.cut(hhs_df['hhvehs'], bins = prj.veh_bins)
    hhs_df['size_bins'] = pd.cut(hhs_df['hhsize'], bins = prj.hhsize_bins)
    persons_df['age_bins'] = pd.cut(persons_df['pagey'], bins = prj.age_bins)
    persons_df = persons_df.merge(hhs_df[['hhno', 'income_bins', 'veh_bins', 'size_bins', 'Jurisdiction', 'Subarea']], on = 'hhno')

    trips_df = pd.read_csv(os.path.join(prj.report_output_location, trip_file), sep = '\t', low_memory = False)
    trips_df = trips_df.merge(taz_subarea[['BKRCastTAZ', 'Subarea']], left_on = 'otaz', right_on = 'BKRCastTAZ').rename(columns={'Subarea':'osubarea'})
    trips_df.drop(columns = ['BKRCastTAZ'], inplace = True)
    trips_df = trips_df.merge(taz_subarea[['BKRCastTAZ', 'Subarea']], left_on = 'dtaz', right_on = 'BKRCastTAZ').rename(columns={'Subarea':'dsubarea'})
    trips_df.drop(columns = ['BKRCastTAZ'], inplace = True)
    print('input files loaded.')

    guides = get_guide(prj.guidefile)
    categorical_dict = guide_to_dict(guides)

    demographic_writer = pd.ExcelWriter(os.path.join(prj.report_summary_output_location, "demographic_report.xlsx"), engine = 'xlsxwriter')
    wksheet = demographic_writer.book.add_worksheet('readme')
    wksheet.write(0, 0, str(datetime.datetime.now()))
    wksheet.write(1, 0, 'model folder')
    wksheet.write(1, 1, prj.project_folder)

    create_demographic_hhs_report(hhs_df, demographic_writer)
    create_demographic_person_report(persons_df, demographic_writer)
    demographic_writer.save()
    print('demographic report is generated.')

    equity_writer = pd.ExcelWriter(os.path.join(prj.report_summary_output_location, 'equity_report.xlsx'), engine = 'xlsxwriter')
    equity_sheet = equity_writer.book.add_worksheet('readme')
    equity_sheet.write(0, 0, str(datetime.datetime.now()))
    equity_sheet.write(1, 0, 'model folder')
    equity_sheet.write(1, 1, prj.project_folder)
        
    # create hhs_by_income sheet
    print('  households by income level')
    hhs_by_jurisdiction = aggregate_by_attribute(hhs_df, 'Jurisdiction', 'income_bins', 'hhexpfac')
    hhs_by_subarea = aggregate_by_attribute(hhs_df, 'Subarea', 'income_bins', 'hhexpfac')
    dict_dfs = {'Households by Income and Jurisdiction':hhs_by_jurisdiction, 'Households by Income and Subarea':hhs_by_subarea}
    srow, scol = write_to_sheet(equity_writer, dict_dfs = dict_dfs, name_of_sheet = 'hhs_by_income', write_index = True, horizontal = True)
    hhs_by_income_sheet = equity_writer.sheets['hhs_by_income']
    hhs_by_income_sheet.write(srow, scol, 'notes')
    hhs_by_income_sheet.write(srow+1, scol, '1. federal poverty line for one person household is $' + str(prj.fed_poverty_1st_person)) 
    hhs_by_income_sheet.write(srow+2, scol, '   add $' + str(prj.fed_poverty_extra_person) + ' for each additional person in the same household.') 

    #create hhs by income and hhsize sheet
    print('  households by income level and household size')
    juris_income_hhsize_df = hhs_df.groupby(['Jurisdiction', 'income_bins', 'size_bins']).agg({'hhexpfac':['sum'], 'hhsize':'sum'}).fillna(0)
    subarea_income_hhsize_df = hhs_df.groupby(['Subarea', 'income_bins', 'size_bins']).agg({'hhexpfac':['sum'], 'hhsize':'sum'}).fillna(0)
    dict_dfs = {'Household Distribution by Jurisdiction, Income Level and Household Size' : juris_income_hhsize_df, 'Households Distribution by Subarea, Income Level and Household Size': subarea_income_hhsize_df}
    write_to_sheet(equity_writer, name_of_sheet = 'hh_income_hhsize', dict_dfs = dict_dfs, write_index = True, horizontal = False)

    # create hhs by income and veh
    print('  households by income level and vehicle ownership')
    juris_income_veh_df = hhs_df.groupby(['Jurisdiction', 'income_bins', 'veh_bins']).sum()[['hhexpfac']].fillna(0)
    juris_income_veh_df.rename(columns = {'hhexpfac':'total_hhs'}, inplace = True)
    subarea_income_veh_df = hhs_df.groupby(['Subarea', 'income_bins', 'veh_bins']).sum()[['hhexpfac']].fillna(0)
    subarea_income_veh_df.rename(columns = {'hhexpfac':'total_hhs'}, inplace = True)
    dict_dfs = {'Household Distribution by Jurisdiction, Income Level and Vehicle Ownership' : juris_income_veh_df, 'Households Distribution by Subarea, Income Level and Vehicle Ownership': subarea_income_veh_df}
    write_to_sheet(equity_writer, name_of_sheet = 'hh_income_veh', dict_dfs = dict_dfs, write_index = True, horizontal = False)

    # create trips made by residents living in subarea
    print('  trips made by residents and subarea')
    persons_df['pid'] = persons_df['hhno'].astype(str) + '-' + persons_df['pno'].astype(str)
    persons_df = persons_df.merge(trips_df, on = ['hhno', 'pno'])
    group_list = ['Subarea', 'income_bins']
    agg_dict = {'pid':'nunique', 'trexpfac':['sum'], 'travdist':'sum', 'travtime':'sum'}
    rename_dict = {'trexpfac': 'total_person_trips', 'pid':'total_persons'}
    trips_by_res_subarea_df = aggregate_trips_by_all_subareas(persons_df, group_attr_name_list=group_list, aggregate_dict=agg_dict, column_rename_dict=rename_dict)
    write_to_sheet(equity_writer, 'trips_by_residents', {'Trips by Subarea Residents': trips_by_res_subarea_df})

    print('  trips originated from subarea')
    group_list = ['osubarea', 'income_bins']
    trips_origin_from_subarea_df = aggregate_trips_by_all_subareas(persons_df, group_attr_name_list=group_list, aggregate_dict=agg_dict, column_rename_dict=rename_dict)
    write_to_sheet(equity_writer, 'trips_from_subarea', {'Trips Originated from Subarea': trips_origin_from_subarea_df})

    # create trip mode share by residents and jurisdiction
    print('  trip mode share by residents, jurisdiction and income level')
    group_list = ['Jurisdiction', 'income_bins', 'mode']
    agg_dict = {'trexpfac':['sum'], 'travdist':'sum', 'travtime':'sum'}
    rename_dict = {'trexpfac': 'total_person_trips'}
    juris_res_mode_share_df = trip_mode_share_residents(persons_df, group_attr_list=group_list,aggregate_dict=agg_dict, column_rename_dict=rename_dict)
    juris_res_mode_share_df.rename(index = categorical_dict['mode'], inplace = True)
    write_to_sheet(equity_writer, 'residents_mode_share_juris', {'Trip Mode Share by Residents': juris_res_mode_share_df})

    # create trip mode share made by residents
    print('  trip mode share by residents, subarea and income level')
    group_list = ['Subarea', 'income_bins', 'mode']
    subarea_res_mode_share_df = trip_mode_share_residents(persons_df, group_attr_list=group_list,aggregate_dict=agg_dict, column_rename_dict=rename_dict)
    subarea_res_mode_share_df.rename(index = categorical_dict['mode'], inplace = True)
    write_to_sheet(equity_writer, 'residents_mode_share_subarea', {'Trip Mode Share by Residents':subarea_res_mode_share_df})

    equity_writer.save()
    print('equity report is generated.')

if __name__ == '__main__':
    main()