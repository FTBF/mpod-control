
import subprocess

#A command example for our purposes is found here:
#snmpget -Oqv -v 2c -M /home/nfs/pastika/Downloads/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB -c guru/public 192.168.46.50 outputVoltage.u104 F 1050.0
class MPOD:
    def __init__(self, mod_num, ip, path, debug=False):
        self.mod_num = mod_num
        self.ip = ip
        self.path = path
        self.debug = debug

        self.chs = [] #list of channel numbers, not used much in this class

        
    #ch_int: integer representing channel on the MPOD device itself.
    #is also the int used in the ".u1XX" suffix. 
    def add_channel(self, ch_int, max_current, ramp_rate, fall_rate):
        #set current limit for new channel
        #channel key string
        ch_key = "u" + str(self.mod_num) + str(ch_int).zfill(2)
        command = self.get_common(com="guru") + "outputCurrent." + ch_key + " F {:.9f}".format(max_current)
        if(self.debug):
            print(command)
        else:
            subprocess.run(command, shell=True)  

        #set the ramp rate for the new channel in V/s
        command = self.get_common(com="guru") + "outputVoltageRiseRate." + ch_key + " F {:.3f}".format(ramp_rate)
        if(self.debug):
            print(command)
        else:
            subprocess.run(command, shell=True)

        #set the fall rate for the new channel in V/s
        command = self.get_common(com="guru") + "outputVoltageFallRate." + ch_key + " F {:.3f}".format(fall_rate)
        if(self.debug):
            print(command)
        else:
            subprocess.run(command, shell=True)

        self.chs.append(ch_int)


    #we only use a few commands, this function will parse
    #them and use the appropriate snmp settings and such. 
    def execute_command(self, command, argument, ch_key=None):
        cmd_to_exec = None 
        if(command == "outputVoltage"):
            if(ch_key is None):
                print("Error: outputVoltage command requires a channel key")
                return
            if(argument < 0 or argument > 2400):
                print("Error: output voltage must be between 0 and 2400")
                return
            cmd_to_exec = self.get_common(com="guru") + "outputVoltage." + ch_key + " F {:.3f}".format(argument)
        
        elif(command == "sysMainSwitch"):
            if(argument != 0 and argument != 1):
                print("Error: sysMainSwitch command requires argument 0 or 1")
                return
            cmd_to_exec = self.get_common(com="private") + "sysMainSwitch.0 i {:d}".format(argument)

        elif(command == "outputSwitch"):
            if(argument != 0 and argument != 1 and argument != 10):
                print("Error: outputSwitch command requires argument 0 or 1 or 10")
                return
            cmd_to_exec = self.get_common(com="guru") + "outputSwitch." + ch_key + " i {:d}".format(argument)

        else:
            print("Error: command '{}' not recognized".format(command))
            return




        if(self.debug):
            print(cmd_to_exec)
        else:
            subprocess.run(cmd_to_exec, shell=True)



    #there is a common string for all commands.
    def get_common(self, com="guru"):
        output = "snmpset -Oqv -v2c  -M " + self.path + " -m +WIENER-CRATE-MIB -c " + com + " "

        output += str(self.ip) + " " 
        
        return output
        
