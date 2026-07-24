"""
Модуль экспорта моделей КТЯ.

Поддерживаемые форматы:
  - .blend (обязательный)
  - .obj
  - .fbx
  - .glb
"""

from __future__ import annotations

import os
from typing import Any

import bpy

from .metadata import generate_metadata, save_metadata


def export_model(
    obj: bpy.types.Object,
    output_dir: str = "exports",
    base_name: str | None = None,
    export_formats: dict[str, bool] | None = None,
    **kwargs: Any,
) -> dict[str, str]:
    """
    Экспортирует модель в указанные форматы.

    Parameters
    ----------
    obj : bpy.types.Object
        Объект для экспорта.
    output_dir : str
        Директория для экспорта.
    base_name : str | None
        Базовое имя файла (без расширения).
        Если None, генерируется автоматически.
    export_formats : dict[str, bool] | None
        Словарь форматов {extension: enabled}.
        По умолчанию: blend=True, obj=True.
    **kwargs : Any
        Дополнительные параметры (quality, state и др.).

    Returns
    -------
    dict[str, str]
        Словарь {формат: путь_к_файлу}.
    """
    if export_formats is None:
        export_formats = {"blend": True, "obj": True}

    # Создаём директорию
    os.makedirs(output_dir, exist_ok=True)

    # Формируем базовое имя
    if base_name is None:
        quality = kwargs.get("quality", "medium")
        state = kwargs.get("state", "closed")
        base_name = f"KTY_{quality}_{state}"

    exported_files: dict[str, str] = {}

    # --- .blend ---
    if export_formats.get("blend", True):
        blend_path = os.path.join(output_dir, f"{base_name}.blend")
        _export_blend(blend_path, obj)
        exported_files["blend"] = blend_path

    # --- .obj ---
    if export_formats.get("obj", True):
        obj_path = os.path.join(output_dir, f"{base_name}.obj")
        _export_obj(obj_path, obj)
        exported_files["obj"] = obj_path

    # --- .fbx ---
    if export_formats.get("fbx", False):
        fbx_path = os.path.join(output_dir, f"{base_name}.fbx")
        _export_fbx(fbx_path, obj)
        exported_files["fbx"] = fbx_path

    # --- .glb ---
    if export_formats.get("glb", False):
        glb_path = os.path.join(output_dir, f"{base_name}.glb")
        _export_glb(glb_path, obj)
        exported_files["glb"] = glb_path

    # Генерируем и сохраняем метаданные
    metadata = generate_metadata(
        obj=obj,
        quality=kwargs.get("quality", "medium"),
        state=kwargs.get("state", "closed"),
        empty_weight=kwargs.get("empty_weight", 0.7),
    )
    metadata_path = os.path.join(output_dir, f"{base_name}.json")
    save_metadata(metadata, metadata_path)
    exported_files["json"] = metadata_path

    return exported_files


def _export_blend(filepath: str, obj: bpy.types.Object) -> None:
    """
    Сохраняет .blend файл с объектом, материалом, камерой и освещением.
    """
    # Выделяем объект
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.wm.save_as_mainfile(filepath=filepath)


def _export_obj(filepath: str, obj: bpy.types.Object) -> None:
    """
    Экспортирует в формат Wavefront OBJ.
    """
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        apply_modifiers=True,
        forward_axis="Y",
        up_axis="Z",
    )


def _export_fbx(filepath: str, obj: bpy.types.Object) -> None:
    """
    Экспортирует в формат FBX.
    """
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            apply_scale_options="FBX_SCALE_UNITS",
            object_types={"MESH"},
            use_mesh_modifiers=True,
            add_leaf_bones=False,
        )
    except Exception as e:
        print(f"[WARN] Ошибка экспорта FBX: {e}")


def _export_glb(filepath: str, obj: bpy.types.Object) -> None:
    """
    Экспортирует в формат glTF Binary (.glb).
    Требует включённого аддона io_scene_gltf2.
    """
    # Проверяем наличие аддона glTF
    gltf_addon = bpy.context.preferences.addons.get("io_scene_gltf2")
    if not gltf_addon:
        print(
            "[WARN] Аддон glTF 2.0 не включён. "
            "Включите его: Edit → Preferences → Add-ons → glTF 2.0"
        )
        return

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    try:
        bpy.ops.export_scene.gltf(
            filepath=filepath,
            use_selection=True,
            export_format="GLB",
            export_draco_mesh_compression_enabled=False,
        )
    except Exception as e:
        print(f"[WARN] Ошибка экспорта GLB: {e}")


def setup_scene_for_export(obj: bpy.types.Object) -> None:
    """
    Настраивает сцену для экспорта:
    - Добавляет камеру
    - Добавляет освещение
    - Настраивает фон
    """
    scene = bpy.context.scene

    # Очищаем сцену
    for o in list(scene.objects):
        if o != obj:
            bpy.data.objects.remove(o, do_unlink=True)

    # --- Камера ---
    cam_data = bpy.data.cameras.new(name="KTY_Camera")
    cam = bpy.data.objects.new("KTY_Camera", cam_data)
    scene.collection.objects.link(cam)

    # Позиционируем камеру
    dims = obj.dimensions
    max_dim = max(dims)
    dist = max_dim * 3.0

    cam.location = (dist * 0.8, -dist * 0.8, dist * 0.6)
    cam.rotation_euler = (60 * 3.14159 / 180, 0, 45 * 3.14159 / 180)

    scene.camera = cam

    # --- Освещение ---
    light_data = bpy.data.lights.new(name="KTY_Light", type="AREA")
    light = bpy.data.objects.new("KTY_Light", light_data)
    scene.collection.objects.link(light)

    light.location = (dist, -dist, dist * 1.5)
    light_data.energy = 200.0
    light_data.size = 5.0

    # Дополнительный заполняющий свет
    fill_light_data = bpy.data.lights.new(name="KTY_FillLight", type="AREA")
    fill_light = bpy.data.objects.new("KTY_FillLight", fill_light_data)
    scene.collection.objects.link(fill_light)

    fill_light.location = (-dist * 0.5, dist * 0.5, dist * 0.3)
    fill_light_data.energy = 100.0
    fill_light_data.size = 3.0
