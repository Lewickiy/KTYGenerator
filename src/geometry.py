"""
Модуль генерации геометрии КТЯ.

Создаёт процедурную mesh-модель коробки с учётом LOD,
размеров и состояния.
"""

from __future__ import annotations

import math
import random
from typing import Any

import bmesh
import bpy
import mathutils

from .lod import LODParams, get_lod_params
from . import states


# ===================================================================
#  Вспомогательные функции
# ===================================================================


def _ensure_object_name(base_name: str) -> str:
    """Генерирует уникальное имя объекта в сцене."""
    collection = bpy.context.collection
    existing = {o.name for o in collection.objects}
    name = base_name
    counter = 1
    while name in existing:
        name = f"{base_name}_{counter:04d}"
        counter += 1
    return name


def _ensure_mesh_data(name: str) -> bpy.types.Mesh:
    """Создаёт или возвращает существующий mesh с указанным именем."""
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    return bpy.data.meshes.new(name)


def _origin_to_bottom_center(obj: bpy.types.Object) -> None:
    """Перемещает начало координат объекта в центр его нижней грани."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)

    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # Находим нижнюю точку (min Z)
    min_z = min(v.co.z for v in bm.verts)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Смещаем вершины вверх
    for v in obj.data.vertices:
        v.co.z -= min_z

    obj.location = (0.0, 0.0, min_z)


# ===================================================================
#  Основная функция генерации
# ===================================================================


def generate_box(
    length_mm: float = 600.0,
    width_mm: float = 400.0,
    height_mm: float = 400.0,
    quality: str = "medium",
    state_name: str = "closed",
    seed: int | None = None,
    **kwargs: Any,
) -> bpy.types.Object:
    """
    Генерирует 3D-модель КТЯ.

    Входные размеры в миллиметрах, внутри конвертируются в метры
    (Blender использует метры как единицу измерения по умолчанию).

    Parameters
    ----------
    length_mm : float
        Длина коробки (мм).
    width_mm : float
        Ширина коробки (мм).
    height_mm : float
        Высота коробки (мм).
    quality : str
        Уровень детализации.
    state_name : str
        Состояние коробки.
    seed : int | None
        Seed для повторяемости случайных эффектов.
    **kwargs : Any
        Дополнительные параметры.

    Returns
    -------
    bpy.types.Object
        Созданный объект коробки.
    """
    # Конвертируем мм в метры (Blender unit)
    length = length_mm / 1000.0
    width = width_mm / 1000.0
    height = height_mm / 1000.0

    lod = get_lod_params(quality)

    if seed is not None:
        random.seed(seed)

    # Создаём базовую геометрию коробки
    obj = _build_base_box(length, width, height, lod)

    # Добавляем толщину стенок (если нужно)
    if lod.thickness > 0:
        _add_wall_thickness(obj, lod)

    # Добавляем верхние клапаны (если нужно)
    if lod.flaps:
        _add_flaps(obj, length, width, height, lod)

    # Добавляем линии сгиба
    if lod.fold_lines:
        _add_fold_lines(obj)

    # Применяем состояние
    if state_name == "open":
        states.make_open(obj, length, width, height,
                         lid_angle=kwargs.get("lid_angle", 90.0))
    elif state_name == "damaged":
        states.make_damaged(obj, length, width, height,
                            damage_level=kwargs.get("damage_level", 0.3),
                            seed=seed)

    # Микродеформации для ultra-high
    if lod.micro_deformation:
        _apply_micro_deformation(obj, lod, seed)

    # Добавляем UV-развёртку
    if lod.add_uv:
        _add_uv(obj)

    # Перемещаем начало координат в центр основания
    _origin_to_bottom_center(obj)

    return obj


# ===================================================================
#  Приватные строительные функции
# ===================================================================


def _build_base_box(
    length: float,
    width: float,
    height: float,
    lod: LODParams,
) -> bpy.types.Object:
    """
    Строит базовую форму коробки.

    Для ultra-low — просто куб.
    Для остальных — параллелепипед с возможными скруглениями.

    Все размеры в метрах.
    """
    name = _ensure_object_name("KTY")
    mesh = _ensure_mesh_data(f"{name}_mesh")
    mesh.clear_geometry()

    bm = bmesh.new()

    # Создаём box, всегда с началом координат в нижнем левом углу (0,0,0)
    if lod.segments <= 2:
        # Простой параллелепипед — 8 вершин
        for x in (0, length):
            for y in (0, width):
                for z in (0, height):
                    bm.verts.new((x, y, z))
        bm.verts.ensure_lookup_table()
        _create_box_faces(bm, length, width, height)
    else:
        # Параллелепипед со скруглениями
        bmesh.ops.create_cube(bm, size=1.0)
        bm.verts.ensure_lookup_table()

        # Масштабируем до нужных размеров
        scale = mathutils.Matrix.Diagonal(
            mathutils.Vector((length, width, height))
        ).to_4x4()
        bmesh.ops.transform(bm, matrix=scale, verts=bm.verts)

        # Сдвигаем так, чтобы нижний левый угол был в (0,0,0),
        # а не в центре (как создаёт create_cube)
        translate = mathutils.Matrix.Translation(
            (length / 2.0, width / 2.0, height / 2.0)
        )
        bmesh.ops.transform(bm, matrix=translate, verts=bm.verts)

        # Bevel для скругления краёв
        if lod.bevel_width > 0:
            edges = [e for e in bm.edges if e.is_boundary]
            bmesh.ops.bevel(
                bm,
                geom=edges,
                offset=lod.bevel_width / 1000.0,
                segments=lod.segments,
                affect="EDGES",
            )

    # Пересчитываем нормали
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _create_box_faces(bm: bmesh.types.BMesh, l: float, w: float, h: float) -> None:
    """Создаёт грани для простого параллелепипеда по 8 вершинам.

    Порядок вершин (создан в _build_base_box):
      0:(0,0,0)  1:(0,0,h)  2:(0,w,0)  3:(0,w,h)
      4:(l,0,0)  5:(l,0,h)  6:(l,w,0)  7:(l,w,h)
    """
    bm.verts.ensure_lookup_table()
    v = bm.verts

    # Нижняя грань (z=0, нормаль -Z)
    bm.faces.new((v[2], v[6], v[4], v[0]))
    # Верхняя грань (z=h, нормаль +Z)
    bm.faces.new((v[1], v[5], v[7], v[3]))
    # Передняя грань (y=0, нормаль -Y)
    bm.faces.new((v[0], v[4], v[5], v[1]))
    # Задняя грань (y=w, нормаль +Y)
    bm.faces.new((v[2], v[3], v[7], v[6]))
    # Левая грань (x=0, нормаль -X)
    bm.faces.new((v[0], v[1], v[3], v[2]))
    # Правая грань (x=l, нормаль +X)
    bm.faces.new((v[4], v[6], v[7], v[5]))

    bm.faces.ensure_lookup_table()


def _add_wall_thickness(obj: bpy.types.Object, lod: LODParams) -> None:
    """
    Добавляет толщину стенкам с помощью модификатора Solidify.
    """
    mod = obj.modifiers.new(name="Solidify", type="SOLIDIFY")
    # lod.thickness в мм, конвертируем в метры
    mod.thickness = lod.thickness / 1000.0
    mod.offset = -1.0  # Толщина внутрь
    mod.use_even_offset = True
    mod.use_quality_normals = True

    if lod.seams:
        mod.show_in_editmode = True


def _add_flaps(
    obj: bpy.types.Object,
    length: float,
    width: float,
    height: float,
    lod: LODParams,
) -> None:
    """
    Добавляет верхние клапаны коробки.

    Все размеры в метрах.
    """
    bm = bmesh.new()
    bm.from_object(obj, bpy.context.evaluated_depsgraph_get())

    t = lod.thickness / 1000.0
    eps = 0.001

    # Пара клапанов по длинной стороне (Y)
    for side in (-1, 1):
        cx = length / 2.0
        cy = width / 2.0 + side * (width * 0.2)
        cz = height

        hw = length * 0.45

        bm.faces.new([
            bm.verts.new((cx - hw, cy - side * eps, cz)),
            bm.verts.new((cx + hw, cy - side * eps, cz)),
            bm.verts.new((cx + hw, cy - side * eps, cz - t)),
            bm.verts.new((cx - hw, cy - side * eps, cz - t)),
        ])

    # Пара клапанов по короткой стороне (X)
    for side in (-1, 1):
        cx = length / 2.0 + side * (length * 0.2)
        cy = width / 2.0
        cz = height

        hh = width * 0.45

        bm.faces.new([
            bm.verts.new((cx - side * eps, cy - hh, cz)),
            bm.verts.new((cx - side * eps, cy + hh, cz)),
            bm.verts.new((cx - side * eps, cy + hh, cz - t)),
            bm.verts.new((cx - side * eps, cy - hh, cz - t)),
        ])

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def _add_fold_lines(obj: bpy.types.Object) -> None:
    """
    Добавляет линии сгиба на гранях коробки.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    for edge in bm.edges:
        if edge.is_boundary:
            continue
        linked_faces = edge.link_faces
        if len(linked_faces) == 2:
            normal_diff = abs(linked_faces[0].normal.dot(linked_faces[1].normal))
            if normal_diff < 0.1:  # Почти перпендикулярны
                edge.seam = True

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode="OBJECT")


def _apply_micro_deformation(
    obj: bpy.types.Object,
    lod: LODParams,
    seed: int | None = None,
) -> None:
    """
    Применяет микродеформации поверхности для ultra-high LOD.
    """
    if seed is not None:
        noise_seed = seed
    else:
        noise_seed = random.randint(0, 9999)

    tex = bpy.data.textures.new(name="KTY_MicroDeform", type="STUCCI")
    tex.noise_scale = 0.05
    tex.noise_basis = "BLENDER"
    tex.turbulence = 0.01

    mod = obj.modifiers.new(name="MicroDeformation", type="DISPLACE")
    mod.texture = tex
    mod.strength = 0.002  # Очень маленькое смещение
    mod.texture_coords = "UV"


def _add_uv(obj: bpy.types.Object) -> None:
    """Добавляет базовую UV-развёртку smart-project."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
