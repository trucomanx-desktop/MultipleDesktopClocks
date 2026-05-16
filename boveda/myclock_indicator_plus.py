#!/usr/bin/python3

import sys, os, json
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QSystemTrayIcon,
                             QMenu, QInputDialog)
from PyQt5.QtGui import QFont, QPainterPath, QRegion, QIcon, QFontMetrics
import pytz
from datetime import datetime

CONFIG_FILE = os.path.expanduser("~/.sticky_clock.json")

# ======== Funções para salvar/carregar ========

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            return data.get("timezones", [])
        except:
            return []
    return []

def save_config(timezones):
    data = {"timezones": timezones}
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ======== Classe da janela do relógio ========

class StickyClock(QWidget):
    def __init__(self, timezone):
        super().__init__()
        self.timezone = timezone

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.HEIGHT = 80
        self.FONTSIZE = 28

        self.RADIUS = 20
        self.resize(250, self.HEIGHT)
        self.move(200, 200)

        self.label = QLabel(self)
        self.label.setStyleSheet("color: white;")
        font = QFont('DejaVu Sans Mono', self.FONTSIZE, QFont.Bold)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.label.setGeometry(0, 0, 250, self.HEIGHT)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        self.old_pos = None
        self.set_rounded_corners(self.RADIUS)

    def set_rounded_corners(self, radius):
        path = QPainterPath()
        rect = QRectF(self.rect())
        path.addRoundedRect(rect, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def update_time(self):
        tz = pytz.timezone(self.timezone)
        now = datetime.now(tz)
        time_str = now.strftime("%H:%M:%S") + " " + self.timezone
        self.label.setText(time_str)

        metrics = QFontMetrics(self.label.font())
        text_width = metrics.horizontalAdvance(time_str) + 20
        self.resize(text_width, self.HEIGHT)
        self.label.setGeometry(0, 0, text_width, self.HEIGHT)
        self.set_rounded_corners(self.RADIUS)

    # Mover a janela com o mouse
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

# ======== Tray com múltiplos relógios ========

class ClockIndicator(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)

        self.clocks = {}  # timezone -> StickyClock

        # Carregar fusos do JSON
        for tz in load_config():
            self.add_clock(tz)

        menu = QMenu(parent)
        add_action = menu.addAction("Adicionar Fuso Horário")
        add_action.triggered.connect(self.add_timezone)
        remove_action = menu.addAction("Remover Fuso Horário")
        remove_action.triggered.connect(self.remove_timezone)
        menu.addSeparator()
        exit_action = menu.addAction("Sair")
        exit_action.triggered.connect(self.exit_app)
        self.setContextMenu(menu)

        self.show()

    def add_clock(self, timezone):
        if timezone in self.clocks:
            return
        clock = StickyClock(timezone)
        clock.show()
        self.clocks[timezone] = clock
        save_config(list(self.clocks.keys()))

    def add_timezone(self):
        tz_list = pytz.all_timezones
        tz, ok = QInputDialog.getItem(None, "Adicionar Fuso Horário",
                                      "Escolha um timezone:", tz_list, 0, False)
        if ok and tz:
            self.add_clock(tz)

    def remove_timezone(self):
        if not self.clocks:
            return
        tz_list = list(self.clocks.keys())
        tz, ok = QInputDialog.getItem(None, "Remover Fuso Horário",
                                      "Escolha um timezone para remover:", tz_list, 0, False)
        if ok and tz:
            self.clocks[tz].close()
            del self.clocks[tz]
            save_config(list(self.clocks.keys()))

    def exit_app(self):
        for clock in self.clocks.values():
            clock.close()
        QApplication.quit()

# ======== Main ========

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    icon = QIcon.fromTheme("preferences-system-time")
    tray = ClockIndicator(icon)

    sys.exit(app.exec_())

