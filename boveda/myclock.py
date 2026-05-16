#!/usr/bin/python3

import sys
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtGui import QFont, QPainterPath, QRegion
import pytz
from datetime import datetime

class StickyClock(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.resize(200, 80)

        # Label para mostrar a hora
        self.label = QLabel(self)
        self.label.setStyleSheet("color: white;")
        font = QFont('DejaVu Sans Mono', 24, QFont.Bold)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, 0, 200, 80)

        # Atualizar hora a cada segundo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        # Variáveis para arrastar a janela
        self.old_pos = None

        # Aplicar bordas arredondadas
        self.set_rounded_corners(20)

    def set_rounded_corners(self, radius):
        path = QPainterPath()
        rect = QRectF(self.rect())  # CORREÇÃO AQUI
        path.addRoundedRect(rect, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def update_time(self, time_zone="America/Lima"):
        tz = pytz.timezone(time_zone)
        now = datetime.now(tz)
        time_str = now.strftime("%H:%M:%S")+" "+time_zone
        self.label.setText(time_str)

    # Eventos para mover a janela clicando e arrastando
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StickyClock()
    window.show()
    sys.exit(app.exec_())

