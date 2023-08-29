"""Built-in Stimuli Classes"""
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QGridLayout, QVBoxLayout, QOpenGLWidget)
from PyQt5.QtCore import QThread, Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QPainter, QBrush, QFont, QSurfaceFormat


class FlashingThread(QThread):
    flash_signal = pyqtSignal()

    def __init__(self, frequency, widget):
        super().__init__()
        self.widget = widget
        self.frequency = frequency
        self.is_running = True

    def run(self):
        interval = 1 / (2 * self.frequency)  # Calculate interval between flashes
        while self.is_running:
            self.flash_signal.emit()
            self.msleep(int(1000 * interval))

    def stop(self):
        self.widget.end()
        self.is_running = False


class FlashingBox(QOpenGLWidget):
    def __init__(self, frequency):
        super().__init__()
        self.frequency = frequency
        self.flash_state = False
        self.flashing_thread = FlashingThread(frequency)
        self.flashing_thread.flash_signal.connect(self.toggle_flash)
        self.flashing_thread.start()

    def toggle_flash(self):
        self.flash_state = not self.flash_state
        self.update()

    def paintGL(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(Qt.black) if self.flash_state else QColor(Qt.white)
        painter.setBrush(QBrush(color))
        # painter.drawEllipse(self.rect())
        painter.drawRect(self.rect())
        painter.setPen(QColor(Qt.black) if not self.flash_state else QColor(Qt.white))
        painter.setFont(QFont('Arial', 16))
        painter.drawText(self.rect(), Qt.AlignCenter, f'{self.frequency:.1f} Hz')

    def closeEvent(self, event):
        self.flashing_thread.stop()
        self.flashing_thread.wait()


class GridFlash(QWidget):
    """
    Flashes frequencies on a grid
    
    Parameters
    ----------
    frequencies: int
        frequencies to include
    rows: int
        number of rows in grid
    cols: int
        number of columns in grid
    """
    def __init__(self, frequencies: list, rows: int, cols: int):
        super().__init__()
        layout = QGridLayout()
        self.setLayout(layout)
        self.setMinimumSize(650, 650)

        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(p)

        n = 0
        for i in range(rows):
            for j in range(cols):
                if n < len(frequencies):
                    box = FlashingBox(frequencies[n])
                    layout.addWidget(box, i, j)
                    n += 1

        fmt = QSurfaceFormat()
        fmt.setSamples(4)
        fmt.setSwapInterval(1)
        fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
        fmt.setRenderableType(QSurfaceFormat.OpenGL)
        QSurfaceFormat.setDefaultFormat(fmt)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def exit(self):
        self.close()


class ToggleThread(QThread):
    flash_signal = pyqtSignal()

    def __init__(self, times, dur):
        super().__init__()
        self.times = times
        self.dur = dur
        self.is_running = True

    def run(self):
        while self.is_running and self.times:
            wdur = self.times[0]
            self.msleep(int(1000 * wdur))
            self.flash_signal.emit()
            self.msleep(int(1000 * self.dur))
            self.flash_signal.emit()
            if len(self.times) > 1:
                self.times[1] -= self.times[0] + self.dur
                self.times = self.times[1:]

    def stop(self):
        self.is_running = False


class PromptBox(QOpenGLWidget):
    def __init__(self, text, times, dur):
        super().__init__()
        self.text = text
        self.flash_state = False
        self.toggle_thread = ToggleThread(times, dur)
        self.toggle_thread.flash_signal.connect(self.toggle_flash)
        self.toggle_thread.start()

    def toggle_flash(self):
        self.flash_state = not self.flash_state
        self.update()

    def paintGL(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(Qt.black) if not self.flash_state else QColor(Qt.white)
        painter.setBrush(QBrush(color))
        painter.drawRect(self.rect())
        painter.setPen(QColor(Qt.white) if not self.flash_state else QColor(Qt.black))
        # painter.setFont(QFont('Arial', 16))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)

    def closeEvent(self, event):
        self.flashing_thread.stop()
        self.flashing_thread.wait()


class RandomPrompt(QWidget):
    """
    Randomly shows prompt with given text during active stimulus blocks
    
    Parameters
    ----------
    prompt: str
        Text to put in prompt
    ppb: int
        Number of prompts per block of active stimulus
    cooldown: int
        Minimum time between prompts in seconds   
    stimcycle: str
        Stimulus cycle for the session
    dur: float
        How long to leave the prompt on the screen
    """
    def __init__(self, prompt: str, ppb: int, cooldown: int, stimcycle: str, dur=1.5):
        super().__init__()
        self.prompt = prompt
        self.ppb = ppb
        self.cooldown = cooldown 
        self.stimcycle = stimcycle 
        self.dur = dur 

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setMinimumSize(650, 650)

        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(p)

        fmt = QSurfaceFormat()
        fmt.setSamples(4)
        fmt.setSwapInterval(1)
        fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
        fmt.setRenderableType(QSurfaceFormat.OpenGL)
        QSurfaceFormat.setDefaultFormat(fmt)

    def show(self):
        self.start()
        super().show()

    def start(self):
        print("START:", datetime.now())
        box = PromptBox(self.prompt, [2, 8, 14], self.dur)
        self.layout.addWidget(box)
    
    def exit(self):
        self.close()
