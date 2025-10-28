from __future__ import annotations

from pathlib import Path
from typing import Dict

from PyQt6 import QtWidgets

from .daw import SoundCraftDAW
from soundcraft.core.ai_agent import Protocol, SoundCraftAgent, Variable, load_protocols


class AgentTab(QtWidgets.QWidget):
    """Standalone widget for manually running SoundCraft protocols."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        self.protocol_dir = (Path(__file__).resolve().parent / "../../core/Agent Protocols").resolve()
        self.protocols: Dict[str, Protocol] = load_protocols(self.protocol_dir)

        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(sorted(self.protocols.keys()))
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

    # --- UI Bridge -------------------------------------------------
    def ask(self, var: Variable):
        if var.type == "choice" and var.options:
            items = [
                f"{opt.label} — {opt.rationale}" if opt.rationale else opt.label
                for opt in var.options
            ]
            item, ok = QtWidgets.QInputDialog.getItem(
                self, var.name, var.prompt or var.name, items, 0, False
            )
            if not ok:
                return var.default
            return var.options[items.index(item)].value
        else:
            val, ok = QtWidgets.QInputDialog.getText(
                self,
                var.name,
                var.prompt or var.name,
                QtWidgets.QLineEdit.EchoMode.Normal,
                "" if var.default is None else str(var.default),
            )
            return val if ok and val != "" else var.default

    def note(self, msg: str):
        self.log.append(f"<b style='color:#1F3B76;'>Amp:</b> {msg}")

    def confirm(self, msg: str) -> bool:
        return (
            QtWidgets.QMessageBox.question(self, "Confirm", msg)
            == QtWidgets.QMessageBox.StandardButton.Yes
        )

    def finalize(self, values: Dict[str, object]):
        self.note("✅ Protocol complete.")
        for key, value in values.items():
            self.note(f"{key}: {value}")

    # --- actions ---------------------------------------------------
    def start_agent(self):
        key = self.combo.currentText()
        if not key:
            return
        protocol = self.protocols.get(key)
        if not protocol:
            self.note("⚠️ No protocol found.")
            return
        agent = SoundCraftAgent(protocol, ui_bridge=self)
        agent.start()

    def reload_protocols(self):
        self.protocols = load_protocols(self.protocol_dir)
        self.combo.clear()
        self.combo.addItems(sorted(self.protocols.keys()))
        self.note("Protocols reloaded.")


def main() -> None:
    app = QtWidgets.QApplication([])
    window = SoundCraftDAW()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
