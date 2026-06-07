# Bench Manager v3.0

Инструмент управления тестовыми стендами (ГОЗ, Арктика, C1M, OrangePi) через SSH/SFTP.  
Шифрование паролей · Современный GUI · Сборка через GitHub Actions.

---

## Быстрый старт (скачать готовый exe)

1. Перейдите в **Releases** → скачайте `BenchManager-windows-vX.X.zip`
2. Распакуйте в любую папку
3. Запустите `BenchManager.exe`

> Никаких Python и библиотек устанавливать не нужно — всё включено в exe.

---

## Сборка через GitHub Actions (для разработчиков)

### Автоматическая сборка при теге

```bash
git add .
git commit -m "release v3.1"
git tag v3.1
git push origin main --tags
```

GitHub Actions автоматически:
1. Установит все зависимости (PyQt5, paramiko, cryptography, …)
2. Соберёт `BenchManager.exe` через PyInstaller
3. Упакует в zip
4. Создаст GitHub Release с архивом

### Ручной запуск сборки

В репозитории: **Actions → Build & Release → Run workflow**

---

## Структура проекта

```
bench_manager/
│
├── main.py               # Точка входа
├── config.yaml           # Конфигурация стендов
├── requirements.txt      # Зависимости Python
├── .gitignore            # .bench_key исключён из git
│
├── core/
│   ├── connector.py      # SSH/SFTP (Paramiko + legacy-совместимость)
│   ├── config.py         # Загрузка config.yaml
│   └── crypto.py         # Шифрование паролей (Fernet/AES-128)
│
├── gui/
│   └── main_window.py    # Интерфейс PyQt5
│
├── logger/
│   └── log.py            # Логгер с ротацией
│
├── logs/                 # Файлы логов
├── uploads/              # Загружаемые файлы (mpo и др.)
├── backups/              # Резервные копии CVS
│
└── .github/
    └── workflows/
        └── build.yml     # GitHub Actions — сборка и релиз
```

---

## Шифрование паролей

Пароли стендов хранятся в зашифрованном виде через **Fernet** (AES-128-CBC + HMAC-SHA256).

### Первая настройка

```bash
# Зашифровать все пароли в config.yaml
python main.py --init-crypto

# или через модуль
python -m core.crypto --init

# Проверить что всё расшифровывается правильно
python -m core.crypto --check
```

После этого `config.yaml` будет содержать зашифрованные токены:
```yaml
password: "ENC:gAAAAABq..."   # вместо открытого "zxcv"
```

### Ключ шифрования

- Хранится в файле `.bench_key` рядом с `config.yaml`
- **Никогда не коммитить в git** — он в `.gitignore`
- При потере ключа нужно запустить `--init-crypto` заново (plain-текст из config.yaml)

---

## Запуск из исходников

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить GUI
python main.py

# Консольные режимы
python main.py --check            # список стендов и их статус
python main.py --stand C1M        # подключиться к стенду
python main.py --diagnose ГОЗ     # диагностика SSH-соединения
python main.py --deploy Арктика   # задеплоить mpo
python main.py --info             # проверить зависимости
python main.py --init-crypto      # зашифровать пароли
```

---

## Фикс SSH для старых Linux-стендов

Старые стенды (Ubuntu 16/18, CentOS 7) используют устаревшие SSH-алгоритмы.
Современный paramiko по умолчанию их блокирует.

В `connector.py` реализована автоматическая повторная попытка с legacy-алгоритмами:
- KEX: `diffie-hellman-group14-sha1`, `diffie-hellman-group1-sha1`
- Ciphers: `aes128-cbc`, `3des-cbc`
- MAC: `hmac-sha1`

При ошибке `No matching key exchange method` или `Incompatible ssh peer` коннектор
автоматически повторит подключение с расширенным набором алгоритмов.

---

## Зависимости

| Пакет          | Назначение                              |
|----------------|-----------------------------------------|
| PyQt5          | Графический интерфейс                   |
| paramiko       | SSH / SFTP подключения                  |
| cryptography   | Шифрование паролей (Fernet)             |
| pyyaml         | Чтение config.yaml                      |
| psutil         | Системная информация (опционально)      |
| scp            | SCP-копирование файлов (опционально)    |
| pyinstaller    | Сборка exe (только в GitHub Actions)    |
