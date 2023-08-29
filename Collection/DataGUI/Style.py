"""Widget-derived custom classes and style sheet"""
import math

from numpy import linspace
from PyQt5.QtCore import Qt, QFileSystemWatcher
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QFrame, QPlainTextEdit, QGridLayout, QLabel, QLineEdit


class StateIndicator(QFrame):
    """Visual indicator for active and inactive states"""
    def __init__(self, active_color, inactive_color, dia=20):
        super().__init__()
        self.setFixedSize(dia, dia)
        self.dia = dia
        self.setFrameStyle(QFrame.Panel | QFrame.Plain)

        self.active = active_color
        self.inactive = inactive_color
        self.set_active(False)
        self.on = False

    def set_active(self, active=True):
        self.on = active
        if active:
            self.setStyleSheet(f"background-color: {self.active}; border-radius: {self.dia//2}px;")
        else:
            self.setStyleSheet(f"background-color: {self.inactive}; border-radius: {self.dia//2}px;")
        self.update()

    def is_active(self):
        return self.on


class GridStimMenu(QGridLayout):
    def __init__(self):
        super().__init__()
        self.stimname = "GridFlash"
        self.setSpacing(5)
        self.setColumnStretch(0, 2)

        self.minfield = QLineEdit()
        self.minfield.setValidator(QIntValidator(1, 10000))
        self.maxfield = QLineEdit()
        self.maxfield.setValidator(QIntValidator(1, 10000))
        self.stepfield = QLineEdit()
        self.maxfield.setValidator(QIntValidator(1, 50))
        self.minlabel = QLabel("Freq. Minimum (Hz):")
        self.maxlabel = QLabel("Freq. Maximum (Hz):")
        self.steplabel = QLabel("Step count:")
        self.minlabel.setObjectName("MenuLabel")
        self.maxlabel.setObjectName("MenuLabel")
        self.steplabel.setObjectName("MenuLabel")

        self.addWidget(self.minlabel, 6, 0, Qt.AlignRight)
        self.addWidget(self.maxlabel, 7, 0, Qt.AlignRight)
        self.addWidget(self.steplabel, 8, 0, Qt.AlignRight)
        self.addWidget(self.minfield, 6, 1)
        self.addWidget(self.maxfield, 7, 1)
        self.addWidget(self.stepfield, 8, 1)
    
    def clear(self):
        self.minfield.setParent(None)
        self.maxfield.setParent(None)
        self.stepfield.setParent(None)
        self.minlabel.clear()
        self.maxlabel.clear()
        self.steplabel.clear()
        self.setParent(None)

    def validate(self, window=None):
        if not self.minfield.text().strip():
            return False, "Minimum freq. missing."
        if not self.maxfield.text().strip():
            return False, "Maximum freq. missing."
        if not self.stepfield.text().strip():
            return False, "Step count missing."
        if not int(self.minfield.text()) <= int(self.minfield.text()):
            return False, "Minimum freq. cannot be greater than maximum freq."
        return True, ""

    def get_args(self):
        """Return usable args for running the stim script"""
        rows = cols = math.ceil(math.sqrt(int(self.stepfield.text())))
        min, max, steps = int(self.minfield.text()), int(self.maxfield.text()), int(self.stepfield.text())
        return linspace(min, max, steps), rows, cols


class RandomPromptMenu(QGridLayout):
    def __init__(self):
        super().__init__()
        self.stimname = "RandomPrompt"
        self.iwindow = None
        self.setSpacing(5)
        self.setColumnStretch(0, 2)

        self.pfield = QLineEdit()
        self.ppbfield = QLineEdit()
        self.ppbfield.setValidator(QIntValidator(1, 1000))
        self.cfield = QLineEdit()
        self.cfield.setValidator(QDoubleValidator(0.00, 10000, 2))
        self.plabel = QLabel("Prompt text:")
        self.ppblabel = QLabel("Prompts per block:")
        self.clabel = QLabel("Prompt cooldown:")
        self.plabel.setObjectName("MenuLabel")
        self.ppblabel.setObjectName("MenuLabel")
        self.clabel.setObjectName("MenuLabel")

        self.addWidget(self.plabel, 6, 0, Qt.AlignRight)
        self.addWidget(self.ppblabel, 7, 0, Qt.AlignRight)
        self.addWidget(self.clabel, 8, 0, Qt.AlignRight)
        self.addWidget(self.pfield, 6, 1)
        self.addWidget(self.ppbfield, 7, 1)
        self.addWidget(self.cfield, 8, 1)

    def clear(self):
        self.pfield.setParent(None)
        self.ppbfield.setParent(None)
        self.cfield.setParent(None)
        self.plabel.clear()
        self.ppbfield.clear()
        self.plabel.clear()
        self.setParent(None)

    def validate(self, iwindow):
        self.iwindow = iwindow
        prompt = self.pfield.text().strip()
        ppb = int(self.ppbfield.text())
        cooldown = float(self.cfield.text())
        if not prompt:
            return False, "No prompt text given."
        if ppb * cooldown > int(iwindow.fblength.text()):
            return False, "The specified number of prompts cannot fit in one block."
        return True, ""
    
    def get_args(self):
        return (self.pfield.text().strip(), int(self.ppbfield.text()), float(self.cfield.text()), 
                self.iwindow.fstimcycle.text().strip())


class QTextEditLogger(QPlainTextEdit):
    """Monitors logfile for updates and prints to GUI"""
    def __init__(self, filepath, parent_layout=None):
        super().__init__()
        self.logfile = open(filepath, buffering=1)
        self.readpos = 0

        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(filepath)
        self.watcher.fileChanged.connect(self.update_log_window)

        self.setReadOnly(True)
        self.setBackgroundVisible(True)
        if parent_layout:
            self.mount(parent_layout)

    def mount(self, layout):
        layout.addWidget(self)

    def update_log_window(self):
        self.logfile.seek(self.readpos)
        line = self.logfile.read()
        self.appendPlainText(line)
        self.readpos = self.logfile.tell()

    def __exit__(self, type, val, traceback):
        self.logfile.close()
        print(traceback)


class Style:
    style = """
    QFrame {
        color: white;
        background-color: #1d2324;
        border-radius: 10px;
    }
    #FullFrame { background-color: #43484d;
                 border-radius: 0px;
    }
    #ModeFrame { background-color: #1d2324; 
                 border-radius: 0px;}
    QLabel {
        color: #c5cfde;
        font: Candara;
        font-size: 18px;
    }
    #FieldLabels { font-weight: bold; }
    #ErrorLabel { color: #c20808 }
    #MenuLabel { font-size: 14px; }
    #Divider { background-color: #6c6f70; }
    QPushButton {
        background-color: #007bff;
        color:  white;
        border: none;
        padding: 8px 12px;
        border-radius: 5px;
        font-size: 18px;
    }
    QPushButton:hover {
        background-color: #0056b3;
    }
    QPushButton:pressed {
        background-color: #003d80;
    }
    QPushButton:disabled {
        background-color: #1d2324;
        color: white;
    }
    QLineEdit {
        padding: 2px;
        margin: 2px;
        border: 1px solid #ccc;
        border-radius: 5px;
        font-size: 18px;
    }
    QTextEdit {
        background-color: white;
        border: 1 px solid #ccc;
        border-radius: 5px;
        padding: 2px;
        font-size: 16px;
        color: black;
        margin: 2px;
    }
    QPlainTextEdit{
        font-family: MonoSpace;
        font-size: 13px;
    }
    QComboBox {
        padding: 2px;
        color: white;
        background-color: #43484d;
        font-size: 16px;
    }
    QComboBox QAbstractItemView{
        color: white;
        background-color: #1d2324;
        border-radius: 0px;
    }"""