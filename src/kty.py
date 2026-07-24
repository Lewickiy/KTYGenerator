"""
Главный класс KTY — публичное API для генерации коробки.

Обеспечивает единый интерфейс для создания, настройки,
экспорта и рендеринга КТЯ.
"""

from __future__ import annotations

import os
import random
from typing import Any

import bpy

from .cli import parse_size
from .config import DEFAULT_CONFIG, load_config, merge_with_cli
from .export import export_model, setup_scene_for_export
from .geometry import generate_box
from .lod import get_lod_params
from .materials import create_cardboard_material
from .render import render_model


class KTY:
    """
    Процедурный генератор картонного тарного ящика (КТЯ).

    Пример использования:
    ```python
    from kty_generator import KTY

    box = KTY(
        size=(600, 400, 400),
        quality="high",
        state="closed"
    )
    box.generate()
    box.export()
    ```

    Parameters
    ----------
    size : tuple[float, float, float] | None
        Размеры коробки (длина, ширина, высота) в мм.
    quality : str
        Уровень детализации (ultra-low, low, medium, high, ultra-high).
    state : str
        Состояние коробки (closed, open, damaged).
    config : str | None
        Путь к конфигурационному YAML-файлу.
    seed : int | None
        Seed для повторяемости.
    cli_args : dict[str, Any] | None
        Аргументы CLI (для интеграции с main.py).
    """

    def __init__(
        self,
        size: tuple[float, float, float] | None = None,
        quality: str = "medium",
        state: str = "closed",
        config: str | None = None,
        seed: int | None = None,
        cli_args: dict[str, Any] | None = None,
    ):
        # Исходная конфигурация — по умолчанию
        self.config = dict(DEFAULT_CONFIG)

        # Если есть CLI-аргументы — применяем их
        if cli_args is not None:
            self.config = merge_with_cli(self.config, cli_args)

        # Если есть файл конфигурации — загружаем
        if config is not None:
            file_config = load_config(config)
            self.config = merge_with_cli(file_config, cli_args or {})

        # Размер
        if size is not None:
            self.length, self.width, self.height = size
        else:
            box_cfg = self.config.get("box", {})
            self.length = box_cfg.get("length", 600.0)
            self.width = box_cfg.get("width", 400.0)
            self.height = box_cfg.get("height", 400.0)

        # Качество
        state_cfg = self.config.get("state", {})
        lod_cfg = self.config.get("lod", {})

        self.quality = quality if quality else lod_cfg.get("quality", "medium")
        self.state = state if state else state_cfg.get("type", "closed")

        # Seed
        if seed is not None:
            self.seed = seed
        else:
            self.seed = self.config.get("seed")

        # Настройки экспорта
        export_cfg = self.config.get("export", {})
        self.export_enabled = export_cfg.get("enabled", True)
        self.export_formats = {
            "blend": export_cfg.get("blend", True),
            "obj": export_cfg.get("obj", True),
            "fbx": export_cfg.get("fbx", False),
            "glb": export_cfg.get("glb", False),
        }

        # Настройки рендера
        render_cfg = self.config.get("render", {})
        self.render_enabled = render_cfg.get("enabled", True)

        # Внутренние атрибуты
        self._obj: bpy.types.Object | None = None
        self._material: bpy.types.Material | None = None
        self._metadata: dict[str, Any] | None = None

        # Масса пустого КТЯ (расчётная)
        self.empty_weight = self._calculate_empty_weight()

    # ---------------------------------------------------------------
    #  Публичные методы
    # ---------------------------------------------------------------

    def generate(self) -> bpy.types.Object:
        """
        Генерирует модель КТЯ и применяет материал.

        Returns
        -------
        bpy.types.Object
            Созданный объект.
        """
        # Проверяем и сбрасываем random seed
        if self.seed is not None:
            random.seed(self.seed)

        # Генерируем геометрию
        self._obj = generate_box(
            length_mm=self.length,
            width_mm=self.width,
            height_mm=self.height,
            quality=self.quality,
            state_name=self.state,
            seed=self.seed,
        )

        # Создаём и применяем материал
        lod_params = get_lod_params(self.quality)
        self._material = create_cardboard_material(
            quality=self.quality,
            lod=lod_params,
        )

        if self._obj.data.materials:
            self._obj.data.materials[0] = self._material
        else:
            self._obj.data.materials.append(self._material)

        # Настраиваем сцену
        setup_scene_for_export(self._obj)

        print(f"[KTY] Сгенерирована коробка: {self._obj.name}")
        print(f"      Размер: {self.length}x{self.width}x{self.height} мм")
        print(f"      Качество: {self.quality}")
        print(f"      Состояние: {self.state}")

        return self._obj

    def export(self, output_dir: str = "exports") -> dict[str, str]:
        """
        Экспортирует модель в файлы.

        Parameters
        ----------
        output_dir : str
            Директория для экспорта.

        Returns
        -------
        dict[str, str]
            Словарь {формат: путь_к_файлу}.

        Raises
        ------
        RuntimeError
            Если модель не была сгенерирована.
        """
        if self._obj is None:
            raise RuntimeError(
                "Сначала вызовите generate() для создания модели."
            )

        base_name = f"KTY_{self.quality}_{self.state}"

        result = export_model(
            obj=self._obj,
            output_dir=output_dir,
            base_name=base_name,
            export_formats=self.export_formats,
            quality=self.quality,
            state=self.state,
            empty_weight=self.empty_weight,
        )

        print(f"[KTY] Экспорт завершён в '{output_dir}':")
        for fmt, path in result.items():
            print(f"      [{fmt}] {os.path.basename(path)}")

        return result

    def render(
        self,
        output_dir: str = "renders",
        resolution: tuple[int, int] = (1920, 1080),
    ) -> str:
        """
        Рендерит изображение КТЯ.

        Parameters
        ----------
        output_dir : str
            Директория для сохранения.
        resolution : tuple[int, int]
            Разрешение (ширина, высота).

        Returns
        -------
        str
            Путь к PNG-файлу.

        Raises
        ------
        RuntimeError
            Если модель не была сгенерирована.
        """
        if self._obj is None:
            raise RuntimeError(
                "Сначала вызовите generate() для создания модели."
            )

        base_name = f"KTY_{self.quality}_{self.state}"

        result = render_model(
            obj=self._obj,
            output_dir=output_dir,
            base_name=base_name,
            resolution=resolution,
            quality=self.quality,
            state=self.state,
        )

        print(f"[KTY] Рендер сохранён: {result}")
        return result

    # ---------------------------------------------------------------
    #  Внутренние методы
    # ---------------------------------------------------------------

    def _calculate_empty_weight(self) -> float:
        """
        Рассчитывает массу пустой коробки на основе её размеров.

        Использует удельную плотность картона (~0.7 кг/м²)
        и площадь поверхности коробки.

        Returns
        -------
        float
            Масса в кг.
        """
        # Площадь поверхности коробки (в м²)
        l_m = self.length / 1000.0
        w_m = self.width / 1000.0
        h_m = self.height / 1000.0

        surface_area = 2.0 * (l_m * w_m + l_m * h_m + w_m * h_m)

        # Удельная плотность трёхслойного гофрокартона ~0.7 кг/м²
        # С учётом клапанов и нахлёстов — добавляем 15%
        cardboard_density = 0.7  # кг/м²
        return round(surface_area * cardboard_density * 1.15, 2)

    # ---------------------------------------------------------------
    #  Свойства
    # ---------------------------------------------------------------

    @property
    def object(self) -> bpy.types.Object | None:
        """Blender-объект сгенерированной коробки."""
        return self._obj

    @property
    def material(self) -> bpy.types.Material | None:
        """Материал коробки."""
        return self._material
