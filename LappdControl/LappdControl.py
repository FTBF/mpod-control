import sys
import time 
import yaml
sys.path.append("../MPOD/")
from MPOD import MPOD
from ipaddress import IPv4Address



class LappdControl:
    def __init__(self, settings):
        self.settings = None
        self.settings_filename = settings
        self.load_settings() #load the settings file
        
        #initialize the MPOD crate
        self.mpod = None #the module object where commands are parsed and sent. 
        self.channel_dict = {} #our own dictionary of channel numbers and names
        self.initialize_crate() #initializes the full stack of channels. also populates self.mpod with MPOD object

        self.is_on = False #flag for whether the channels are on or off
        
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


    def initialize_crate(self):
        #shorter pneumonic for settings dictionary
        s = self.settings
        mn = 1 #Module number, this IS a relevant number, it references the first digit of the .UX16 suffix for selecting channel
        mpod = MPOD.MPOD(mn, IPv4Address(s['ip']), s['crate_path'], debug=s["debug"]) # (a)          

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
                self.channel_dict['{}_pc'.format(lnum)] = 'u{:d}'.format(mn) + str(ch).zfill(2)
            elif(ch % 3 == 1):
                mpod.add_channel(ch, max_current=float(max_i['mcp1']), ramp_rate=float(s["ramp_rate"]), fall_rate=float(s["fall_rate"]))
                self.channel_dict['{}_mcp1'.format(lnum)] = 'u{:d}'.format(mn) + str(ch).zfill(2)
            else:
                mpod.add_channel(ch, max_current=float(max_i['mcp2']), ramp_rate=float(s["ramp_rate"]), fall_rate=float(s["fall_rate"]))
                self.channel_dict['{}_mcp2'.format(lnum)] = 'u{:d}'.format(mn) + str(ch).zfill(2)
                lappd_count +=1

        self.mpod = mpod

    def load_new_setpoints(self):
        #first load the settings file again
        self.load_settings()

        #then update the setpoints for each channel
        for ch in self.channel_dict:
            lappd = ch.split('_')[0]
            vtap = ch.split('_')[1]
            setp = float(self.settings[lappd]["set_v"][vtap])
            self.mpod.execute_command('outputVoltage', setp, ch_key=self.channel_dict[ch])
    
    def channels_on(self):
        self.mpod.execute_command('groupsSwitch', 1)
        self.is_on = True
    
    def channels_off(self):
        self.mpod.execute_command('groupsSwitch', 0)
        self.is_on = False


    def get_string_setpoints(self):
        output = ""
        ls = ["l" + _ for _ in self.settings["lappds_in_use"]]
        vtaps = ["pc", "mcp1", "mcp2"]
        for l in ls:
            output += l + ":\n"
            for v in vtaps:
                output += "\t" + v + " : " + str(self.settings[l]["set_v"][v]) + " V\n"
            
        return output