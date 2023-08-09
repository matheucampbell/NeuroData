import json
import threading

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QGridLayout, QWidget, QFrame
from PyQt5.QtCore import Qt, QTimer, QTime
from datetime import datetime


class StateIndicator(QFrame):
    def __init__(self, active_color, inactive_color):
        super().__init__()
        self.setFixedSize(40, 40)
        self.active = active_color
        self.inactive = inactive_color
        self.set_color(False)

    def set_color(self, active=True):
        if active:
            self.setStyleSheet(f"#StateIndicator {{ background-color: {self.active}; border-radius: 20px; }}")
        else:
            self.setStyleSheet(f"#StateIndicator {{ background-color: {self.inactive}; border-radius: 20px; }}")


class DataCollectionGUI(QMainWindow):
    def __init__(self, infopath):
        super().__init__()
        self.infopath = infopath
        with open(infopath, 'r') as i:
            self.info = json.loads(i.read())

        self.bcount = int(self.info['SessionParams']['BlockCount'])
        self.blength = int(self.info['SessionParams']['BlockLength'])
        self.stimcycle = self.info['SessionParams']['StimCycle']
        self.current_block = 1
        self.start_time = None
        self.t = 0
        self.complete = False
        self.timer = QTimer(self)

        self.central_widget = QWidget(self)
        self.label_status = QLabel(f"Block: {self.current_block}/{self.bcount}\t00:00")
        self.label_timer = QLabel(f"00:00")
        self.label_stimcycle = QLabel(self.get_stimcycle_text())
        self.entry_button = QPushButton("Add Annotation")
        self.entry_annotation = QLineEdit(self)
        self.state_indicator = StateIndicator("#04d481", "#1d2324")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.init()

    def init(self):
        self.setWindowTitle("Data Collection GUI")
        self.setFixedSize(500, 500)

        self.setCentralWidget(self.central_widget)

        layout = QGridLayout()

        layout.addWidget(self.label_status)
        layout.addWidget(self.label_stimcycle)

        ind_layout = QGridLayout()
        ind_layout.addWidget(self.state_indicator, 0, 1, Qt.AlignRight)
        layout.addLayout(ind_layout)

        self.entry_annotation.returnPressed.connect(self.on_enter_annotation)
        self.entry_annotation.setPlaceholderText("t0")
        layout.addWidget(self.entry_annotation)

        self.entry_button.clicked.connect(self.on_enter_annotation)
        layout.addWidget(self.entry_button)

        self.start_button.clicked.connect(self.start_session)
        layout.addWidget(self.start_button)

        self.stop_button.clicked.connect(self.stop_session)
        layout.addWidget(self.stop_button)
        self.stop_button.setDisabled(True)

        self.state_indicator.setFrameShape(QFrame.StyledPanel)
        self.state_indicator.setObjectName("StateIndicator")
        self.central_widget.setLayout(layout)
        self.show()

        with open("style.txt", 'r') as f:
            self.setStyleSheet(f.read())

    def start_session(self):
        self.current_block = 1
        self.start_time = datetime.now()
        self.complete = False
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(10)  # Timer interval in milliseconds
        self.start_button.setDisabled(True)
        self.stop_button.setDisabled(False)

    def stop_session(self):
        self.current_block = 1
        self.start_time = None
        self.complete = False
        self.timer.stop()
        self.label_status.setText(f"Block: {self.current_block}/{self.bcount}\t00:00")
        self.label_stimcycle.setText(self.get_stimcycle_text())

        self.state_indicator.set_color(active=False)

        self.start_button.setDisabled(False)
        self.stop_button.setDisabled(True)

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

    def tlabel(self):
        self.t += 1
        return f"t{self.t}"

    def get_stimcycle_text(self):
        if self.current_block - 1 < len(self.stimcycle):
            stimulus_active = self.stimcycle[self.current_block - 1] == '1'
            return f"Stimulus in Current Block: {'Active' if stimulus_active else 'Inactive'}"
        else:
            return "Stimcycle data not available for current block"

    def update_current_block(self, ftime):
        elapsed_time = datetime.now() - self.start_time
        self.current_block = int(elapsed_time.total_seconds() / self.blength) + 1
        if self.current_block > self.bcount:
            self.current_block = self.bcount
            self.timer.stop()
            self.label_stimcycle.setText("Session complete")
            self.complete = True
            self.state_indicator.set_color(active=False)
            self.stop_button.setDisabled(False)
        else:
            self.label_status.setText(f"Block: {self.current_block}/{self.bcount}\t{ftime}")
            self.label_stimcycle.setText(self.get_stimcycle_text())
            stimulus_active = self.stimcycle[self.current_block - 1] == '1'
            self.state_indicator.set_color(stimulus_active)

    def update_timer(self):
        if self.start_time:
            # Call the update_current_block method in a separate thread
            elapsed_time = datetime.now() - self.start_time
            elapsed_seconds = int(elapsed_time.total_seconds())

            if self.current_block <= self.bcount and not self.complete:
                remaining_seconds = max(0, self.blength - (elapsed_seconds % self.blength))
                formatted_time = QTime(0, 0).addSecs(remaining_seconds).toString("mm:ss")

                thread = threading.Thread(target=self.update_current_block, args=(formatted_time,))
                thread.start()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    data_collection_gui = DataCollectionGUI(".cache.json")
    sys.exit(app.exec_())
