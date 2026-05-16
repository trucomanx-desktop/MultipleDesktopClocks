#!/usr/bin/python3

import sys
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QFont, QPainterPath, QRegion, QIcon, QFontMetrics
import pytz
from datetime import datetime

class StickyClock(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool    # <- adicionada essa flag
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.WIDTH = 300
        self.HEIGHT = 100
        self.XPOS = 150
        self.YPOS = 150
        self.RADIUS = 20
        self.FONTSIZE = 28


        self.resize(self.WIDTH, self.HEIGHT)
        self.move(self.XPOS, self.YPOS)  # <<< define posição inicial da janela

        # Label para mostrar a hora
        self.label = QLabel(self)
        self.label.setStyleSheet("color: white;")
        font = QFont('DejaVu Sans Mono', self.FONTSIZE, QFont.Bold)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.label.setGeometry(0, 0, self.WIDTH, self.HEIGHT)

        # Atualizar hora a cada segundo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()

        # Variáveis para arrastar a janela
        self.old_pos = None

        # Aplicar bordas arredondadas
        self.set_rounded_corners(self.RADIUS)

    def set_rounded_corners(self, radius):
        path = QPainterPath()
        rect = QRectF(self.rect())
        path.addRoundedRect(rect, radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def update_time(self, time_zone="America/Lima"):
        tz = pytz.timezone(time_zone)
        now = datetime.now(tz)
        time_str = now.strftime("%H:%M:%S")+" "+time_zone
        self.label.setText(time_str)
        
        # Calcular largura necessária
        metrics = QFontMetrics(self.label.font())
        text_width = metrics.horizontalAdvance(time_str) + 20  # margem
        self.resize(text_width, self.HEIGHT)
        self.label.setGeometry(0, 0, text_width, self.HEIGHT)

        # Reaplicar bordas arredondadas para novo tamanho
        self.set_rounded_corners(self.RADIUS)

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

class ClockIndicator(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)

        # Janela do relógio, inicialmente escondida
        self.clock_window = StickyClock()

        # Menu do tray
        menu = QMenu(parent)
        toggle_action = menu.addAction("Mostrar/Ocultar Relógio")
        toggle_action.triggered.connect(self.toggle_clock)
        exit_action = menu.addAction("Sair")
        exit_action.triggered.connect(self.exit_app)
        self.setContextMenu(menu)

        # Ícone visível
        self.show()

        # Clique no ícone também alterna a janela
        self.activated.connect(self.on_click)

    def toggle_clock(self):
        if self.clock_window.isVisible():
            self.clock_window.hide()
        else:
            self.clock_window.show()

    def on_click(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # clique simples
            self.toggle_clock()

    def exit_app(self):
        self.clock_window.close()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    icon = QIcon.fromTheme("preferences-system-time")  # ícone do relógio padrão do sistema

    tray = ClockIndicator(icon)
    sys.exit(app.exec_())

