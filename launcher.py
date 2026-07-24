#!/usr/bin/env python3
"""
launcher.py — Обёртка для запуска генератора КТЯ из командной строки.

Упрощает вызов Blender с правильными параметрами.

Использование:
    python launcher.py --quality high --state closed --size 600x400x400

Все флаги передаются в main.py.
Если Blender не установлен в PATH, укажите путь через переменную BLENDER_PATH.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys


def main() -> None:
    """Запускает main.py через Blender в headless режиме."""
    # Определяем путь к Blender
    blender_path = os.environ.get(
        "BLENDER_PATH",
        shutil.which("blender") or "blender",
    )

    if not blender_path:
        print(
            "ОШИБКА: Blender не найден. Установите Blender или "
            "укажите путь через переменную окружения BLENDER_PATH."
        )
        sys.exit(1)

    # Формируем команду
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "main.py")

    # Аргументы для Blender
    blender_args = [
        blender_path,
        "--background",
        "--python",
        main_script,
        "--",
    ]

    # Передаём все аргументы, кроме имени скрипта
    blender_args.extend(sys.argv[1:])

    # Выводим команду
    cmd_str = " ".join(shlex.quote(a) for a in blender_args)
    print(f"[LAUNCHER] Запуск: {cmd_str}")

    # Запускаем
    try:
        result = subprocess.run(blender_args, check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        print(f"[LAUNCHER] Ошибка выполнения: {e}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(
            f"[LAUNCHER] Blender не найден по пути '{blender_path}'. "
            f"Укажите верный путь в BLENDER_PATH."
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[LAUNCHER] Прервано пользователем.")
        sys.exit(130)


if __name__ == "__main__":
    main()
