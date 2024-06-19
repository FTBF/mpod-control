import sys
sys.path.append("LappdControl/")
from LappdControl import LappdControl
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QGridLayout


class HVControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HV Control")
        self.resize(600, 400)
        self.layout = QGridLayout()
        self.button_load_setpoints = QPushButton("Load New Setpoints")
        self.on_button = QPushButton("Channels ON")
        self.off_button = QPushButton("Channels OFF")
        self.on_button.setCheckable(True)

        self.pc_on_button = QPushButton("Photocathode ON")
        self.pc_off_button = QPushButton("Photocathode OFF")
        self.test_button_for_evan = QPushButton("Test Button for Evan")

        self.text_output = QTextEdit() #output for messages
    
        #emergency off button
        self.emerg_button = QPushButton("Emergency Off")
        self.emerg_button.setStyleSheet("background-color: #f5877f; border-radius: 50px; border: 2px solid black")  # Modified line
          

        #connections to functions
        self.button_load_setpoints.clicked.connect(self.load_setpoints)
        self.on_button.clicked.connect(self.toggle_channels_on)
        self.off_button.clicked.connect(self.toggle_channels_off)
        self.emerg_button.clicked.connect(self.emergency_off)
        self.pc_on_button.clicked.connect(self.toggle_pc_on)
        self.pc_off_button.clicked.connect(self.toggle_pc_off)
        

        #move buttons around
        self.layout.addWidget(self.on_button, 0, 0)
        self.layout.addWidget(self.off_button, 0, 1)
        self.layout.addWidget(self.pc_on_button, 1, 0)
        self.layout.addWidget(self.pc_off_button, 1, 1)
        self.layout.addWidget(self.button_load_setpoints, 2, 0)
        self.layout.addWidget(self.text_output, 3, 0)
        self.layout.addWidget(self.emerg_button, 4, 0)  
        self.layout.addWidget(self.test_button_for_evan, 5, 0)
        self.setLayout(self.layout)

        self.lc = LappdControl.LappdControl(sys.argv[-1])

        self.text_output.append("------------------------\nJust started HV control program. We have not loaded new setpoints yet. We have reconfigured current limits and ramp rates. The channels may even be on! But feel free to press the `Channels ON' button to resend that command either way.\n--------------------\n\n")
        
        self.test_button_for_evan.clicked.connect(self.lc.get_current_voltages)
        
    def load_setpoints(self):
        self.lc.load_new_setpoints()
        # Add your code here to load new setpoints
        self.text_output.append("New setpoints loaded from file:")
        self.text_output.append(self.lc.get_string_setpoints())


    def toggle_channels_on(self):
        # Add your code here to toggle ON / OFF
        self.off_button.setStyleSheet("")
        self.on_button.setStyleSheet("background-color: green")
        self.text_output.append("Channels are now ACTIVELY going to setpoints")
        self.lc.channels_on()
    
    def toggle_channels_off(self):
        #deactivate the on button
        self.on_button.setStyleSheet("")
        self.off_button.setStyleSheet("background-color: green")
        self.text_output.append("Channels are now off and resetting to 0V as gracefully as possible")
        self.lc.channels_off()


    def toggle_pc_on(self):
        # Add your code here to toggle ON / OFF
        self.pc_off_button.setStyleSheet("")
        self.pc_on_button.setStyleSheet("background-color: green")
        self.text_output.append("Photocathode has been set to ON")
        self.lc.photocathode_on()
    
    def toggle_pc_off(self):
        #deactivate the on button
        self.pc_on_button.setStyleSheet("")
        self.pc_off_button.setStyleSheet("background-color: green")
        self.text_output.append("Photocathode is now ramping off")
        self.lc.photocathode_off()

    def emergency_off(self):
        self.lc.emergency_off()
        self.text_output.append("Emergency off button pressed!! You will now have to physically go to the MPOD and turn it back on.")

if __name__ == "__main__":
    if(len(sys.argv) < 2):
        print("Usage: python run_hv_control.py <settings_file.yml>")
        sys.exit(1)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    gui = HVControlGUI()
    gui.show()
    sys.exit(app.exec_())