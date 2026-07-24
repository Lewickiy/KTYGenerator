"""
Модуль генерации метаданных КТЯ.

Создаёт JSON-файл с описанием каждой сгенерированной коробки.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import bpy


def generate_metadata(
    obj: bpy.types.Object,
    quality: str = "medium",
    state: str = "closed",
    empty_weight: float = 0.7,
    box_id: str | None = None,
) -> dict[str, Any]:
    """
    Генерирует словарь метаданных для КТЯ.

    Parameters
    ----------
    obj : bpy.types.Object
        Объект коробки.
    quality : str
        Уровень качества LOD.
    state : str
        Состояние коробки.
    empty_weight : float
        Масса пустой коробки (кг).
    box_id : str | None
        Идентификатор коробки. Если None, генерируется автоматически.

    Returns
    -------
    dict[str, Any]
        Словарь с метаданными.
    """
    if box_id is None:
        box_id = _generate_box_id()

    dims = obj.dimensions

    metadata = {
        "id": box_id,
        "type": "CARTON_BOX",
        "dimensions": {
            "x": round(dims.x * 1000, 1),  # Переводим в мм
            "y": round(dims.y * 1000, 1),
            "z": round(dims.z * 1000, 1),
        },
        "emptyWeight": empty_weight,
        "state": state,
        "quality": quality,
        "content": "external",  # Товар генерируется внешним модулем
        "generatedAt": datetime.now().isoformat(),
        "formatVersion": "1.2",
    }

    return metadata


def _generate_box_id() -> str:
    """Генерирует уникальный идентификатор коробки."""
    import random
    import string

    # Формат: KTY_ + 6 цифр
    prefix = "KTY_"
    number = random.randint(1, 999999)
    return f"{prefix}{number:06d}"


def save_metadata(
    metadata: dict[str, Any],
    filepath: str,
    indent: int = 2,
) -> str:
    """
    Сохраняет метаданные в JSON-файл.

    Parameters
    ----------
    metadata : dict[str, Any]
        Словарь с метаданными.
    filepath : str
        Путь к JSON-файлу.
    indent : int
        Отступы в JSON.

    Returns
    -------
    str
        Путь к сохранённому файлу.
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=indent, ensure_ascii=False)

    return filepath


def load_metadata(filepath: str) -> dict[str, Any] | None:
    """
    Загружает метаданные из JSON-файла.

    Parameters
    ----------
    filepath : str
        Путь к JSON-файлу.

    Returns
    -------
    dict[str, Any] | None
        Словарь метаданных или None при ошибке.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Ошибка загрузки метаданных из '{filepath}': {e}")
        return None
