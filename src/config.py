"""
Модуль загрузки конфигурационных YAML-файлов.

Позволяет задать все параметры генерации через единый YAML-файл.
"""

from __future__ import annotations

import os
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


DEFAULT_CONFIG: dict[str, Any] = {
    "box": {
        "length": 600.0,
        "width": 400.0,
        "height": 400.0,
    },
    "state": {
        "type": "closed",
        "lid_angle": 90.0,
        "damage_level": 0.0,
    },
    "lod": {
        "quality": "medium",
    },
    "export": {
        "blend": True,
        "obj": True,
        "fbx": False,
        "glb": False,
        "enabled": True,
    },
    "render": {
        "enabled": True,
    },
    "seed": None,
}


def load_config(config_path: str) -> dict[str, Any]:
    """
    Загружает конфигурацию из YAML-файла.
    Если файл не найден или произошла ошибка, возвращает конфигурацию по умолчанию.

    Parameters
    ----------
    config_path : str
        Путь к YAML-файлу.

    Returns
    -------
    dict[str, Any]
        Словарь с конфигурацией.
    """
    if yaml is None:
        print("[WARN] PyYAML не установлен. Используется конфигурация по умолчанию.")
        return dict(DEFAULT_CONFIG)

    if not os.path.exists(config_path):
        print(f"[WARN] Файл конфигурации '{config_path}' не найден. "
              f"Используется конфигурация по умолчанию.")
        return dict(DEFAULT_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)

        if not isinstance(user_config, dict):
            print(f"[WARN] Файл конфигурации '{config_path}' пуст или некорректен.")
            return dict(DEFAULT_CONFIG)

        # Глубокое слияние с конфигурацией по умолчанию
        merged = _deep_merge(dict(DEFAULT_CONFIG), user_config)
        return merged

    except Exception as e:
        print(f"[WARN] Ошибка загрузки конфигурации '{config_path}': {e}")
        return dict(DEFAULT_CONFIG)


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Рекурсивно сливает override в base.

    Parameters
    ----------
    base : dict
        Базовая конфигурация.
    override : dict
        Переопределяющая конфигурация.

    Returns
    -------
    dict
        Результат слияния.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def merge_with_cli(
    config: dict[str, Any],
    cli_args: dict[str, Any],
) -> dict[str, Any]:
    """
    Объединяет конфигурацию из файла с аргументами CLI.
    Аргументы CLI имеют приоритет.

    Parameters
    ----------
    config : dict[str, Any]
        Конфигурация из файла.
    cli_args : dict[str, Any]
        Аргументы из CLI.

    Returns
    -------
    dict[str, Any]
        Итоговая конфигурация.
    """
    result = dict(config)

    if cli_args.get("quality"):
        result.setdefault("lod", {})["quality"] = cli_args["quality"]

    if cli_args.get("state"):
        result.setdefault("state", {})["type"] = cli_args["state"]

    if cli_args.get("size"):
        from .cli import parse_size
        l, w, h = parse_size(cli_args["size"])
        result.setdefault("box", {})["length"] = l
        result.setdefault("box", {})["width"] = w
        result.setdefault("box", {})["height"] = h

    if cli_args.get("no_export"):
        result.setdefault("export", {})["enabled"] = False

    if cli_args.get("no_render"):
        result.setdefault("render", {})["enabled"] = False

    if cli_args.get("seed") is not None:
        result["seed"] = cli_args["seed"]

    return result
