from __future__ import annotations
import os, re
from PyQt6 import QtWidgets, QtCore, QtGui
from .theme import APP_QSS, STARSEED_GOLD
from ...core import synthesis, recorder, tts_engine, smith_equivalence as se, midi_export
from ...core.ai_agent import load_protocols, SoundCraftAgent

# ────────────────────────────────────────────────────────────────
#  Transport Bar
# ────────────────────────────────────────────────────────────────
class TransportBar(QtWidgets.QWidget):
    play_clicked = QtCore.pyqtSignal()
    stop_clicked = QtCore.pyqtSignal()
    rec_clicked = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        h = QtWidgets.QHBoxLayout(self)
        self.play = QtWidgets.QPushButton("▶ Play")
        self.stop = QtWidgets.QPushButton("■ Stop")
        self.rec = QtWidgets.QPushButton("● Rec")
        h.addWidget(self.play)
        h.addWidget(self.stop)
        h.addWidget(self.rec)
        self.play.clicked.connect(self.play_clicked.emit)
        self.stop.clicked.connect(self.stop_clicked.emit)
        self.rec.clicked.connect(self.rec_clicked.emit)

# ────────────────────────────────────────────────────────────────
#  Track List and Timeline
# ────────────────────────────────────────────────────────────────
class TrackList(QtWidgets.QListWidget):
    pass

class Timeline(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(QtGui.QColor(STARSEED_GOLD))
        w = self.width()
        for x in range(0, w, 40):
            p.drawLine(x, 0, x, self.height())
        p.end()

# ────────────────────────────────────────────────────────────────
#  Intent Listener
# ────────────────────────────────────────────────────────────────
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
            self.ui_bridge.status.showMessage("⚠️ Protocol not found.", 5000)
            return
        p = self.protocols[protocol_id]
        agent = SoundCraftAgent(protocol=p, ui_bridge=self.ui_bridge)
        agent.start()

# ────────────────────────────────────────────────────────────────
#  Main DAW Window
# ────────────────────────────────────────────────────────────────
class SoundCraftDAW(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoundCraft — Ritual DAW")
        self.resize(1100, 700)
        self.setStyleSheet(APP_QSS)

        # central layout
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        v = QtWidgets.QVBoxLayout(central)

        # transport
        self.transport = TransportBar()
        v.addWidget(self.transport)

        # splitter: left tracks / right timeline
        split = QtWidgets.QSplitter()
        split.setOrientation(QtCore.Qt.Orientation.Horizontal)
        v.addWidget(split, 1)

        # Left: track list
        left = QtWidgets.QWidget()
        left_v = QtWidgets.QVBoxLayout(left)
        left_v.addWidget(QtWidgets.QLabel("Tracks"))
        self.tracks = TrackList()
        left_v.addWidget(self.tracks, 1)
        add_btn = QtWidgets.QPushButton("+ Add Tone Track")
        add_btn.clicked.connect(self.add_tone_track)
        left_v.addWidget(add_btn)
        split.addWidget(left)

        # Right: timeline + quick actions
        right = QtWidgets.QWidget()
        right_v = QtWidgets.QVBoxLayout(right)
        right_v.addWidget(QtWidgets.QLabel("Timeline"))
        self.timeline = Timeline()
        self.timeline.setMinimumHeight(300)
        right_v.addWidget(self.timeline, 1)

        # Controls group
        ctrl = QtWidgets.QGroupBox("Quick Actions")
        form = QtWidgets.QFormLayout(ctrl)

        self.freq_in = QtWidgets.QDoubleSpinBox()
        self.freq_in.setRange(16.0, 20000.0)
        self.freq_in.setValue(432.0)

        self.dur_in = QtWidgets.QDoubleSpinBox()
        self.dur_in.setRange(1.0, 600.0)
        self.dur_in.setValue(10.0)

        self.beat_in = QtWidgets.QDoubleSpinBox()
        self.beat_in.setRange(0.0, 40.0)
        self.beat_in.setValue(7.0)

        self.file_out = QtWidgets.QLineEdit(
            os.path.expanduser("~/SoundCraft_Output/output.wav")
        )

        gen_btn = QtWidgets.QPushButton("Generate Binaural WAV")
        gen_btn.clicked.connect(self.generate_binaural)
        rec_btn = QtWidgets.QPushButton("Record Voice 5s")
        rec_btn.clicked.connect(self.record_voice)
        tts_btn = QtWidgets.QPushButton("TTS → WAV")
        tts_btn.clicked.connect(self.tts_to_wav)

        form.addRow("Carrier Hz:", self.freq_in)
        form.addRow("Duration (s):", self.dur_in)
        form.addRow("Beat Hz:", self.beat_in)
        form.addRow("Output Path:", self.file_out)
        form.addRow(gen_btn)
        form.addRow(rec_btn)
        form.addRow(tts_btn)

        right_v.addWidget(ctrl)
        split.addWidget(right)

        # status bar
        self.status = self.statusBar()

        # ───────────────────────────────────────────────
        #  Autonomous SoundCraft Agent Invocation
        #   (point to the folder that actually contains the YAML)
        # ───────────────────────────────────────────────
        self.protocol_dir = os.path.join(
           os.path.dirname(__file__),
           "../../core/Agent Protocols"
        )
        self.intent_listener = IntentListener(self, self.protocol_dir)
        self.intent_listener.trigger_detected.connect(self.intent_listener.run_protocol)

        # command input at bottom
        self.command_input = QtWidgets.QLineEdit()
        self.command_input.setPlaceholderText(
            "Type here — e.g. 'I want to create a SoundCraft production'"
        )
        self.command_input.returnPressed.connect(self.on_command_entered)
        v.addWidget(self.command_input)

    # ───────────────────────────────────────────────
    #  Intent Listener + Amp Bridge
    # ───────────────────────────────────────────────
    def on_command_entered(self):
        text = self.command_input.text().strip()
        if not text:
            return
        self.command_input.clear()
        self.status.showMessage(f"Operator: {text}", 4000)
        self.intent_listener.check_intent(text)

    def ask(self, var):
        if getattr(var, "type", "") == "choice" and getattr(var, "options", None):
            opts = [f"{o.label} — {o.rationale}" if getattr(o, "rationale", "") else o.label for o in var.options]
            item, ok = QtWidgets.QInputDialog.getItem(
                self, var.name, var.prompt or var.name, opts, 0, False
            )
            if not ok:
                return None
            idx = opts.index(item)
            return var.options[idx].value
        else:
            val, ok = QtWidgets.QInputDialog.getText(self, var.name, var.prompt or var.name)
            return val if ok else None

    def note(self, msg):
        self.status.showMessage(f"Amp: {msg}", 8000)

    def confirm(self, msg):
        return (
            QtWidgets.QMessageBox.question(self, "Confirm", msg)
            == QtWidgets.QMessageBox.StandardButton.Yes
        )

    def finalize(self, values):
        self.note("✅ Protocol complete.")
        for k, v in values.items():
            self.note(f"{k}: {v}")

    # ───────────────────────────────────────────────
    #  Existing actions
    # ───────────────────────────────────────────────
    def add_tone_track(self):
        self.tracks.addItem(f"Tone Track {self.tracks.count() + 1}")

    def generate_binaural(self):
        hz = self.freq_in.value()
        dur = self.dur_in.value()
        beat = self.beat_in.value()

        suggested = os.path.expanduser("~/SoundCraft_Output/binaural.wav")
        os.makedirs(os.path.dirname(suggested), exist_ok=True)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Binaural WAV As", suggested, "WAV Files (*.wav)"
        )
        if not path:
            self.status.showMessage("Binaural export cancelled", 3000)
            return

        try:
            data = synthesis.binaural_wave(hz, beat, dur)
            synthesis.write_wav(path, data)
            self.status.showMessage(f"Binaural written → {path}", 5000)
            self._after_render_dialog("Binaural Render Complete", path)
        except Exception as e:
            self.status.showMessage(f"Binaural failed: {e}", 8000)

    def record_voice(self):
        suggested = os.path.expanduser("~/SoundCraft_Output/voice.wav")
        os.makedirs(os.path.dirname(suggested), exist_ok=True)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Recording As", suggested, "WAV Files (*.wav)"
        )
        if not path:
            self.status.showMessage("Recording cancelled", 3000)
            return

        try:
            recorder.record_wav(path, 5.0)
            self.status.showMessage(f"Recorded voice → {path}", 5000)
            self._after_render_dialog("Recording Complete", path)
        except Exception as e:
            self.status.showMessage(f"Recording failed: {e}", 8000)

    def tts_to_wav(self):
        text, ok = QtWidgets.QInputDialog.getMultiLineText(
            self,
            "Text-to-Speech",
            "Enter text for SoundCraft to speak:",
            "This is SoundCraft speaking.",
        )
        if not ok or not text.strip():
            self.status.showMessage("TTS cancelled", 3000)
            return

        suggested = os.path.expanduser("~/SoundCraft_Output/tts.wav")
        os.makedirs(os.path.dirname(suggested), exist_ok=True)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save TTS Output As", suggested, "WAV Files (*.wav)"
        )
        if not path:
            self.status.showMessage("Save cancelled", 3000)
            return

        try:
            tts_engine.speak_to_wav(text.strip(), path)
            self.status.showMessage(f"TTS saved → {path}", 5000)
            self._after_render_dialog("TTS Complete", path)
        except Exception as e:
            self.status.showMessage(f"TTS failed: {e}", 8000)

    def _after_render_dialog(self, title: str, path: str):
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(f"Saved to:\n{path}")
        msg.setInformativeText("Open file location or play now?")
        open_btn = msg.addButton("Open Folder", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        play_btn = msg.addButton("Play", QtWidgets.QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Close", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == open_btn:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.dirname(path)))
        elif msg.clickedButton() == play_btn:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
