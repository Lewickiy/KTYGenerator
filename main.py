#!/usr/bin/env python3
"""
main.py — Точка входа для запуска KTY Generator через Blender.

Использование:
    blender --background --python main.py -- --quality high --state closed --size 600x400x400

Полный список параметров:
    --quality      ultra-low | low | medium | high | ultra-high
    --state        closed | open | damaged
    --size         LxWxH (напр. 600x400x400)
    --config       путь к YAML-конфигу
    --no-export    отключить экспорт
    --no-render    отключить рендер
    --seed         seed для повторяемости
    --count        количество коробок (пакетная генерация)
"""

from __future__ import annotations

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli import parse_cli, parse_size
from src.kty import KTY


def main() -> None:
    """Основная функция генерации."""
    # Парсим аргументы
    args = parse_cli()
    quality = args.get("quality", "medium")
    state = args.get("state", "closed")
    size_str = args.get("size", "600x400x400")
    config_path = args.get("config")
    no_export = args.get("no_export", False)
    no_render = args.get("no_render", False)
    seed = args.get("seed")
    count = args.get("count", 1)

    # Парсим размер
    length, width, height = parse_size(size_str)

    print("=" * 60)
    print("  Procedural KTY Generator v1.2")
    print("=" * 60)
    print(f"  Качество:    {quality}")
    print(f"  Состояние:   {state}")
    print(f"  Размер:      {length}x{width}x{height} мм")
    print(f"  Количество:  {count}")
    if seed is not None:
        print(f"  Seed:        {seed}")
    print(f"  Экспорт:     {'да' if not no_export else 'нет'}")
    print(f"  Рендер:      {'да' if not no_render else 'нет'}")
    print("=" * 60)

    if count > 1:
        print(f"\n[INFO] Пакетная генерация: {count} коробок")
        for i in range(1, count + 1):
            print(f"\n--- Коробка {i}/{count} ---")
            _generate_single(
                quality=quality,
                state=state,
                size=(length, width, height),
                config_path=config_path,
                no_export=no_export,
                no_render=no_render,
                seed=seed,
                box_index=i,
            )
    else:
        _generate_single(
            quality=quality,
            state=state,
            size=(length, width, height),
            config_path=config_path,
            no_export=no_export,
            no_render=no_render,
            seed=seed,
        )

    print("\n[KTY] Генерация завершена успешно!")


def _generate_single(
    quality: str,
    state: str,
    size: tuple[float, float, float],
    config_path: str | None = None,
    no_export: bool = False,
    no_render: bool = False,
    seed: int | None = None,
    box_index: int | None = None,
) -> None:
    """Генерирует одну коробку."""
    # Создаём генератор
    box = KTY(
        size=size,
        quality=quality,
        state=state,
        config=config_path,
        seed=seed,
    )

    # Генерируем
    box.generate()

    # Экспортируем
    if not no_export:
        export_dir = "exports"
        if box_index is not None:
            export_dir = f"exports/batch_{box_index:04d}"
        box.export(output_dir=export_dir)

    # Рендерим
    if not no_render:
        render_dir = "renders"
        if box_index is not None:
            render_dir = f"renders/batch_{box_index:04d}"
        box.render(output_dir=render_dir)


if __name__ == "__main__":
    main()
