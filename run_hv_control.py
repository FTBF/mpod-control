import sys
sys.path.append("LappdControl/")
from LappdControl import LappdControl
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QGridLayout, QSpacerItem, QSizePolicy, QTextEdit


class HVControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control of LAPPD HV supplies in FTBF")
        #self.resize(600, 800)
        self.layout = QGridLayout()
        self.layout.setSpacing(0)

        self.text_output = QTextEdit() #GUI text terminal gets passed to LC object. 
        self.lc = LappdControl.LappdControl(sys.argv[-1], self.text_output)

        lnums = self.lc.settings["lappds_in_use"]
        #buttons for each LAPPD column
        self.ch_on_buttons = {}
        self.ch_off_buttons = {}
        self.pc_on_buttons = {}
        self.pc_off_buttons = {}
        self.load_setpoints_buttons = {}
        self.ch_status_buttons = {}
        offset = 3 #how many columns dedicated for each LAPPD
        for i, l in enumerate(lnums):
            self.layout.addWidget(QLabel("LAPPD {}".format(l)), 0, 0 + i*offset)
            self.ch_on_buttons[l] = QPushButton("Channels ON")
            self.ch_on_buttons[l].clicked.connect(lambda _, x=l: self.channels_on(x))
            self.layout.addWidget(self.ch_on_buttons[l], 1, 0 + i*offset)
            self.ch_off_buttons[l] = QPushButton("Channels OFF")
            self.ch_off_buttons[l].clicked.connect(lambda _, x=l: self.channels_off(x))
            self.layout.addWidget(self.ch_off_buttons[l], 1, 1 + i*offset)
            self.pc_on_buttons[l] = QPushButton("Photocathode ON")
            self.pc_on_buttons[l].clicked.connect(lambda _, x=l: self.photocathode_on(x))
            self.layout.addWidget(self.pc_on_buttons[l], 2, 0 + i*offset)
            self.pc_off_buttons[l] = QPushButton("Photocathode OFF")
            self.pc_off_buttons[l].clicked.connect(lambda _, x=l: self.photocathode_off(x))
            self.layout.addWidget(self.pc_off_buttons[l], 2, 1 + i*offset)
            self.load_setpoints_buttons[l] = QPushButton("Load New Setpoints")
            self.load_setpoints_buttons[l].clicked.connect(lambda _, x=l: self.load_new_setpoints(x))
            self.layout.addWidget(self.load_setpoints_buttons[l], 3, 0 + i*offset)
            #self.ch_status_buttons[l] = QPushButton("Read Channels")
            #self.ch_status_buttons[l].clicked.connect(lambda _, x=l: self.read_channels(x))
            #self.layout.addWidget(self.ch_status_buttons[l], 3, 1 + i*offset)
            self.layout.addItem(QSpacerItem(80, 40, QSizePolicy.Minimum, QSizePolicy.Expanding),0, 2 + i*offset)
            

        #emergency off button
        self.emerg_button = QPushButton("Emergency Off")
        self.emerg_button.setStyleSheet("background-color: #f5877f; border-radius: 50px; border: 2px solid black")  # Modified line
        self.layout.addWidget(self.emerg_button, 0, len(lnums)*offset-1)
        self.emerg_button.clicked.connect(self.emergency_off)

        #Text output
        self.layout.addWidget(self.text_output, 5, 0, 1, 5)

        self.setLayout(self.layout)

        #initialize the button statuses (green or grey depending on what the state of channels are)
        for l in lnums:
            if(self.lc.are_channels_on(l, check=False)):
                self.ch_on_buttons[l].setStyleSheet("background-color: green")
            else:
                self.ch_off_buttons[l].setStyleSheet("background-color: green")
            if(self.lc.is_photocathode_on(l, check=False)):
                self.pc_on_buttons[l].setStyleSheet("background-color: green")
            else:
                self.pc_off_buttons[l].setStyleSheet("background-color: green")


        #startup message
        self.text_output.append("Welcome to the LAPPD HV Control GUI")
        self.text_output.append("The config file that was loaded has the following settings:")
        for l in lnums:
            self.text_output.append("LAPPD {}: ".format(l))
            pc_config = float(self.lc.settings["l"+l]["set_v"]["pc"])
            mcp1_config = float(self.lc.settings["l"+l]["set_v"]["mcp1"])
            mcp2_config = float(self.lc.settings["l"+l]["set_v"]["mcp2"])
            self.text_output.append("  Setpoints in config file:\t\t PC {:.0f}V,\t MCP1 {:.0f},\t MCP2 {:.0f}".format(pc_config, mcp1_config, mcp2_config))
            pc_mpod = float(self.lc.channel_dict["l"+l+"_pc"]["set_v"])
            mcp1_mpod = float(self.lc.channel_dict["l"+l+"_mcp1"]["set_v"])
            mcp2_mpod = float(self.lc.channel_dict["l"+l+"_mcp2"]["set_v"])
            self.text_output.append("  Setpoints loaded on the MPOD:\t PC {:.0f}V,\t MCP1 {:.0f},\t MCP2 {:.0f}".format(pc_mpod, mcp1_mpod, mcp2_mpod))
            pc_mpod = float(self.lc.channel_dict["l"+l+"_pc"]["v_term"])
            mcp1_mpod = float(self.lc.channel_dict["l"+l+"_mcp1"]["v_term"])
            mcp2_mpod = float(self.lc.channel_dict["l"+l+"_mcp2"]["v_term"])
            self.text_output.append("  Terminal voltages on MPOD:\t PC {:.0f}V,\t MCP1 {:.0f},\t MCP2 {:.0f}".format(pc_mpod, mcp1_mpod, mcp2_mpod))
            self.text_output.append("  Channels are presently {}".format("ON" if self.lc.are_channels_on(l) else "OFF"))
        
    def load_new_setpoints(self, l):
        retval = self.lc.load_new_setpoints(l)
        if(retval):
            self.text_output.append("New setpoints loaded for LAPPD {}:".format(l))
            pc_mpod = float(self.lc.channel_dict["l"+l+"_pc"]["set_v"])
            mcp1_mpod = float(self.lc.channel_dict["l"+l+"_mcp1"]["set_v"])
            mcp2_mpod = float(self.lc.channel_dict["l"+l+"_mcp2"]["set_v"])
            self.text_output.append("\tPC {:.0f}V,\t MCP1 {:.0f},\t MCP2 {:.0f}".format(pc_mpod, mcp1_mpod, mcp2_mpod))
        else:
            self.text_output.append("Error: New setpoints could not be loaded for LAPPD {}".format(l))
            self.text_output.append("Check the terminal for more information as to why")

    def channels_on(self, l):
        self.ch_off_buttons[l].setStyleSheet("")
        self.ch_on_buttons[l].setStyleSheet("background-color: green")
        retval = self.lc.channels_on(l)
        if(retval):
            self.text_output.append("Channels turned on for LAPPD {}".format(l))
        else:
            self.text_output.append("The channels were already on! So we did nothing. If you want to load new setpoints, click the button below.")
    
    def channels_off(self, l):
        self.ch_on_buttons[l].setStyleSheet("")
        self.ch_off_buttons[l].setStyleSheet("background-color: green")
        retval = self.lc.channels_off(l)
        if(retval):
            self.text_output.append("Channels turned off for LAPPD {}".format(l))
        else:
            self.text_output.append("The channels were already off! So we did nothing.")

    def photocathode_on(self, l):
        self.pc_off_buttons[l].setStyleSheet("")
        retval = self.lc.photocathode_on(l)
        if(retval):
            self.text_output.append("Photocathode turned on for LAPPD {}".format(l))
            self.pc_on_buttons[l].setStyleSheet("background-color: green")
        else:
            self.text_output.append("Error: Photocathode could not be turned on for LAPPD {}".format(l))
            self.text_output.append("Check the terminal for more information as to why")
    
    def photocathode_off(self, l):
        self.pc_on_buttons[l].setStyleSheet("")
        self.pc_off_buttons[l].setStyleSheet("background-color: green")
        self.lc.photocathode_off(l)
        self.text_output.append("Photocathode turned off for LAPPD {}".format(l))

    def emergency_off(self):
        self.lc.emergency_off()
        self.text_output.append("!!!Emergency of has been sent!!! You'll now have to physically switch the module back on.")

    #reads all of the data that we want to display on the GUI
    #such as channel on/off status, setpoint voltages, and terminal voltages
    def read_channels(self, l):
        pass


if __name__ == "__main__":
    if(len(sys.argv) < 2):
        print("Usage: python run_hv_control.py <settings_file.yml>")
        sys.exit(1)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    gui = HVControlGUI()
    gui.show()
    sys.exit(app.exec_())