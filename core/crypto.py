#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Шифрование паролей стендов через Fernet (AES-128-CBC + HMAC-SHA256).

Ключ хранится в .bench_key рядом с config.yaml (600 permissions).
Зашифрованные значения имеют префикс ENC: в config.yaml.

Использование:
    python -m core.crypto --init          # зашифровать все plain пароли в config.yaml
    python -m core.crypto --encrypt zxcv  # вывести токен для ручной вставки
    python -m core.crypto --check         # проверить расшифровку всех стендов
"""

import os
import sys
import argparse

try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

KEY_FILENAME = ".bench_key"


# ── Управление ключом ─────────────────────────────────────

def _key_path(base_dir: str = None) -> str:
    d = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(d, KEY_FILENAME)


def generate_key(base_dir: str = None) -> bytes:
    """Сгенерировать новый ключ и сохранить в .bench_key."""
    if not HAS_CRYPTO:
        raise RuntimeError("pip install cryptography")
    key = Fernet.generate_key()
    path = _key_path(base_dir)
    with open(path, "wb") as f:
        f.write(key)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return key


def load_key(base_dir: str = None) -> bytes:
    """Загрузить ключ; если нет файла — создать автоматически."""
    path = _key_path(base_dir)
    if not os.path.exists(path):
        return generate_key(base_dir)
    with open(path, "rb") as f:
        return f.read().strip()


# ── Шифрование / расшифровка ──────────────────────────────

def encrypt_password(plain: str, base_dir: str = None) -> str:
    """Вернуть строку вида  ENC:<fernet-token>"""
    if not HAS_CRYPTO:
        return plain          # graceful fallback — хранить открытым текстом
    f = Fernet(load_key(base_dir))
    token = f.encrypt(plain.encode("utf-8"))
    return "ENC:" + token.decode("ascii")


def decrypt_password(value: str, base_dir: str = None) -> str:
    """
    Расшифровать пароль.
    Значение без префикса ENC: возвращается как есть (обратная совместимость).
    """
    if not value:
        return ""
    if not value.startswith("ENC:"):
        return value          # plain-text — вернуть как есть
    if not HAS_CRYPTO:
        raise RuntimeError(
            "Пароль зашифрован, но cryptography не установлена.\n"
            "pip install cryptography"
        )
    try:
        f = Fernet(load_key(base_dir))
        return f.decrypt(value[4:].encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise ValueError(
            "Не удалось расшифровать пароль — ключ .bench_key изменён или повреждён.\n"
            "Запустите:  python -m core.crypto --init"
        )


def is_encrypted(value: str) -> bool:
    return isinstance(value, str) and value.startswith("ENC:")


# ── CLI ───────────────────────────────────────────────────

def _cmd_init(cfg_path: str):
    import yaml
    base_dir = os.path.dirname(os.path.abspath(cfg_path))
    if not os.path.exists(cfg_path):
        print(f"[!] Не найден: {cfg_path}")
        sys.exit(1)

    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    changed = 0
    for stand in cfg.get("stands", []):
        pwd = stand.get("password", "")
        if pwd and not is_encrypted(pwd):
            stand["password"] = encrypt_password(pwd, base_dir)
            changed += 1
            print(f"  ✓  {stand['name']}: пароль зашифрован")

    if changed:
        with open(cfg_path, "w", encoding="utf-8") as fh:
            yaml.dump(cfg, fh, allow_unicode=True, sort_keys=False)
        print(f"\n  Сохранено: {cfg_path}")
        print(f"  Ключ:      {_key_path(base_dir)}")
        print("\n  ⚠  Добавьте .bench_key в .gitignore — не коммитьте ключ!")
    else:
        print("  Нет паролей для шифрования (уже зашифрованы или пусты).")


def _cmd_encrypt(plain: str, base_dir: str = None):
    print(f"  Токен: {encrypt_password(plain, base_dir)}")


def _cmd_check(cfg_path: str):
    import yaml
    base_dir = os.path.dirname(os.path.abspath(cfg_path))
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    for stand in cfg.get("stands", []):
        name = stand["name"]
        pwd  = stand.get("password", "")
        try:
            dec = decrypt_password(pwd, base_dir)
            status = f"✓ OK  (длина {len(dec)})" if dec else "— пусто"
        except Exception as e:
            status = f"✗ ОШИБКА: {e}"
        print(f"  {name:12}: {status}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Bench Manager — управление паролями")
    p.add_argument("--init",    action="store_true", help="Зашифровать plain пароли в config.yaml")
    p.add_argument("--encrypt", metavar="PASS",      help="Зашифровать строку и вывести токен")
    p.add_argument("--check",   action="store_true", help="Проверить расшифровку всех паролей")
    p.add_argument("--config",  default="config.yaml")
    args = p.parse_args()

    if args.init:
        _cmd_init(args.config)
    elif args.encrypt:
        _cmd_encrypt(args.encrypt)
    elif args.check:
        _cmd_check(args.config)
    else:
        p.print_help()
