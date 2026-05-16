import sys, os, json, signal
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QSystemTrayIcon,
                             QMenu, QInputDialog)
from PyQt5.QtGui import QFont, QPainterPath, QRegion, QIcon, QFontMetrics
import pytz
from datetime import datetime

import multiple_desktop_clocks.about as about
from multiple_desktop_clocks.modules.configure import load_config, save_config
from multiple_desktop_clocks.modules.resources import resource_path
from multiple_desktop_clocks.modules.wabout  import show_about_window
from multiple_desktop_clocks.desktop import create_desktop_file
from multiple_desktop_clocks.desktop import create_desktop_directory
from multiple_desktop_clocks.desktop import create_desktop_menu

CONFIG_PATH = os.path.join( os.path.expanduser("~"),
                            ".config",
                            about.__package__,
                            "config.json")


# ======== Classe da janela do relógio ========

class StickyClock(QWidget):
    def __init__(self, timezone):
        super().__init__()
        self.timezone = timezone
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.HEIGHT = 80
        self.FONTSIZE = 24
        self.COLOR = "white"

        self.RADIUS = 20
        self.resize(250, self.HEIGHT)
        self.move(200, 200)

        self.label = QLabel(self)
        self.label.setStyleSheet(f"color: {self.COLOR};")
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
        if hasattr(self, "tray_ref"):   # se o relógio conhece o tray
            self.tray_ref.save_all_positions()

# ======== Tray com múltiplos relógios ========

class ClockIndicator(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)

        self.clocks = {}  # timezone -> StickyClock

        # Carregar fusos do JSON
        self.config = load_config(CONFIG_PATH)
        for tz, pos in self.config.items():
            x = pos.get("x", 200)
            y = pos.get("y", 200)
            self.add_clock(tz, x, y)


        menu = QMenu(parent)
        
        # Add
        add_action = menu.addAction("➕ Add time zone")
        add_action.triggered.connect(self.add_timezone)
        
        # Remove
        remove_action = menu.addAction("➖ Remove time zone")
        remove_action.triggered.connect(self.remove_timezone)
        
        #
        menu.addSeparator()
        
        # About
        about_action = menu.addAction("ℹ️ About")
        about_action.triggered.connect(self.show_about)
        
        # Exit
        exit_action = menu.addAction("❌ Exit")
        exit_action.triggered.connect(self.exit_app)
        
        self.setContextMenu(menu)

        self.show()

    def add_clock(self, timezone, x=200, y=200):
        if timezone in self.clocks:
            return
        clock = StickyClock(timezone)
        clock.move(x, y)
        clock.tray_ref = self   # <<< adiciona referência ao tray
        clock.show()
        self.clocks[timezone] = clock
        self.save_all_positions()

    def save_all_positions(self):
        data = {}
        for tz, clock in self.clocks.items():
            data[tz] = {"x": clock.x(), "y": clock.y()}
        save_config(CONFIG_PATH, data)


    def add_timezone(self):
        tz_list = pytz.all_timezones
        tz, ok = QInputDialog.getItem(None, "Add time zone",
                                      "Choose a timezone:", tz_list, 0, False)
        if ok and tz:
            self.add_clock(tz)

    def remove_timezone(self):
        if not self.clocks:
            return
        tz_list = list(self.clocks.keys())
        tz, ok = QInputDialog.getItem(None, "Remove time zone",
                                      "Choose a timezone to remove:", tz_list, 0, False)
        if ok and tz:
            self.clocks[tz].close()
            del self.clocks[tz]
            save_config(CONFIG_PATH,list(self.clocks.keys()))

    def show_about(self):
        data = {
            "version": about.__version__,
            "package": about.__package__,
            "program_name": about.__program_name__,
            "author": about.__author__,
            "email": about.__email__,
            "description": about.__description__,
            "url_source": about.__url_source__,
            "url_doc": about.__url_doc__,
            "url_funding": about.__url_funding__,
            "url_bugs": about.__url_bugs__
        }
        
        logo_path = resource_path('icons', 'logo.png')
        
        show_about_window(data, logo_path)


    
    def exit_app(self):
        for clock in self.clocks.values():
            clock.close()
        QApplication.quit()

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    
    create_desktop_directory()    
    create_desktop_menu()
    create_desktop_file('~/.local/share/applications')
    
    for n in range(len(sys.argv)):
        if sys.argv[n] == "--autostart":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file('~/.config/autostart', overwrite=True)
            return
        if sys.argv[n] == "--applications":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file('~/.local/share/applications', overwrite=True)
            return
    
    
    app = QApplication(sys.argv)
    app.setApplicationName(about.__package__) # xprop WM_CLASS # *.desktop -> StartupWMClass  
    app.setQuitOnLastWindowClosed(False)

    # Get base directory for icons
    icon_path = resource_path('icons', 'logo.png')
    
    icon = QIcon(icon_path)
    tray = ClockIndicator(icon)

    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()

