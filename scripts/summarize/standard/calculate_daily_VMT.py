import pandas as pd
import os, sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
from input_configuration import *
from emme_configuration import *

# 10/25/2021
# modified to be compatible with python 3

# link selectors. only one selection one link selector can be used for now
# it may have multiple selections. For example, we can select by jurisdiction boundary 
# and subarea boundary. They are two seperate and independent selections. That's OK.
# but you cannot have a selection of ul1=1000 and ul2=60. This kind of selection is not allowed
#link_selectors = {'@bkrlink': 1, '@studyarea': 1, '@studyarea405': 1,'@studyareafreeway': 1, '@studyarearamps': 1}
link_selectors = {'@corearea': 1}

# file will be exported to default output folder.
outputfilename = 'system_metrics.txt'

def main():
    print(network_summary_project)
    my_project = EmmeProject(network_summary_project)

    for key, value in sound_cast_net_dict.items():
        my_project.change_active_database(key)
        network = my_project.current_scenario.get_network()
        network.create_attribute('NODE', 'numIn')
        network.create_attribute('NODE', 'numOut')
        for node in network.nodes():
            node.numIn = len(list(node.incoming_links()))        
            node.numOut = len(list(node.outgoing_links()))

        network.create_attribute('LINK', 'isAuto')
        network.create_attribute('LINK', 'isTransit')
        network.create_attribute('LINK', 'isConnector')
        network.create_attribute('LINK', 'isOneWay')
        auto_mode = set([m for m in network.modes() if m.type == 'AUTO'])
        transit_mode = set([m for m in network.modes() if m.types == 'TRANSIT'])

        link_data = {'i_node':{}, 'j_node': {}}
        link_data.update({k: [] for k in network.attributes('LINK')})
        for link in network.links():
            link.isAuto == auto_mode in link.modes
            link.isTransit = bool(link.modes.intersection(transit_mode))
            link.isConnector = (link.i_nde.is_centroid or link.j_node.is_centroid)
            link.isOneWay = network.link(link.j_node, link.i_node) is None

            for k in network.attributes('LINK'):
                link_data[k].append(link[k])

            link_data['i_node'].append(link.i_node.number)
            link_data['j_node'].append(link.j_node.number)
        links_df = pd.DataFrame(link_data)

        my_project.closeDesktop()
 

    outputfile = os.path.join(project_folder, 'outputs/network', outputfilename)

    # export to file also calculate daily VMT/VHT/VDT
    with open(outputfile, 'w')  as f:
        for flag, val in metrics.items():
            daily_vmt = 0
            daily_vht = 0
            daily_vdt = 0
            daily_vol = 0
            f.write('Selection: %s\n' % flag)
            for tod, value in val.items():
                f.write('  ')
                f.write('Time of Day: %s\n' % tod)
                for variable, var_val in value.items():
                    f.write('    ')
                    f.write('%s: %.2f\n' % (variable, var_val))
                    if variable == 'VMT':
                        daily_vmt = daily_vmt + var_val
                    elif variable == 'VHT':
                        daily_vht = daily_vht + var_val
                    elif variable == 'VDT':
                        daily_vdt = daily_vdt + var_val
                    elif variable == 'TotalVol':
                        daily_vol = daily_vol + var_val
            f.write('  Time of Day: Daily\n')
            f.write('    VMT: %.2f\n' % daily_vmt)
            f.write('    VHT: %.2f\n' % daily_vht)
            f.write('    VDT: %.2f\n' % daily_vdt)
            f.write('    Vol: %.2f\n' % daily_vol)
            f.write('\n')
    print('Done')
if __name__ == '__main__':
    main()
