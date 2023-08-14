import brainflow
from brainflow.board_shim import BoardShim, BrainFlowInputParams
import json
import numpy as np
import os
import pandas as pd
import random
import threading

from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QStackedWidget, QFrame, QFileDialog, QComboBox)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import QTimer, QTime, pyqtSignal, pyqtSlot
from time import sleep, ctime
from threading import Thread, Event
from DataSim import DataSim

# Multi-page structure adapted from 
# https://stackoverflow.com/questions/56867107/how-to-make-a-multi-page-application-in-pyqt5


def create_empty_info():
    return {
        "SessionParams": {
            "SubjectName": "",
            "ResponseType": "",
            "StimulusType": "",
            "BlockLength": 0,
            "BlockCount": 0,
            "StimCycle": 0
        },
        "HardwareParams": {
            "SampleRate": 0,
            "HeadsetConfiguration": "",
            "HeadsetModel": "",
            "BufferSize": "100000"
        },
        "ProjectName": "",
        "Description": "",
        "Annotations": [],
        "Date": datetime.now().strftime("%m-%d-%y"),
        "Time": datetime.now().strftime("%H:%M"),
        "S3Path": None,
        "SessionID": None
        }


class CollectionSession(Thread):
    class PrepInterruptedException(Exception):
        """Raised by user closing the window during board preparation."""

    def __init__(self, boardshim: brainflow.BoardShim, sespath, buffsize):
        super().__init__(name="CollectionThread")
        self.board = boardshim
        self.sim = DataSim()
        self.buffsize = buffsize
        self.sespath = sespath
        self.fname = "data_" + ctime()[-13:-8].replace(":", "") + ".csv"
        self.ready_flag, self.ongoing, self.error_flag = Event(), Event(), Event()
        self.start_event, self.stop_event = Event(), Event()
        self.data = np.zeros((5, 1))
        self.error_message = ""

    def prepare(self):
        try:
            # self.board.prepare_session()
            # proc = multiprocessing.Process(target=self.board.prepare_session)
            proc = Thread(target=sleep, args=(5,), daemon=True)
            proc.start()
            while proc.is_alive():
                if self.stop_event.is_set():
                    raise CollectionSession.PrepInterruptedException("Window closed during board preparation.")
            self.ready_flag.set()
        except brainflow.BrainFlowError as E:
            self.error_message = str(E)
            self.error_flag.set()
        except CollectionSession.PrepInterruptedException as E:
            return

    def start_stream(self):
        print("Stream started...")
        if not self.ready_flag.is_set():
            return
        # self.board.start_stream()
        self.sim.start_stream()

    def update_data(self):
        print("Updating data...")
        try:
            if random.randint(1, 5) == 10:
                self.error_message = "RandomError: Encountered random error."
                self.error_flag.set()
            if not self.data.any():
                # self.data = self.board.get_board_data()
                self.data = self.sim.get_data()
            else:
                # self.data = np.hstack((self.data, self.board.get_board_data()))
                self.data = np.hstack((self.data, self.sim.get_data()))
            self.save_data()
        except brainflow.BrainFlowError as E:
            self.error_message = f"Error: {E}"
            self.error_flag.set()
            self.end_session()
            return

    def save_data(self):
        print("Update saved.")
        pd.DataFrame(np.copy(self.data)).to_csv(os.path.join(self.sespath, self.fname))

    def run(self):
        self.prepare()

        while not self.start_event.is_set() and not self.stop_event.is_set():
            sleep(0.1)
        if self.stop_event.is_set():
            print("over")
            return
        
        self.start_stream()
        self.ongoing.set()

        stopped = False
        while not (error := self.error_flag.is_set()) and not (stopped := self.stop_event.is_set()):
            sleep(5)
            self.update_data()

        if error:
            print(self.error_message)
            self.end_session()
            return
        if stopped:
            print("Stopped.")
            self.end_session()

    def end_session(self):
        self.save_data()
        # self.board.stop_stream()
        # self.board.release_session()
        self.sim.stop_stream()
        self.ready_flag.clear()
        self.ongoing.clear()

    def get_error(self):
        return self.error_message

    def get_flags(self):
        return (self.ready_flag, self.ongoing, self.error_flag), (self.start_event, self.stop_event)


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


class PageWindow(QFrame):
    gosig = pyqtSignal(str)

    def goto(self, name):
        self.gosig.emit(name),


class DataCollectionGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pages = {}
        self.setWindowTitle("Data Collection GUI")
        # self.setFixedWidth(500)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        cwindow = CollectionWindow()
        self.register(cwindow, "collect")
        self.register(InfoWindow(cwindow), "info")
        self.stack.setCurrentWidget(self.pages['info'])

        with open("style.txt", 'r') as f:
            self.setStyleSheet(f.read())
        self.show()

    def register(self, widget, name):
        self.pages[name] = widget
        self.stack.addWidget(widget)
        widget.gosig.connect(self.goto)

    @pyqtSlot(str)
    def goto(self, name):
        widget = self.pages[name]
        self.stack.setCurrentWidget(widget)

    def closeEvent(self, event):
        for thread in threading.enumerate():
            if thread.is_alive():
                print(thread.name)
        cwin = self.pages["collect"]
        if self.stack.currentWidget() == cwin:
            cwin.stop_session()

        event.accept()


class InfoWindow(PageWindow):
    boardmap = {'Cyton': (0, 125),
                'CytonDaisy': (2, 250)}
    buffsize_d = 100000
    buffsize_max = 450000
    buffsize_min = 500
    blengthmax = 3600
    bcountmax = 360

    def __init__(self, collection_window):
        super().__init__()
        self.setObjectName("InfoFrame")
        self.date = datetime.now().strftime("%m-%d-%y")
        self.time = datetime.now().strftime("%H:%M")
        self.infodict = create_empty_info()
        self.sespath = None
        self.infodict['Date'] = self.date
        self.infodict['Time'] = self.time
        
        # Directory Row
        self.dirlabel = QLabel("Session directory: ")
        self.curdir = QLabel(os.getcwd())
        self.dir_select = QPushButton("Browse")
        self.dir_select.clicked.connect(self.get_directory)
        self.dirframe = QFrame()
        self.dirframe.setFrameStyle(QFrame.Panel | QFrame.Plain)

        # Session Parameters
        self.sname = QLabel("Subject name:")
        self.pname = QLabel("Project name:")
        self.rtype = QLabel("Response type:")
        self.stype = QLabel("Stimulus type:")
        self.blength = QLabel("Block length (s):")
        self.bcount = QLabel("Block count:")
        self.stimcycle = QLabel("Stimulus cycle:")
        self.description = QLabel("Description")
        self.fsname = QLineEdit()
        self.fpname = QLineEdit()
        self.frtype = QComboBox()
        self.init_combobox(self.frtype, "SSVEP", "SSVEP", "ERP", "other")
        self.fstype = QComboBox()
        self.init_combobox(self.fstype, "visual", "visual", "audio", "other")
        self.fblength = QLineEdit()
        self.fblength.setValidator(QIntValidator(1, self.blengthmax))
        self.fbcount = QLineEdit()
        self.fbcount.setValidator(QIntValidator(1, self.blengthmax))
        self.fstimcycle = QLineEdit()
        self.fdescription = QLineEdit()
        self.sesframe = QFrame()
        self.sesframe.setFrameStyle(QFrame.Panel | QFrame.Plain)
        self.errorframe = QFrame()
        self.datelabel = QLabel(f"Date: {self.date}")
        self.timelabel = QLabel(f"Time: {self.time}")
        self.errlabel = QLabel()

        # Hardware Parameters
        self.config = QLabel("Headset configuration:")
        self.model = QLabel("Headset model:")
        self.buffsize = QLabel("Buffer size (samples):")
        self.serialport = QLabel("Serial port: ")
        self.fconfig = QComboBox()
        self.init_combobox(self.fconfig, "standard", "Standard", "Occipital", "Other")
        self.fmodel = QComboBox()
        self.init_combobox(self.fmodel, "CytonDaisy", "CytonDaisy", "Cyton")
        self.fbuffsize = QLineEdit()
        self.fbuffsize.setPlaceholderText(str(self.buffsize_d))
        self.fbuffsize.setValidator(QIntValidator(10, 450000))
        self.fserialport = QLineEdit()
        self.hardframe = QFrame()
        self.hardframe.setFrameStyle(QFrame.Panel | QFrame.Plain)

        # Confirmation
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.confirm_and_start)

        self.dir = self.curdir.text()
        self.colwin = collection_window
        self.init()

    def init(self):
        layout = QVBoxLayout()
        
        # Directory Selector
        dirlayout = QGridLayout()
        dirlayout.addWidget(self.dirlabel, 0, 0, 1, 2)
        dirlayout.addWidget(self.curdir, 0, 2)
        dirlayout.addWidget(self.dir_select, 0, 3)
        self.dirframe.setLayout(dirlayout)
        layout.addWidget(self.dirframe)

        # Parameter layout
        middlebar = QHBoxLayout()

        # Session Parameters and Error Box
        seslayout = QGridLayout()
        seslayout.addWidget(self.sname, 0, 0)
        seslayout.addWidget(self.fsname, 0, 1)
        seslayout.addWidget(self.pname, 1, 0)
        seslayout.addWidget(self.fpname, 1, 1)
        seslayout.addWidget(self.rtype, 2, 0)
        seslayout.addWidget(self.frtype, 2, 1)
        seslayout.addWidget(self.stype, 3, 0)
        seslayout.addWidget(self.fstype, 3, 1)
        seslayout.addWidget(self.blength, 4, 0)
        seslayout.addWidget(self.fblength, 4, 1)
        seslayout.addWidget(self.bcount, 5, 0)
        seslayout.addWidget(self.fbcount, 5, 1)
        seslayout.addWidget(self.stimcycle, 6, 0)
        seslayout.addWidget(self.fstimcycle, 6, 1)
        seslayout.addWidget(self.description, 7, 0, 1, 2)
        seslayout.addWidget(self.fdescription, 8, 0, 1, 2)
        self.sesframe.setLayout(seslayout)

        middlebar.addWidget(self.sesframe)

        # Hardware Parameters
        rightlayout = QVBoxLayout()
        hardlayout = QGridLayout()
        hardlayout.addWidget(self.config, 1, 0)
        hardlayout.addWidget(self.fconfig, 1, 1)
        hardlayout.addWidget(self.model, 2, 0)
        hardlayout.addWidget(self.fmodel, 2, 1)
        hardlayout.addWidget(self.buffsize, 3, 0)
        hardlayout.addWidget(self.fbuffsize, 3, 1)
        hardlayout.addWidget(self.serialport, 4, 0)
        hardlayout.addWidget(self.fserialport, 4, 1)
        self.hardframe.setLayout(hardlayout)
        rightlayout.addWidget(self.hardframe)

        errlayout = QGridLayout()
        errlayout.addWidget(self.datelabel, 0, 0)
        errlayout.addWidget(self.timelabel, 0, 1)
        errlayout.addWidget(self.errlabel, 1, 0, 1, 2)
        self.errorframe.setLayout(errlayout)
        rightlayout.addWidget(self.errorframe)

        middlebar.addLayout(rightlayout)

        layout.addLayout(middlebar)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

    def init_combobox(self, cbox, default, *options):
        cbox.setCurrentText(default)
        cbox.addItems(options)

    def confirm_and_start(self):
        if not (res := self.check_info())[0]:
            self.errlabel.setText(f"Error: {res[1]}")
            return
        else:
            ipath = self.save_info()
        
        params = BrainFlowInputParams()
        params.serial_port = self.fserialport.text()
        bid = self.boardmap[self.fmodel.currentText()][0]
        try:
            board = BoardShim(bid, params)
        except brainflow.BrainFlowError as E:
            self.errlabel.setText(
                "Error creating BoardShim object.\n{E}"
            )

        session = CollectionSession(board, self.sespath, int(self.fbuffsize.text()))
        self.colwin.activate(os.path.join(self.sespath, "info.json"), session)
        self.goto_collection()
    
    def check_info(self):
        if not self.fsname.text():
            return False, "No subject name supplied."
        if not self.fpname.text():
            return False, "No project name supplied."
        bl = self.fblength.text()
        if not bl:
            return False, "No block length supplied."
        bl = int(bl)
        if bl < 1:
            return False, "Block length must be positive."
        if bl > self.blengthmax:
            return False, f"Block length too high. (Max: {self.blengthmax})"
        bc = self.fbcount.text()
        if not bc:
            return False, "No block count supplied."
        bc = int(bc)
        if bc < 1:
            return False, "Block count must be positive."
        elif bc > self.bcountmax:
            return False, f"Block count too high. (Max: {self.bcountmax})"
        
        if not self.fstimcycle.text():
            return False, "No stimulus cycle supplied."
        if len(self.fstimcycle.text()) != bc:
            return False, "Invalid stim cycle."
        if self.fbuffsize.text() == "":
            return False, "No buffer size supplied."
        if int(self.fbuffsize.text()) > 450000:
            return False, f"Buffer size too high. (Max: {self.buffsize_max})"
        if int(self.fbuffsize.text()) < 500:
            return (False, f"Buffer size too low. (Min: {self.buffsize_min})")
        if not self.fserialport.text():
            return False, "No serial port supplied."
        
        return True, ""

    def save_info(self):
        info = self.infodict
        info['SessionParams']['SubjectName'] = self.fsname.text()
        info['SessionParams']['ResponseType'] = self.frtype.currentText()
        info['SessionParams']['StimulusType'] = self.fstype.currentText()
        blength, bcount = self.fblength.text(), self.fbcount.text(),
        info['SessionParams']['BlockLength'] = blength
        info['SessionParams']['BlockCount'] = bcount
        info['SessionParams']['StimCycle'] = self.fstimcycle.text()
        info['HardwareParams']['HeadsetConfiguration'] = self.fconfig.currentText()
        model = self.fmodel.currentText()
        info['HardwareParams']['HeadsetModel'] = model
        info['HardwareParams']['SampleRate'] = str(self.boardmap[model][1])
        info['HardwareParams']['BufferSize'] = str(self.fbuffsize.text())
        info['ProjectName'] = self.fpname.text()
        info['Description'] = self.fdescription.text()

        bcount = int(bcount)
        blength = int(blength)
        info['Annotations'] = [(float(blength*k), f"Block{k}") for k in range(1, bcount+1)]

        suffix = self.date + "_" + self.time.replace(":", "")
        self.sespath = os.path.join(self.curdir.text(), f"session_{suffix}")
        os.makedirs(self.sespath, exist_ok=True, mode=0o777)
        with open(os.path.join(self.sespath, "info.json"), 'w') as f:
            json.dump(info, f, ensure_ascii=False, indent=4)

    def get_directory(self):
        dir = QFileDialog.getExistingDirectory(self, "Choose a directory")
        self.curdir.setText(dir)

    def goto_collection(self):
        self.goto("collect")


class CollectionWindow(PageWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("CollectFrame")

    def activate(self, infopath, csession):
        self.csession = csession
        self.csession.start()

        self.infopath = infopath
        with open(infopath, 'r') as i:
            self.info = json.loads(i.read())

        flags = self.csession.get_flags()
        # Only set by collection thread to indicate board status
        self.ready_flag, self.ongoing, self.error_flag = flags[0]
        # Set by GUI thread to start collection, but stop may be set by either collection or GUI thread
        self.start_event, self.stop_event = flags[1]

        self.session_status = "Preparing"
        self.bcount = int(self.info['SessionParams']['BlockCount'])
        self.blength = int(self.info['SessionParams']['BlockLength'])
        self.stimcycle = self.info['SessionParams']['StimCycle']
        self.itext = None

        self.current_block = 0
        self.start_time = None
        self.t = 0
        self.complete = False
        self.timer = QTimer(self)

        # Top section
        self.info_panel = QFrame(self)
        self.info_panel.setFrameStyle(QFrame.Panel | QFrame.Plain)

        self.info_labels = QLabel(parent=self.info_panel)
        self.info_labels.setText("Subject:\nProject:\nResponse type:\nStimulus type:\n\nSampling rate:\n" + 
                                 "Configuration:\nModel:\n\nSession status:")
        self.info_labels.setObjectName('FieldLabels')
        self.info_text = QLabel(parent=self.info_panel)

        # Bottom Left Panel
        self.status_panel = QFrame(self)
        self.status_panel.setFrameStyle(QFrame.Panel | QFrame.Plain)
        self.status_panel.setFixedWidth(235)
        self.status_label = QLabel("Active")
        self.status_info = QLabel()
        self.timer_label = QLabel("00:00")
        self.stimer_label = QLabel("00:00")

        # Bottom Right Panel
        self.session_panel = QFrame(self)
        self.session_panel.setFrameStyle(QFrame.Panel | QFrame.Plain)
        self.session_label = QLabel(f"Block Count: {self.bcount}\nBlock Length: {self.blength}s\n" +
                                    f"Cycle: {self.stimcycle}")
        
        # Buttons and top level widgets
        self.entry_button = QPushButton("Mark Event")
        self.entry_annotation = QLineEdit(self)
        self.entry_annotation.returnPressed.connect(self.on_enter_annotation)
        self.state_indicator = StateIndicator("#04d481", "black")
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        self.init()

    def init(self):
        layout = QVBoxLayout()
        gridlayout = QGridLayout()

        infolayout = QHBoxLayout()
        infolayout.addWidget(self.info_labels)
        infolayout.addWidget(self.info_text)
        self.info_panel.setLayout(infolayout)
        gridlayout.addWidget(self.info_panel, 0, 0, 1, 2)

        statuslayout = QGridLayout()
        statuslayout.addWidget(self.state_indicator, 0, 0)
        statuslayout.addWidget(self.status_label, 0, 1)
        statuslayout.addWidget(self.status_info, 1, 0, 1, 2)
        statuslayout.addWidget(self.timer_label, 1, 3)
        statuslayout.addWidget(self.stimer_label, 0, 3)
        self.status_panel.setLayout(statuslayout)
        gridlayout.addWidget(self.status_panel, 1, 0)

        sessionlayout = QVBoxLayout()
        sessionlayout.addWidget(self.session_label)
        self.session_panel.setLayout(sessionlayout)
        gridlayout.addWidget(self.session_panel, 1, 1)

        layout.addLayout(gridlayout)
        layout.addWidget(self.entry_annotation)
        layout.addWidget(self.entry_button)
        self.entry_button.clicked.connect(self.on_enter_annotation)
        self.entry_button.setDisabled(True)
        layout.addWidget(self.start_button)
        self.start_button.clicked.connect(self.start_session)
        self.start_button.setDisabled(True)
        layout.addWidget(self.stop_button)
        self.stop_button.clicked.connect(self.stop_session)
        self.stop_button.setDisabled(True)

        self.setLayout(layout)
        self.entry_annotation.setPlaceholderText("t0")
        self.set_info()
        self.update_status()
        ready_thread = Thread(target=self.wait_for_ready, name="ReadyThread")
        ready_thread.start()

    def wait_for_ready(self):
        i = 0
        while not (ready := self.ready_flag.is_set()) and not self.error_flag.is_set():
            self.session_status = "Preparing" + "." * i
            self.set_info()
            i = (i+1) % 4
            sleep(0.5)
        if ready:
            self.session_status = "Ready"
            self.set_info()
            self.start_button.setDisabled(False)
        elif self.error_flag.is_set():
            self.session_status = self.csession.get_error()
            self.set_info()

    def show_ongoing(self):
        i = 0
        while not self.stop_event.is_set() and not self.error_flag.is_set():
            self.session_status = "Collecting" + "." * i
            self.set_info()
            i = (i+1) % 4
            sleep(0.5)

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
            return
        else:  # Negative current block or current block > bcount. Should never happen.
            return
        
        if self.stimcycle[self.current_block-1] == '1':
            self.state_indicator.set_active(True)
        else:
            self.state_indicator.set_active(False)

    def update_timer(self):
        if self.error_flag.is_set():
            self.set_info()
            self.stop_session()
            return

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
            self.session_status = "Complete"
            self.current_block = self.bcount
            self.timer_label.setText("00:00")
            self.stop_session()

    def start_session(self):
        if not self.ready_flag.is_set():
            return
        ongoing_thread = Thread(target=self.show_ongoing, name="OngoingThread")
        ongoing_thread.start()
        self.start_event.set()
        self.current_block = 1
        self.start_time = datetime.now()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(10)  # Timer interval in milliseconds
        self.entry_button.setDisabled(False)
        self.start_button.setDisabled(True)
        self.stop_button.setDisabled(False)        

    def stop_session(self):
        self.stop_event.set()
        self.timer.stop()
        self.state_indicator.set_active(False)
        self.stop_button.setDisabled(True)
        self.entry_button.setDisabled(True)
        if self.error_flag.is_set():
            self.session_status = self.csession.get_error()
        else:
            self.session_status = "Complete"
        self.set_info()

    def tlabel(self):
        self.t += 1
        return f"t{self.t}"


if __name__ == "__main__":
    app = QApplication([])
    gui = DataCollectionGUI()
    app.exec_()
