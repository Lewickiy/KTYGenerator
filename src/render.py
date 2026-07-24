"""
Модуль рендеринга КТЯ.

Создаёт PNG-изображения модели с нейтральным фоном и освещением.
"""

from __future__ import annotations

import os
from typing import Any

import bpy
import mathutils


def render_model(
    obj: bpy.types.Object,
    output_dir: str = "renders",
    base_name: str | None = None,
    resolution: tuple[int, int] = (1920, 1080),
    **kwargs,
) -> str:
    """
    Рендерит изображение КТЯ и сохраняет в PNG.

    Parameters
    ----------
    obj : bpy.types.Object
        Объект для рендеринга.
    output_dir : str
        Директория для сохранения.
    base_name : str | None
        Имя файла (без расширения).
        Если None, генерируется автоматически.
    resolution : tuple[int, int]
        Разрешение (ширина, высота).
    **kwargs : Any
        Дополнительные параметры (quality, state и др.).

    Returns
    -------
    str
        Путь к сохранённому PNG-файлу.
    """
    # Создаём директорию
    os.makedirs(output_dir, exist_ok=True)

    # Имя файла
    if base_name is None:
        quality = kwargs.get("quality", "medium")
        state = kwargs.get("state", "closed")
        base_name = f"KTY_{quality}_{state}"

    filepath = os.path.join(output_dir, f"{base_name}.png")

    # Настраиваем сцену для рендера
    _setup_render_scene(obj, resolution)

    # Настройки рендера
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = filepath
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100

    # Выполняем рендер
    print(f"[RENDER] Рендеринг {filepath}...")
    bpy.ops.render.render(write_still=True)

    print(f"[RENDER] Сохранено: {filepath}")
    return filepath


def _setup_render_scene(
    obj: bpy.types.Object,
    resolution: tuple[int, int],
) -> None:
    """
    Настраивает сцену для рендеринга:
    - Камера
    - Освещение
    - Фон
    """
    scene = bpy.context.scene

    # Выбираем рендер-движок
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.eevee.use_taa_reprojection = True

    # Цвет фона
    scene.world = _create_world_background()

    # --- Настройка камеры ---
    cam = scene.camera
    if cam is None:
        cam_data = bpy.data.cameras.new(name="Render_Camera")
        cam = bpy.data.objects.new("Render_Camera", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam

    # Автопозиционирование камеры
    _position_camera(obj, cam, resolution)

    # --- Настройка освещения ---
    _setup_lights(obj)


def _create_world_background() -> bpy.types.World:
    """Создаёт нейтральный фон."""
    world = bpy.data.worlds.new(name="Render_World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.9, 0.9, 0.9, 1.0)
        bg.inputs["Strength"].default_value = 1.0
    return world


def _position_camera(
    obj: bpy.types.Object,
    cam: bpy.types.Object,
    resolution: tuple[int, int],
) -> None:
    """Позиционирует камеру для оптимального обзора."""
    dims = obj.dimensions
    max_dim = max(dims)

    # Расстояние камеры
    dist = max_dim * 2.5

    # Изометрический ракурс
    cam.location = (
        dist * 0.8,
        -dist * 0.8,
        dist * 0.5,
    )

    # Направляем камеру на центр объекта
    look_at = mathutils.Vector((
        dims.x / 2.0,
        dims.y / 2.0,
        dims.z / 2.0,
    ))

    direction = look_at - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _setup_lights(obj: bpy.types.Object) -> None:
    """Настраивает освещение сцены."""
    dims = obj.dimensions
    max_dim = max(dims)
    dist = max_dim * 2.0

    # Ключевой свет
    key_light_data = bpy.data.lights.new(name="Key_Light", type="AREA")
    key_light = bpy.data.objects.new("Key_Light", key_light_data)
    bpy.context.collection.objects.link(key_light)
    key_light.location = (dist, -dist, dist * 0.8)
    key_light_data.energy = 300.0
    key_light_data.size = 2.0

    # Заполняющий свет
    fill_light_data = bpy.data.lights.new(name="Fill_Light", type="AREA")
    fill_light = bpy.data.objects.new("Fill_Light", fill_light_data)
    bpy.context.collection.objects.link(fill_light)
    fill_light.location = (-dist * 0.5, dist * 0.5, dist * 0.3)
    fill_light_data.energy = 150.0
    fill_light_data.size = 2.0

    # Фоновый свет
    rim_light_data = bpy.data.lights.new(name="Rim_Light", type="SUN")
    rim_light = bpy.data.objects.new("Rim_Light", rim_light_data)
    bpy.context.collection.objects.link(rim_light)
    rim_light.location = (-dist, dist * 0.5, dist)
    rim_light_data.energy = 0.5
