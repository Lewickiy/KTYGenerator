from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except ImportError:  # Blender is optional for metadata-only validation.
    bpy = None
    Vector = None


@dataclass(frozen=True)
class KTYConfig:
    QUALITIES = ("ultra-low", "low", "medium", "high", "ultra-high")
    STATES = ("closed", "open", "damaged")

    size: tuple[float, float, float] = (600.0, 400.0, 400.0)
    quality: str = "high"
    state: str = "closed"
    lid_angle: float | None = None
    damage_level: float = 0.65
    empty_weight: float = 0.7
    seed: int = 42
    instance_index: int = 0
    export: bool = True
    render: bool = True


class KTY:
    """Procedural cardboard box generator with readable open and damaged states."""

    def __init__(self, size: tuple[float, float, float] | None = None, quality: str | None = None,
                 state: str | None = None, config: KTYConfig | None = None) -> None:
        if config is None:
            config = KTYConfig(size=size or KTYConfig.size, quality=quality or "high", state=state or "closed")
        self.config = config
        self.objects: list[Any] = []
        self.rng = random.Random(config.seed)

    def generate(self) -> "KTY":
        if bpy is None:
            return self
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
        self._materials()
        if self.config.quality == "ultra-low":
            self._cube_shell("KTY_ultra_low_shell")
        else:
            self._panel_box()
        self._add_scene()
        return self

    def export(self) -> "KTY":
        stem = f"KTY_{self.config.quality}_{self.config.state}_{self.config.instance_index:04d}"
        Path("exports").mkdir(exist_ok=True)
        Path("renders").mkdir(exist_ok=True)
        self._write_metadata(Path("exports") / f"{stem}.json")
        if bpy is not None and self.config.export:
            bpy.ops.wm.save_as_mainfile(filepath=str(Path("exports") / f"{stem}.blend"))
        if bpy is not None and self.config.render:
            bpy.context.scene.render.filepath = str(Path("renders") / f"{stem}.png")
            bpy.ops.render.render(write_still=True)
        return self

    def _materials(self) -> None:
        def mat(name: str, color: tuple[float, float, float, float], roughness: float) -> Any:
            material = bpy.data.materials.new(name)
            material.use_nodes = True
            bsdf = material.node_tree.nodes.get("Principled BSDF")
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = 0
            return material

        self.card = mat("corrugated_cardboard_outer", (0.55, 0.34, 0.16, 1), 0.88)
        self.inner = mat("lighter_raw_cardboard_inner", (0.72, 0.52, 0.28, 1), 0.93)
        self.edge = mat("dark_exposed_corrugation_and_tears", (0.23, 0.14, 0.07, 1), 0.96)

    def _cube_shell(self, name: str) -> None:
        l, w, h = (v / 1000 for v in self.config.size)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = (l, w, h)
        obj.data.materials.append(self.card)
        self.objects.append(obj)

    def _panel_box(self) -> None:
        l, w, h = (v / 1000 for v in self.config.size)
        t = 0.012 if self.config.quality in {"high", "ultra-high"} else 0.008
        self._panel("bottom_panel", (0, 0, t / 2), (l, w, t), self.card)
        self._panel("front_wall", (0, -w / 2, h / 2), (l, t, h), self.card)
        self._panel("back_wall", (0, w / 2, h / 2), (l, t, h), self.card)
        self._panel("left_wall", (-l / 2, 0, h / 2), (t, w, h), self.card)
        self._panel("right_wall", (l / 2, 0, h / 2), (t, w, h), self.card)
        self._flaps(l, w, h, t)
        if self.config.state == "damaged":
            self._damage(l, w, h, t)
        if self.config.quality in {"medium", "high", "ultra-high"}:
            self._creases(l, w, h)

    def _panel(self, name: str, loc: tuple[float, float, float], scale: tuple[float, float, float],
               material: Any) -> Any:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = scale
        obj.data.materials.append(material)
        bevel = obj.modifiers.new("slightly_soft_cardboard_edges", "BEVEL")
        bevel.width = min(scale) * 0.25
        bevel.segments = 2
        obj.modifiers.new("weighted_realistic_normals", "WEIGHTED_NORMAL")
        self.objects.append(obj)
        return obj

    def _flaps(self, l: float, w: float, h: float, t: float) -> None:
        state = self.config.state

        angle = (
            self.config.lid_angle
            if self.config.lid_angle is not None
            else (115 if state == "open" else 0)
        )

        if state == "damaged":
            angle = 38 + 35 * self.config.damage_level

        # Размеры клапанов как у реальной четырёхклапанной КТЯ
        #
        # Длинные клапаны:
        # закрывают половину ширины коробки
        #
        # Малые клапаны:
        # короче, чтобы не замыкаться друг с другом
        long_flap_depth = w * 0.5
        short_flap_depth = l * 0.33

        flap_defs = [
            # name,
            # hinge position,
            # local center relative to hinge,
            # dimensions,
            # rotation axis,
            # direction

            (
                "front_flap",
                (0, -w / 2, h),
                (0, long_flap_depth / 2, 0),
                (l, long_flap_depth, t),
                "X",
                -1,
            ),

            (
                "back_flap",
                (0, w / 2, h),
                (0, -long_flap_depth / 2, 0),
                (l, long_flap_depth, t),
                "X",
                1,
            ),

            (
                "left_flap",
                (-l / 2, 0, h),
                (short_flap_depth / 2, 0, 0),
                (short_flap_depth, w, t),
                "Y",
                1,
            ),

            (
                "right_flap",
                (l / 2, 0, h),
                (-short_flap_depth / 2, 0, 0),
                (short_flap_depth, w, t),
                "Y",
                -1,
            ),
        ]

        for name, hinge_loc, local_loc, scale, axis, direction in flap_defs:

            # Шарнир на линии сгиба
            hinge = bpy.data.objects.new(
                f"{name}_hinge",
                None
            )

            bpy.context.collection.objects.link(hinge)

            hinge.location = hinge_loc

            # Создание клапана относительно шарнира
            obj = self._panel(
                f"{name}_{state}",
                (0, 0, 0),
                scale,
                self.inner if angle else self.card
            )

            obj.parent = hinge

            # Смещение от линии сгиба
            obj.location = local_loc

            # Открытие
            rotation = math.radians(direction * angle)

            if axis == "X":
                hinge.rotation_euler[0] = rotation
            else:
                hinge.rotation_euler[1] = rotation

    def _damage(self, l: float, w: float, h: float, t: float) -> None:
        d = self.config.damage_level
        for obj in self.objects:
            if "wall" in obj.name or "flap" in obj.name:
                obj.rotation_euler[2] += self.rng.uniform(-0.09, 0.09) * d
                obj.location.z += self.rng.uniform(-0.035, 0.01) * d
        for i, (x, y) in enumerate([(l / 2, w / 2), (-l / 2, w / 2), (l / 2, -w / 2)]):
            dent = self._panel(f"crushed_corner_dent_{i}", (x * 0.96, y * 0.96, h * (0.72 + i * 0.08)),
                               (0.09 * d, 0.035, 0.16 * d), self.edge)
            dent.rotation_euler = (self.rng.uniform(-0.5, 0.5), self.rng.uniform(-0.7, 0.7),
                                   self.rng.uniform(-0.8, 0.8))
        for i in range(5):
            tear = self._panel(f"jagged_dark_tear_{i}",
                               (self.rng.uniform(-l * .35, l * .35), -w / 2 - .009, self.rng.uniform(h * .35, h * .95)),
                               (0.012, 0.006, 0.08 * d), self.edge)
            tear.rotation_euler[2] = self.rng.uniform(-0.7, 0.7)

    def _creases(self, l: float, w: float, h: float) -> None:
        for i, z in enumerate([h * .25, h * .5, h * .75]):
            self._panel(f"horizontal_fold_crease_{i}", (0, -w / 2 - .007, z), (l * .92, .004, .006), self.edge)
        for i, x in enumerate([-l * .25, l * .25]):
            self._panel(f"vertical_manufacturing_seam_{i}", (x, w / 2 + .007, h / 2), (.006, .004, h * .82), self.edge)

    def _add_scene(self) -> None:
        # Освещение
        bpy.ops.object.light_add(type="AREA", location=(0, -2.5, 2.5))
        light = bpy.context.object
        light.name = "large_softbox_reflections_on_cardboard"
        light.data.energy = 420
        light.data.size = 4

        # Получаем общий центр всех объектов
        min_corner = Vector((float("inf"), float("inf"), float("inf")))
        max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))

        for obj in self.objects:
            if obj.type != "MESH":
                continue

            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ Vector(corner)

                min_corner = Vector((
                    min(min_corner.x, world_corner.x),
                    min(min_corner.y, world_corner.y),
                    min(min_corner.z, world_corner.z),
                ))

                max_corner = Vector((
                    max(max_corner.x, world_corner.x),
                    max(max_corner.y, world_corner.y),
                    max(max_corner.z, world_corner.z),
                ))

        center = (min_corner + max_corner) / 2
        size = max_corner - min_corner

        # Диагональ объекта
        radius = size.length

        # Камера на изометрическом ракурсе
        camera_distance = radius * 2.4

        camera_location = center + Vector((
            camera_distance * 0.8,
            -camera_distance * 0.9,
            camera_distance * 0.65,
        ))

        bpy.ops.object.camera_add(
            location=camera_location
        )

        camera = bpy.context.object
        camera.name = "auto_centered_product_camera"

        # Наводим камеру на объект
        direction = center - camera.location
        camera.rotation_euler = direction.to_track_quat(
            "-Z",
            "Y"
        ).to_euler()

        camera.data.lens = 55

        bpy.context.scene.camera = camera

        # Настройки рендера
        bpy.context.scene.render.resolution_x = 1400
        bpy.context.scene.render.resolution_y = 1000

    def _write_metadata(self, path: Path) -> None:
        l, w, h = self.config.size
        data = {"id": f"KTY_{self.config.instance_index:06d}", "type": "CARTON_BOX",
                "dimensions": {"x": l, "y": w, "z": h}, "emptyWeight": self.config.empty_weight,
                "state": self.config.state, "quality": self.config.quality, "content": "external",
                "visualStateNotes": self._visual_notes()}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _visual_notes(self) -> list[str]:
        if self.config.state == "open":
            return ["four top flaps rotated outward", "lighter inner cardboard is visible",
                    "open rim exposes box volume"]
        if self.config.state == "damaged":
            return ["flaps sag irregularly", "corners include dark crushed dents",
                    "front face includes jagged tear strips"]
        return ["top flaps lie flat in transport-closed position"]
