#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Загрузка config.yaml с автоматической расшифровкой паролей."""

import os
import yaml
from logger.log import get_logger

log = get_logger("config")

DEFAULTS = {
    "monitoring": {"check_interval": 5, "ssh_timeout": 10, "auto_reconnect": False},
    "logging":    {"level": "INFO", "file": "logs/bench_manager.log",
                   "max_size": 10_485_760, "backup_count": 5, "console": True, "colors": True},
    "paths":      {"downloads": "downloads", "uploads": "uploads",
                   "backups": "backups", "scripts": "scripts"},
    "jenkins":    {"enabled": False, "url": "", "username": "admin"},
    "gui":        {"theme": "dark", "language": "ru", "refresh_interval": 3000,
                   "window_width": 1200, "window_height": 800},
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(path: str) -> dict:
    base_dir = os.path.dirname(os.path.abspath(path))
    cfg = _deep_merge(DEFAULTS, {})
    cfg["_base_dir"] = base_dir

    if not os.path.exists(path):
        log.warning(f"config.yaml не найден ({path}), используются дефолты")
        cfg["stands"] = _default_stands()
        return cfg

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        cfg = _deep_merge(DEFAULTS, raw)
        cfg["_base_dir"] = base_dir

        # Расшифровать пароли
        from core.crypto import decrypt_password
        for stand in cfg.get("stands", []):
            pwd = stand.get("password", "")
            if pwd:
                try:
                    stand["password"] = decrypt_password(pwd, base_dir)
                except Exception as e:
                    log.error(f"Не удалось расшифровать пароль стенда {stand.get('name')}: {e}")
                    stand["password"] = ""

        log.info(f"Конфигурация загружена: {path} ({len(cfg.get('stands', []))} стендов)")
    except yaml.YAMLError as e:
        log.error(f"Ошибка разбора config.yaml: {e}")
        cfg["stands"] = _default_stands()

    return cfg


def _default_stands() -> list:
    return [
        {"name": "ГОЗ",     "ip": "192.168.243.248", "username": "pkrv",     "password": "zxcv", "port": 22,
         "folders": {"cvs": "/home/pkrv/CVS", "tmp": "/tmp"},
         "board": {"type": "основная", "can_flash": True, "executable": "1po2_1n"}},
        {"name": "Арктика", "ip": "192.168.243.249", "username": "pkrv",     "password": "zxcv", "port": 22,
         "folders": {"cvs": "/home/pkrv/CVS", "tmp": "/tmp"},
         "board": {"type": "основная", "can_flash": True, "executable": "1po2_1n"}},
        {"name": "C1M",     "ip": "192.168.243.254", "username": "pkrv",     "password": "zxcv", "port": 22,
         "folders": {"cvs": "/home/pkrv/CVS", "tmp": "/tmp"},
         "board": {"type": "основная", "can_flash": True, "executable": "1po2_1n"}},
        {"name": "OrangePi","ip": "192.168.243.46",  "username": "orangepi", "password": "",     "port": 22,
         "folders": {},
         "board": {"type": "orange_pi", "can_flash": False, "view_only": True}},
    ]
