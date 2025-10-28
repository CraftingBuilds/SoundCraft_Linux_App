\
STARSEED_BLUE = "#1F3B76"
STARSEED_GOLD = "#D8C48A"

APP_QSS = f"""
QWidget {{
    background-color: #0f1221;
    color: white;
    font-family: 'Inter', 'DejaVu Sans', Arial;
}}
QMainWindow::separator {{
    background: {STARSEED_GOLD};
}}
QPushButton {{
    background: {STARSEED_BLUE};
    border: 1px solid {STARSEED_GOLD};
    padding: 6px 10px;
    border-radius: 4px;
}}
QPushButton:hover {{
    border-color: white;
}}
QGroupBox {{
    border: 1px solid {STARSEED_GOLD};
    margin-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {STARSEED_GOLD};
}}
"""
