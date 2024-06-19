import sys
sys.path.append("LappdControl/")
from LappdControl import LappdControl
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QGridLayout, QSpacerItem, QSizePolicy, QRadioButton


class HVControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control of LAPPD HV supplies in FTBF")
        #self.resize(600, 800)
        self.layout = QGridLayout()
        self.layout.setSpacing(0)

        self.lc = LappdControl.LappdControl(sys.argv[-1])

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
            self.ch_status_buttons[l] = QPushButton("Read Channels")
            self.ch_status_buttons[l].clicked.connect(lambda _, x=l: self.read_channels(x))
            self.layout.addWidget(self.ch_status_buttons[l], 3, 1 + i*offset)
            self.layout.addItem(QSpacerItem(80, 40, QSizePolicy.Minimum, QSizePolicy.Expanding),0, 2 + i*offset)
            

        #emergency off button
        self.emerg_button = QPushButton("Emergency Off")
        self.emerg_button.setStyleSheet("background-color: #f5877f; border-radius: 50px; border: 2px solid black")  # Modified line
        self.layout.addWidget(self.emerg_button, 0, len(lnums)*offset)
        self.emerg_button.clicked.connect(self.emergency_off)

        self.setLayout(self.layout)

        
    def load_new_setpoints(self, l):
        self.lc.load_new_setpoints(l)

    def channels_on(self, l):
        self.ch_off_buttons[l].setStyleSheet("")
        self.ch_on_buttons[l].setStyleSheet("background-color: green")
        self.lc.channels_on(l)
    
    def channels_off(self, l):
        self.ch_on_buttons[l].setStyleSheet("")
        self.ch_off_buttons[l].setStyleSheet("background-color: green")
        self.lc.channels_off(l)

    def photocathode_on(self, l):
        self.pc_off_buttons[l].setStyleSheet("")
        self.pc_on_buttons[l].setStyleSheet("background-color: green")
        self.lc.photocathode_on(l)
    
    def photocathode_off(self, l):
        self.pc_on_buttons[l].setStyleSheet("")
        self.pc_off_buttons[l].setStyleSheet("background-color: green")
        self.lc.photocathode_on(l)

    def emergency_off(self):
        self.lc.emergency_off()

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