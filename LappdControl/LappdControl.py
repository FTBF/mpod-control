import sys
import time 
import yaml
import os
sys.path.append("../MPOD/")
from MPOD import MPOD
from ipaddress import IPv4Address


class LappdControl:
    def __init__(self, settings, guitext):
        self.settings = None
        self.settings_filename = settings
        self.guitext = guitext
        self.load_settings() #load the settings file

        #need to check and set environment variables to tell
        #shell where to locate snmp commands
        self.set_paths()

        
        #initialize the MPOD crate
        self.mpod = None #the module object where commands are parsed and sent. 

        #this channel dict is where most information is stored. It holds a lot. The keys are:
        #"l<n>_pc"/mcp1/mcp2 for channel selection, which itself holds a dictionary with these keys:
        #"uid" - the unique identifier for the channel in the MPOD system
        #"v_term" - the terminal voltage of the channel
        #"set_v" - the set voltage of the channel
        #"state" - the on/off state of the channel
        #***ALL VOLTAGES IN SOFTWARE ARE POSITIVE, as we assume the supply always is negative, even with messages of positive voltages
        self.channel_dict = {} #our own dictionary of channel numbers, names, current voltages, setpoint voltages, etc. 

        #this dictionary is more for global LAPPD statuses and data, such as whether the photocathoe
        #voltage setpoint is set to on, or below the mcp1. Each lnum is a key, like lappd_dict['157'] = {}
        #with keys:
        #"pc_state" - whether the photocathode is on or off
        self.lappd_dict = {} #dictionary of LAPPD statuses, such as whether the photocathode is on or off.
        for lappd in self.settings['lappds_in_use']:
            self.lappd_dict[lappd] = {}
        self.initialize_crate() #initializes the full stack of channels. also populates self.mpod with MPOD object

        
    def load_settings(self):
        self.settings = None
        #do yaml safe read of the settings file
        #into a dictionary
        with open(self.settings_filename, 'r') as stream:
            try:
                self.settings = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                sys.exit(1)

    def set_paths(self):
        #get PATH environment variable
        p = os.environ.get('PATH')
        #get the path to snmp commands
        snmp_path = self.settings['snmp_path']
        if(snmp_path in p):
            return
        else:
            os.environ['PATH'] = p + ":" + snmp_path
            return

    def initialize_crate(self):
        #shorter pneumonic for settings dictionary
        s = self.settings
        mn = 1 #Module number, this IS a relevant number, it references the first digit of the .UX16 suffix for selecting channel
        mpod = MPOD.MPOD(mn, IPv4Address(s['ip']), s['crate_path'], debug=s["debug"]) # (a)    

        #Evan believes that the crate can be in the "off" state 
        #without the user knowing. And this "off" state is not
        #whether the channel are outputting voltage. Turn the crate on. 
        mpod.execute_command('sysMainSwitch', 1)      

        #Let's add software channels to the module that represent
        #(1) a photocathode channel
        #(2) an MCP1 channel
        #(3) an MCP2 channel
        #for N LAPPDs, ordering will be as above.  
        #Naming convention will be 'l<n>_mcp<m>' and 'l<n>_pc' for LAPPD n and MCP m

        lappds_in_use = s['lappds_in_use']
        lappd_count = 0 #loop counter for labeling
        for ch in range(len(lappds_in_use)*3):
            lnum = "l"+lappds_in_use[lappd_count] #string, identifier of LAPPD number that matches the yaml config
            max_i = s[lnum]['max_i'] #dictionary of max currents for each channel
            if(ch % 3 == 0):
                mpod.add_channel(ch, max_current=float(max_i['pc']), ramp_rate=float(s["ramp_rate"]), fall_rate=float(s["fall_rate"]))
                self.channel_dict['{}_pc'.format(lnum)] = {}
                self.channel_dict['{}_pc'.format(lnum)]["uid"] = 'u{:d}'.format(mn) + str(ch).zfill(2)
            elif(ch % 3 == 1):
                mpod.add_channel(ch, max_current=float(max_i['mcp1']), ramp_rate=float(s["ramp_rate"]), fall_rate=float(s["fall_rate"]))
                self.channel_dict['{}_mcp1'.format(lnum)] = {}
                self.channel_dict['{}_mcp1'.format(lnum)]["uid"] = 'u{:d}'.format(mn) + str(ch).zfill(2)
            else:
                mpod.add_channel(ch, max_current=float(max_i['mcp2']), ramp_rate=float(s["ramp_rate"]), fall_rate=float(s["fall_rate"]))
                self.channel_dict['{}_mcp2'.format(lnum)] = {}
                self.channel_dict['{}_mcp2'.format(lnum)]["uid"] = 'u{:d}'.format(mn) + str(ch).zfill(2)
                lappd_count +=1

        self.mpod = mpod

        #get the statuses of channel voltages and on/off states, 
        #and ALSO reads whether the photocathode is on or off. 
        self.read_terminal_voltages()
        self.read_setpoint_voltages()
        self.read_switch_states()

        #if the channels are on and such, the GUI will now reflect that. 
        #Check whether the voltage of the photocathode is set to be above or below mcp1
        for l in self.settings['lappds_in_use']:
            self.lappd_dict[l]["pc_state"] = self.is_photocathode_on(l)

    def check_setpoints_sanity(self):
        #check the setpoints and make sure that they are within reason
        #of one another, making sure typos don't totally mess up the system. 
        for lappd in self.settings['lappds_in_use']:
            lnum = "l"+lappd
            pc = float(self.settings[lnum]['set_v']['pc'])
            mcp1 = float(self.settings[lnum]['set_v']['mcp1'])
            mcp2 = float(self.settings[lnum]['set_v']['mcp2'])

            if(pc > 2600 or mcp1 > 2600 or mcp2 > 2600):
                print("Error: set voltages must be less than 2600 due to software safety controls")
                return False
            
            if(pc < 0 or mcp1 < 0 or mcp2 < 0):
                print("Error: set voltages must be greater than 0")
                return False
            
            if((pc - mcp1) > 150):
                print("Error: pc - mcp1 must be less than 150")
                return False
            
            if((mcp1 - mcp2) > 1400):
                print("Error: mcp1 - mcp2 must be less than 1400")
                return False
            
            if(mcp2 > 1300):
                print("Error: mcp2 must be less than 1300")
                return False
        
        return True

    #l is the lnum of the lappd looking to be loaded
    def load_new_setpoints(self, l):
        #first load the settings file again
        self.load_settings()

        if(self.check_setpoints_sanity() == False):
            print("Failed sanity check on setpoints, not loading new setpoints")
            return False

        #then update the setpoints for each channel
        #on the requested LAPPD
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            vtap = ch.split('_')[1]
            setp = float(self.settings[lappd]["set_v"][vtap])

            #we are going to have some conditions for if the PC is on verses off. 
            if(vtap == "pc" and self.lappd_dict[l]["pc_state"] == 0):
                setp = float(self.settings["l"+l]["set_v"]["mcp1"]) + float(self.settings["pc_off_bias"])
                self.mpod.execute_command('outputVoltage', setp, ch_key=self.channel_dict[ch]["uid"])
                self.channel_dict[ch]["set_v"] = setp 
            else:
                self.mpod.execute_command('outputVoltage', setp, ch_key=self.channel_dict[ch]["uid"])
                self.channel_dict[ch]["set_v"] = setp
        
        return True

    #Turns channels on for a given LAPPD, 
    #ramping them to their setpoint voltages. 
    def channels_on(self, l):
        #first, check that the channels are off. If they are on, do nothing! just a repeat click. 
        if(self.are_channels_on(l)):
            return False
        
        #Channels are off. So we will establish a ramp up procedure that sequences
        #the MCPs and PC in order. 
        mcp2_temp = self.channel_dict["l"+l+"_mcp2"]["set_v"]
        mcp1_temp = mcp2_temp
        pc_temp = mcp2_temp

        #first ramp to the mcp2 voltage for all terminals
        self.mpod.execute_command("outputVoltage", mcp2_temp, ch_key=self.channel_dict["l"+l+"_mcp2"]["uid"])
        self.mpod.execute_command("outputVoltage", mcp1_temp, ch_key=self.channel_dict["l"+l+"_mcp1"]["uid"])
        self.mpod.execute_command("outputVoltage", pc_temp, ch_key=self.channel_dict["l"+l+"_pc"]["uid"])
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            ch_key = self.channel_dict[ch]["uid"]
            self.mpod.execute_command("outputSwitch", 10, ch_key=ch_key)
            self.mpod.execute_command("outputSwitch", 1, ch_key=ch_key)

        #this should take a few seconds based on ramp rate, so wait that many seconds + 5
        tramp = mcp2_temp/float(self.settings["ramp_rate"]) + 4 #seconds
        print("Ramping all terminals first to MCP2 voltage, this will take {} seconds".format(tramp))
        for i in range(int(tramp)):
            if(i % 2 == 0):
                print("{}...".format(i))
            time.sleep(1)
        time.sleep(1)

        #check the terminal voltages have made it there
        self.read_terminal_voltages()
        error_allowed = 5 #V 
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            if(abs(self.channel_dict[ch]["v_term"] - mcp2_temp) > error_allowed):
                print("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("I suggest you turn the channels off and try again.")
                return False
            
        #now ramp the other two to mcp1 
        mcp1_temp = self.channel_dict["l"+l+"_mcp1"]["set_v"]
        pc_temp = mcp1_temp
        self.mpod.execute_command("outputVoltage", mcp1_temp, ch_key=self.channel_dict["l"+l+"_mcp1"]["uid"])
        self.mpod.execute_command("outputVoltage", pc_temp, ch_key=self.channel_dict["l"+l+"_pc"]["uid"])
        #this should take a few seconds based on ramp rate, so wait that many seconds + 5
        tramp = (mcp1_temp - mcp2_temp)/float(self.settings["ramp_rate"]) + 4 #seconds
        print("Ramping MCP1 and PC to the MCP1 voltage, this will take {} seconds".format(tramp))
        for i in range(int(tramp)):
            if(i % 2 == 0):
                print("{}...".format(i))
            time.sleep(1)
        time.sleep(1)

        #check the terminal voltages have made it there
        self.read_terminal_voltages()
        error_allowed = 5 #V 
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            if("mcp2" in ch):
                continue
            if(abs(self.channel_dict[ch]["v_term"] - mcp2_temp) > error_allowed):
                print("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("I suggest you turn the channels off and try again.")
                return False

        #finally, if the PC is set to ON, ramp it to the PC voltage
        if(self.lappd_dict[l]["pc_state"] == 1):
            pc_temp = self.channel_dict["l"+l+"_pc"]["set_v"]
            self.mpod.execute_command("outputVoltage", pc_temp, ch_key=self.channel_dict["l"+l+"_pc"]["uid"])
            #this should take a few seconds based on ramp rate, so wait that many seconds + 5
            tramp = (pc_temp - mcp1_temp)/float(self.settings["ramp_rate"]) + 4
            print("Ramping PC to the PC voltage, this will take {} seconds".format(tramp))
            for i in range(int(tramp)):
                if(i % 2 == 0):
                    print("{}...".format(i))
                time.sleep(1)
            time.sleep(1)
        
            #check the terminal voltages have made it there
            self.read_terminal_voltages()
            error_allowed = 5
            if(abs(self.channel_dict["l"+l+"_pc"]["v_term"] - pc_temp) > error_allowed):
                print("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("I suggest you turn the channels off and try again.")
                return False

        self.guitext.append("All channels ramped to setpoints successfully")
        self.print_terminal_voltages(l, check=True)
        return True
    
    def channels_off(self, l):
        #first check that the channels are on, if they are not, do nothing, just a repeat click!
        if(self.are_channels_on(l) == False):
            return False
        
        #reload terminal voltages and use those as a reference for ramping down
        self.read_terminal_voltages()
        
        #Channels are on. So we will establish a ramp down procedure that sequences
        #the MCPs and PC in order.
        
        #first turn the PC off. 
        self.photocathode_off(l)

        #next ramp to MCP1 and PC to the MCP2 voltage
        mcp2_temp = self.channel_dict["l"+l+"_mcp2"]["v_term"]
        mcp1_temp = mcp2_temp
        pc_temp = mcp2_temp
        self.mpod.execute_command("outputVoltage", pc_temp, ch_key=self.channel_dict["l"+l+"_pc"]["uid"])
        self.mpod.execute_command("outputVoltage", mcp1_temp, ch_key=self.channel_dict["l"+l+"_mcp1"]["uid"])

        #this should take a few seconds based on ramp rate, so wait that many seconds + 5
        tramp = mcp2_temp/float(self.settings["fall_rate"]) + 4 #seconds
        print("Ramping MCP1 and PC to the MCP2 voltage, this will take {} seconds".format(tramp))
        for i in range(int(tramp)):
            if(i % 2 == 0):
                print("{}...".format(i))
            time.sleep(1)
        time.sleep(1)

        #check the terminal voltages have made it there
        self.read_terminal_voltages()
        error_allowed = 5 #V
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            if("mcp2" in ch):
                continue
            if(abs(self.channel_dict[ch]["v_term"] - mcp2_temp) > error_allowed):
                print("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("Error: terminal voltage did not reach setpoint for channel {}. Check the browser readout GUI!".format(ch))
                self.guitext.append("I suggest you turn the channels off and try again.")
                return False
        
        #now turn off the channels, which will ramp them all at the same rate to 0V
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            ch_key = self.channel_dict[ch]["uid"]
            self.mpod.execute_command("outputSwitch", 10, ch_key=ch_key)
            self.mpod.execute_command("outputSwitch", 0, ch_key=ch_key)

        return True

    def photocathode_on(self, l):
        #check first if the photocathode is already on
        if(self.is_photocathode_on(l)):
            return
        
        #check that the terminal voltage of the mcp1 is nonzero
        if(self.channel_dict["l"+l+"_mcp1"]["v_term"] <= 0): 
            print("Error: MCP1 terminal voltage is zero or negative, cannot turn on photocathode")
            return False
        
        #finally do a sanity check on setpoints 
        if(self.check_setpoints_sanity() == False):
            print("Failed sanity check on setpoints, not turning on photocathode")
            return False
        
        ch = "l"+l+"_pc"
        ch_key = self.channel_dict[ch]["uid"]
        #raise the setpoint to the photocathode voltage from the settings file
        self.load_settings()
        setp = float(self.settings["l"+l]["set_v"]["pc"])
        self.mpod.execute_command("outputVoltage", setp, ch_key=ch_key)
        self.channel_dict[ch]["set_v"] = setp
        self.lappd_dict[l]["pc_state"] = 1


    def photocathode_off(self, l):
        #check first if the photocathode is already off
        if(self.is_photocathode_on(l) == False):
            return

        ch = "l"+l+"_pc"
        ch_key = self.channel_dict[ch]["uid"]
        #lower the setpoint to the MCP1 voltage from the settings file
        #MINUS some small negative bias of -0.5V
        self.load_settings()
        setp = float(self.settings["l"+l]["set_v"]["mcp1"]) + float(self.settings["pc_off_bias"]) #This number is negative in the config file
        self.mpod.execute_command("outputVoltage", setp, ch_key=ch_key)
        self.channel_dict[ch]["set_v"] = setp
        self.lappd_dict[l]["pc_state"] = 0

    def emergency_off(self):
        self.mpod.execute_command("sysMainSwitch", 0)

    #in development until we fully get some test outputs from the test function above. 
    def read_terminal_voltages(self):
        for ch in self.channel_dict:
            result = self.mpod.execute_command("outputMeasurementTerminalVoltage", ch_key=self.channel_dict[ch]["uid"])

            if(self.settings["debug"]):
                lnum = ch.split('_')[0]
                vtap = ch.split('_')[1]
                result = "{:.3f} V".format(self.settings[lnum]["set_v"][vtap])
            
            volt_str = result.split(" ")[-2]
            try:
                volts = abs(float(volt_str)) #we absolute value because in software we will work with positives only
            except:
                print("Had issue with string parsing of current voltage in get_current_voltages")
                continue
            self.channel_dict[ch]["v_term"] = volts

    def print_terminal_voltages(self, l, check=True):
        if(check):
            self.read_terminal_voltages()

        pc = self.channel_dict["l"+l+"_pc"]["v_term"]
        mcp1 = self.channel_dict["l"+l+"_mcp1"]["v_term"]
        mcp2 = self.channel_dict["l"+l+"_mcp2"]["v_term"]
        self.guitext.append("Terminal voltages for LAPPD {}:\t PC {:.0f}V,\t MCP1 {:.0f},\t MCP2 {:.0f}".format(l, pc, mcp1, mcp2))

    #THIS IS a critical distinction where you read the setpoint
    #voltages from the machine, rather than "loading" setpoint voltages from our
    #config file. The resulting setpoint goes into the same data structure location,
    #but whenever a setpoint is "set" by the user, it loads new setpoints from file. 
    def read_setpoint_voltages(self):
        for ch in self.channel_dict:
            result = self.mpod.execute_command("outputVoltage", ch_key=self.channel_dict[ch]["uid"])

            if(self.settings["debug"]):
                lnum = ch.split('_')[0]
                vtap = ch.split('_')[1]
                result = "{:.3f} V".format(-1*self.settings[lnum]["set_v"][vtap])
            
            volt_str = result.split(" ")[-2]
            try:
                volts = abs(float(volt_str)) #we absolute value because in software we will work with positives only
            except:
                print("Had issue with string parsing of current voltage in read_setpoint_voltages")
                continue
            self.channel_dict[ch]["set_v"] = volts

    def read_switch_states(self):
        for ch in self.channel_dict:
            result = self.mpod.execute_command("outputSwitch", ch_key=self.channel_dict[ch]["uid"])
            #assumes result is "on or ff"
            if(self.settings["debug"]):
                if(("state" in self.channel_dict[ch]) == False):
                    result = "off"
                elif(self.channel_dict[ch]["state"] == 1):   
                    result = "on"
                else:
                    result = "off"

            if("on" in result.lower()):
                self.channel_dict[ch]["state"] = 1
            elif("off" in result.lower()):
                self.channel_dict[ch]["state"] = 0
            else:
                print("Could not tell status of the channel, parsing issue in load_switch_states")
                self.channel_dict[ch]["state"] = -1

    #simple boolean for the GUI to check if channels are on for a given LAPPD
    def are_channels_on(self, l, check=True):
        if(check):
            self.read_switch_states()
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            if(self.channel_dict[ch]["state"] == 0):
                return False
        return True

    #this function now is checking if the photocathode Voltage
    #is set to be above or below~equal to mcp1, not whether the switch is on. 
    #If you know you just read terminal voltages, then you can set check to False
    #and it wont read again. 
    def is_photocathode_on(self, l, check=True):
        if(check):
            self.read_setpoint_voltages()

        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            if(lappd != "l"+l):
                continue
            if(ch.split('_')[1] == "pc"):
                if(self.channel_dict[ch]["set_v"] > self.channel_dict["l"+l+"_mcp1"]["set_v"]):
                    return True
                else:
                    return False

        return None #if something wrong happens

