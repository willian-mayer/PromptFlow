"""PromptFlow — teleprompter de escritorio en Python/PySide6."""
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect, QSettings
from PySide6.QtGui import QIcon, QFont, QFontMetrics, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QSlider, QCheckBox, QFileDialog,
    QMessageBox, QDialog, QFormLayout, QComboBox, QLineEdit, QSpinBox,
    QProgressBar, QFrame, QSizePolicy, QStackedWidget, QListWidget, QListWidgetItem, QInputDialog
)
from ai_service import MODELS, generate

BASE = Path(__file__).resolve().parent
PURPLE = "#8855e8"
STYLE = """
QWidget { background: #10121c; color: #f2f2fb; font-family: Arial; font-size: 13px; }
QFrame#top, QFrame#bottom { background: #181b29; }
QFrame#sidebar { background: #151827; }
QTextEdit, QLineEdit, QComboBox, QSpinBox {
 background: #222637; border: 1px solid #353a51; border-radius: 9px;
 padding: 8px; color: #f6f5ff; selection-background-color: #8855e8;
}
QPushButton { background: #292d40; border: 1px solid #383d53; border-radius: 9px;
 padding: 10px 14px; font-weight: 600; }
QPushButton:hover { background: #383c54; }
QPushButton:disabled { color: #8e90a2; }
QPushButton#primary { background: #7446d2; border-color: #7446d2; }
QPushButton#primary:hover { background: #8759e9; }
QSlider::groove:horizontal { background: #36394d; height: 5px; border-radius: 2px; }
QSlider::handle:horizontal { background: #aa83ff; width: 16px; margin: -6px 0; border-radius: 8px; }
QScrollArea { border: none; background: #090b12; }
QScrollBar:vertical { background: #171a26; width: 12px; }
QScrollBar::handle:vertical { background: #444861; border-radius: 5px; min-height: 25px; }
"""

class ScriptCanvas(QWidget):
    """Dibuja texto con soporte de reflejo horizontal real."""
    def __init__(self):
        super().__init__()
        self.text = ""
        self.point_size = 54
        self.mirrored = False
        self.lines = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def update_layout(self):
        width = max(120, self.width() - 100)
        font = QFont("Arial", self.point_size)
        fm = QFontMetrics(font)
        lines = []
        for paragraph in self.text.split("\n"):
            if not paragraph:
                lines.append("")
                continue
            words = paragraph.split(" ")
            line = ""
            for word in words:
                candidate = (line + " " + word) if line else word
                if line and fm.horizontalAdvance(candidate) > width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        self.lines = lines
        line_height = int(fm.lineSpacing() * 1.22)
        self.setFixedHeight(max(500, 100 + len(lines) * line_height + 300))
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_layout()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#090b12"))
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self.mirrored:
            p.translate(self.width(), 0)
            p.scale(-1, 1)
        font = QFont("Arial", self.point_size)
        p.setFont(font)
        p.setPen(QColor("#f4f6ff"))
        fm = QFontMetrics(font)
        line_height = int(fm.lineSpacing() * 1.22)
        y = 100 + fm.ascent()
        for line in self.lines:
            p.drawText(QRect(50, y - fm.ascent(), max(1, self.width()-100), line_height),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, line)
            y += line_height
        p.end()

class AiWorker(QThread):
    success = Signal(str)
    failure = Signal(str)
    def __init__(self, args):
        super().__init__()
        self.args = args
    def run(self):
        try:
            self.success.emit(generate(*self.args))
        except Exception as exc:
            self.failure.emit(str(exc))

class AiDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Generate Script with AI")
        self.resize(610, 720)
        self.worker = None
        outer = QVBoxLayout(self)
        form = QFormLayout()
        self.provider = QComboBox()
        self.provider.addItems(MODELS)
        self.model = QLineEdit(MODELS["OpenAI"])
        self.provider.currentTextChanged.connect(lambda name: self.model.setText(MODELS[name]))
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("API key (this session only)")
        self.idea = QTextEdit()
        self.idea.setPlaceholderText("Describe your video or presentation...")
        self.idea.setFixedHeight(95)
        self.tone = QComboBox()
        self.tone.addItems(["Natural", "Professional", "Educational", "Enthusiastic"])
        self.minutes = QSpinBox()
        self.minutes.setRange(1, 30)
        self.minutes.setValue(3)
        for label, widget in [
            ("Provider", self.provider), ("Model (editable)", self.model),
            ("API key", self.key), ("Your idea", self.idea),
            ("Tone", self.tone), ("Duration (minutes)", self.minutes)
        ]:
            form.addRow(label, widget)
        outer.addLayout(form)
        self.status = QLabel("Your API key is not saved. It is sent to the selected provider.")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.generate_button = QPushButton("✦ Generate Script")
        self.generate_button.setObjectName("primary")
        self.generate_button.clicked.connect(self.generate_script)
        outer.addWidget(self.generate_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        outer.addWidget(self.progress)
        outer.addWidget(QLabel("Preview (editable)"))
        self.preview = QTextEdit()
        outer.addWidget(self.preview, 1)
        self.insert_button = QPushButton("Insert into Editor")
        self.insert_button.setEnabled(False)
        self.insert_button.clicked.connect(self.insert_script)
        outer.addWidget(self.insert_button)

    def generate_script(self):
        args = (self.provider.currentText(), self.model.text().strip(), self.key.text(),
                self.idea.toPlainText(), self.tone.currentText(), self.minutes.value())
        if not all(args[:4]):
            self.status.setText("Enter a provider, model, API key, and idea.")
            return
        self.generate_button.setEnabled(False)
        self.insert_button.setEnabled(False)
        self.progress.show()
        self.status.setText("Generating script...")
        self.worker = AiWorker(args)
        self.worker.success.connect(self.on_success)
        self.worker.failure.connect(self.on_failure)
        self.worker.start()

    def on_success(self, result):
        self.preview.setPlainText(result)
        self.status.setText("Script ready. Review it before inserting.")
        self.insert_button.setEnabled(True)
        self.generate_button.setEnabled(True)
        self.progress.hide()

    def on_failure(self, message):
        self.status.setText("Error: " + message)
        self.generate_button.setEnabled(True)
        self.progress.hide()

    def insert_script(self):
        if not self.preview.toPlainText().strip():
            return
        answer = QMessageBox.question(self, "Replace Script",
                                      "Replace the current script with the generated text?")
        if answer == QMessageBox.StandardButton.Yes:
            self.parent().set_script(self.preview.toPlainText())
            self.accept()

class MainWindow(QMainWindow):
    # Interfaz limpia: biblioteca, editor y lector sin distracciones.
    def __init__(self):
        super().__init__()
        self.settings = QSettings("PromptFlow", "PromptFlow")
        self.setWindowTitle("PromptFlow")
        self.resize(1250, 780)
        self.setMinimumSize(780, 540)
        self.playing = False
        self.last_tick = time.monotonic()
        self._fraction = 0.0
        self.script_file = None
        self.library_dir = Path.home() / "Documents" / "PromptFlow" / "Scripts"
        self.library_dir.mkdir(parents=True, exist_ok=True)
        icon = BASE / "assets" / "promptflow.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.make_library()
        self.make_editor()
        self.make_reader()
        self.set_script("Hello! Welcome to PromptFlow.\n\nWrite your script, click Read, and start your presentation.")
        self.refresh_library()
        self.stack.setCurrentWidget(self.library_page)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def button(self, label, action, primary=False):
        b = QPushButton(label)
        if primary:
            b.setObjectName("primary")
        b.clicked.connect(action)
        return b

    def page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 22, 26, 24)
        layout.setSpacing(16)
        self.stack.addWidget(page)
        return page, layout

    def heading(self, name, subtitle=None):
        group = QVBoxLayout()
        label = QLabel(name)
        label.setStyleSheet("font-size: 29px; font-weight: 750; color: white;")
        group.addWidget(label)
        if subtitle:
            small = QLabel(subtitle)
            small.setStyleSheet("color: #9da1b6;")
            group.addWidget(small)
        return group

    def make_library(self):
        self.library_page, layout = self.page()
        bar = QHBoxLayout()
        bar.addLayout(self.heading("PromptFlow"))
        bar.addStretch()
        bar.addWidget(self.button("Open .txt", self.open_file))
        bar.addWidget(self.button("✦ Generate with AI", self.show_ai))
        bar.addWidget(self.button("+ New Script", self.new_script, True))
        layout.addLayout(bar)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #2d3040;")
        layout.addWidget(line)
        header = QHBoxLayout()
        header.addLayout(self.heading("Scripts"))
        header.addStretch()
        header.addWidget(self.button("Refresh", self.refresh_library))
        layout.addLayout(header)
        self.scripts = QListWidget()
        self.scripts.setStyleSheet('''QListWidget {background:#171923; border:1px solid #303342;
            border-radius:16px; padding:10px; font-size:15px;}
            QListWidget::item {padding:17px; margin:4px; border-radius:10px;}
            QListWidget::item:selected {background:#47336e;}''')
        self.scripts.itemDoubleClicked.connect(self.open_library_item)
        layout.addWidget(self.scripts, 1)
        info = QLabel("Scripts saved from the editor appear here automatically.")
        info.setStyleSheet("color:#a3a5b6;")
        layout.addWidget(info)

    def make_editor(self):
        self.editor_page, layout = self.page()
        bar = QHBoxLayout()
        bar.addWidget(self.button("← Scripts", self.go_library))
        bar.addLayout(self.heading("Edit Script"))
        bar.addStretch()
        bar.addWidget(self.button("Open .txt", self.open_file))
        bar.addWidget(self.button("Save .txt", self.save_file))
        bar.addWidget(self.button("✦ Generate with AI", self.show_ai))
        bar.addWidget(self.button("▶ Read", self.go_reader, True))
        layout.addLayout(bar)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText("Write your script here...")
        self.editor.setStyleSheet('''QTextEdit {font-size:19px; line-height:145%; padding:28px;
            border:1px solid #343747; background:#171923; border-radius:16px;}''')
        self.editor.textChanged.connect(self.update_script)
        layout.addWidget(self.editor, 1)
        footer = QLabel("Tip: save your script in the library to find it on the Scripts screen.")
        footer.setStyleSheet("color:#9da1b6;")
        layout.addWidget(footer)

    def make_reader(self):
        self.reader_page, layout = self.page()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        top = QFrame()
        top.setObjectName("top")
        topbar = QHBoxLayout(top)
        topbar.addWidget(self.button("← Editor", self.go_editor))
        title = QLabel("PromptFlow")
        title.setStyleSheet("font-size:18px; font-weight:700; color:#e7d9ff;")
        topbar.addWidget(title)
        topbar.addStretch()
        topbar.addWidget(self.button("Restart", self.reset))
        layout.addWidget(top)
        self.reader = QScrollArea()
        self.reader.setWidgetResizable(True)
        self.reader.setStyleSheet("QScrollArea {background:#090b12; border:0;}")
        self.canvas = ScriptCanvas()
        self.reader.setWidget(self.canvas)
        layout.addWidget(self.reader, 1)
        bottom = QFrame()
        bottom.setObjectName("bottom")
        controls = QHBoxLayout(bottom)
        controls.setContentsMargins(20, 12, 20, 12)
        self.play = self.button("▶ Play", self.toggle_play, True)
        controls.addWidget(self.play)
        controls.addWidget(QLabel("Speed"))
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(10, 180)
        saved_speed = self.settings.value("reading_speed", 45, type=int)
        self.speed.setValue(max(10, min(180, saved_speed)))
        self.speed.valueChanged.connect(self.save_preferences)
        controls.addWidget(self.speed, 1)
        controls.addWidget(QLabel("Text"))
        self.font_size = QSlider(Qt.Orientation.Horizontal)
        self.font_size.setRange(28, 100)
        saved_font_size = self.settings.value("font_size", 54, type=int)
        self.font_size.setValue(max(28, min(100, saved_font_size)))
        self.font_size.valueChanged.connect(self.change_font)
        self.font_size.valueChanged.connect(self.save_preferences)
        self.change_font(self.font_size.value())
        controls.addWidget(self.font_size, 1)
        self.mirror = QCheckBox("Mirror mode")
        saved_mirror = self.settings.value("mirror_mode", False, type=bool)
        self.mirror.setChecked(saved_mirror)
        self.mirror.toggled.connect(self.set_mirror)
        self.mirror.toggled.connect(self.save_preferences)
        self.set_mirror(self.mirror.isChecked())
        controls.addWidget(self.mirror)
        layout.addWidget(bottom)

    def go_library(self):
        self.pause()
        self.refresh_library()
        self.stack.setCurrentWidget(self.library_page)

    def go_editor(self):
        self.pause()
        self.stack.setCurrentWidget(self.editor_page)

    def go_reader(self):
        self.pause()
        self.canvas.update_layout()
        self.reader.verticalScrollBar().setValue(0)
        self.stack.setCurrentWidget(self.reader_page)

    def new_script(self):
        self.script_file = None
        self.set_script("")
        self.go_editor()

    def refresh_library(self):
        self.scripts.clear()
        files = sorted(self.library_dir.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
        for file in files:
            item = QListWidgetItem("📄  " + file.stem)
            item.setData(Qt.ItemDataRole.UserRole, str(file))
            self.scripts.addItem(item)
        if not files:
            item = QListWidgetItem("No scripts yet. Click “+ New Script” to get started.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.scripts.addItem(item)

    def open_library_item(self, item):
        filename = item.data(Qt.ItemDataRole.UserRole)
        if filename:
            self.load_file(Path(filename))

    def set_script(self, text):
        self.pause()
        self.editor.setPlainText(text)
        self.reader.verticalScrollBar().setValue(0)

    def update_script(self):
        self.canvas.text = self.editor.toPlainText()
        self.canvas.update_layout()

    def change_font(self, value):
        self.canvas.point_size = value
        self.canvas.update_layout()

    def set_mirror(self, enabled):
        self.canvas.mirrored = enabled
        self.canvas.update()

    def save_preferences(self, *args):
        self.settings.setValue("reading_speed", self.speed.value())
        self.settings.setValue("font_size", self.font_size.value())
        self.settings.setValue("mirror_mode", self.mirror.isChecked())
        self.settings.sync()

    def toggle_play(self):
        self.playing = not self.playing
        self.last_tick = time.monotonic()
        self.play.setText("⏸ Pause" if self.playing else "▶ Play")

    def pause(self):
        self.playing = False
        if hasattr(self, "play"):
            self.play.setText("▶ Play")
        self.last_tick = time.monotonic()

    def reset(self):
        self.pause()
        self._fraction = 0.0
        self.reader.verticalScrollBar().setValue(0)

    def tick(self):
        now = time.monotonic()
        elapsed = min(now - self.last_tick, 0.1)
        self.last_tick = now
        if not self.playing:
            return
        bar = self.reader.verticalScrollBar()
        if bar.maximum() <= 0:
            self.pause()
            return
        self._fraction += elapsed * self.speed.value()
        pixels = int(self._fraction)
        self._fraction -= pixels
        if pixels:
            bar.setValue(min(bar.maximum(), bar.value() + pixels))
            if bar.value() >= bar.maximum():
                self.pause()

    def load_file(self, filename):
        try:
            text = filename.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "Could Not Open File", str(exc))
            return
        self.script_file = filename
        self.set_script(text)
        self.go_editor()

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Script", "", "Text Files (*.txt)")
        if filename:
            self.load_file(Path(filename))

    def save_file(self):
        initial = str(self.script_file or (self.library_dir / "My Script.txt"))
        filename, _ = QFileDialog.getSaveFileName(self, "Save Script", initial, "Text Files (*.txt)")
        if filename:
            path = Path(filename)
            if path.suffix.lower() != ".txt":
                path = path.with_suffix(".txt")
            try:
                path.write_text(self.editor.toPlainText(), encoding="utf-8")
                self.script_file = path
            except OSError as exc:
                QMessageBox.critical(self, "Could Not Save File", str(exc))

    def show_ai(self):
        self.go_editor()
        dialog = AiDialog(self)
        dialog.exec()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
