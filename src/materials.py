"""
Модуль создания материала картона (Corrugated Cardboard).

Создаёт PBR-материал с настройками:
  - Base color: коричневый
  - Roughness: высокий
  - Metallic: 0
  - Нормал-мап текстура гофрокартона (процедурная)
"""

from __future__ import annotations

import bpy
from mathutils import Vector

from .lod import LODParams


def create_cardboard_material(
    quality: str = "medium",
    lod: LODParams | None = None,
) -> bpy.types.Material:
    """
    Создаёт и возвращает материал гофрированного картона.

    Parameters
    ----------
    quality : str
        Уровень качества для определения сложности материала.
    lod : LODParams | None
        Параметры LOD (если уже загружены).

    Returns
    -------
    bpy.types.Material
        Созданный материал.
    """
    mat_name = "KTY_Cardboard"
    existing = bpy.data.materials.get(mat_name)
    if existing:
        bpy.data.materials.remove(existing)

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Очищаем стандартные ноды
    for node in list(nodes):
        nodes.remove(node)

    # --- Основные параметры ---
    # Base Color: коричневый картон
    base_color = (0.52, 0.35, 0.20, 1.0)   # sRGB
    roughness = 0.85
    metallic = 0.0

    # --- Создаём ноды ---
    # Principled BSDF
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled.location = (0, 0)
    principled.inputs["Base Color"].default_value = base_color
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic

    # Output
    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (300, 0)

    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    if quality not in ("ultra-low", "low"):
        _add_texture_detail(mat, nodes, links, principled, quality)

    return mat


def _add_texture_detail(
    mat: bpy.types.Material,
    nodes: bpy.types.Nodes,
    links: bpy.types.NodeLinks,
    principled: bpy.types.Node,
    quality: str,
) -> None:
    """
    Добавляет процедурную текстурную детализацию для материала.

    Создаёт эффект гофрированного картона через ноды текстур.
    """
    # Базовый цвет картона (должен совпадать с create_cardboard_material)
    base_color = (0.52, 0.35, 0.20, 1.0)

    # Координаты текстур
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    tex_coord.location = (-800, 200)

    # Mapping для масштаба
    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-600, 200)
    mapping.inputs["Scale"].default_value = (2.0, 2.0, 2.0)

    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    # Шум для текстуры картона
    noise_tex = nodes.new(type="ShaderNodeTexNoise")
    noise_tex.location = (-400, 300)
    noise_tex.inputs["Scale"].default_value = 50.0
    noise_tex.inputs["Detail"].default_value = 5.0 if quality == "ultra-high" else 2.0
    noise_tex.inputs["Roughness"].default_value = 0.7

    links.new(mapping.outputs["Vector"], noise_tex.inputs["Vector"])

    # Color Ramp для создания полос гофры
    color_ramp = nodes.new(type="ShaderNodeValToRGB")
    color_ramp.location = (-200, 300)
    color_ramp.color_ramp.elements[0].position = 0.4
    color_ramp.color_ramp.elements[0].color = (0.45, 0.30, 0.15, 1.0)
    color_ramp.color_ramp.elements[1].position = 0.6
    color_ramp.color_ramp.elements[1].color = (0.55, 0.38, 0.22, 1.0)

    links.new(noise_tex.outputs["Fac"], color_ramp.inputs["Fac"])

    # Mix для смешивания шумовой текстуры с базовым цветом
    mix = nodes.new(type="ShaderNodeMixRGB")
    mix.location = (0, 300)
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.3
    mix.inputs["Color2"].default_value = base_color

    links.new(color_ramp.outputs["Color"], mix.inputs["Color1"])
    links.new(mix.outputs["Color"], principled.inputs["Base Color"])

    # Bump для рельефа
    if quality in ("high", "ultra-high"):
        bump = nodes.new(type="ShaderNodeBump")
        bump.location = (0, -200)
        bump.inputs["Strength"].default_value = 0.5
        bump.inputs["Distance"].default_value = 0.1

        links.new(noise_tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], principled.inputs["Normal"])
