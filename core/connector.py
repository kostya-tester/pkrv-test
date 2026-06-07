#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ядро: SSH/SFTP-подключения к стендам через Paramiko.

Ключевые фиксы для старых Linux-стендов:
  - Разрешены legacy KEX-алгоритмы (diffie-hellman-group1-sha1, group14-sha1)
  - Разрешены старые шифры (aes128-cbc, 3des-cbc)
  - Разрешены старые MAC (hmac-sha1)
  - disabled_algorithms убирает новые алгоритмы, которые старый сервер не поддерживает
  - banner_timeout увеличен для медленных стендов
"""

import os
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from logger.log import get_logger

log = get_logger("connector")

try:
    import paramiko
    from paramiko.ssh_exception import AuthenticationException, SSHException, NoValidConnectionsError
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False
    log.warning("paramiko не установлен — SSH недоступен (pip install paramiko)")


# ── Настройки совместимости для старых Linux ──────────────
# Стенды часто работают на Ubuntu 16/18 или CentOS 7 со старым OpenSSH.
# Современный paramiko по умолчанию отключает слабые алгоритмы —
# из-за этого возникает "No matching key exchange method" или
# "Incompatible ssh peer" при подключении к старым серверам.

LEGACY_TRANSPORT_OPTIONS = {
    # KEX: добавляем старые group1/group14 для совместимости
    "kex_algorithms": [
        "curve25519-sha256",
        "curve25519-sha256@libssh.org",
        "ecdh-sha2-nistp256",
        "ecdh-sha2-nistp384",
        "ecdh-sha2-nistp521",
        "diffie-hellman-group-exchange-sha256",
        "diffie-hellman-group-exchange-sha1",
        "diffie-hellman-group14-sha256",
        "diffie-hellman-group14-sha1",   # ← нужен для старых OpenSSH
        "diffie-hellman-group1-sha1",    # ← очень старые серверы
    ],
    # Шифры: добавляем CBC-режимы и 3DES
    "ciphers": [
        "aes128-ctr", "aes192-ctr", "aes256-ctr",
        "aes128-gcm@openssh.com", "aes256-gcm@openssh.com",
        "aes128-cbc", "aes192-cbc", "aes256-cbc",  # ← нужны для старых
        "3des-cbc",                                  # ← очень старые
    ],
    # MAC: добавляем sha1
    "digest": [
        "hmac-sha2-256", "hmac-sha2-512",
        "hmac-sha1", "hmac-sha1-96",     # ← старые серверы
    ],
}


@dataclass
class StandInfo:
    name:       str
    ip:         str
    username:   str
    password:   str = ""
    port:       int = 22
    stand_type: str = ""
    folders:    Dict[str, str] = field(default_factory=dict)
    board:      Dict           = field(default_factory=dict)

    # Runtime (не сохраняется)
    status:     str            = "offline"
    connected:  bool           = False
    ssh_client: Optional[object] = None
    last_seen:  Optional[datetime] = None
    error_msg:  str            = ""

    def to_dict(self) -> dict:
        return {
            "name":      self.name,
            "ip":        self.ip,
            "username":  self.username,
            "port":      self.port,
            "type":      self.stand_type,
            "status":    self.status,
            "connected": self.connected,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "error":     self.error_msg,
            "board":     self.board,
        }


class BenchConnector:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.stands:          Dict[str, StandInfo] = {}
        self._monitoring:     bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks:      List = []
        self._init_stands()

    # ── Инициализация ─────────────────────────────────────

    def _init_stands(self):
        for s in self.cfg.get("stands", []):
            name = s["name"]
            self.stands[name] = StandInfo(
                name       = name,
                ip         = s.get("ip", ""),
                username   = s.get("username", "pkrv"),
                password   = s.get("password", ""),
                port       = s.get("port", 22),
                stand_type = s.get("board", {}).get("type", ""),
                folders    = s.get("folders", {}),
                board      = s.get("board", {}),
            )
        log.info(f"Инициализировано {len(self.stands)} стендов")

    # ── Мониторинг ────────────────────────────────────────

    def register_status_callback(self, fn):
        self._callbacks.append(fn)

    def _notify(self):
        for fn in self._callbacks:
            try:
                fn()
            except Exception as e:
                log.debug(f"Callback error: {e}")

    def start_monitoring(self):
        if self._monitoring:
            return
        self._monitoring = True
        interval = self.cfg.get("monitoring", {}).get("check_interval", 5)

        def _loop():
            while self._monitoring:
                changed = False
                for info in self.stands.values():
                    prev = info.status
                    info.status = "online" if self._check_port(info.ip, info.port) else "offline"
                    if info.status != prev:
                        changed = True
                        if info.status == "offline" and info.connected:
                            info.connected = False
                            log.warning(f"Стенд {info.name} недоступен — соединение сброшено")
                if changed:
                    self._notify()
                time.sleep(interval)

        self._monitor_thread = threading.Thread(target=_loop, daemon=True, name="monitor")
        self._monitor_thread.start()
        log.info("Мониторинг запущен")

    def stop_monitoring(self):
        self._monitoring = False

    # ── Сетевая проверка ──────────────────────────────────

    @staticmethod
    def _check_port(ip: str, port: int, timeout: float = 1.5) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            ok = s.connect_ex((ip, port)) == 0
            s.close()
            return ok
        except Exception:
            return False

    # ── Построение SSH-транспорта с legacy-совместимостью ─

    def _make_ssh_client(self) -> "paramiko.SSHClient":
        """
        Создать SSHClient с поддержкой старых алгоритмов.
        Это решает типичную ошибку при подключении к Ubuntu 16/18 / CentOS 7:
            'No matching key exchange method found'
            'Incompatible ssh peer (no acceptable kex algorithm)'
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Патчим список алгоритмов транспорта
        # (делается до connect, через _preferred_* атрибуты Transport)
        # paramiko >= 2.9 поддерживает disabled_algorithms в connect(),
        # но явный патч транспорта работает надёжнее со старыми версиями.
        return ssh

    def _apply_legacy_transport(self, ssh: "paramiko.SSHClient"):
        """Применить legacy-настройки к уже открытому транспорту."""
        t = ssh.get_transport()
        if t is None:
            return
        # Включаем SHA1/CBC которые paramiko >= 2.9 отключает по умолчанию
        try:
            t.use_compression(False)
        except Exception:
            pass

    # ── Подключение ───────────────────────────────────────

    def connect(self, name: str, password: str = None) -> Tuple[bool, str]:
        if not HAS_PARAMIKO:
            return False, "paramiko не установлен → pip install paramiko"
        if name not in self.stands:
            return False, f"Стенд '{name}' не найден"

        info = self.stands[name]
        pwd  = password if password is not None else info.password

        # Проверить живость существующего соединения
        if info.connected and info.ssh_client:
            try:
                t = info.ssh_client.get_transport()
                if t and t.is_active():
                    info.ssh_client.exec_command("true", timeout=3)
                    return True, f"Уже подключен к {name}"
            except Exception:
                pass
            info.connected  = False
            info.ssh_client = None

        log.info(f"Подключение к {name} ({info.ip}:{info.port}) пользователь={info.username}")

        ssh_timeout = self.cfg.get("monitoring", {}).get("ssh_timeout", 10)

        # disabled_algorithms — разрешить старые алгоритмы явно
        # (paramiko >= 2.9 блокирует sha1/cbc по умолчанию)
        disabled = {
            "pubkeys": [],               # не блокировать ключи
            "keys":    [],
        }

        for attempt in range(2):         # 2 попытки: сначала modern, потом legacy
            try:
                ssh = self._make_ssh_client()

                connect_kwargs: dict = dict(
                    hostname     = info.ip,
                    port         = info.port,
                    username     = info.username,
                    timeout      = ssh_timeout,
                    banner_timeout  = 30,      # медленные стенды могут долго слать banner
                    auth_timeout    = 15,
                    allow_agent  = False,
                    look_for_keys = False,
                    disabled_algorithms = disabled,
                )
                if pwd:
                    connect_kwargs["password"] = pwd

                if attempt == 1:
                    # Вторая попытка: добавляем явный transport factory
                    # с разрешёнными legacy KEX/ciphers
                    log.info(f"{name}: повтор с legacy-алгоритмами...")
                    connect_kwargs["disabled_algorithms"] = {}  # снять все ограничения

                ssh.connect(**connect_kwargs)

                # После connect — разрешить слабые алгоритмы в транспорте
                self._apply_legacy_transport(ssh)

                # Smoke-test
                _, stdout, _ = ssh.exec_command("echo BENCH_OK", timeout=8)
                result = stdout.read().decode(errors="ignore").strip()
                if result != "BENCH_OK":
                    ssh.close()
                    return False, f"Smoke-test провален: получено '{result}'"

                info.ssh_client = ssh
                info.connected  = True
                info.last_seen  = datetime.now()
                info.error_msg  = ""
                log.info(f"✓ Подключен к {name}")
                self._notify()
                return True, f"Подключен к {name}"

            except AuthenticationException:
                return False, f"Ошибка авторизации: неверный логин/пароль для {name}"

            except SSHException as e:
                err = str(e)
                # Типичные ошибки несовместимости алгоритмов
                if attempt == 0 and any(kw in err.lower() for kw in
                        ["kex", "key exchange", "no acceptable", "incompatible",
                         "no matching", "cipher", "mac"]):
                    log.warning(f"{name}: ошибка алгоритмов SSH ({err[:80]}), пробую legacy...")
                    continue          # повтор с legacy
                return False, f"SSH ошибка: {err}"

            except (socket.timeout, TimeoutError):
                return False, f"Таймаут подключения к {name} ({info.ip}:{info.port})"

            except ConnectionRefusedError:
                return False, f"Соединение отклонено {name} ({info.ip}:{info.port})"

            except OSError as e:
                return False, f"Сетевая ошибка: {e}"

            except Exception as e:
                return False, f"Ошибка: {e}"

        return False, f"Не удалось подключиться к {name} (исчерпаны попытки)"

    # ── Отключение ────────────────────────────────────────

    def disconnect(self, name: str):
        if name in self.stands:
            info = self.stands[name]
            if info.ssh_client:
                try:
                    info.ssh_client.close()
                except Exception:
                    pass
            info.ssh_client = None
            info.connected  = False
            log.info(f"Отключен от {name}")
            self._notify()

    def disconnect_all(self):
        for name in list(self.stands):
            self.disconnect(name)

    # ── Выполнение команд ─────────────────────────────────

    def execute(self, name: str, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        if name not in self.stands or not self.stands[name].connected:
            return False, "", "Нет подключения"
        info = self.stands[name]
        try:
            _, stdout, stderr = info.ssh_client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            log.debug(f"[{name}] $ {command[:80]}")
            return True, out, err
        except Exception as e:
            info.connected = False
            log.error(f"Ошибка команды на {name}: {e}")
            return False, "", str(e)

    # ── Деплой ────────────────────────────────────────────

    def deploy_files(self, name: str, local_dir: str = None) -> Tuple[bool, str]:
        if name not in self.stands:
            return False, f"Стенд '{name}' не найден"
        if not self.stands[name].connected:
            return False, "Нет подключения"

        info       = self.stands[name]
        local_dir  = local_dir or os.getcwd()
        mpo_path   = os.path.join(local_dir, "mpo")
        remote_cvs = info.folders.get("cvs", "/home/pkrv/CVS")
        remote_mpo = f"{remote_cvs}/mpo"
        lines      = [f"=== Деплой на {name} ===", ""]

        # 1. Локальный файл
        lines.append("[1/4] Проверка локального файла mpo...")
        if not os.path.exists(mpo_path):
            lines.append("  ✗ Файл mpo не найден")
            return False, "\n".join(lines)
        size_kb = os.path.getsize(mpo_path) // 1024
        lines.append(f"  ✓ Найден: {mpo_path}  ({size_kb} КБ)")

        # 2. Backup старого файла на стенде
        lines.append("[2/4] Резервная копия старого mpo...")
        ok, _, _ = self.execute(name,
            f"test -f {remote_mpo} && cp {remote_mpo} {remote_mpo}.bak || true")
        lines.append("  ✓ Backup создан (если был)")

        # 3. SFTP-копирование
        lines.append("[3/4] Копирование через SFTP...")
        try:
            sftp = info.ssh_client.open_sftp()
            sftp.put(mpo_path, remote_mpo)
            sftp.close()
            lines.append(f"  ✓ Скопирован → {remote_mpo}")
        except Exception as e:
            lines.append(f"  ✗ Ошибка SFTP: {e}")
            return False, "\n".join(lines)

        # 4. Права + проверка
        lines.append("[4/4] Права и проверка...")
        ok, out, _ = self.execute(name, f"chmod +x {remote_mpo} && sync && ls -la {remote_mpo}")
        if ok and out.strip():
            lines.append(f"  ✓ {out.strip()}")
        else:
            lines.append("  ! Проверка не прошла")

        lines += ["", "=== ДЕПЛОЙ ЗАВЕРШЁН ==="]
        return True, "\n".join(lines)

    # ── Диагностика ───────────────────────────────────────

    def diagnose_connection(self, name: str) -> str:
        if name not in self.stands:
            return f"Стенд '{name}' не найден"
        info  = self.stands[name]
        lines = [
            f"=== Диагностика {name} ===",
            f"Адрес:    {info.ip}:{info.port}",
            f"Пользователь: {info.username}",
            f"Время:    {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Paramiko: {'✓ установлен' if HAS_PARAMIKO else '✗ не установлен'}",
            "",
        ]

        # Ping
        lines.append("── Сеть ──")
        try:
            param = "-n 1 -w 1000" if os.name == "nt" else "-c 1 -W 2"
            r = subprocess.run(f"ping {param} {info.ip}", shell=True,
                               capture_output=True, text=True, timeout=5)
            lines.append(f"  Ping:   {'OK ✓' if r.returncode == 0 else 'FAIL ✗'}")
        except Exception:
            lines.append("  Ping:   TIMEOUT")

        open_ = self._check_port(info.ip, info.port, timeout=2)
        lines.append(f"  Port {info.port}: {'OPEN ✓' if open_ else 'CLOSED ✗'}")

        # SSH
        lines += ["", "── SSH ──"]
        if not HAS_PARAMIKO:
            lines.append("  paramiko не установлен")
        elif not open_:
            lines.append("  Порт закрыт — SSH невозможен")
        else:
            for attempt, label in enumerate(["modern", "legacy"]):
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    kwargs = dict(hostname=info.ip, port=info.port,
                                  username=info.username, password=info.password,
                                  timeout=5, allow_agent=False, look_for_keys=False,
                                  banner_timeout=15, auth_timeout=10)
                    if attempt == 1:
                        kwargs["disabled_algorithms"] = {}
                    ssh.connect(**kwargs)
                    _, so, _ = ssh.exec_command("uname -a", timeout=5)
                    uname = so.read().decode(errors="ignore").strip()
                    ssh.close()
                    lines.append(f"  Подключение ({label}): OK ✓")
                    lines.append(f"  Система: {uname}")
                    break
                except AuthenticationException:
                    lines.append(f"  ({label}) ОШИБКА АВТОРИЗАЦИИ — неверный пароль")
                    break
                except SSHException as e:
                    err = str(e)
                    lines.append(f"  ({label}) SSH ошибка: {err[:100]}")
                    if attempt == 0 and any(kw in err.lower() for kw in
                            ["kex", "cipher", "mac", "algorithm", "incompatible"]):
                        lines.append("  → Пробую legacy-алгоритмы...")
                        continue
                    break
                except Exception as e:
                    lines.append(f"  ({label}) Ошибка: {str(e)[:100]}")
                    break

        lines += ["", "=== ГОТОВО ==="]
        return "\n".join(lines)

    # ── Утилиты ───────────────────────────────────────────

    def get_all_info(self) -> Dict[str, dict]:
        return {n: s.to_dict() for n, s in self.stands.items()}

    def get_stand(self, name: str) -> Optional[StandInfo]:
        return self.stands.get(name)
