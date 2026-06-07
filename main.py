#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bench Manager — точка входа."""

import sys
import os
import argparse
import time

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    APP_DIR  = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR  = BASE_DIR

sys.path.insert(0, BASE_DIR)

from core.config    import load_config
from core.connector import BenchConnector
from logger.log     import get_logger, setup_logging


def parse_args():
    p = argparse.ArgumentParser(description="Bench Manager v3.0")
    p.add_argument("--console",  "-c", action="store_true")
    p.add_argument("--check",         action="store_true")
    p.add_argument("--version",  "-v", action="store_true")
    p.add_argument("--info",          action="store_true")
    p.add_argument("--stand",    "-s", type=str)
    p.add_argument("--deploy",   "-d", type=str)
    p.add_argument("--diagnose",      type=str)
    p.add_argument("--init-crypto",   action="store_true",
                   help="Зашифровать пароли в config.yaml")
    return p.parse_args()


def main():
    args = parse_args()

    if args.version:
        print("Bench Manager v3.0")
        return

    if args.info:
        for pkg in ("paramiko", "PyQt5", "cryptography", "yaml"):
            try:
                m = __import__(pkg)
                ver = getattr(m, "__version__", "?")
                print(f"  ✓  {pkg:<14} {ver}")
            except ImportError:
                print(f"  ✗  {pkg:<14} не установлен")
        return

    cfg_path = os.path.join(APP_DIR, "config.yaml")

    if args.init_crypto:
        from core.crypto import _cmd_init
        _cmd_init(cfg_path)
        return

    cfg = load_config(cfg_path)
    setup_logging(**cfg.get("logging", {}))
    log = get_logger("main")

    bc = BenchConnector(cfg)

    # ── Консольный режим ──────────────────────────────────
    if any([args.console, args.check, args.stand, args.deploy, args.diagnose]):
        bc.start_monitoring()
        time.sleep(1.2)

        if args.check:
            print("\n=== Стенды ===\n")
            for n, info in bc.get_all_info().items():
                s = "ONLINE " if info["status"] == "online" else "OFFLINE"
                print(f"  {n:12} {info['ip']:18}:{info['port']}  {s}  {info['type']}")

        elif args.stand:
            ok, msg = bc.connect(args.stand)
            print(f"  {'✓' if ok else '✗'}  {msg}")

        elif args.deploy:
            ok, msg = bc.connect(args.deploy)
            if ok:
                ok2, result = bc.deploy_files(args.deploy)
                print(result)
            else:
                print(f"  Подключение не удалось: {msg}")

        elif args.diagnose:
            print(bc.diagnose_connection(args.diagnose))

        else:
            for name in bc.stands:
                ok, msg = bc.connect(name)
                print(f"  {'✓' if ok else '✗'}  {name}: {msg}")

        bc.stop_monitoring()
        return

    # ── GUI режим ─────────────────────────────────────────
    try:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore    import Qt
        from gui.main_window import MainWindow

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,    True)

        app = QApplication(sys.argv)
        app.setApplicationName("Bench Manager")

        window = MainWindow(bc)
        window.show()
        bc.start_monitoring()

        sys.exit(app.exec_())

    except ImportError as e:
        print(f"PyQt5 не установлен: {e}")
        print("pip install PyQt5")
        sys.exit(1)


if __name__ == "__main__":
    main()
