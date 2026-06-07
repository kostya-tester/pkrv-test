#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
from logging.handlers import RotatingFileHandler

_LOGGERS: dict = {}

COLORS = {
    "DEBUG":    "\033[36m",
    "INFO":     "\033[32m",
    "WARNING":  "\033[33m",
    "ERROR":    "\033[31m",
    "CRITICAL": "\033[35m",
    "RESET":    "\033[0m",
}


class _ColorFormatter(logging.Formatter):
    FMT = "[{asctime}] [{levelname:8}] [{name}] {message}"

    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        reset = COLORS["RESET"]
        record.levelname = f"{color}{record.levelname}{reset}"
        return logging.Formatter(self.FMT, datefmt="%H:%M:%S", style="{").format(record)


def setup_logging(file="logs/bench_manager.log", level="INFO",
                  max_size=10_485_760, backup_count=5,
                  console=True, colors=True, **_):
    d = os.path.dirname(file)
    if d:
        os.makedirs(d, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    fh = RotatingFileHandler(file, maxBytes=max_size, backupCount=backup_count, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))
    root.addHandler(fh)
    if console:
        ch = logging.StreamHandler()
        ch.setFormatter(_ColorFormatter() if colors else logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] %(message)s", datefmt="%H:%M:%S"))
        root.addHandler(ch)


def get_logger(name: str) -> logging.Logger:
    if name not in _LOGGERS:
        _LOGGERS[name] = logging.getLogger(f"bench.{name}")
    return _LOGGERS[name]
