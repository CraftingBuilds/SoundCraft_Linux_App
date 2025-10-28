\
from PyQt6 import QtWidgets
from .daw import SoundCraftDAW
from PyQt6 import QtCore
import re
from soundcraft.core.ai_agent import load_protocols, SoundCraftAgent

class IntentListener(QtCore.QObject):
    trigger_detected = QtCore.pyqtSignal(str)

    def __init__(self, ui_bridge, protocol_dir):
        super().__init__()
        self.ui_bridge = ui_bridge
        self.protocol_dir = protocol_dir
        self.patterns = [
            re.compile(r"\bcreate (a )?soundcraft\b", re.I),
            re.compile(r"\bstart (a )?soundscape\b", re.I),
            re.compile(r"\bgenerate (a )?tone\b", re.I),
            re.compile(r"\bbegin ritual\b", re.I),
        ]
        self.protocols = load_protocols(protocol_dir)

    def check_intent(self, text: str):
        for pat in self.patterns:
            if pat.search(text):
                self.trigger_detected.emit("soundcraft.creation.protocol")
                return True
        return False

    def run_protocol(self, protocol_id):
        if protocol_id not in self.protocols:
            self.ui_bridge.note("⚠️ No protocol found.")
            return
        p = self.protocols[protocol_id]
        agent = SoundCraftAgent(protocol=p, ui_bridge=self.ui_bridge)
        agent.start()

def main():
    app = QtWidgets.QApplication([])
    w = SoundCraftDAW()
    w.show()
    app.exec()

if __name__ == "__main__":
    main()

# soundcraft/ui/qt/main.py (append near the bottom)
from PyQt6 import QtWidgets, QtCore
from soundcraft.core.ai_agent import load_protocols, SoundCraftAgent
import os

class AgentTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        self.protocol_dir = os.path.join(os.path.dirname(__file__), "../../core/Agent Protocols")
        self.protocols = load_protocols(self.protocol_dir)

        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(self.protocols.keys())
        layout.addWidget(QtWidgets.QLabel("Select Protocol"))
        layout.addWidget(self.combo)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        btn_layout = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start Agent")
        self.reload_btn = QtWidgets.QPushButton("Reload")
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reload_btn)
        layout.addLayout(btn_layout)

        self.start_btn.clicked.connect(self.start_agent)
        self.reload_btn.clicked.connect(self.reload_protocols)

    # --- UI Bridge ---
    def ask(self, var):
        if var.type == "choice" and var.options:
            items = [f"{o.label} — {o.rationale}" for o in var.options]
            item, ok = QtWidgets.QInputDialog.getItem(self, var.name, var.prompt, items, 0, False)
            if not ok: return None
            return var.options[items.index(item)].value
        else:
            val, ok = QtWidgets.QInputDialog.getText(self, var.name, var.prompt)
            return val if ok else None

    def note(self, msg):
        self.log.append(f"<b style='color:#1F3B76;'>Amp:</b> {msg}")

    def confirm(self, msg):
        return QtWidgets.QMessageBox.question(self, "Confirm", msg) == QtWidgets.QMessageBox.StandardButton.Yes

    def finalize(self, values):
        self.note("✅ Protocol complete.")
        for k,v in values.items():
            self.note(f"{k}: {v}")

    # --- actions ---
    def start_agent(self):
        key = self.combo.currentText()
        if not key: return
        proto = self.protocols[key]
        agent = SoundCraftAgent(proto, ui_bridge=self)
        agent.start()

    def reload_protocols(self):
        self.protocols = load_protocols(self.protocol_dir)
        self.combo.clear()
        self.combo.addItems(self.protocols.keys())
        self.note("Protocols reloaded.")
