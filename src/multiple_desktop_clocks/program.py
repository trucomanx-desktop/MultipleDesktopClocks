import sys, os, json, signal
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtWidgets import (QApplication, QLabel, QWidget, QSystemTrayIcon,
                             QMenu, QInputDialog, QColorDialog)
from PyQt5.QtGui import QFont, QPainterPath, QRegion, QIcon, QFontMetrics, QColor
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
GUI_CONFIG_PATH = os.path.join(os.path.dirname(CONFIG_PATH), "config_gui.json")
DEFAULT_GUI_TEXT = {
    "add_timezone": "➕ Add time zone",
    "remove_timezone": "➖ Remove time zone",
    "choose_timezone": "Choose a timezone:",
    "font_size": "Set font size...",
    "font_family": "Set font family...",
    "font_color": "Set font color...",
    "font_size_title": "Font size",
    "font_size_prompt": "Enter font size:",
    "font_family_title": "Font family",
    "font_family_prompt": "Enter font family:",
    "font_color_title": "Font color",
    "about": "ℹ️ About",
    "exit": "❌ Exit",
}


def load_gui_text():
    """Load editable GUI labels, creating English defaults on first run."""
    os.makedirs(os.path.dirname(GUI_CONFIG_PATH), exist_ok=True)
    try:
        with open(GUI_CONFIG_PATH, "r", encoding="utf-8") as gui_file:
            saved_text = json.load(gui_file)
        if not isinstance(saved_text, dict):
            saved_text = {}
    except (OSError, json.JSONDecodeError):
        saved_text = {}

    gui_text = {**DEFAULT_GUI_TEXT, **saved_text}
    if gui_text != saved_text:
        with open(GUI_CONFIG_PATH, "w", encoding="utf-8") as gui_file:
            json.dump(gui_text, gui_file, indent=4, ensure_ascii=False)
    return gui_text


# ======== Classe da janela do relógio ========

class StickyClock(QWidget):
    def __init__(self, timezone, font_settings):
        super().__init__()
        self.timezone = timezone
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.HEIGHT = 80
        self.font_settings = font_settings
        self.FONTSIZE = font_settings["font_size"]
        self.COLOR = font_settings["font_color"]

        self.RADIUS = 20
        self.resize(250, self.HEIGHT)
        self.move(200, 200)

        self.label = QLabel(self)
        self.label.setStyleSheet(f"color: {self.COLOR};")
        font = QFont(font_settings["font_family"], self.FONTSIZE, QFont.Bold)
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

        # load_config returns the dictionary stored under "clocks".
        # Keep shared font settings in that dictionary under a reserved key.
        self.config = load_config(CONFIG_PATH)
        self.font_settings = {
            "font_family": "DejaVu Sans Mono",
            "font_size": 24,
            "font_color": "#FFFFFF",
        }
        saved_settings = self.config.pop("__settings__", {})
        if isinstance(saved_settings, dict):
            self.font_settings.update(saved_settings)

        self.gui_text = load_gui_text()

        for tz, pos in self.config.items():
            x = pos.get("x", 200)
            y = pos.get("y", 200)
            self.add_clock(tz, x, y)


        menu = QMenu(parent)
        
        # Add
        add_action = menu.addAction(self.gui_text["add_timezone"])
        add_action.triggered.connect(self.add_timezone)
        
        # Remove
        remove_action = menu.addAction(self.gui_text["remove_timezone"])
        remove_action.triggered.connect(self.remove_timezone)
        
        #
        menu.addSeparator()
        
        # Font controls
        font_size_action = menu.addAction(self.gui_text["font_size"])
        font_size_action.triggered.connect(self.set_font_size)
        font_family_action = menu.addAction(self.gui_text["font_family"])
        font_family_action.triggered.connect(self.set_font_family)
        font_color_action = menu.addAction(self.gui_text["font_color"])
        font_color_action.triggered.connect(self.set_font_color)

        menu.addSeparator()

        # About
        about_action = menu.addAction(self.gui_text["about"])
        about_action.triggered.connect(self.show_about)
        
        # Exit
        exit_action = menu.addAction(self.gui_text["exit"])
        exit_action.triggered.connect(self.exit_app)
        
        self.setContextMenu(menu)

        self.show()

    def add_clock(self, timezone, x=200, y=200):
        if timezone in self.clocks:
            return
        clock = StickyClock(timezone, self.font_settings)
        clock.move(x, y)
        clock.tray_ref = self   # <<< adiciona referência ao tray
        clock.show()
        self.clocks[timezone] = clock
        self.save_all_positions()

    def save_all_positions(self):
        data = {"__settings__": self.font_settings.copy()}
        for tz, clock in self.clocks.items():
            data[tz] = {"x": clock.x(), "y": clock.y()}
        save_config(CONFIG_PATH, data)


    def add_timezone(self):
        tz_list = pytz.all_timezones
        tz, ok = QInputDialog.getItem(None, self.gui_text["add_timezone"],
                                      self.gui_text["choose_timezone"], tz_list, 0, False)
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
            self.save_all_positions()

    def apply_font_settings(self):
        for clock in self.clocks.values():
            clock.COLOR = self.font_settings["font_color"]
            clock.FONTSIZE = self.font_settings["font_size"]
            clock.label.setStyleSheet(f"color: {clock.COLOR};")
            clock.label.setFont(QFont(self.font_settings["font_family"],
                                      clock.FONTSIZE, QFont.Bold))
            clock.update_time()
        self.save_all_positions()

    def set_font_size(self):
        size, ok = QInputDialog.getInt(None, self.gui_text["font_size_title"],
                                       self.gui_text["font_size_prompt"],
                                       self.font_settings["font_size"], 6, 96, 1)
        if ok:
            self.font_settings["font_size"] = size
            self.apply_font_settings()

    def set_font_family(self):
        family, ok = QInputDialog.getText(None, self.gui_text["font_family_title"],
                                          self.gui_text["font_family_prompt"],
                                          text=self.font_settings["font_family"])
        if ok and family.strip():
            self.font_settings["font_family"] = family.strip()
            self.apply_font_settings()

    def set_font_color(self):
        color = QColorDialog.getColor(QColor(self.font_settings["font_color"]),
                                      None, self.gui_text["font_color_title"])
        if color.isValid():
            self.font_settings["font_color"] = color.name()
            self.apply_font_settings()

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

