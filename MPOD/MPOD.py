
import subprocess
import yaml


#A command example for our purposes is found here:
#snmpget -Oqv -v 2c -M /home/nfs/pastika/Downloads/net-snmp-5.9.4/mibs -m +WIENER-CRATE-MIB -c guru/public 192.168.46.50 outputVoltage.u104 F 1050.0
class MPOD:
    def __init__(self, mod_num, ip, path, debug=False):
        self.mod_num = mod_num
        self.ip = ip
        self.path = path
        self.debug = debug

        #for debugging puposes, I create a little simulation
        #of the registers in the MPOD as a fixed yaml file here. Only
        #used in debug mode
        if(self.debug):
            self.simulation = None
            self.load_simulation()

    
    def load_simulation(self):
        with open("simulation.yml") as file:
            try:
                self.simulation = yaml.load(file, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                print(exc)
    
    def save_simulation(self):
        with open("simulation.yml", "w") as file:
            yaml.dump(self.simulation, file)


    def set_current_limit(self, ch_key, current):
        command = self.get_common(com="guru") + "outputCurrent." + ch_key + " F {:.9f}".format(current)
        if(self.debug):
            print(command)
        else:
            subprocess.run(command, shell=True)

    def set_ramp_rate(self, ch_key, rate):
        command = self.get_common(com="guru") + "outputVoltageRiseRate." + ch_key + " F {:.3f}".format(rate)
        if(self.debug):
            print(command)
        else:
            subprocess.run(command, shell=True)


    #we only use a few commands, this function will parse
    #them and use the appropriate snmp settings and such. 
    def execute_command(self, command, argument = None, ch_key=None):
        cmd_to_exec = None 
        if(command == "outputVoltage"):
            if(ch_key is None):
                print("Error: outputVoltage command requires a channel key")
                return
            if(argument != None):
                if(argument < 0 or argument > 2400):
                    print("Error: output voltage must be between 0 and 2400")
                    return
                cmd_to_exec = self.get_common(com="guru") + "outputVoltage." + ch_key + " F {:.3f}".format(argument)
                if(self.debug):
                    self.simulation[ch_key]["outputVoltage"] = argument
                    self.simulation[ch_key]["outputMeasurementTerminalVoltage"] = -1*argument
                    self.save_simulation()
                    print(cmd_to_exec)
            else:
                cmd_to_exec = self.get_common(com="public") + "outputVoltage." + ch_key
                if(self.debug):
                    print(cmd_to_exec)
                    return str(self.simulation[ch_key]["outputVoltage"]) + " V"
        
        elif(command == "sysMainSwitch"):
            if(argument is None):
                cmd_to_exec = self.get_common(com="public") + "sysMainSwitch.0"
            elif(argument != 0 and argument != 1):
                print("Error: sysMainSwitch command requires argument 0 or 1")
                return
            else:
                cmd_to_exec = self.get_common(com="guru") + "sysMainSwitch.0 i {:d}".format(argument)

        elif(command == "outputSwitch"):
            if(argument is None):
                cmd_to_exec = self.get_common(com="public") + "outputSwitch." + ch_key
                if(self.debug):
                    print(cmd_to_exec)
                    retval = self.simulation[ch_key]["outputSwitch"]
                    if(retval == 0):
                        return "off"
                    else:
                        return "on"
            elif(argument != 0 and argument != 1 and argument != 10):
                print("Error: outputSwitch command requires argument 0 or 1 or 10")
                return
            else:
                cmd_to_exec = self.get_common(com="guru") + "outputSwitch." + ch_key + " i {:d}".format(argument)
                if(self.debug):
                    self.simulation[ch_key]["outputSwitch"] = argument
                    self.save_simulation()
                    print(cmd_to_exec)

        elif(command == "outputMeasurementTerminalVoltage"):
            #argument can be anything
            if(ch_key is None):
                print("Error: outputMeasurementTerminalVoltage command requires a channel key")
                return
            cmd_to_exec = self.get_common(com="public") + "outputMeasurementTerminalVoltage." + ch_key
            if(self.debug):
                print(cmd_to_exec)
                if(self.simulation[ch_key]["outputSwitch"] == 0):
                    return "0.0 V"
                else:
                    return str(self.simulation[ch_key]["outputMeasurementTerminalVoltage"]) + " V"

        elif(command == "outputStatus"):
            if(ch_key is None):
                print("Error: outputStatus command requires a channel key")
                return
            cmd_to_exec = self.get_common(com="public") + "outputStatus." + ch_key
        else:
            print("Error: command '{}' not recognized".format(command))
            return

        if(cmd_to_exec == None):
            return

        result = subprocess.run(cmd_to_exec, shell=True, capture_output = True, text = True)
        return result.stdout



    #there is a common string for all commands.
    def get_common(self, com="guru"):
        if(com == "public"):
            output = "snmpget -Oqv -v2c  -M " + self.path + " -m +WIENER-CRATE-MIB -c " + com + " "
        else:
            output = "snmpset -Oqv -v2c  -M " + self.path + " -m +WIENER-CRATE-MIB -c " + com + " "

        output += str(self.ip) + " " 
        
        return output
        
