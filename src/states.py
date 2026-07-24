"""
Модуль управления состояниями КТЯ.

Поддерживаемые состояния:
  - CLOSED  — закрытая коробка (по умолчанию)
  - OPEN    — открытая коробка с регулируемым углом клапанов
  - DAMAGED — повреждённая коробка с уровнем повреждений
"""

from __future__ import annotations

import math
import random
from typing import Any

import bmesh
import bpy
import mathutils


def make_open(
    obj: bpy.types.Object,
    length: float,
    width: float,
    height: float,
    lid_angle: float = 90.0,
) -> None:
    """
    Переводит коробку в состояние OPEN.

    Разворачивает верхние клапаны на заданный угол.

    Parameters
    ----------
    obj : bpy.types.Object
        Объект коробки.
    length : float
        Длина коробки.
    width : float
        Ширина коробки.
    height : float
        Высота коробки.
    lid_angle : float
        Угол открытия клапанов (0-180 градусов).
    """
    if lid_angle < 0 or lid_angle > 180:
        print(f"[WARN] lid_angle={lid_angle} вне диапазона [0, 180]. "
              f"Используется 90.")
        lid_angle = 90.0

    angle_rad = math.radians(lid_angle)

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # Находим вершины на верхней части коробки (z ≈ height)
    # и разворачиваем их наружу
    top_z = height
    center_x = length / 2.0
    center_y = width / 2.0

    for vert in bm.verts:
        if abs(vert.co.z - top_z) < 0.001:
            # Определяем, к какой стороне относится вершина
            dx = vert.co.x - center_x
            dy = vert.co.y - center_y

            # Разворачиваем наружу по оси, где отклонение максимально
            if abs(dx) > abs(dy):
                # Разворот вдоль оси X
                direction = 1.0 if dx > 0 else -1.0
                # Новое положение: поднимаем и отводим в сторону
                new_x = vert.co.x + direction * math.sin(angle_rad) * height * 0.5
                new_z = top_z + math.cos(angle_rad) * height * 0.5
                vert.co.x = new_x
                vert.co.z = new_z
            else:
                # Разворот вдоль оси Y
                direction = 1.0 if dy > 0 else -1.0
                new_y = vert.co.y + direction * math.sin(angle_rad) * height * 0.5
                new_z = top_z + math.cos(angle_rad) * height * 0.5
                vert.co.y = new_y
                vert.co.z = new_z

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode="OBJECT")


def make_damaged(
    obj: bpy.types.Object,
    length: float,
    width: float,
    height: float,
    damage_level: float = 0.3,
    seed: int | None = None,
) -> None:
    """
    Применяет повреждения к коробке.

    Parameters
    ----------
    obj : bpy.types.Object
        Объект коробки.
    length : float
        Длина коробки.
    width : float
        Ширина коробки.
    height : float
        Высота коробки.
    damage_level : float
        Уровень повреждений (0.0 — нет, 1.0 — максимальный).
    seed : int | None
        Seed для повторяемости.
    """
    if damage_level < 0.0 or damage_level > 1.0:
        print(f"[WARN] damage_level={damage_level} вне диапазона [0, 1]. "
              f"Используется 0.3.")
        damage_level = 0.3

    rng = random.Random(seed)

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")

    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    # 1. Смятие углов
    _crush_corners(bm, length, width, height, damage_level, rng)

    # 2. Деформация стенок
    _deform_walls(bm, length, width, height, damage_level, rng)

    # 3. Разрывы (для high damage)
    if damage_level > 0.5:
        _tear_cardboard(bm, damage_level, rng)

    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode="OBJECT")


def _crush_corners(
    bm: bmesh.types.BMesh,
    length: float,
    width: float,
    height: float,
    damage_level: float,
    rng: random.Random,
) -> None:
    """Сминает углы коробки."""
    corners = [
        (0.0, 0.0, 0.0),
        (length, 0.0, 0.0),
        (0.0, width, 0.0),
        (length, width, 0.0),
        (0.0, 0.0, height),
        (length, 0.0, height),
        (0.0, width, height),
        (length, width, height),
    ]

    crush_distance = damage_level * min(length, width, height) * 0.15

    for corner in corners:
        for vert in bm.verts:
            dx = vert.co.x - corner[0]
            dy = vert.co.y - corner[1]
            dz = vert.co.z - corner[2]
            dist = math.sqrt(dx**2 + dy**2 + dz**2)

            if dist < crush_distance * 2 and rng.random() < damage_level:
                # Сдвигаем вершину к центру угла
                factor = 1.0 - (crush_distance - dist * 0.5) / crush_distance
                factor = max(0.0, min(1.0, factor))
                vert.co.x += (corner[0] - vert.co.x) * factor * 0.3
                vert.co.y += (corner[1] - vert.co.y) * factor * 0.3
                vert.co.z += (corner[2] - vert.co.z) * factor * 0.3


def _deform_walls(
    bm: bmesh.types.BMesh,
    length: float,
    width: float,
    height: float,
    damage_level: float,
    rng: random.Random,
) -> None:
    """Деформирует стенки коробки."""
    deform_strength = damage_level * 0.08 * min(length, width, height)

    for vert in bm.verts:
        # Применяем синусоидальную деформацию
        noise_val = math.sin(vert.co.x * 0.1 + rng.random() * 10) * \
                     math.cos(vert.co.y * 0.1 + rng.random() * 10)
        displacement = noise_val * deform_strength * damage_level

        vert.co.x += displacement * 0.1
        vert.co.y += displacement * 0.1
        vert.co.z += displacement


def _tear_cardboard(
    bm: bmesh.types.BMesh,
    damage_level: float,
    rng: random.Random,
) -> None:
    """Создаёт разрывы картона при высоком уровне повреждений."""
    for edge in bm.edges:
        if rng.random() < damage_level * 0.1:  # 10% рёбер при max damage
            # Раздвигаем вершины ребра
            mid = (edge.verts[0].co + edge.verts[1].co) / 2.0
            for vert in edge.verts:
                direction = (vert.co - mid).normalized()
                vert.co += direction * damage_level * 5.0 * rng.random()
