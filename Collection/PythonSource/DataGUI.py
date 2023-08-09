import json
import threading

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFrame
from PyQt5.QtCore import Qt, QTimer, QTime
from datetime import datetime


class StateIndicator(QFrame):

    def __init__(self, active_color, inactive_color, dia=20):
        super().__init__()
        self.setFixedSize(dia, dia)
        self.dia = dia
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("StateIndicator")

        self.active = active_color
        self.inactive = inactive_color
        self.set_active(False)

    def set_active(self, active=True):
        if active:
            self.setStyleSheet(f"#StateIndicator {{ background-color: {self.active}; border-radius: {self.dia//2}px; }}")
        else:
            self.setStyleSheet(f"#StateIndicator {{ background-color: {self.inactive}; border-radius: {self.dia//2}px; }}")


class DataCollectionGUI(QMainWindow):
    def __init__(self, infopath):
        super().__init__()
        self.infopath = infopath
        with open(infopath, 'r') as i:
            self.info = json.loads(i.read())
        
        self.bcount = int(self.info['SessionParams']['BlockCount'])
        self.blength = int(self.info['SessionParams']['BlockLength'])
        self.stimcycle = self.info['SessionParams']['StimCycle']
        self.session_status = "Ready"
        self.itext = None

        self.current_block = 0
        self.start_time = None
        self.t = 0
        self.complete = False
        self.timer = QTimer(self)

        # Top section
        self.info_panel = QFrame(self)
        self.info_panel.setFrameStyle(QFrame.Panel|QFrame.Plain)

        self.info_labels = QLabel(parent=self.info_panel)
        self.info_labels.setText("Subject:\nProject:\nResponse Type:\nStimulus Type:\n\nSampling Rate:\n" + 
                                 "Configuration:\nModel:\n\nSession Status:")
        self.info_labels.setObjectName('FieldLabels')
        self.info_text = QLabel(parent=self.info_panel)

        # Bottom Left Panel
        self.status_panel = QFrame(self)
        self.status_panel.setFrameStyle(QFrame.Panel|QFrame.Plain)
        self.status_panel.setFixedWidth(235)
        self.status_label = QLabel("Active")
        self.status_info = QLabel()
        self.timer_label = QLabel("00:00")
        self.stimer_label = QLabel("00:00")

        # Bottom Right Panel
        self.session_panel = QFrame(self)
        self.session_panel.setFrameStyle(QFrame.Panel|QFrame.Plain)
        self.session_label = QLabel(f"Block Count: {self.bcount}\nBlock Length: {self.blength}s\n" +
                                    f"Cycle: {self.stimcycle}")
        
        # Buttons and top level widgets
        self.central_widget = QWidget(self)
        self.entry_button = QPushButton("Add Annotation")
        self.entry_annotation = QLineEdit(self)
        self.state_indicator = StateIndicator("#04d481", "black")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.init()

    def init(self):
        self.setWindowTitle("Data Collection GUI")
        self.setFixedSize(500, 500)
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()
        gridlayout = QGridLayout()
        gridlayout.setColumnMinimumWidth(0, 5)
        gridlayout.setColumnMinimumWidth(2, 2)
        gridlayout.setColumnMinimumWidth(4, 5)
        gridlayout.setRowMinimumHeight(0, 5)
        gridlayout.setRowMinimumHeight(2, 5)
        gridlayout.setRowMinimumHeight(4, 5)

        infolayout = QHBoxLayout()
        infolayout.addWidget(self.info_labels)
        infolayout.addWidget(self.info_text)
        self.info_panel.setLayout(infolayout)
        gridlayout.addWidget(self.info_panel, 1, 1, 1, 3)

        statuslayout = QGridLayout()
        statuslayout.addWidget(self.state_indicator, 0, 0)
        statuslayout.addWidget(self.status_label, 0, 1)
        statuslayout.addWidget(self.status_info, 1, 0, 1, 3)
        statuslayout.addWidget(self.timer_label, 1, 3)
        statuslayout.addWidget(self.stimer_label, 0, 3)
        self.status_panel.setLayout(statuslayout)
        gridlayout.addWidget(self.status_panel, 3, 1)

        sessionlayout = QVBoxLayout()
        sessionlayout.addWidget(self.session_label)
        self.session_panel.setLayout(sessionlayout)
        gridlayout.addWidget(self.session_panel, 3, 3)

        layout.addLayout(gridlayout)
        layout.addWidget(self.entry_annotation)
        layout.addWidget(self.entry_button)
        layout.addWidget(self.start_button)
        self.start_button.clicked.connect(self.start_session)
        layout.addWidget(self.stop_button)
        self.stop_button.clicked.connect(self.stop_session)

        self.central_widget.setLayout(layout)
        self.set_info()
        self.update_status()
        self.show()
        with open("style.txt", 'r') as f:
            self.setStyleSheet(f.read())

    def add_annotation(self, time, note):
        self.info['Annotations'].append([time, note])
        with open(self.infopath, 'w') as file:
            json.dump(self.info, file, ensure_ascii=False, indent=4)

    def on_enter_annotation(self):
        if not self.start_time:
            return
        annotation = self.entry_annotation.text()
        timestamp = round((datetime.now() - self.start_time).total_seconds(), 2)

        if not annotation:
            annotation = f"t{self.t}"

        self.add_annotation(timestamp, annotation)
        self.entry_annotation.clear()
        self.entry_annotation.setPlaceholderText(self.tlabel())

    def set_info(self):
        if not self.itext:
            sub = self.info['SessionParams'].get('SubjectName', '--') + '\n'
            proj = self.info.get('ProjectName', '--') + '\n'
            resp = self.info['SessionParams'].get('ResponseType', '--') + '\n'
            stype = self.info['SessionParams'].get('StimulusType', '--') + '\n\n'
            srate = self.info['HardwareParams'].get('SampleRate', '--') + '\n'
            config = self.info['HardwareParams'].get('HeadsetConfiguration', '--') + '\n'
            model = self.info['HardwareParams'].get('HeadsetModel', '--')
            self.itext = sub + proj + resp + stype + srate + config + model
        
        self.info_text.setText(self.itext + f"\n\n{self.session_status}")
    
    def update_status(self):
        if 1 <= self.current_block < len(self.stimcycle):  # Session in progress and not last block
            next_active = self.stimcycle[self.current_block] == '1'
            next = "Active" if next_active else "Inactive"
            self.status_info.setText(f"Block: {self.current_block}/{self.bcount}\nNext: {next}")
        elif self.current_block == self.bcount:  # Session in progress on last block
            self.status_info.setText(f"Block: {self.current_block}/{self.bcount}\nNext: None")
        elif self.current_block == 0:  # Initial state before starting session
            next_active = self.stimcycle[self.current_block] == '1'
            next = "Active" if next_active else "Inactive"
            self.status_info.setText(f"Block: {self.current_block}/{self.bcount}\nNext: {next}")
        else:  # Negative current block or current block > bcount. Should never happen.
            return
        
        if self.stimcycle[self.current_block-1] == '1':
            self.state_indicator.set_active(True)
        else:
            self.state_indicator.set_active(False)

    def update_timer(self):
        elapsed_time = datetime.now() - self.start_time
        elapsed_seconds = int(elapsed_time.total_seconds())
        remaining_seconds = max(0, self.blength - (elapsed_seconds % self.blength))
        formatted_time = QTime(0, 0).addSecs(remaining_seconds).toString("mm:ss")
        self.timer_label.setText(formatted_time)
        self.stimer_label.setText(QTime(0, 0).addSecs(elapsed_seconds).toString("mm:ss"))

        self.update_status()
        self.update_block(elapsed_time)
    
    def update_block(self, elapsed):
        self.current_block = int(elapsed.total_seconds() / self.blength) + 1
        if self.current_block > self.bcount:
            self.current_block = self.bcount
            self.timer_label.setText("00:00")
            self.stop_session()

    def start_session(self):
        self.current_block = 1
        self.start_time = datetime.now()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(10)  # Timer interval in milliseconds
        self.start_button.setDisabled(True)
        self.stop_button.setDisabled(False)

    def stop_session(self):
        self.timer.stop()
        self.state_indicator.set_active(False)
        self.stop_button.setDisabled(True)
        self.entry_button.setDisabled(True)

    def tlabel(self):
        self.t += 1
        return f"t{self.t}"


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    data_collection_gui = DataCollectionGUI(".cache.json")
    data_collection_gui.show()
    sys.exit(app.exec_())
