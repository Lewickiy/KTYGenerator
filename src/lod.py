"""
Модуль управления уровнями детализации (LOD).

Определяет параметры геометрии для каждого уровня качества:
  - ultra-low
  - low
  - medium
  - high
  - ultra-high
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LODParams:
    """
    Параметры геометрии для конкретного уровня LOD.

    Attributes
    ----------
    segments : int
        Количество сегментов по длине/ширине для скруглений.
    thickness : float
        Толщина картона (мм). 0 — означает отсутствие толщины.
    flaps : bool
        Генерировать ли верхние клапаны.
    inner_surface : bool
        Генерировать ли внутреннюю поверхность.
    fold_lines : bool
        Генерировать ли линии сгиба.
    seams : bool
        Генерировать ли технологические швы.
    micro_deformation : bool
        Включать ли микродеформации поверхности.
    damage_detail : bool
        Детализировать ли повреждения.
    subdivisions : int
        Количество подразделений для сабсерф-деформаций.
    polygon_estimate : str
        Оценка полигональности (для документации).
    """
    segments: int = 0
    thickness: float = 0.0
    flaps: bool = False
    inner_surface: bool = False
    fold_lines: bool = False
    seams: bool = False
    micro_deformation: bool = False
    damage_detail: bool = False
    subdivisions: int = 0
    polygon_estimate: str = "6-12"

    # Дополнительные настройки
    bevel_width: float = 0.0
    add_uv: bool = False


# ---------- Словарь конфигураций по уровням ----------

LOD_TABLE: dict[str, LODParams] = {
    "ultra-low": LODParams(
        segments=0,
        thickness=0.0,
        flaps=False,
        inner_surface=False,
        fold_lines=False,
        seams=False,
        micro_deformation=False,
        damage_detail=False,
        subdivisions=0,
        polygon_estimate="6-12",
        bevel_width=0.0,
        add_uv=False,
    ),
    "low": LODParams(
        segments=2,
        thickness=1.0,
        flaps=False,
        inner_surface=False,
        fold_lines=False,
        seams=False,
        micro_deformation=False,
        damage_detail=False,
        subdivisions=0,
        polygon_estimate="50-100",
        bevel_width=0.0,
        add_uv=True,
    ),
    "medium": LODParams(
        segments=4,
        thickness=3.0,
        flaps=True,
        inner_surface=False,
        fold_lines=True,
        seams=True,
        micro_deformation=False,
        damage_detail=False,
        subdivisions=0,
        polygon_estimate="500-1000",
        bevel_width=1.0,
        add_uv=True,
    ),
    "high": LODParams(
        segments=8,
        thickness=3.0,
        flaps=True,
        inner_surface=True,
        fold_lines=True,
        seams=True,
        micro_deformation=False,
        damage_detail=False,
        subdivisions=1,
        polygon_estimate="2000-5000",
        bevel_width=2.0,
        add_uv=True,
    ),
    "ultra-high": LODParams(
        segments=12,
        thickness=3.0,
        flaps=True,
        inner_surface=True,
        fold_lines=True,
        seams=True,
        micro_deformation=True,
        damage_detail=True,
        subdivisions=2,
        polygon_estimate="5000-20000",
        bevel_width=3.0,
        add_uv=True,
    ),
}


def get_lod_params(quality: str) -> LODParams:
    """
    Возвращает параметры геометрии для указанного уровня качества.

    Parameters
    ----------
    quality : str
        Ключ уровня качества (ultra-low, low, medium, high, ultra-high).

    Returns
    -------
    LODParams
        Параметры LOD. Если уровень не найден, возвращается medium.
    """
    if quality in LOD_TABLE:
        return LOD_TABLE[quality]
    print(f"[WARN] Неизвестный уровень качества '{quality}'. "
          f"Используется 'medium'.")
    return LOD_TABLE["medium"]


def validate_quality(quality: str) -> bool:
    """
    Проверяет, является ли указанный уровень качества допустимым.

    Parameters
    ----------
    quality : str
        Проверяемый уровень качества.

    Returns
    -------
    bool
        True если уровень допустим.
    """
    return quality in LOD_TABLE
