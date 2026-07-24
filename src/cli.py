"""
Модуль парсинга аргументов командной строки.

Поддерживает флаги:
  --quality      ultra-low | low | medium | high | ultra-high
  --state        closed | open | damaged
  --size         LxWxH (например 600x400x400)
  --config       путь к YAML-файлу конфигурации
  --no-export    отключение экспорта
  --no-render    отключение рендера
  --seed         seed для повторяемости
  --count        количество коробок для пакетной генерации
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

# ---------- Константы ----------

QUALITY_CHOICES = ("ultra-low", "low", "medium", "high", "ultra-high")
STATE_CHOICES = ("closed", "open", "damaged")


def parse_cli(argv: list[str] | None = None) -> dict[str, Any]:
    """
    Парсит аргументы командной строки.

    Parameters
    ----------
    argv : list[str] | None
        Если None — читает sys.argv.

    Returns
    -------
    dict[str, Any]
        Словарь с распарсенными аргументами.
    """
    if argv is None:
        argv = sys.argv

    # Blender передаёт свои аргументы после --
    # Ищем разделитель
    try:
        separator_index = argv.index("--")
        blender_args = argv[separator_index + 1:]
    except ValueError:
        # Если -- нет, то берём все аргументы после первого
        blender_args = argv[1:] if len(argv) > 1 else []

    parser = _build_parser()
    namespace = parser.parse_args(blender_args)
    return vars(namespace)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Procedural KTY Generator — генерация картонных тарных ящиков.",
        add_help=True,
    )

    # --- Качество / LOD ---
    parser.add_argument(
        "--quality",
        type=str,
        default="medium",
        choices=QUALITY_CHOICES,
        help="Уровень детализации (LOD). По умолчанию: medium.",
    )

    # --- Состояние ---
    parser.add_argument(
        "--state",
        type=str,
        default="closed",
        choices=STATE_CHOICES,
        help="Состояние коробки. По умолчанию: closed.",
    )

    # --- Размер ---
    parser.add_argument(
        "--size",
        type=str,
        default="600x400x400",
        help="Размер коробки в формате LxWxH (мм). По умолчанию: 600x400x400.",
    )

    # --- Конфигурационный файл ---
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Путь к YAML-файлу конфигурации.",
    )

    # --- Отключение экспорта ---
    parser.add_argument(
        "--no-export",
        action="store_true",
        default=False,
        help="Отключить экспорт модели.",
    )

    # --- Отключение рендера ---
    parser.add_argument(
        "--no-render",
        action="store_true",
        default=False,
        help="Отключить рендеринг.",
    )

    # --- Seed ---
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed для повторяемости случайных вариаций.",
    )

    # --- Пакетная генерация ---
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Количество коробок для пакетной генерации. По умолчанию: 1.",
    )

    return parser


def parse_size(size_str: str) -> tuple[float, float, float]:
    """
    Разбирает строку размера "LxWxH" в кортеж чисел.

    Parameters
    ----------
    size_str : str
        Строка вида "600x400x400".

    Returns
    -------
    tuple[float, float, float]
        (length, width, height) в миллиметрах.
    """
    parts = size_str.lower().replace("х", "x").split("x")
    if len(parts) != 3:
        raise ValueError(
            f"Неверный формат размера: '{size_str}'. "
            f"Ожидается формат LxWxH, например 600x400x400."
        )
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        raise ValueError(
            f"Неверные числовые значения в размере: '{size_str}'."
        )
