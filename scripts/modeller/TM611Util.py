#-------------------------------------------------------------------------------
# Name:        TM611
# Purpose:
#  TM611 is a python tool for the EMME demand model. It repackages turning movement
#  volumes in EMME format (at-node from-node to-node vol) to more user friendly
#  format:
#   Int_ID NBL NBT NBR SBL SBT SBR EBL EBT EBR WBL WBT WBR
#  The output file will be served as an input file for post processing turnadj.
# Author:      Hu Dong
#
# Created:     1/27/2014
# Revision 1.1
#   Add exception control to detect extra empty lines in input files, and
#   display error message to the interface.
# Copyright:   (c) hdong 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# 05/19/2022
# upgraded to python 3.7


import sys
import string
import inro.modeller as _modeller
import inro.emme.matrix as _matrix
import inro.emme.desktop.app as _app
import os
import operator

class TM611kUtility(_modeller.Tool()):
    '''
    '''
    scenarios = _modeller.Attribute(list)
    linkFilename = _modeller.Attribute(object)
    emmeTMFilename = _modeller.Attribute(object)
    outputFilename = _modeller.Attribute(object)
    tool_run_msg = ""

    @property
    def current_scenario(self):
        return _modeller.Modeller().desktop.data_explorer().primary_scenario.core_scenario

    def page(self):
        pb = _modeller.ToolPageBuilder(self, title="TM611",
                     description="Create a user friendly turning movement volume input file",
                     branding_text="City of Bellevue")

        pb.add_select_file("linkFilename", "file", "*.*", self.default_path, "Select a link file")
        pb.add_select_file("emmeTMFilename", "file", "*.*", self.default_path, "Select an EMME TM file")
        self.outputFilename = "mTM_pm_4000_10fn_241.prn"
        pb.add_text_box("outputFilename", 30, title = "Enter output file name")
        if self.tool_run_msg != "":
           pb.tool_run_status(self.tool_run_msg_status)


        return pb.render()

    def run(self):
        self(self.scenarios)
        self.tool_run_msg = ""

    @_modeller.logbook_trace(name="TM611", save_arguments=True)
    def __call__(self, scenarios):
        if self.linkFilename == None:
            self.tool_run_msg = _modeller.PageBuilder.format_info("Please select a link file")
            exit(2)
        if self.emmeTMFilename == None:
            self.tool_run_msg = _modeller.PageBuilder.format_info("Please select a EMME TM file")
            exit(2)
        if self.outputFilename == None:
            self.tool_run_msg = _modeller.PageBuilder.format_info("Please input an output file name")
            exit(2)

        try:
            linkFile = EMMELinkFile(self.linkFilename)
        except IndexError:
            self.tool_run_msg = _modeller.PageBuilder.format_info("Error: Link file has extra empty line or not complete.")
            exit(2)
        except Exception as e:
            self.tool_run_msg = _modeller.PageBuilder.format_exception(exception = e, chain = False)
            exit(2)

        try:
            tmFile = EMMETMFile(self.emmeTMFilename)
            tmFile.sort(True)
            #tmFile.output()
        except IndexError:
            self.tool_run_msg = _modeller.PageBuilder.format_info("Error: Turn file has extra empty line or not complete.")
            exit(2)
        except Exception as e:
            self.tool_run_msg = _modeller.PageBuilder.format_exception(exception = e, chain = False)
            exit(2)



        # for output turning movement volumes
        outputfile = TMVolFile()

        try:
            errFp = open("turns_not_in_turn_vols.dat", "w")
            errFp.write("The following intersections have turns that are not in the EMME turn volume file. Please check.")
        except:
            self.tool_run_msg += _modeller.PageBuilder.format_info("turns_not_in_turn_vols.dat cannot be opened")
            exit(2)

        count = 0
        invalidNodes = []
        for inter in linkFile.intersections:
            turns = inter.turns
            size = len(turns)
            vols = [] # store tm vols nbl nbt nbl sbl sbt sbr ebl ebt ebr wbl wbt wbr
            for turn in turns:
                vol = 0
                print(turn)
                emmetm = tmFile.search(turn)
                if (emmetm == None):
                    vol = 0
                    nds = turn.split("-")
                    if (not(nds[0] in ["0", "9999", "9998", "9997"] or (nds[2] in ["0", "9999", "9998", "9997"]))):
                        invalidNodes.append(nds[1])
                        #print >> errFp, turn
                else:
                    print(emmetm.key + " " + emmetm.vol)
                    vol = emmetm.vol
                vols.append(vol)
            tm = TMVol(inter.id, vols[0], vols[1], vols[2], vols[3], vols[4], vols[5], vols[6], vols[7], vols[8], vols[9], vols[10], vols[11])
            outputfile.add(tm)

        try:
            fp = open(self.outputFilename, "w")
        except:
            self.tool_run_msg += _modeller.PageBuilder.format_info("Output file " + self.outputFilename + " cannot be opened")

        outputfile.output(fp)
        fp.close()

        errFp.write('Below are invalid nodes:')
        for n in set(invalidNodes):
            errFp.write(n + '\n')
        errFp.close()
        self.tool_run_msg += "File Exported."
        _modeller.logbook_write("File exported to  " + self.outputFilename)



    def __init__(self):
        '''
        Constructor
        '''
        self.default_path = os.path.dirname(self.current_scenario.emmebank.path).replace("\\", "/")


    @_modeller.method(return_type=str)
    def tool_run_msg_status(self):
        return self.tool_run_msg

class EMMEAjacentNode:
    """define an intersection and its adjacent nodes to the noth, south, east,
    and west.
      #  @Node North South  East  West
    -----------------------------------
       1   981  5010  9999  5454  5478
    """
    def __init__(self, id, at=0, north=0, south=0, east=0, west=0):
        self.id = id        # subject intersection ID
        self.at = at        # subject intersection node
        self.north = north  # north node
        self.south = south  # south node
        self.east = east    # east node
        self.west = west    # west node
        # create movement index.
        self.NBL = f'{at}-{south}-{west}'
        self.NBT = f'{at}-{south}-{north}'
        self.NBR = f'{at}-{south}-{east}'
        self.SBL = f'{at}-{north}-{east}'
        self.SBT = f'{at}-{north}-{south}'
        self.SBR = f'{at}-{north}-{west}'
        self.EBL = f'{at}-{west}-{north}'
        self.EBT = f'{at}-{west}-{east}'
        self.EBR = f'{at}-{west}-{south}'
        self.WBL = f'{at}-{east}-{south}'
        self.WBT = f'{at}-{east}-{west}'
        self.WBR = f'{at}-{east}-{north}'

        self.turns = [self.NBL, self.NBT, self.NBR, self.SBL, self.SBT, self.SBR, self.EBL, self.EBT, self.EBR, self.WBL, self.WBT, self.WBR]

    def isTIntersection(self):
        """return true if it is a T intersection"""
        count = self.__counts
        if count == 3:
            return True
        else:
             return False

    def __counts(self):
        """count how many adjacent nodes the subject intersection has"""
        count = 0
        if self.north == 0:
            count += 1
        if self.south == 0:
            count += 1
        if self.east == 0:
            count += 1
        if self.west == 0:
            count += 1
        return count

    def isNotIntersection(self):
        """return true if it is not an intersection"""
        count = self.__counts
        if count >= 3:
            return True
        else:
            return False

    def output(self):
        line = '%4s %8s %8s %8s %8s %8s' % (self.id, self.at, self.north, self.south, self.east, self.west)
        print(line)



class EMMELinkFile:
    """
    define a class for EMME link file. Each row in the file represents an intersection and
    is kept in EMMEAjacentNode. All intersections are kept in a list.
    """
    def __init__(self, filename=None):
        self.filename = filename
        self.intersections = []
        fp = None
        try:
            fp = open(filename, "r")
            lines = fp.readlines()
            lines = lines[3:]   # delete the first three rows (header)
            for line in lines:
                items = line.split(' ')
                intersection = EMMEAjacentNode(int(items[0]), int(items[1]), int(items[2]), int(items[3]), int(items[4]), int(items[5]))
                intersection.output()
                self.intersections.append(intersection)
        except IOError:
            print(filename + "is not a valid file")
        except IndexError:
            raise IndexError
        finally:
            if fp != None:
                fp.close()

    def __comapreAssending(self, x, y):
        if int(x.id) > int(y.id):
            return 1
        elif int(x.id) == int(y.id):
            return 0
        else:   # x < y
            return -1

    def __compareDecending(self, x, y):
        if int(x.id) > int(y.id):
            return -1
        elif int(x.id) == int(y.id):
            return 0
        else:   # x < y
            return 1

    def sort(self, isAsscending):
        """
        sort the intersections list in either asscending or decending order.
        isAsscending: in asscending order if True, otherwise False.
        """
        if isAsscending:
            self.intersections.sort(self.__comapreAssending)
        else:
            self.intersections.sort(self.__compareDecending)

    def output(self):
        for inter in self.intersections:
            inter.output()

    def size(self):
        """
        return how many EMMEAdjacentNode objects are stored in the intersections
        list.
        """
        return len(self.intersections)


class EMMETMVol:
    '''
    define a class for turning movement volume in EMME format
      jnode  inode  knode      result
        979   5417   5417           0
    '''
    def __init__(self, at, fromnode, tonode, vol):
        self.at = at
        self.fromnode = fromnode
        self.tonode = tonode
        self.vol = vol
        self.key = at + "-" + fromnode + "-" + tonode # unique index for sorting and search.

    def output(self):
        line = '%20s %8s %8s %8s %8s' % (self.key, self.at, self.fromnode, self.tonode, self.vol)
        print(line)
        return line

class EMMETMFile:
    '''
    define a class to keep all EMME turning movemnt volumes.
    '''

    def __init__(self, filename):
        self.filename = filename
        self.tmVols = []
        fp = None
        try:
            fp = open(filename, "r")
            lines = fp.readlines()
            lines = lines[1:]   # delete the first rows (header)
            for line in lines:
                items = line.split()
                tm = EMMETMVol(items[0], items[1], items[2], items[4])
                self.tmVols.append(tm)
        except IOError:
            print(filename + "is not a valid file")
        except IndexError:
            raise IndexError
        finally:
            if fp != None:
                fp.close()

    def size(self):
        '''
        return how many EMMETMVol objects are stored in the TMVols list.
        '''
        return len(self.tmVols)

    def sort(self, isAsscending):
        self.tmVols = sorted(self.tmVols, key = lambda x: getattr(x, 'key'), reverse = not(isAsscending))
        

    def output(self):
        with open('TMVol.prn', 'w') as f:
            for tm in self.tmVols:
                line = tm.output()
                f.write(line + '\n')

    def search(self, key):
        '''
        Binary search. Assume the tmVols list is sorted. Return the EMTMVol object
        if found, otherwise return None.
        key: Search index.
        '''
        low = 0
        high = self.size() - 1

        while (low <= high):
            mid = int((low + high) / 2)
            if key == '1907-5010-5478':
                print(self.tmVols[mid].key)
            if self.tmVols[mid].key < key:
                low = mid + 1
            elif self.tmVols[mid].key > key:
                high = mid - 1
            else:
                #self.tmVols[mid].output()
                return self.tmVols[mid]
        return None

class TMVol:
    '''
    Define a turning movement class to store turning movement volumes for a
    standard intersection (four legs, 12 movements).
    the turning movement volumes are stored in a list by the order shown below.
    INT        NB             SB             EB             WB
     #   LT   TH   RT   LT   TH   RT   LT   TH   RT   LT   TH   RT
     1    0    0    0   75    0   77   39  242    0    0  321   15
    '''
    def __init__(self, intid, nbl=0, nbt=0, nbr=0, sbl=0, sbt=0, sbr=0, ebl=0, ebt=0, ebr=0, wbl=0, wbt=0, wbr=0):
        self.intid = intid
        self.NBL = nbl
        self.NBT = nbt
        self.NBR = nbr
        self.SBL = sbl
        self.SBT = sbt
        self.SBR = sbr
        self.EBL = ebl
        self.EBT = ebt
        self.EBR = ebr
        self.WBL = wbl
        self.WBT = wbt
        self.WBR = wbr
        self.tmvol = [nbl, nbt, nbr, sbl, sbt, sbr, ebl, ebt, ebr, wbl, wbt, wbr]

    def output(self):
        line = '%6s %6s %6s %6s %6s %6s %6s %6s %6s %6s %6s %6s %6s' % (self.intid, self.NBL, self.NBT, self.NBR, self.SBL, self.SBT, self.SBR, self.EBL, self.EBT, self.EBR, self.WBL, self.WBT, self.WBR)
        print(line)


class TMVolFile:
    def __init__(self, fp=None):
        self.fp = fp
        self.tmVols = []

    def add(self, obj):
        self.tmVols.append(obj)

    def size(self):
        return len(self.tmVols)

    def output(self, fp):
        fp.write("%5s %10s %15s %15s %15s\n" % ("INT", "NB", "SB", "EB", "WB"))
        fp.write("%5s %5s %5s %5s %5s %5s %5s %5s %5s %5s %5s %5s %5s\n" % ("#", "LT", "TH", "RT", "LT", "TH", "RT", "LT", "TH", "RT", "LT", "TH", "RT"))
        try:
            for tm in self.tmVols:
                line = "%5s %5s %5s %5s %5s %5s %5s %5s %5s %5s %5s %5s %5s\n" % (tm.intid, tm.NBL, tm.NBT, tm.NBR, tm.SBL, tm.SBT, tm.SBR, tm.EBL, tm.EBT, tm.EBR, tm.WBL, tm.WBT, tm.WBR)
                fp.write(line)

        except:
            print("Turning movement volumes cannot be written to file")



