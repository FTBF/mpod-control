import sys
sys.path.append("LappdControl/")
from LappdControl import LappdControl
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit


class HVControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HV Control")
        self.layout = QVBoxLayout()
        self.button_load_setpoints = QPushButton("Load New Setpoints")
        self.on_button = QPushButton("Turn channels on, ramping to setpoints")
        self.on_button.setCheckable(True)
        self.layout.addWidget(self.on_button)


        

        self.text_output = QTextEdit()
        self.layout.addWidget(self.button_load_setpoints)
        self.layout.addWidget(self.text_output)

        #emergency off button
        self.emerg_button = QPushButton("Emergency Off")
        self.emerg_button.setGeometry(200, 150, 100, 100)
        self.emerg_button.setStyleSheet("background-color: #f5877f; border-radius: 50px; border: 2px solid black")  # Modified line
        self.layout.addWidget(self.emerg_button)    

        self.setLayout(self.layout)
        self.button_load_setpoints.clicked.connect(self.load_setpoints)
        self.on_button.clicked.connect(self.toggle_on_off)
        self.emerg_button.clicked.connect(self.emergency_off)

        self.lc = LappdControl.LappdControl(sys.argv[-1])

    def load_setpoints(self):
        self.lc.load_new_setpoints()
        # Add your code here to load new setpoints
        self.text_output.append("New setpoints loaded from file:")
        self.text_output.append(self.lc.get_string_setpoints())


    def toggle_on_off(self):
        # Add your code here to toggle ON / OFF
        if(self.on_button.isChecked()):
            self.on_button.setStyleSheet("background-color: green")
            self.on_button.setText("Channels are ACTIVELY going to setpoints")
            self.text_output.append("Channels are now ACTIVELY going to setpoints")
            self.lc.channels_on()
        else:
            self.on_button.setStyleSheet("background-color: grey")
            self.on_button.setText("Channels are OFF at 0V")
            self.text_output.append("Channels are now off and not going to setpoints")
            self.lc.channels_off()

    def emergency_off(self):
        # Add your code here to turn off all channels
        self.text_output.append("Emergency off button pressed")
        self.lc.emergency_off()

if __name__ == "__main__":
    if(len(sys.argv) < 2):
        print("Usage: python run_hv_control.py <settings_file.yml>")
        sys.exit(1)
    app = QApplication(sys.argv)
    gui = HVControlGUI()
    gui.show()
    sys.exit(app.exec_())