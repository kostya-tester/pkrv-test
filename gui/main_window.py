#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bench Manager — главное окно PyQt5.
Современный тёмный интерфейс: боковая панель + вкладки.
"""

import os
from datetime import datetime

from PyQt5.QtCore  import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt5.QtGui   import QFont, QTextCursor, QIcon, QPainter, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QTextEdit, QComboBox, QLineEdit,
    QFrame, QStatusBar, QGroupBox, QGridLayout, QMessageBox,
    QFileDialog, QProgressBar, QScrollArea, QSizePolicy, QSplitter,
    QListWidget, QListWidgetItem,
)

from core.connector import BenchConnector
from logger.log import get_logger

log = get_logger("gui")

# ─── Палитра ─────────────────────────────────────────────

C = {
    "bg":        "#0f1117",
    "sidebar":   "#161b22",
    "card":      "#1c2128",
    "card_hover":"#21262d",
    "border":    "#30363d",
    "accent":    "#2f81f7",
    "accent2":   "#1f6feb",
    "success":   "#3fb950",
    "warning":   "#d29922",
    "danger":    "#f85149",
    "text":      "#e6edf3",
    "text2":     "#8b949e",
    "text3":     "#484f58",
    "terminal":  "#010409",
    "tag_blue":  "#1f3a5f",
    "tag_green": "#1a3a2a",
}

QSS = f"""
* {{ font-family: 'Segoe UI', 'SF Pro Display', 'Ubuntu', sans-serif; font-size: 13px; }}

QMainWindow, QWidget#central {{
    background: {C['bg']};
    color: {C['text']};
}}

/* ── Sidebar ── */
QWidget#sidebar {{
    background: {C['sidebar']};
    border-right: 1px solid {C['border']};
    min-width: 200px;
    max-width: 200px;
}}
QPushButton#nav_btn {{
    background: transparent;
    color: {C['text2']};
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
}}
QPushButton#nav_btn:hover {{
    background: {C['card']};
    color: {C['text']};
}}
QPushButton#nav_btn[active="true"] {{
    background: {C['tag_blue']};
    color: {C['accent']};
    font-weight: 600;
}}
QLabel#logo {{
    color: {C['text']};
    font-size: 15px;
    font-weight: 700;
    padding: 20px 16px 8px;
}}
QLabel#logo_sub {{
    color: {C['text3']};
    font-size: 11px;
    padding: 0 16px 20px;
}}

/* ── Content ── */
QWidget#content_area {{
    background: {C['bg']};
    color: {C['text']};
}}
QLabel#page_title {{
    font-size: 18px;
    font-weight: 700;
    color: {C['text']};
    padding: 20px 24px 4px;
}}
QLabel#page_sub {{
    font-size: 12px;
    color: {C['text2']};
    padding: 0 24px 16px;
}}

/* ── Cards ── */
QFrame#card {{
    background: {C['card']};
    border: 1px solid {C['border']};
    border-radius: 8px;
}}
QFrame#card_online {{
    background: {C['card']};
    border: 1px solid #2ea043;
    border-radius: 8px;
}}
QFrame#card_connected {{
    background: {C['tag_green']};
    border: 1px solid {C['success']};
    border-radius: 8px;
}}

/* ── Buttons ── */
QPushButton {{
    background: {C['card']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
}}
QPushButton:hover {{ background: {C['card_hover']}; border-color: {C['accent']}; }}
QPushButton:disabled {{ color: {C['text3']}; background: {C['sidebar']}; border-color: {C['border']}; }}

QPushButton#btn_primary {{
    background: {C['accent2']};
    color: #fff;
    border: 1px solid {C['accent']};
    font-weight: 600;
}}
QPushButton#btn_primary:hover {{ background: {C['accent']}; }}
QPushButton#btn_success {{
    background: #196c2e;
    color: {C['success']};
    border: 1px solid {C['success']};
    font-weight: 600;
}}
QPushButton#btn_success:hover {{ background: #1f8a3a; }}
QPushButton#btn_danger {{
    background: #4a1515;
    color: {C['danger']};
    border: 1px solid {C['danger']};
}}
QPushButton#btn_danger:hover {{ background: #6b1e1e; }}
QPushButton#btn_sm {{
    padding: 4px 10px;
    font-size: 11px;
    border-radius: 4px;
}}

/* ── Inputs ── */
QTextEdit, QLineEdit {{
    background: {C['terminal']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 8px;
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    selection-background-color: {C['accent2']};
}}
QTextEdit:focus, QLineEdit:focus {{ border-color: {C['accent']}; }}

QComboBox {{
    background: {C['card']};
    color: {C['text']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 140px;
}}
QComboBox:focus {{ border-color: {C['accent']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {C['card']};
    color: {C['text']};
    border: 1px solid {C['border']};
    selection-background-color: {C['accent2']};
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {C['border']};
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 8px;
    color: {C['text2']};
    font-size: 12px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}

/* ── StatusBar ── */
QStatusBar {{
    background: {C['sidebar']};
    color: {C['text2']};
    border-top: 1px solid {C['border']};
    font-size: 11px;
    padding: 2px 8px;
}}

/* ── Scrollbar ── */
QScrollBar:vertical {{
    background: {C['bg']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {C['border']};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {C['text3']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── ProgressBar ── */
QProgressBar {{
    background: {C['border']};
    border: none;
    border-radius: 3px;
    height: 4px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {C['accent']}; border-radius: 3px; }}

/* ── Separator ── */
QFrame#sep {{ background: {C['border']}; max-height: 1px; }}
"""


# ─── Worker Thread ────────────────────────────────────────

class Worker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn, self._a, self._kw = fn, args, kwargs

    def run(self):
        try:
            ok, msg = self._fn(*self._a, **self._kw)
            self.done.emit(ok, msg)
        except Exception as e:
            self.done.emit(False, str(e))


# ─── StandCard ────────────────────────────────────────────

class StandCard(QFrame):
    sig_connect    = pyqtSignal(str)
    sig_disconnect = pyqtSignal(str)
    sig_diagnose   = pyqtSignal(str)

    def __init__(self, name: str, info: dict):
        super().__init__()
        self.stand_name = name
        self.setObjectName("card")
        self.setMinimumHeight(130)
        self._build(info)

    def _build(self, info: dict):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        self.lbl_indicator = QLabel("●")
        self.lbl_indicator.setStyleSheet(f"color: {C['text3']}; font-size: 10px;")
        hdr.addWidget(self.lbl_indicator)

        self.lbl_name = QLabel(info["name"])
        self.lbl_name.setFont(QFont("Segoe UI", 13, QFont.Bold))
        hdr.addWidget(self.lbl_name)
        hdr.addStretch()

        self.lbl_badge = QLabel("OFFLINE")
        self.lbl_badge.setStyleSheet(
            f"color:{C['text3']}; background:{C['border']}; border-radius:4px;"
            f"padding:2px 8px; font-size:10px; font-weight:600;")
        hdr.addWidget(self.lbl_badge)
        lay.addLayout(hdr)

        # Meta
        self.lbl_meta = QLabel(
            f"{info['ip']}:{info['port']}  ·  {info['username']}  ·  {info['type']}")
        self.lbl_meta.setStyleSheet(f"color:{C['text2']}; font-size:11px;")
        lay.addWidget(self.lbl_meta)

        # Error
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet(f"color:{C['danger']}; font-size:11px;")
        self.lbl_err.setVisible(False)
        lay.addWidget(self.lbl_err)

        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.btn_con = QPushButton("Подключить")
        self.btn_con.setObjectName("btn_primary")
        self.btn_con.setProperty("class", "btn_sm")
        self.btn_con.setFixedHeight(28)
        self.btn_con.clicked.connect(lambda: self.sig_connect.emit(self.stand_name))
        btns.addWidget(self.btn_con)

        self.btn_dis = QPushButton("Отключить")
        self.btn_dis.setObjectName("btn_danger")
        self.btn_dis.setFixedHeight(28)
        self.btn_dis.setEnabled(False)
        self.btn_dis.clicked.connect(lambda: self.sig_disconnect.emit(self.stand_name))
        btns.addWidget(self.btn_dis)

        self.btn_diag = QPushButton("Диагностика")
        self.btn_diag.setFixedHeight(28)
        self.btn_diag.clicked.connect(lambda: self.sig_diagnose.emit(self.stand_name))
        btns.addWidget(self.btn_diag)

        btns.addStretch()
        lay.addLayout(btns)

    def refresh(self, info: dict):
        connected = info["connected"]
        online    = info["status"] == "online"
        error     = info.get("error", "")

        if connected:
            self.setObjectName("card_connected")
            self.lbl_indicator.setStyleSheet(f"color:{C['success']}; font-size:10px;")
            self.lbl_badge.setText("CONNECTED")
            self.lbl_badge.setStyleSheet(
                f"color:{C['success']}; background:{C['tag_green']}; border-radius:4px;"
                f"padding:2px 8px; font-size:10px; font-weight:600;")
        elif online:
            self.setObjectName("card_online")
            self.lbl_indicator.setStyleSheet(f"color:{C['warning']}; font-size:10px;")
            self.lbl_badge.setText("ONLINE")
            self.lbl_badge.setStyleSheet(
                f"color:{C['warning']}; background:#2d2008; border-radius:4px;"
                f"padding:2px 8px; font-size:10px; font-weight:600;")
        else:
            self.setObjectName("card")
            self.lbl_indicator.setStyleSheet(f"color:{C['text3']}; font-size:10px;")
            self.lbl_badge.setText("OFFLINE")
            self.lbl_badge.setStyleSheet(
                f"color:{C['text3']}; background:{C['border']}; border-radius:4px;"
                f"padding:2px 8px; font-size:10px; font-weight:600;")

        self.lbl_err.setText(error)
        self.lbl_err.setVisible(bool(error) and not connected)

        self.btn_con.setEnabled(online and not connected)
        self.btn_dis.setEnabled(connected)

        self.setStyle(self.style())   # force repaint


# ─── Страницы ─────────────────────────────────────────────

def _sep():
    f = QFrame()
    f.setObjectName("sep")
    f.setFrameShape(QFrame.HLine)
    return f


class StandsPage(QWidget):
    def __init__(self, bc: BenchConnector, log_fn):
        super().__init__()
        self.bc     = bc
        self._log   = log_fn
        self._cards: dict[str, StandCard] = {}
        self._workers: list[Worker] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 24)
        root.setSpacing(0)

        # Toolbar
        bar = QHBoxLayout()
        btn_all = QPushButton("⚡  Подключить все")
        btn_all.setObjectName("btn_primary")
        btn_all.clicked.connect(self._connect_all)
        bar.addWidget(btn_all)

        btn_dis = QPushButton("✕  Отключить все")
        btn_dis.setObjectName("btn_danger")
        btn_dis.clicked.connect(self._disconnect_all)
        bar.addWidget(btn_dis)

        btn_ref = QPushButton("↻  Обновить")
        btn_ref.clicked.connect(self.refresh)
        bar.addWidget(btn_ref)
        bar.addStretch()
        root.addLayout(bar)
        root.addSpacing(16)

        # Grid of cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        self._grid = QGridLayout(inner)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(0, 0, 0, 0)

        col, row = 0, 0
        for name, info in self.bc.get_all_info().items():
            card = StandCard(name, info)
            card.sig_connect.connect(self._connect_stand)
            card.sig_disconnect.connect(self._disconnect_stand)
            card.sig_diagnose.connect(self._diagnose)
            self._cards[name] = card
            self._grid.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col, row = 0, row + 1

        scroll.setWidget(inner)
        root.addWidget(scroll)

        bc = self.bc
        bc.register_status_callback(self.refresh)

    def refresh(self):
        for name, card in self._cards.items():
            info = self.bc.get_all_info().get(name)
            if info:
                card.refresh(info)

    def _connect_stand(self, name: str):
        self._log(f"Подключение к {name}...")
        w = Worker(self.bc.connect, name)
        w.done.connect(lambda ok, msg: self._on_done(name, ok, msg))
        self._workers.append(w)
        w.start()

    def _on_done(self, name: str, ok: bool, msg: str):
        self._log(("✓ " if ok else "✗ ") + msg)
        self.refresh()

    def _disconnect_stand(self, name: str):
        self.bc.disconnect(name)
        self._log(f"Отключен от {name}")
        self.refresh()

    def _connect_all(self):
        for name in self.bc.stands:
            self._connect_stand(name)

    def _disconnect_all(self):
        self.bc.disconnect_all()
        self.refresh()

    def _diagnose(self, name: str):
        self._log(f"Диагностика {name}...")
        result = self.bc.diagnose_connection(name)
        dlg = QMessageBox(self)
        dlg.setWindowTitle(f"Диагностика — {name}")
        dlg.setText(f"<pre>{result}</pre>")
        dlg.exec_()


class TerminalPage(QWidget):
    def __init__(self, bc: BenchConnector, log_fn):
        super().__init__()
        self.bc   = bc
        self._log = log_fn
        self._history: list[str] = []
        self._hist_idx = -1
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 24)
        lay.setSpacing(10)

        # Top bar
        top = QHBoxLayout()
        top.addWidget(QLabel("Стенд:"))
        self.cmb = QComboBox()
        self.cmb.addItems(self.bc.stands.keys())
        top.addWidget(self.cmb)
        top.addStretch()

        btn_clear = QPushButton("Очистить")
        btn_clear.clicked.connect(lambda: self.out.clear())
        top.addWidget(btn_clear)
        lay.addLayout(top)

        # Output
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("JetBrains Mono", 11))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.out.setHtml(
            f"<span style='color:{C['text2']}'>Bench Manager Terminal [{ts}]</span><br>"
            f"<span style='color:{C['text3']}'>─────────────────────────────────</span><br>"
        )
        lay.addWidget(self.out, stretch=1)

        # Input
        inp = QHBoxLayout()
        self.prompt = QLabel("$")
        self.prompt.setStyleSheet(f"color:{C['accent']}; font-family:monospace; font-weight:bold; font-size:14px;")
        inp.addWidget(self.prompt)

        self.cmd = QLineEdit()
        self.cmd.setPlaceholderText("введите команду…")
        self.cmd.returnPressed.connect(self._run)
        self.cmd.installEventFilter(self)
        inp.addWidget(self.cmd)

        btn_run = QPushButton("▶")
        btn_run.setObjectName("btn_primary")
        btn_run.setFixedWidth(40)
        btn_run.clicked.connect(self._run)
        inp.addWidget(btn_run)
        lay.addLayout(inp)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self.cmd and event.type() == QEvent.KeyPress:
            from PyQt5.QtCore import Qt as _Qt
            if event.key() == _Qt.Key_Up and self._history:
                self._hist_idx = max(0, self._hist_idx - 1)
                self.cmd.setText(self._history[self._hist_idx])
            elif event.key() == _Qt.Key_Down and self._history:
                self._hist_idx = min(len(self._history), self._hist_idx + 1)
                self.cmd.setText(self._history[self._hist_idx] if self._hist_idx < len(self._history) else "")
        return super().eventFilter(obj, event)

    def _run(self):
        cmd  = self.cmd.text().strip()
        if not cmd:
            return
        name = self.cmb.currentText()
        self._history.append(cmd)
        self._hist_idx = len(self._history)

        self.out.append(
            f"<span style='color:{C['text2']}'>[{name}]</span> "
            f"<span style='color:{C['accent']}; font-weight:bold'>$ {cmd}</span>"
        )

        ok, stdout, stderr = self.bc.execute(name, cmd)
        if ok:
            if stdout.strip():
                self.out.append(f"<span style='color:{C['text']}'><pre style='margin:0'>{stdout.rstrip()}</pre></span>")
            if stderr.strip():
                self.out.append(f"<span style='color:{C['warning']}'><pre style='margin:0'>{stderr.rstrip()}</pre></span>")
        else:
            self.out.append(
                f"<span style='color:{C['danger']}'>✗ {stderr or 'Нет подключения к ' + name}</span>"
            )

        self.cmd.clear()
        self.out.moveCursor(QTextCursor.End)


class DeployPage(QWidget):
    def __init__(self, bc: BenchConnector, log_fn):
        super().__init__()
        self.bc   = bc
        self._log = log_fn
        self._worker = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 24)
        lay.setSpacing(14)

        # Settings group
        grp = QGroupBox("Параметры")
        g   = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnStretch(1, 1)

        g.addWidget(QLabel("Стенд:"), 0, 0)
        self.cmb_stand = QComboBox()
        self.cmb_stand.addItems(self.bc.stands.keys())
        g.addWidget(self.cmb_stand, 0, 1)

        g.addWidget(QLabel("Директория mpo:"), 1, 0)
        self.path_edit = QLineEdit(os.getcwd())
        g.addWidget(self.path_edit, 1, 1)

        btn_browse = QPushButton("Обзор…")
        btn_browse.clicked.connect(self._browse)
        g.addWidget(btn_browse, 1, 2)

        lay.addWidget(grp)

        # Action
        row = QHBoxLayout()
        self.btn_deploy = QPushButton("🚀  Запустить деплой")
        self.btn_deploy.setObjectName("btn_success")
        self.btn_deploy.setMinimumHeight(36)
        self.btn_deploy.clicked.connect(self._deploy)
        row.addWidget(self.btn_deploy)
        row.addStretch()
        lay.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)
        lay.addWidget(self.progress)

        # Output
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("JetBrains Mono", 11))
        self.out.setPlaceholderText("Результат деплоя появится здесь…")
        lay.addWidget(self.out, stretch=1)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Директория mpo", self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def _deploy(self):
        name = self.cmb_stand.currentText()
        if not self.bc.stands.get(name) or not self.bc.stands[name].connected:
            QMessageBox.warning(self, "Нет подключения",
                                f"Сначала подключитесь к стенду {name} на вкладке «Стенды».")
            return

        self.btn_deploy.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.out.clear()
        local_dir = self.path_edit.text()

        self._worker = Worker(self.bc.deploy_files, name, local_dir)
        self._worker.done.connect(self._done)
        self._worker.start()

    def _done(self, ok: bool, msg: str):
        self.out.setPlainText(msg)
        self.btn_deploy.setEnabled(True)
        self.progress.setVisible(False)
        self._log(f"Деплой {'завершён ✓' if ok else 'ОШИБКА ✗'}")


class LogsPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 24)
        lay.setSpacing(10)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(QFont("JetBrains Mono", 11))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.out.append(f"<span style='color:{C['text2']}'>=== Bench Manager лог [{ts}] ===</span>")
        lay.addWidget(self.out)

        bar = QHBoxLayout()
        btn_clear = QPushButton("Очистить")
        btn_clear.clicked.connect(self.out.clear)
        bar.addWidget(btn_clear)
        bar.addStretch()
        lay.addLayout(bar)

    def append(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.out.append(f"<span style='color:{C['text3']}'>[{ts}]</span> {text}")
        self.out.moveCursor(QTextCursor.End)


# ─── MainWindow ───────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, bc: BenchConnector):
        super().__init__()
        self.bc = bc
        cfg = bc.cfg.get("gui", {})
        self.setWindowTitle("Bench Manager")
        self.resize(cfg.get("window_width", 1200), cfg.get("window_height", 800))
        self.setStyleSheet(QSS)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        lbl = QLabel("⚙ Bench")
        lbl.setObjectName("logo")
        sb_lay.addWidget(lbl)

        sub = QLabel("Manager v3.0")
        sub.setObjectName("logo_sub")
        sb_lay.addWidget(sub)

        sb_lay.addWidget(_sep())

        self._nav_btns: list[QPushButton] = []
        pages_meta = [
            ("🖥  Стенды",   "stands"),
            ("⌨  Терминал", "terminal"),
            ("🚀  Деплой",   "deploy"),
            ("📋  Логи",     "logs"),
        ]
        for label, key in pages_meta:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setProperty("page_key", key)
            btn.clicked.connect(lambda _, k=key: self._switch(k))
            sb_lay.addWidget(btn)
            self._nav_btns.append(btn)

        sb_lay.addStretch()
        sb_lay.addWidget(_sep())

        # Статус в сайдбаре
        self.sb_status = QLabel("Инициализация…")
        self.sb_status.setStyleSheet(f"color:{C['text3']}; font-size:10px; padding:10px 16px;")
        self.sb_status.setWordWrap(True)
        sb_lay.addWidget(self.sb_status)

        main_lay.addWidget(sidebar)

        # ── Content ──────────────────────────────────────
        right = QWidget()
        right.setObjectName("content_area")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        # Page header
        self.page_title = QLabel("Стенды")
        self.page_title.setObjectName("page_title")
        right_lay.addWidget(self.page_title)

        self.page_sub = QLabel("Управление SSH-подключениями к стендам")
        self.page_sub.setObjectName("page_sub")
        right_lay.addWidget(self.page_sub)

        right_lay.addWidget(_sep())
        right_lay.addSpacing(12)

        # Pages stack
        self._stack = QStackedWidget()
        self._logs_page = LogsPage()

        self._pages: dict[str, QWidget] = {
            "stands":   StandsPage(bc, self._logs_page.append),
            "terminal": TerminalPage(bc, self._logs_page.append),
            "deploy":   DeployPage(bc, self._logs_page.append),
            "logs":     self._logs_page,
        }
        for w in self._pages.values():
            self._stack.addWidget(w)

        right_lay.addWidget(self._stack)
        main_lay.addWidget(right)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Activate first page
        self._switch("stands")

        # Timer
        interval = cfg.get("refresh_interval", 3000)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(interval)

        bc.register_status_callback(self._tick)

    # ── Navigation ────────────────────────────────────────

    _PAGE_META = {
        "stands":   ("Стенды",   "Управление SSH-подключениями к стендам"),
        "terminal": ("Терминал", "Выполнение команд на стендах"),
        "deploy":   ("Деплой",   "Копирование и установка файлов mpo"),
        "logs":     ("Логи",     "Журнал событий приложения"),
    }

    def _switch(self, key: str):
        self._stack.setCurrentWidget(self._pages[key])
        title, sub = self._PAGE_META.get(key, (key, ""))
        self.page_title.setText(title)
        self.page_sub.setText(sub)
        for btn in self._nav_btns:
            active = btn.property("page_key") == key
            btn.setProperty("active", "true" if active else "false")
            btn.setStyle(btn.style())

    # ── Tick ─────────────────────────────────────────────

    def _tick(self):
        info   = self.bc.get_all_info()
        online = sum(1 for v in info.values() if v["status"] == "online")
        conn   = sum(1 for v in info.values() if v["connected"])
        ts     = datetime.now().strftime("%H:%M:%S")
        self.status_bar.showMessage(
            f"Стендов: {len(info)}   Online: {online}   Подключено: {conn}   {ts}"
        )
        self.sb_status.setText(
            f"Online: {online}/{len(info)}\nПодкл: {conn}/{len(info)}"
        )
        # Обновить карточки если видна страница стендов
        page = self._pages["stands"]
        if isinstance(page, StandsPage):
            page.refresh()

    # ── Close ─────────────────────────────────────────────

    def closeEvent(self, event):
        self.bc.stop_monitoring()
        self.bc.disconnect_all()
        event.accept()
