###############################################################################
#
# class MoveTrain
# Calls dispatcher to e train from one station to another
# given engine and start and end positions
#
###############################################################################

import os
import java
import jmri
import math

from javax.swing import JTable, JScrollPane, JFrame, JPanel, JComboBox,  BorderFactory, DefaultCellEditor, JLabel, UIManager, SwingConstants
from javax.swing.table import  TableCellRenderer, DefaultTableCellRenderer
from java.awt.event import MouseAdapter,MouseEvent, WindowListener, WindowEvent
from java.awt import GridLayout, Dimension, BorderLayout, Color
from javax.swing.table import AbstractTableModel, DefaultTableModel
from java.lang.Object import getClass
import jarray
from javax.swing.event import TableModelListener, TableModelEvent
#, defaultTableModel


#import platform

class MoveTrain(jmri.jmrit.automat.AbstractAutomaton):

    global trains_dispatched
    global trains

    def __init__(self, station_from_name, station_to_name, train_name, graph):
        self.logLevel = 0
        self.station_from_name = station_from_name
        self.station_to_name = station_to_name
        self.train_name = train_name
        self.graph = graph

    def setup(self):
        return True

    def handle(self):
        #move between stations in the thread
        if self.logLevel > 1: print"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        if self.logLevel > 1: print "move between stations in the thread"
        if self.logLevel > 1: print"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        self.move_between_stations(self.station_from_name, self.station_to_name, self.train_name, self.graph)
        return False

    def move_between_stations(self, station_from_name, station_to_name, train_name, graph):
        if self.logLevel > 1: print "Moving from " + station_from_name + " to " + station_to_name
        #need to look up the required transit in the graph
        StateVertex_start = station_from_name
        StateVertex_end = station_to_name
        # for e in graph.edgeSet():
        # if self.logLevel > 1: print (graph.getEdgeSource(e) + " --> " + graph.getEdgeTarget(e))
        if self.logLevel > 1: print "calling shortest path", StateVertex_start, StateVertex_end
        paths = DijkstraShortestPath.findPathBetween(graph, StateVertex_start, StateVertex_end)
        if self.logLevel > 0: print "graph", graph
        if self.logLevel > 0: print "paths", paths
        if self.logLevel > 0: print "returned from shortest path"
        if self.logLevel > 1: print "in move_between_stations trains = ", trains, "train_name = ", train_name
        train = trains[train_name]
        if self.logLevel > 1: print "train" , train
        penultimate_block_name = train["penultimate_block_name"]
        if self.logLevel > 1: print "penultimate_block_name" , penultimate_block_name
        previous_edge = train["edge"]
        previous_direction = train["direction"]

        trains_dispatched.append(str(train_name))

        count_path = 0

        if paths == None or paths == []:
            print "1Error cannot find shortest path. restart the system. " + \
                  "The stop dispatcher system routine does not work properly with multiple layout panels. Sorry"
            return

        for e in paths:
            # need to check whether:
            #   last block of previous edge and current first block
            #   are the same

            # if the same the train must change direction. as we are going in and out the same path
            #
            previous_edge = train["edge"]
            penultimate_block_name = train["penultimate_block_name"]
            previous_direction = train["direction"]
            current_edge = e
            neighbor_name = e.getItem("neighbor_name")
            if self.logLevel > 0: print train
            if self.logLevel > 0: print "neighbor_name = ", neighbor_name
            if self.logLevel > 0: print "penultimate_block_name" , penultimate_block_name

            BlockManager = jmri.InstanceManager.getDefault(jmri.BlockManager)
            previous_block = BlockManager.getBlock(penultimate_block_name)
            current_block = BlockManager.getBlock(previous_edge.getItem("last_block_name"))
            next_block = BlockManager.getBlock(current_edge.getItem("second_block_name"))
            if count_path == 0:
                # we are on a new path and must determine the direction
                [transit_direction, transit_instruction]  = self.set_direction(previous_block, current_block, next_block, previous_direction)
                self.announce1(e, transit_direction, transit_instruction, train)
            else:
                # if there are several edges in a path, then we are on an express route, and there is a change in direction at each junction
                if previous_block.getUserName() == next_block.getUserName() : #we are at a stub/siding
                    if previous_direction == "forward":
                        transit_direction = "reverse"
                    else:
                        transit_direction = "forward"
                    transit_instruction = "stub"
                else:
                    [transit_direction, transit_instruction] = self.set_direction(previous_block, current_block, next_block, previous_direction)

                speech_reqd = self.speech_required_flag()
                # make announcement as train enters platform
                # print "making announcement"
                self.announce1(e, transit_direction, transit_instruction, train)
                time_to_stop_in_station = self.get_time_to_stop_in_station(e, transit_direction)
                t = time_to_stop_in_station / 1000
                msg = "started waiting for " + str(int(t)) + " seconds"
                if self.logLevel > 0: self.speak(msg)
                self.waitMsec(int(time_to_stop_in_station))
                msg = "finished waiting for " + str(t) + " seconds"
                if self.logLevel > 0: self.speak(msg)

            result = self.move(e, transit_direction, transit_instruction,  train_name)
            if self.logLevel > 1: print "returned from self.move, result = ", result
            if result == False:
                trains_dispatched.remove(str(train_name))
                break
            #store the current edge for next move
            train["edge"] = e
            train["penultimate_block_name"] = e.getItem("penultimate_block_name")
            train["direction"] = transit_direction
            count_path +=1

        if self.logLevel > 1: print "transit finished, removing train from dispatch list"
        if str(train_name) in trains_dispatched:
            trains_dispatched.remove(str(train_name))
        if self.logLevel > 1: print "trains_dispatched", trains_dispatched

    def set_direction(self, previous_block, current_block, next_block, previous_direction):
        LayoutBlockManager=jmri.InstanceManager.getDefault(jmri.jmrit.display.layoutEditor.LayoutBlockManager)
        current_layout_block = LayoutBlockManager.getLayoutBlock(current_block)
        if current_layout_block.validThroughPath(previous_block, next_block):
            transit_instruction = "same"
        else:
            transit_instruction = "change"
        if transit_instruction == "change":
            if previous_direction == "forward":
                transit_direction = "reverse"
            else:
                transit_direction = "forward"
        else:
            transit_direction = previous_direction
        return [transit_direction, transit_instruction]


    def get_time_to_stop_in_station(self, edge, direction):

        if direction == "forward":
            filename_fwd = self.get_filename(edge, "fwd")
            trainInfo_fwd = jmri.jmrit.dispatcher.TrainInfoFile().readTrainInfo(filename_fwd)
            station_wait_time = trainInfo_fwd.getWaitTime()
        else:
            filename_fwd = self.get_filename(edge, "rvs")
            trainInfo_fwd = jmri.jmrit.dispatcher.TrainInfoFile().readTrainInfo(filename_fwd)
            station_wait_time = trainInfo_fwd.getWaitTime()
        if station_wait_time != None:
            return math.floor(float(station_wait_time+0)) * 1000  # set in milli secs
        else:
            return 0

    def is_integer(self, n):
        try:
            if n == None: return False
            float(n)
        except ValueError:
            return False
        else:
            return float(n).is_integer()

    def announce1(self, e, direction, instruction, train):
        to_name = e.getTarget()
        from_name = e.getSource()
        speech_reqd = self.speech_required_flag()
        self.announce( from_name, to_name, speech_reqd, direction, instruction)

    def move(self, e, direction, instruction, train):
        if self.logLevel > 1: print "++++++++++++++++++++++++"
        if self.logLevel > 1: print e, "Target", e.getTarget()
        if self.logLevel > 1: print e, "Source", e.getSource()
        if self.logLevel > 1: print e, "Train", train
        if self.logLevel > 1: print "++++++++++++++++++++++++"
        to_name = e.getTarget()
        from_name = e.getSource()
        sensor_move_name = "MoveInProgress"+to_name.replace(" ","_")

        self.set_sensor(sensor_move_name, "active")
        speech_reqd = self.speech_required_flag()
        #self.announce( from_name, to_name, speech_reqd, direction, instruction)  # now done when train arrives in platfor instead of when leaving
        if self.logLevel > 1: print "***************************"
        result = self.call_dispatch(e, direction, train)
        if self.logLevel > 1: print "______________________"
        if result == True:
            #Wait for the Active Trains List to have the
            DF = jmri.InstanceManager.getDefault(jmri.jmrit.dispatcher.DispatcherFrame)
            java_active_trains_list = DF.getActiveTrainsList()
            java_active_trains_Arraylist= java.util.ArrayList(java_active_trains_list)
            for t in java_active_trains_Arraylist:
                if self.logLevel > 1: print "t=",t,t.getActiveTrainName()
                #active_trains_list = java.util.Arrays.asList(java_active_trains_list)
            if self.logLevel > 1: print "!!!!!!!! train = ", train, "active_trains_list", java_active_trains_Arraylist
            active_train_names_list = [str(t.getTrainName()) for t in java_active_trains_Arraylist]
            if self.logLevel > 1: print "!!!!!!!! train = ", train, "active_trains_name_list", active_train_names_list
            while train in active_train_names_list:
                self.waitMsec(500)
                DF = jmri.InstanceManager.getDefault(jmri.jmrit.dispatcher.DispatcherFrame)
                active_trains_list = DF.getActiveTrainsList()
                active_train_names_list = [str(t.getTrainName()) for t in java_active_trains_Arraylist]
                java_active_trains_Arraylist= java.util.ArrayList(java_active_trains_list)
                active_train_names_list = [str(t.getTrainName()) for t in java_active_trains_Arraylist]
                if self.logLevel > 1: print "!!!!!!!! train = ", train, "active_train_names_list", active_train_names_list
            self.set_sensor(sensor_move_name, "inactive")
            if self.logLevel > 1: print ("+++++ sensor " + sensor_move_name + " inactive")
        else:
            self.set_sensor(sensor_move_name, "inactive")
        return result

    def speech_required_flag(self):
        self.sound_sensor = sensors.getSensor("soundSensor")
        if self.sound_sensor is None:
            OptionDialog().displayMessage("No sound Sensor set up")
            return None
        sound_state = self.sound_sensor.getKnownState()
        if self.logLevel > 1: print sound_state,ACTIVE
        if sound_state == ACTIVE:
            sound_flag = True
        else:
            sound_flag = False
        return sound_flag

    def call_dispatch(self, e, direction, train):
        if self.logLevel > 1: print ("in dispatch")
        to_name = e.getTarget()
        from_name = e.getSource()
        if self.logLevel > 1: print ("incall_dispatch: move from " + from_name + " to " + to_name)

        if direction == "forward":
            filename = self.get_filename(e, "fwd")
        else:
            filename = self.get_filename(e, "rvs")

        if self.logLevel > 1: print "filename = ", filename, "direction = " , direction
        result = self.doDispatch(filename, "ROSTER", train)
        if self.logLevel > 1: print "result", result
        return result

    def get_filename(self, e, suffix):

        # suffix is "fwd" or "rvs"
        # e is edge

        from_station_name = g.g_express.getEdgeSource(e)
        to_station_name = g.g_express.getEdgeTarget(e)
        neighbor_name = e.getItem("neighbor_name")
        index = e.getItem("index")

        filename = "From " + str(from_station_name) + " To " + str(to_station_name) + " Via " + str(neighbor_name) + " " + str(index)
        filename = filename.replace(" ", "_")
        filename = filename + "_" + suffix + ".xml"

        return filename

        #    Dispatch (<filename.xml>, [USER | ROSTER | OPERATIONS >,<dccAddress, RosterEntryName or Operations>

    def doDispatch(self, traininfoFileName, type, value):
        DF = jmri.InstanceManager.getDefault(jmri.jmrit.dispatcher.DispatcherFrame)
        #try:
        if self.logLevel > 1: print "traininfoFileName",traininfoFileName
        result = DF.loadTrainFromTrainInfo(traininfoFileName, type, value)
        if result == -1:
            if self.logLevel > 1: print "result from dispatcher frame" , result
            return False  #No train allocated
        else:
            if self.logLevel > 1: print "result from dispatcher frame" , result
            return True
        # except:
        # if self.logLevel > 1: print ("FAILURE tried to run dispatcher with file {} type {} value {}".format(traininfoFileName,  type, value))
        # pass
        # return False


    def set_sensor(self, sensorName, sensorState):
        sensor = sensors.getSensor(sensorName)
        if sensor is None:
            self.displayMessage('{} - Sensor {} not found'.format(self.threadName, sensorName))
            return
        if sensorState == 'active':
            newState = ACTIVE
        elif sensorState == 'inactive':
            if self.logLevel > 1: print "set_sensor ", sensorName, 'inactive'
            newState = INACTIVE
        else:
            self.displayMessage('{} - Sensor state, {}, is not valid'.format(self.threadName, sensorState))
        sensor.setKnownState(newState)
        return

    def wait_sensor(self, sensorName, sensorState):
        sensor = sensors.getSensor(sensorName)
        if sensor is None:
            self.displayMessage('{} - Sensor {} not found'.format(self.threadName, sensorName))
            return
        if sensorState == 'active':
            self.waitSensorActive(sensor)
        elif sensorState == 'inactive':
            self.waitSensorInactive(sensor)
        else:
            self.displayMessage('{} - Sensor state, {}, is not valid'.format(self.threadName, sensorState))

    ## ***********************************************************************************

    ## sound routines

    ## ***********************************************************************************

    def getOperatingSystem(self):
        #detecting the operating system using `os.name` System property
        os = java.lang.System.getProperty("os.name")
        os = os.lower()
        if "win" in os:
            return "WINDOWS"
        elif "nix" in os or "nux" in os or "aix" in os:
            return "LINUX"
        elif "mac" in os:
            return "MAC"
        return None

    def speak(self, msg):
        os = self.getOperatingSystem()
        if os == "WINDOWS":
            self.speak_windows(msg)
        elif os == "LINUX":
            self.speak_linux(msg)
        elif os == "MAC":
            self.speak_mac(msg)

    def speak_windows(self,msg) :
        try:
            cmd1 = "Add-Type -AssemblyName System.Speech"
            cmd2 = '$SpeechSynthesizer = New-Object -TypeName System.Speech.Synthesis.SpeechSynthesizer'
            cmd3 = "$SpeechSynthesizer.Speak('" + msg + "')"
            cmd = cmd1 + ";" + cmd2 + ";" + cmd3
            os.system("powershell " + cmd )
        except:
            msg = "Announcements not working \n Only supported on windows versions with powershell and SpeechSynthesizer"
            JOptionPane.showMessageDialog(None, msg, "Warning", JOptionPane.WARNING_MESSAGE)

    def speak_mac(self, msg):
        try:
            java.lang.Runtime.getRuntime().exec("say {}".format(msg))
        except:
            msg = "Announcements not working \n say not working on your Mac"
            JOptionPane.showMessageDialog(None, msg, "Warning", JOptionPane.WARNING_MESSAGE)

    def speak_linux(self, msg):
        try:
            #os.system("""echo %s | spd-say -e -w -t male1""" % (msg,))
            #os.system("""echo %s | spd-say -e -w -t female3""" % (msg,))
            #os.system("""echo %s | spd-say -e -w -t child_male""" % (msg,))
            os.system("""echo %s | spd-say -e -w -t child_female""" % (msg,))  #slightly slower
        except:
            msg = "Announcements not working \n spd-say not set up on your linux system"
            JOptionPane.showMessageDialog(None, msg, "Warning", JOptionPane.WARNING_MESSAGE)

    def announce(self, fromblockname, toblockname, speak_on, direction, instruction):

        from_station = self.get_station_name(fromblockname)
        to_station = self.get_station_name(toblockname)

        if speak_on == True:
            if direction == "forward":
                platform = " platform 1 "
            else:
                platform = " platform 2 "
            self.speak("The train in" + platform + " is due to depart to " + to_station)
            #self.speak("The train in "+ from_station + " is due to depart to " + to_station )

    def get_station_name(self, block_name):
        BlockManager = jmri.InstanceManager.getDefault(jmri.BlockManager)
        block = BlockManager.getBlock(block_name)
        comment = block.getComment()
        # % is the delimeter for block name
        delimeter = '"'
        if delimeter in comment:
            station_name = self.get_substring_between_delimeters(comment, delimeter)
        else:
            station_name = block_name
        return station_name

    def get_substring_between_delimeters(self, comment, delimeter):
        start = delimeter
        end = delimeter
        s = comment
        substring = s[s.find(start)+len(start):s.rfind(end)]
        return substring


    def bell(self, bell_on = "True"):
        if bell_on == "True":
            snd = jmri.jmrit.Sound("resources/sounds/Bell.wav")
            snd.play(snd)

class NewTrainMaster(jmri.jmrit.automat.AbstractAutomaton):

    # responds to the newTrainSensor, and allocates trains available for dispatching
    # we make the allocated flag global as we will use it in DispatchMaster when we dispatch a train

    global trains_allocated
    logLevel = 0
    #instanceList = []   # List of file based instances

    def init(self):
        self.logLevel = 0
        if self.logLevel > 0: print 'Create Stop Thread'

    def setup(self):
        global trains_allocated
        #self.initialise_train()
        newTrainSensor = "newTrainSensor"
        self.new_train_sensor = sensors.getSensor(newTrainSensor)
        if self.new_train_sensor is None:
            return False
        self.new_train_sensor.setKnownState(INACTIVE)
        trains_allocated = []
        self.od = OptionDialog()
        return True

    def handle(self):

        global trains_allocated

        #this repeats
        # wait for a sensor requesting to check for new train
        if self.logLevel > 0: print ("wait for a sensor requesting to check for new train")

        self.waitSensorActive(self.new_train_sensor)
        self.new_train_sensor.setKnownState(INACTIVE)


        #display the allocated trains
        msg = "choose"
        actions = ["setup 1 train","setup several trains", "check train direction", "reset trains"]
        action = self.od.List(msg, actions)
        if action == "setup 1 train":
            # msg = "choose"
            # actions = ["setup 1 train","setup 2+ trains"]
            # action = self.od.List(msg, actions)
            # if action == "setup 1 train":
            station_block_name, new_train_name = self.check_new_train_in_siding()
            if self.logLevel > 0: print "station_block_name",station_block_name, "existing train name", new_train_name
            if station_block_name != None:
                # take actions for new train
                if new_train_name == None:
                    all_trains = self.get_all_roster_entries_with_speed_profile()
                    if all_trains == []:
                        msg = "There are no engines with speed profiles, cannot operate without any"
                        JOptionPane.showMessageDialog(None,msg)
                    else:
                        msg = self.get_all_trains_msg()
                        title = None
                        opt1 = "Select section"
                        s = self.od.customMessage(msg, title, opt1)
                        if self.logLevel > 0: print "station_block_name",station_block_name, "s", s
                        if self.od.CLOSED_OPTION == False:
                            msg = "Select section"
                            sections_to_choose = self.get_non_allocated_trains_sections()
                            new_section_name = self.od.List(msg, sections_to_choose)
                            if self.od.CLOSED_OPTION == False:
                                msg = "Select the train in " + new_section_name
                                trains_to_choose = self.get_non_allocated_trains()
                                if trains_to_choose == []:
                                    s = OptionDialog().displayMessage("no more trains with speed profiles \nto select")
                                else:
                                    new_train_name = self.od.List(msg, trains_to_choose)
                                    if self.od.CLOSED_OPTION == False:
                                        if new_train_name not in trains_allocated:
                                            trains_allocated.append(new_train_name)
                                        #print "*****", "new_train_name", new_train_name, "new_section_name", new_section_name
                                        self.add_to_train_list_and_set_new_train_location(new_train_name, new_section_name)
                                        if self.od.CLOSED_OPTION == False:  #only do this if have not closed a frame in add_to_train_list_and_set_new_train_location
                                            self.set_blockcontents(new_section_name, new_train_name)
                                            self.set_length(new_train_name)
                else:
                    if self.logLevel > 1 : print "!!!!5"
                    trains_to_choose = self.get_non_allocated_trains()
                    msg = "In " + station_block_name + " Select train roster"
                    new_train_name = modifiableJComboBox(trains_to_choose,msg).return_val()
                    if new_train_name not in trains_allocated:
                        trains_allocated.append(new_train_name)

                    self.add_to_train_list_and_set_new_train_location(new_train_name, station_block_name)
                    self.set_blockcontents(station_block_name, new_train_name)
                    self.set_length(new_train_name)
            else:
                if self.logLevel > 0: print "about to show message no new train in siding"
                msg = self.get_all_trains_msg()
                msg +=  "\nPut a train in a section so it can be allocated!\n"
                title = "All trains allocated"
                opt1 = "Continue"
                opt2 = "Delete the trains already set up and start again"
                ans = self.od.customQuestionMessage2(msg, title, opt1, opt2)
                if self.od.CLOSED_OPTION == True:
                    pass
                elif ans == JOptionPane.NO_OPTION:
                    self.reset_allocation()
        elif action == "setup several trains":
            createandshowGUI(self)


        elif action == "reset trains":
            msg = self.get_all_trains_msg()
            msg +=  "\nReset all these trains\n"
            title = "Reset"
            opt1 = "Continue"
            opt2 = "Delete the trains already set up and start again"
            ans = self.od.customQuestionMessage2(msg, title, opt1, opt2)
            if self.od.CLOSED_OPTION == True:
                pass
            elif ans == JOptionPane.NO_OPTION:
                self.reset_allocation1()
        #elif action == "reset control sensors"
        else: #"check train direction"
            all_trains = self.get_all_roster_entries_with_speed_profile()
            if all_trains == []:
                msg = "There are no engines with speed profiles, cannot operate without any"
                JOptionPane.showMessageDialog(None,msg)
            else:
                msg = self.get_allocated_trains_msg()
                title = None
                opt1 = "Select section"
                s = self.od.customMessage(msg, title, opt1)
                if self.logLevel > 0: print "station_block_name",station_block_name, "s", s
                if self.od.CLOSED_OPTION == False:
                    msg = "Select section"
                    sections_to_choose = self.get_allocated_trains_sections()
                    new_section_name = self.od.List(msg, sections_to_choose)
                    if self.od.CLOSED_OPTION == False:
                        msg = "Select the train in " + new_section_name
                        trains_to_choose = self.get_allocated_trains()
                        if trains_to_choose == []:
                            s = OptionDialog().displayMessage("no more trains with speed profiles \nto select")
                        else:
                            new_train_name = self.od.List(msg, trains_to_choose)
                            if self.od.CLOSED_OPTION == False:
                                #print "need to find the direction of train", new_train_name
                                self.check_train_direction(new_train_name, new_section_name)

        return True

    # def createAndShowGUI(self, super):
    #     createandshowGUI(self,super)



    def check_train_direction(self, train_name, station_block_name):
        global train
        if train_name in trains:
            train = trains[train_name]
            direction = train["direction"]
            #print direction
            penultimate_layout_block = self.get_penultimate_layout_block(station_block_name)

            saved_state = penultimate_layout_block.getUseExtraColor()
            in_siding = self.in_siding(station_block_name)
            if not in_siding:
                # highlight the penultimate block
                penultimate_layout_block.setUseExtraColor(True)
                msg = "train travelling " + direction + " away from highlighted block"
                s = OptionDialog().displayMessage(msg)
                penultimate_layout_block.setUseExtraColor(saved_state)
            else:
                msg = "train travelling " + direction + " away from siding"
                s = OptionDialog().displayMessage(msg)
                penultimate_layout_block.setUseExtraColor(saved_state)


    def get_train_length(self, new_train_name):
        EngineManager=jmri.InstanceManager.getDefault(jmri.jmrit.operations.rollingstock.engines.EngineManager)
        engineRoad = "Set by Dispatcher System"
        engineNumber = new_train_name
        engine = EngineManager.newRS(engineRoad, engineNumber)
        #get the current length of the engine
        default = "10"
        current_length = engine.getLength()
        return [engine, current_length]

    def set_length(self, new_train_name):
        [engine,current_length] = self.get_train_length(new_train_name)
        if current_length == "0":
            current_length = default
            engine.setLength(default)
        #ask if want to change length
        title = "Set the length of the engine/train"
        msg = "length of " + new_train_name + " = " + str(current_length)
        opt1 = "OK"
        opt2 = "Change"
        request = self.od.customQuestionMessage2str(msg,title,opt1, opt2)
        if request == "Change":
            #set the new length
            msg = "input length of " + new_train_name
            title = "length of " + new_train_name
            default_value = current_length
            new_length = self.od.input(msg, title, default_value)
            engine.setLength(new_length)

    def get_allocated_trains_msg(self):
        allocated_trains =[ str(train) + " in block " + str(trains[train]["edge"].getTarget()) for train in trains_allocated]
        if allocated_trains ==[]:
            msg = "There are no allocated trains \n"
        else:
            msg = "The Allocated trains are: \n" +'\n'.join(allocated_trains)
        return msg

    def get_allocated_trains(self):
        return trains_allocated

    def get_non_allocated_trains(self):
        all_trains = self.get_all_roster_entries_with_speed_profile()
        non_allocated_trains = copy.copy(all_trains)
        for train in trains_allocated:
            if train in non_allocated_trains:
                non_allocated_trains.remove(train)
        return non_allocated_trains

    def get_non_allocated_trains_msg(self):
        trains_in_sections_allocated1 = self.trains_in_sections_allocated()
        msg = "the non-allocated trains are in sections: \n\n" + "\n".join(["  " + str(train[0]) for train in trains_in_sections_allocated1 if train[2] == "non-allocated"])
        return msg

    def get_all_sections(self):
        return [section for section in sections.getNamedBeanSet()]

    def get_all_blocks(self):
        return [block for block in blocks.getNamedBeanSet()]
    
    def get_sections_for_trains_in_table(self, trains_in_table):
        return [str(train) for train in trains_in_table]

    def get_non_allocated_trains_sections(self):
        trains_in_sections_allocated1 = self.trains_in_sections_allocated()
        return [str(train[0]) for train in trains_in_sections_allocated1 if train[2] == "non-allocated"]

    def get_allocated_trains_sections(self):
        trains_in_sections_allocated1 = self.trains_in_sections_allocated()
        return [str(train[0]) for train in trains_in_sections_allocated1 if train[2] == "allocated"]

    def get_all_trains_msg(self):
        return self.get_allocated_trains_msg() + "\n" + self.get_non_allocated_trains_msg()

    def reset_allocation(self):
        global trains_allocated
        if trains_allocated == []:
            if self.logLevel > 0: print ("a")
            msg = "Nothing to reset"
            OptionDialog().displayMessage(msg)
        else:
            if self.logLevel > 0: print ("b")
            msg = "Select train to modify"
            train_name_to_remove = modifiableJComboBox(trains_allocated,msg).return_val()
            trains_allocated.remove(train_name_to_remove)
            self.new_train_sensor.setKnownState(ACTIVE)

    def reset_allocation1(self):
        global trains_allocated
        if trains_allocated == []:
            if self.logLevel > 0: print ("a")
            msg = "Nothing to reset"
            OptionDialog().displayMessage(msg)
        else:
            if self.logLevel > 0: print ("b")
            #set trains_allocated to []
            for train_name_to_remove in trains_allocated:
                msg = "Select train to modify"
                #train_name_to_remove = modifiableJComboBox(trains_allocated,msg).return_val()
                trains_allocated.remove(train_name_to_remove)           #remove the train from trains_allocated
                self.reset_train_in_blocks(train_name_to_remove)  #remove the blockcontents text
            if self.logLevel > 0: print "trains_allocated",trains_allocated
            #self.new_train_sensor.setKnownState(ACTIVE)

    def get_all_roster_entries_with_speed_profile(self):
        roster_entries_with_speed_profile = []
        r = jmri.jmrit.roster.Roster.getDefault()
        for roster_entry in jmri.jmrit.roster.Roster.getAllEntries(r):
            if self.logLevel > 0: print "roster_entry.getSpeedProfile()",roster_entry,roster_entry.getSpeedProfile()
            if roster_entry.getSpeedProfile() != None:
                roster_entries_with_speed_profile.append(roster_entry.getId())
                if self.logLevel > 0: print "roster_entry.getId()",roster_entry.getId()
        return roster_entries_with_speed_profile

    def add_to_train_list_and_set_new_train_location(self, train_name, station_block_name):
        # trains is a dictionary, with keys of the train_name
        # each value is itself a dictionary with 3 items
        # edge
        # penultimate_block_name
        # direction
        global train
        global trains_allocated
        if train_name not in trains:
            trains[train_name] = {}
            train = trains[train_name]
            train["train_name"] = train_name
        else:
            #train_name = self.get_train_name()
            self.set_train_in_block(station_block_name, train_name)

        # 2) set the last traversed edge to the edge going into the siding
        edge = None
        j = 0
        #print "edge_before" , edge
        #print "g.g_stopping.edgesOf(station_block_name)",g.g_stopping.edgesOf(station_block_name)
        break1 = False
        #print "no edges", g.g_stopping.edgeSet()
        # for e in g.g_stopping.edgeSet():
        #     print "e" , e
        for e in g.g_stopping.edgeSet():
            j+=1
            LayoutBlockManager=jmri.InstanceManager.getDefault(jmri.jmrit.display.layoutEditor.LayoutBlockManager)
            station_block = LayoutBlockManager.getLayoutBlock(station_block_name)
            number_neighbors = station_block.getNumberOfNeighbours()
            #print "station block number neighbors", number_neighbors
            in_siding = (number_neighbors == 1)
            #print "in_siding", in_siding
            for i in range(station_block.getNumberOfNeighbours()):
                neighbor_name = station_block.getNeighbourAtIndex(i).getDisplayName()
                #print "neighbor_name", neighbor_name
                #print "station_block_name", station_block_name
                #print "penultimate_block_name", e.getItem("penultimate_block_name")
                #print "last_block_name", e.getItem("last_block_name")
                #print "***************"
                if e.getItem("penultimate_block_name") == neighbor_name and e.getItem("last_block_name") == station_block_name:
                    edge = e
                    break1 = True
            if break1 == True:
                break
            #print "******************************++"
        if edge == None:
            print "Error the required block has not been found. restart and try again. Sorry!"
            return
        train["edge"] = edge
        train["penultimate_block_name"] = edge.getItem("penultimate_block_name")

        # 3) set direction so can check direction of transit

        penultimate_block_name = edge.getItem("penultimate_block_name")
        penultimate_layout_block = LayoutBlockManager.getLayoutBlock(penultimate_block_name)
        saved_state = penultimate_layout_block.getUseExtraColor()
        if not in_siding:
            # highlight the penultimate block
            penultimate_layout_block.setUseExtraColor(True)
        train_direction = self.set_train_direction(station_block_name, in_siding)
        #check the condition set in set_train_direction
        train["direction"] = train_direction
        penultimate_layout_block.setUseExtraColor(saved_state)

        # 4) add to allocated train list
        if str(train_name) not in trains_allocated:
            trains_allocated.append(str(train_name))


    def add_to_train_list_and_set_new_train_location0(self, train_name, station_block_name,
                                                      train_direction, train_length):
        # trains is a dictionary, with keys of the train_name
        # each value is itself a dictionary with 3 items
        # edge
        # penultimate_block_name
        # direction
        global train
        global trains_allocated
        if train_name not in trains:
            trains[train_name] = {}
            train = trains[train_name]
            train["train_name"] = train_name
        else:
            #train_name = self.get_train_name()
            self.set_train_in_block(station_block_name, train_name)

        # 2) set the last traversed edge to the edge going into the siding
        edge = None
        j = 0
        #print "edge_before" , edge
        #print "g.g_stopping.edgesOf(station_block_name)",g.g_stopping.edgesOf(station_block_name)
        break1 = False
        #print "no edges", g.g_stopping.edgeSet()
        # for e in g.g_stopping.edgeSet():
        #     print "e" , e
        for e in g.g_stopping.edgeSet():
            j+=1
            LayoutBlockManager=jmri.InstanceManager.getDefault(jmri.jmrit.display.layoutEditor.LayoutBlockManager)
            station_block = LayoutBlockManager.getLayoutBlock(station_block_name)
            number_neighbors = station_block.getNumberOfNeighbours()
            #print "station block number neighbors", number_neighbors
            in_siding = (number_neighbors == 1)
            #print "in_siding", in_siding
            for i in range(station_block.getNumberOfNeighbours()):
                neighbor_name = station_block.getNeighbourAtIndex(i).getDisplayName()
                #print "neighbor_name", neighbor_name
                #print "station_block_name", station_block_name
                #print "penultimate_block_name", e.getItem("penultimate_block_name")
                #print "last_block_name", e.getItem("last_block_name")
                #print "***************"
                if e.getItem("penultimate_block_name") == neighbor_name and e.getItem("last_block_name") == station_block_name:
                    edge = e
                    break1 = True
            if break1 == True:
                break
            #print "******************************++"
        if edge == None:
            print "Error the required block has not been found. restart and try again. Sorry!"
            return
        train["edge"] = edge
        train["penultimate_block_name"] = edge.getItem("penultimate_block_name")

        # 3) set direction so can check direction of transit

        # penultimate_block_name = edge.getItem("penultimate_block_name")
        # penultimate_layout_block = LayoutBlockManager.getLayoutBlock(penultimate_block_name)
        # saved_state = penultimate_layout_block.getUseExtraColor()
        # if not in_siding:
        #     # highlight the penultimate block
        #     penultimate_layout_block.setUseExtraColor(True)
        # train_direction = self.set_train_direction(station_block_name, in_siding)
        #check the condition set in set_train_direction
        train["direction"] = train_direction
        #penultimate_layout_block.setUseExtraColor(saved_state)

        # 4) add to allocated train list
        if str(train_name) not in trains_allocated:
            trains_allocated.append(str(train_name))

        [engine,current_length] = self.get_train_length(train_name)
        engine.setLength(train_length)



    def add_to_train_list_and_set_new_train_location2(self, train_name, station_block_name):

        # 1)
        # trains is a dictionary, with keys of the train_name
        # each value is itself a dictionary with 3 items
        # edge
        # penultimate_block_name
        # direction
        global train
        global trains_allocated
        print ("in add_to_train_list_and_set_new_train_location")
        if train_name not in trains:
            trains[train_name] = {}
            train = trains[train_name]
            train["train_name"] = train_name
        else:
            #train_name = self.get_train_name()
            # print("set_train_in_block")
            self.set_train_in_block(station_block_name, train_name)

        # print("calling highlight_penultimate_block")
        [edge, train_direction, result]  = self.highlight_penultimate_block(station_block_name)
        if edge == "Error" :
            return

            #check the condition set in set_train_direction
        train["direction"] = train_direction
        train["edge"] = edge
        train["penultimate_block_name"] = edge.getItem("penultimate_block_name")

        # 4) add to allocated train list
        if str(train_name) not in trains_allocated:
            trains_allocated.append(str(train_name))

    def add_to_train_list_and_set_new_train_location1(self, train_name, station_block_name):

        #     self.allocate_train(train_name)
        #     [edge, train_direction, result]  = self.highlight_penultimate_block(station_block_name)
        #     self.register_train(edge, train_direction)
        #
        #
        # def allocate_train(self, train_name):

        # 1)
        # trains is a dictionary, with keys of the train_name
        # each value is itself a dictionary with 3 items
        # edge
        # penultimate_block_name
        # direction
        global train
        global trains_allocated
        # print ("in add_to_train_list_and_set_new_train_location")
        if train_name not in trains:
            # print("train_name", train_name)
            # print("trains", trains)
            # print("train_name not in trains")
            trains[train_name] = {}
            train = trains[train_name]
            train["train_name"] = train_name
        else:
            #train_name = self.get_train_name()
            # print("set_train_in_block")
            self.set_train_in_block(station_block_name, train_name)

        # # print("calling highlight_penultimate_block")
        # [edge, train_direction, result]  = self.highlight_penultimate_block(station_block_name)
        #
        # #check the condition set in set_train_direction
        # train["direction"] = train_direction
        # train["edge"] = edge
        # train["penultimate_block_name"] = edge.getItem("penultimate_block_name")

        # 4) add to allocated train list
        if str(train_name) not in trains_allocated:
            trains_allocated.append(str(train_name))

    def highlight_penultimate_block(self, station_block_name):
        # print("highlight_penultimate_block")
        # 2) set the last traversed edge to the edge going into the siding
        edge = None
        j = 0
        #print "edge_before" , edge
        #print "g.g_stopping.edgesOf(station_block_name)",g.g_stopping.edgesOf(station_block_name)
        break1 = False
        #print "no edges", g.g_stopping.edgeSet()
        # for e in g.g_stopping.edgeSet():
        #     print "e" , e
        for e in g.g_stopping.edgeSet():
            j+=1
            LayoutBlockManager=jmri.InstanceManager.getDefault(jmri.jmrit.display.layoutEditor.LayoutBlockManager)
            station_block = LayoutBlockManager.getLayoutBlock(station_block_name)
            number_neighbors = station_block.getNumberOfNeighbours()
            #print "station block number neighbors", number_neighbors
            in_siding = (number_neighbors == 1)
            #print "in_siding", in_siding
            for i in range(station_block.getNumberOfNeighbours()):
                neighbor_name = station_block.getNeighbourAtIndex(i).getDisplayName()
                #print "neighbor_name", neighbor_name
                #print "station_block_name", station_block_name
                #print "penultimate_block_name", e.getItem("penultimate_block_name")
                #print "last_block_name", e.getItem("last_block_name")
                #print "***************"
                if e.getItem("penultimate_block_name") == neighbor_name and e.getItem("last_block_name") == station_block_name:
                    edge = e
                    break1 = True
            if break1 == True:
                break
            #print "******************************++"
        if edge == None:
            # print "Error the required block has not been found. restart and try again. Sorry!"
            return ["Error", "Error", "Error"]

         # 3) set direction so can check direction of transit

        penultimate_block_name = edge.getItem("penultimate_block_name")
        penultimate_layout_block = LayoutBlockManager.getLayoutBlock(penultimate_block_name)
        saved_state = penultimate_layout_block.getUseExtraColor()
        if not in_siding:
            # highlight the penultimate block
            penultimate_layout_block.setUseExtraColor(True)
        [train_direction, result] = self.set_train_direction(station_block_name, in_siding)
        penultimate_layout_block.setUseExtraColor(saved_state)

        return [edge, train_direction, result]

    def get_penultimate_layout_block(self, station_block_name):
        # get the last traversed edge to the edge of the station_block
        edge = None
        j = 0
        #print "edge_before" , edge
        #print "g.g_stopping.edgesOf(station_block_name)",g.g_stopping.edgesOf(station_block_name)
        break1 = False
        #print "no edges", g.g_stopping.edgeSet()
        for e in g.g_stopping.edgeSet():
            j+=1
            LayoutBlockManager=jmri.InstanceManager.getDefault(jmri.jmrit.display.layoutEditor.LayoutBlockManager)
            station_block = LayoutBlockManager.getLayoutBlock(station_block_name)
            number_neighbors = station_block.getNumberOfNeighbours()
            #print "station block number neighbors", number_neighbors
            in_siding = (number_neighbors == 1)
            for i in range(station_block.getNumberOfNeighbours()):
                neighbor_name = station_block.getNeighbourAtIndex(i).getDisplayName()
                # print "neighbor_name", neighbor_name
                # print "station_block_name", station_block_name
                # print "penultimate_block_name", e.getItem("penultimate_block_name")
                # print "last_block_name", e.getItem("last_block_name")
                # print "***************"
                if e.getItem("penultimate_block_name") == neighbor_name and e.getItem("last_block_name") == station_block_name:
                    edge = e
                    break1 = True
            if break1 == True:
                break
        if edge == None:
            # print "Error the required block has not been found. restart and try again. Sorry!"
            return None
        penultimate_block_name = edge.getItem("penultimate_block_name")
        LayoutBlockManager=jmri.InstanceManager.getDefault(jmri.jmrit.display.layoutEditor.LayoutBlockManager)
        penultimate_layout_block = LayoutBlockManager.getLayoutBlock(penultimate_block_name)
        return penultimate_layout_block

    def in_siding(self, station_block_name):
        LayoutBlockManager=jmri.InstanceManager.getDefault(jmri.jmrit.display.layoutEditor.LayoutBlockManager)
        station_block = LayoutBlockManager.getLayoutBlock(station_block_name)
        number_neighbors = station_block.getNumberOfNeighbours()
        #print "station block number neighbors", number_neighbors
        in_siding = (number_neighbors == 1)
        return in_siding

    def set_train_direction(self, block_name, in_siding):

        options = ["forward", "reverse"]
        default = "forward"
        if in_siding:
            msg = "In block: " + block_name + "\n" +'What way is train facing\ntowards buffer?'
        else:
            msg = "In block: " + block_name + "\n" +'What way is train facing\ntowards highlighted block?'
        title = "Set Train Facing Direction"
        type = JOptionPane.QUESTION_MESSAGE
        self.od.CLOSED_OPTION = True
        while self.od.CLOSED_OPTION == True:
            result = self.od.customQuestionMessage2str(msg, title, "forward", "reverse")
            if self.od.CLOSED_OPTION == True:
                self.od.displayMessage("Sorry Can't Cancel at this point")

        if in_siding:
            if result == "reverse":
                train_direction = "reverse"
            else:
                train_direction = "forward"
        else:
            if result == "forward":
                train_direction = "reverse"
            else:
                train_direction = "forward"
        return [train_direction, result]


    def set_train_in_block(self, block_name, train_name):
        mem_val = train_name
        self.set_blockcontents(block_name, mem_val)

    def reset_train_in_blocks(self, train_name):
        for block in blocks.getNamedBeanSet():
            #print "block name", block.getUserName(), "block.getValue()" , block.getValue()
            if block.getValue() == train_name:
                #print "yes"
                block.setValue("")
                #print "block name yes", block.getUserName(), "block.getValue()" , block.getValue()


    def trains_in_sections_allocated(self):
        trains_in_sections_allocated = []
        #trains_in_sections_nonallocated = []
        for station_block_name in g.station_block_list:
            block_value = self.get_blockcontents(station_block_name)
            block_occupied_state = self.check_sensor_state_given_block_name(station_block_name)
            if block_occupied_state == True:
                if block_value not in trains_allocated:
                    trains_in_sections_allocated.append([station_block_name, block_value, "non-allocated"])
                elif (block_value != None and block_value != "" and block_value != "none"):
                    trains_in_sections_allocated.append([station_block_name, block_value, "allocated"])
                else:
                    trains_in_sections_allocated.append([station_block_name, block_value, "other"])
        if self.logLevel > 0: print str(trains_in_sections_allocated)
        return trains_in_sections_allocated

    def occupied_blocks_allocated(self):
        occupied_blocks = [block for [block, train, state] in self.trains_in_sections_allocated() if state == "allocated"]
        return occupied_blocks

    def occupied_blocks_not_allocated(self):
        # print "self.trains_in_sections_allocated()", self.trains_in_sections_allocated()
        occupied_blocks = [block for [block, train,  state] in self.trains_in_sections_allocated() if state == "non-allocated"]
        return occupied_blocks

    def train_blocks(self, train_list, in_list):
        occupied_blocks = \
        [station_block_name for station_block_name in g.station_block_list \
         if self.check_sensor_state_given_block_name(station_block_name) == True]

        # print "occupied_blocks", occupied_blocks
        # print "train_list", train_list
        self.get_blockcontents(station_block_name),
        if in_list:
            items_in_list = \
                [[self.get_blockcontents(block_name), block_name, self.check_sensor_state_given_block_name(block_name)] \
                            for block_name in occupied_blocks if self.get_blockcontents(block_name) in train_list]
            # [train_name , block_name, block_state] = items_in_list     # for clarity
            return items_in_list
        else:
            items_not_in_list = \
                [[self.get_blockcontents(block_name), block_name, self.check_sensor_state_given_block_name(block_name)] \
                            for block_name in occupied_blocks if self.get_blockcontents(block_name) not in train_list]
            # [train_name , block_name, block_state] = items_in_list     # for clarity
            return items_not_in_list

    def train_blocks_in_list(self,train_list):
        return self.train_blocks(train_list, True)
    def train_blocks_not_in_list(self,train_list):
        return self.train_blocks(train_list, False)


    # def trains_in_sections(self, train_list):
    #     # given the train list, return list of all trains [[station_block_name, block_value, msg],...]
    #     # where msg says whether item in list or not
    #     trains_in_sections = []
    #     for station_block_name in g.station_block_list:
    #         block_value = self.get_blockcontents(station_block_name)
    #         block_occupied_state = self.check_sensor_state_given_block_name(station_block_name)
    #         if block_occupied_state == True:
    #             if block_value not in train_list:
    #                 trains_in_sections.append([station_block_name, block_value, "non-in-list"])
    #             elif (block_value != None and block_value != "" and block_value != "none"):
    #                 trains_in_sections.append([station_block_name, block_value, "in-list"])
    #             else:
    #                 trains_in_sections.append([station_block_name, block_value, "other"])
    # if self.logLevel > 0: print str(trains_in_sections)
    # return trains_in_sections


    def check_new_train_in_siding(self):

        # go through all station
        global trains_allocated

        for station_block_name in g.station_block_list:

            #get a True if the block block_value has the train name in it
            block_value = self.get_blockcontents(station_block_name)
            if self.logLevel > 0: print " a trains_allocated:", trains_allocated, ": block_value", block_value

            #get a True if the block is occupied
            block_occupied_state = self.check_sensor_state_given_block_name(station_block_name)

            if self.logLevel > 0: print ("station block name {} : block_value {}". format(station_block_name, str(block_value)))

            #check if the block is occupied and has the required train in it
            if (block_value == None or block_value == "" or block_value == "none") and block_occupied_state == True:
                return [station_block_name, None]
            elif block_occupied_state == True and (block_value != None and block_value != "" and block_value != "none"):
                #check if there is already a thread for the train
                #check if the train has already been allocated
                #if self.new_train_thread_required(block_value):
                if block_value not in trains_allocated:
                    return [station_block_name, block_value]
                else:
                    if self.logLevel > 0: print "block_value in trains_allocated"
                    if self.logLevel > 0: print "b trains_allocated:", trains_allocated, ": block_value", block_value
                    pass
            else:
                pass
        return [None, None]

    def is_roster_entry(self, v):
        return type(v) is jmri.jmrit.roster.RosterEntry

    def train_thread_exists(self, train_name):
        for thread in instanceList:
            if thread is not None:
                if thread.isRunning():
                    existing_train_name = thread.getName()
                    if existing_train_name == train_name:
                        return True
        return False

    def create_new_train_thread(self, train_name):
        idx = len(instanceList)
        instanceList.append(RunDispatch())          # Add a new instance
        instanceList[idx].setName(train_name)        # Set the instance name
        #if instanceList[idx].setup():               # Compile the train actions
        instanceList[idx].start()               # Compile was successful


    def get_blockcontents(self, block_name):
        block = blocks.getBlock(block_name)
        value =  block.getValue()
        return value


    def set_blockcontents(self, block_name, value):
        block = blocks.getBlock(block_name)
        value =  block.setValue(value)


    def check_sensor_state_given_block_name(self, station_block_name):
        #if self.logLevel > 0: print("station block name {}".format(station_block_name))
        layoutBlock = layoutblocks.getLayoutBlock(station_block_name)
        station_sensor = layoutBlock.getOccupancySensor()
        if station_sensor is None:
            OptionDialog().displayMessage(' Sensor in block {} not found'.format(station_block_name))
            return
        currentState = True if station_sensor.getKnownState() == ACTIVE else False
        return currentState

class createandshowGUI(TableModelListener):

    def __init__(self, super):
        self.super = super
        #Create and set up the window.

        self.initialise_model(super)


        # tablePanel = self.self_table()
        # jpane = JScrollPane(tablePanel)
        # panel = JPanel()
        # panel.add(jpane)
        # self.frame = JFrame("SimpleTableDemo")
        self.frame = JFrame("Set up trains")
        self.frame.setSize(600, 600);
        #self.frame.addWindowListener(MyFrameListener())

        self.completeTablePanel()
        # print "about to populate"
        self.populate_action(None)
        # self.frame.setSize(600, 600);
        # self.frame.getContentPane().add( tablePanel )
        # #self.frame.add(JScrollPane(panel))
        # #self.frame.add(tablePanel)
        # self.frame.pack();
        # self.frame.setVisible(True)

        self.cancel = False

        # #self.frame.setdefaultCloseOperation(JFrame.EXIT_ON_CLOSE)   #do bot close on exit
        #
        # #Create and set up the content pane.
        # self.initialise_model()
        # newContentPane = self.completeTablePanel()
        # newContentPane.setOpaque(True) #content panes must be opaque
        # self.scrollPane = JScrollPane()
        # self.scrollPane.add(newContentPane)
        # #self.frame.setContentPane(newContentPane)
        # self.frame.setSize(600, 600);
        #
        # #self.frame.getContentPane().add( newContentPane )
        # self.frame.add(self.scrollPane)
        # #self.frame.add( newContentPane, java.awt.BorderLayout.CENTER)
        # #Display the window.
        # self.frame.pack();
        # self.frame.setVisible(True);
        #
        # DEBUG = False;

        # print "super1 set up ********************************************************************************"
        self.cancel = False

    def completeTablePanel(self):

        self.topPanel= JPanel();
        self.topPanel.setLayout(BoxLayout(self.topPanel, BoxLayout.X_AXIS))
        self.self_table()

        scrollPane = JScrollPane(self.table);
        scrollPane.setSize(600,600);

        self.topPanel.add(scrollPane);

        self.buttonPane = JPanel();
        self.buttonPane.setLayout(BoxLayout(self.buttonPane, BoxLayout.LINE_AXIS))
        self.buttonPane.setBorder(BorderFactory.createEmptyBorder(0, 10, 10, 10))

        button_add = JButton("Add Row", actionPerformed = self.add_row_action)
        self.buttonPane.add(button_add);
        self.buttonPane.add(Box.createRigidArea(Dimension(10, 0)))

        button_populate = JButton("Populate", actionPerformed = self.populate_action)
        self.buttonPane.add(button_populate);
        self.buttonPane.add(Box.createRigidArea(Dimension(10, 0)))

        button_tidy = JButton("Tidy", actionPerformed = self.tidy_action)
        self.buttonPane.add(button_tidy);
        self.buttonPane.add(Box.createRigidArea(Dimension(10, 0)))

        button_apply = JButton("Apply", actionPerformed = self.apply_action)
        self.buttonPane.add(button_apply)
        self.buttonPane.add(Box.createHorizontalGlue());

        button_cancel = JButton("Close", actionPerformed = self.cancel_action)
        self.buttonPane.add(button_cancel)
        self.buttonPane.add(Box.createHorizontalGlue());

        # button_save = JButton("Save", actionPerformed = self.save_action)
        # self.buttonPane.add(button_save)
        # self.buttonPane.add(Box.createHorizontalGlue());

        contentPane = self.frame.getContentPane()

        contentPane.removeAll()
        contentPane.add(self.topPanel, BorderLayout.CENTER)
        contentPane.add(self.buttonPane, BorderLayout.PAGE_END)

        self.frame.pack();
        self.frame.setVisible(True)

        return
    def buttonPanel(self):
        row1_1_button = JButton("Add Row", actionPerformed = self.add_row_action)
        row1_2_button = JButton("Save", actionPerformed = self.save_action)

        row1 = JPanel()
        row1.setLayout(BoxLayout(row1, BoxLayout.X_AXIS))

        row1.add(Box.createVerticalGlue())
        row1.add(Box.createRigidArea(Dimension(20, 0)))
        row1.add(row1_1_button)
        row1.add(Box.createRigidArea(Dimension(20, 0)))
        row1.add(row1_2_button)

        layout = BorderLayout()
        # layout.setHgap(10);
        # layout.setVgap(10);

        jPanel = JPanel()
        jPanel.setLayout(layout);
        jPanel.add(self.table,BorderLayout.NORTH)
        jPanel.add(row1,BorderLayout.SOUTH)

        #return jPanel
        return topPanel

    def initialise_model(self, super):

        self.model = None
        self.model = MyTableModel()
        self.table = JTable(self.model)
        self.model.addTableModelListener(MyModelListener(self, super));
        pass
    def self_table(self):

        #table.setPreferredScrollableViewportSize(Dimension(500, 70));
        #table.setFillsViewportHeight(True)
        #self.table.getModel().addtableModelListener(self)
        self.table.setFillsViewportHeight(True);
        self.table.setRowHeight(30);
        #table.setAutoResizeMode( JTable.AUTO_RESIZE_OFF );
        # self.resizeColumnWidth(table)

        #renderer = DefaultTableCellRenderer()

        #renderer.setToolTipText("Click for combo box");
        # set first 3 cols to combobox
        # comboBox = [1,2,3]
        # column = [1,2,3]


        self.trainColumn = self.table.getColumnModel().getColumn(0);
        self.combobox0 = JComboBox()

        self.all_trains = self.super.get_all_roster_entries_with_speed_profile()
        self.non_allocated_trains = self.super.get_non_allocated_trains()
        for train in self.non_allocated_trains:
            self.combobox0.addItem(train)
        self.trainColumn.setCellEditor(DefaultCellEditor(self.combobox0));
        renderer0 = ComboBoxCellRenderer()
        self.trainColumn.setCellRenderer(renderer0);

        self.all_sections = self.super.get_all_sections()
        self.all_blocks = self.super.get_all_blocks()

        self.sectionColumn = self.table.getColumnModel().getColumn(1);
        self.combobox1 = JComboBox()
        self.sections_to_choose = self.super.get_non_allocated_trains_sections()
        for section in self.sections_to_choose:
            self.combobox1.addItem(section)
            #self.set_train_selections(combobox0)
        self.sectionColumn.setCellEditor(DefaultCellEditor(self.combobox1));
        renderer1 = ComboBoxCellRenderer()
        self.sectionColumn.setCellRenderer(renderer1);
        jpane = JScrollPane(self.table)
        panel = JPanel()
        panel.add(jpane)
        result = JScrollPane(panel)
        return self.table

    def add_row_action(self, e):
        model = e.getSource()
        data = self.model.getValueAt(0, 0)
        count = self.model.getRowCount()
        colcount = self.model.getColumnCount()
        self.model.add_row()
        self.completeTablePanel()

    def populate_action(self, event):
        column = 1  #block
        all_blocks = [block.getUserName() for block in self.all_blocks]
        blocks_in_table = [block for block in (self.model.getValueAt(r, column) for r in range(self.table.getRowCount())) if block in all_blocks]
        #blocks_in_table1 = [section for section in (self.model.getValueAt(r, column) for r in range(self.table.getRowCount())) ]
        # print "self.all_sections", all_sections
        # print "sections in table", blocks_in_table
        # print "sections in table1", blocks_in_table1
        # # # starting with non_allocated_trains remove the ones in my_train_list
        # # print "sections to choose", self.sections_to_choose
        # # print "trains_in_table",trains_in_table
        # # print "sections True", self.super.train_blocks(trains_in_table, True)
        # # print "sections False", self.super.train_blocks(trains_in_table, False)
        # # allocated_blocks = self.super.occupied_blocks_allocated()
        not_allocated_blocks = self.super.occupied_blocks_not_allocated()
        # print "not_allocated_blocks", not_allocated_blocks
        blocks_to_put_in_dropdown = [s for s in not_allocated_blocks if s not in blocks_in_table]
        # print "blocks_to_put_in_dropdown", blocks_to_put_in_dropdown
        self.model.populate(blocks_to_put_in_dropdown)
        # print "COMPLETING TABLE PANEL"
        self.completeTablePanel()

    def tidy_action(self,e):
        self.model.remove_not_set_row()
        self.completeTablePanel()

    def save_action(self, event):
        # print "save action"
        for row in self.model.data:
            # print("row",row[0])
            pass
        #self.super.add_to_train_list_and_set_new_train_location(new_train_name, new_section_name)
        pass

    def cancel_action(self, event):
        self.frame.dispatchEvent(WindowEvent(self.frame, WindowEvent.WINDOW_CLOSING));

    def apply_action(self, event):
        train = 0
        block = 1
        direction = 2
        length = 4
        # print "apply action"
        for row in reversed(range(len(self.model.data))):
            train_name = self.model.data[row][train]
            block_name = self.model.data[row][block]
            train_direction = self.model.data[row][direction]
            train_length = self.model.data[row][length]
            if train_name != "" and block_name != "":
                self.super.add_to_train_list_and_set_new_train_location0(train_name, block_name,
                                                                         train_direction, train_length)
                self.model.data.pop(row)
        self.completeTablePanel()
    def set_train_selections(self, combobox):
        pass

class MyModelListener(TableModelListener):

    def __init__(self, class_createandshowGUI, class_NewTrainMaster):
        self.class_createandshowGUI = class_createandshowGUI
        self.class_NewTrainMaster = class_NewTrainMaster
        self.super = super
        self.cancel = False
    def tableChanged(self, e) :
        global trains_allocated
        row = e.getFirstRow()
        column = e.getColumn()
        model = e.getSource()
        columnName = model.getColumnName(column)
        data = model.getValueAt(row, column)
        class_createandshowGUI = self.class_createandshowGUI
        class_NewTrainMaster = self.class_NewTrainMaster
        tablemodel = class_createandshowGUI.model
        if column == 0:     #trains
            class_createandshowGUI.combobox0.removeAllItems()
            #the non_allocated trains are stored in self.non_allocated_trains
            # each time a cell is edited we regenerate the list if trains in the drop down
            # we set to the non_allocated_trains less the ones marked ro be allocated in the table

            # for r in range(class_createandshowGUI.table.getRowCount()):
                # print "r",r,"column",column
                # print "r", r, "(model.getValueAt(r, column)", (model.getValueAt(r, column))
            #trains_in_table = [train for train in (model.getValueAt(r, column) for r in range(class_createandshowGUI.table.getRowCount()))
            trains_in_table = [train for train in (model.getValueAt(r, column) for r in range(class_createandshowGUI.table.getRowCount())) if train in class_createandshowGUI.all_trains]
            # print "trains in table", trains_in_table
            # starting with non_allocated_trains remove the ones in my_train_list
            #trains_to_put_in_dropdown = [t for t in class_createandshowGUI.non_allocated_trains if t not in trains_in_table]
            trains_to_put_in_dropdown = [t for t in class_createandshowGUI.non_allocated_trains]
            # print "trains_to_put_in_dropdown", trains_to_put_in_dropdown
            class_createandshowGUI.combobox0.removeAllItems()
            #put the remaining trains in the combo dropdown
            class_createandshowGUI.combobox0.addItem("")
            [class_createandshowGUI.combobox0.addItem(train) for train in trains_to_put_in_dropdown]
            class_createandshowGUI.trainColumn.setCellEditor(DefaultCellEditor(class_createandshowGUI.combobox0));

            # populate the length of the engine
            train_name = model.getValueAt(row, 0)
            [engine, train_length] = class_NewTrainMaster.get_train_length(train_name)
            model.setValueAt(train_length, row,4)
            # print "%%%%%%%%%%%%%%%%end col1 %%%%%%%%%%%%%%%%%%%%%%%%"
        elif column == 1:       # sections
            class_createandshowGUI.combobox1.removeAllItems()
            # print "%%%%%%%%%%%%%%%%start col2 %%%%%%%%%%%%%%%%%%%%%%%%"
            # print "class_createandshowGUI.all_sections", class_createandshowGUI.all_sections
            # print "range class_createandshowGUI.table.getRowCount()", range(class_createandshowGUI.table.getRowCount())
            for r in range(class_createandshowGUI.table.getRowCount()):
                # print "r",r,"column",column
                # print "r", r, "(model.getValueAt(r, column)", (model.getValueAt(r, column))
                pass
            all_sections = [str(block.getUserName()) for block in class_createandshowGUI.all_sections]
            all_blocks = [str(block.getUserName()) for block in class_createandshowGUI.all_blocks]
            # print "all_sections", all_sections
            trains_in_table = \
                [train for train in (model.getValueAt(r, column) for r in range(class_createandshowGUI.table.getRowCount()))
                 if train in class_createandshowGUI.all_trains]
            X =  [str(model.getValueAt(r, column)) for r in range(class_createandshowGUI.table.getRowCount())]
            # print "X", X
            blocks_in_table = [block for block in X if block in all_blocks]
            # print "sections in table", blocks_in_table
            # starting with non_allocated_trains remove the ones in my_train_list
            # print "sections to choose", class_createandshowGUI.sections_to_choose
            # print "trains_in_table",trains_in_table
            # print "sections True", class_createandshowGUI.train_blocks(trains_in_table, True)
            # print "sections False", class_createandshowGUI.train_blocks(trains_in_table, False)
            allocated_blocks = class_createandshowGUI.super.occupied_blocks_allocated()
            not_allocated_blocks = class_createandshowGUI.super.occupied_blocks_not_allocated()
            #blocks_to_put_in_dropdown = [s for s in not_allocated_blocks if s not in blocks_in_table]
            blocks_to_put_in_dropdown = [s for s in not_allocated_blocks]
            # print("blocks_to_put_in_dropdown", blocks_to_put_in_dropdown)
            #put the remaining trains in the combo dropdown
            class_createandshowGUI.combobox1.removeAllItems()
            class_createandshowGUI.combobox1.addItem("")
            [class_createandshowGUI.combobox1.addItem(section) for section in blocks_to_put_in_dropdown]

            # [class_createandshowGUI.combobox1.addItem(section) for section in blocks_to_put_in_dropdown]
            class_createandshowGUI.sectionColumn.setCellEditor(DefaultCellEditor(class_createandshowGUI.combobox1));
            # print "%%%%%%%%%%%%%%%%end col2 %%%%%%%%%%%%%%%%%%%%%%%%"
        elif column == 3:       # show the direction on the layout to enable the facing direction to be chosen
            # print "cancel on entry", self.cancel
            if self.cancel == True:
                self.cancel = False
                # print "set cancel", self.cancel
                return
            station_block_name = model.getValueAt(row, 1)
            # print "station_block_name", station_block_name
            if station_block_name != None and station_block_name != "" and station_block_name != "None Available":
                [edge, train_direction, result] = class_createandshowGUI.super.highlight_penultimate_block(station_block_name)
                self.cancel = True
                model.setValueAt(result, row, 2)      #set the direction box to the result (forwards or reverse)
                model.setValueAt(False, row, 3)       #reset the check box (need the self.cancel code to stop retriggering of the event code)
            else:
                OptionDialog().displayMessage("must set Block first")


class ComboBoxCellRenderer (TableCellRenderer):
    def getTableCellRendererComponent(self, jtable, value, isSelected, hasFocus, row, column):
        combo = JComboBox()
        combo.setSelectedItem(value);
        return combo
#


    # def __init__(self, comboBox) :
    #     for i in range(comboBox.getItemCount()):
    #         self.combo.addItem(comboBox.getItemAt(i))
    #         pass
    #
    # combo = JComboBox()

    def getTableCellRendererComponent(self, jtable, value, isSelected, hasFocus, row, column) :
        panel = self.createPanel(value)
        return panel

    def createPanel(self, s) :
        p = JPanel(BorderLayout())
        p.add(JLabel(s, JLabel.LEFT), BorderLayout.WEST)
        icon = UIManager.getIcon("Table.descendingSortIcon");
        p.add(JLabel(icon, JLabel.RIGHT), BorderLayout.EAST);
        p.setBorder(BorderFactory.createLineBorder(Color.blue));
        return p;


class MyTableModel (DefaultTableModel):

    columnNames = ["Train",
                   "Block",
                   "Set Direction",
                   "Direction Facing",
                   "Length"]

    def __init__(self):
        l1 = ["", "", "click ->", False, 10]
        self.data = [l1]

    def remove_not_set_row(self):
        b = False
        for row in reversed(range(len(self.data))):
            if len(self.data) >1:
                # print "row", row
                if self.data[row][0] == "":
                    self.data.pop(row)

        if len (self.data) ==1 and self.data[0][0] == "":
            OptionDialog().displayMessage("deleted Not Set train rows, but no train set")

    def add_row(self):
        # print "addidn row"
        # if row < len(self.data):
        # print "add"
        self.data.append(["", "", "click ->", False, 10])
        # print self.data
        # print "added"

    def populate(self, blocks_to_put_in_dropdown):
        # append all blocks to put in dropdown
        for block in blocks_to_put_in_dropdown:
            self.data.append(["", block, "click ->", False, 10])
        # delete rows with no blocks
        for row in reversed(range(len(self.data))):
            if self.data[row][1] == None or self.data[row][1] == "":
                if len(self.data)>1:
                    self.data.pop(row)

    def getColumnCount(self) :
        return len(self.columnNames)


    def getRowCount(self) :
        return len(self.data)


    def getColumnName(self, col) :
        return self.columnNames[col]


    def getValueAt(self, row, col) :
        return self.data[row][col]

    def getColumnClass(self, c) :
        if c <= 1:
            return java.lang.Boolean.getClass(JComboBox)
        return java.lang.Boolean.getClass(self.getValueAt(0,c))


    #only include if table editable
    def isCellEditable(self, row, col) :
        # Note that the data/cell address is constant,
        # no matter where the cell appears onscreen.
        if col != 2:
            return True
        else:
            return False

    # only include if data can change.
    def setValueAt(self, value, row, col) :
        self.data[row][col] = value
        self.fireTableCellUpdated(row, col)

