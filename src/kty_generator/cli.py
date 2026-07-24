from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generator import KTY, KTYConfig


def load_simple_yaml_config(path: Path) -> dict[str, object]:
    """Read the small project YAML shape without adding a runtime dependency."""
    data: dict[str, object] = {}
    section: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not raw_line.startswith(" ") and line.endswith(":"):
            section = line[:-1]
            data.setdefault(section, {})
            continue
        if section and ":" in line:
            key, value = (part.strip() for part in line.split(":", 1))
            target = data.setdefault(section, {})
            if isinstance(target, dict):
                target[key] = value
    return data


def _argv_after_blender_separator() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]


def parse_size(value: str) -> tuple[float, float, float]:
    try:
        length, width, height = (float(part) for part in value.lower().split("x"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size must use LxWxH, for example 600x400x400") from exc
    if min(length, width, height) <= 0:
        raise argparse.ArgumentTypeError("all size dimensions must be positive")
    return length, width, height


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate procedural cardboard KTY boxes in Blender.")
    parser.add_argument("--quality", choices=KTYConfig.QUALITIES, default="high")
    parser.add_argument("--state", choices=KTYConfig.STATES, default="closed")
    parser.add_argument("--size", type=parse_size, default=(600.0, 400.0, 400.0))
    parser.add_argument("--lid-angle", type=float, default=None, help="Open flap angle in degrees for --state open.")
    parser.add_argument("--damage-level", type=float, default=0.65, help="0.0-1.0 damage intensity for --state damaged.")
    parser.add_argument("--empty-weight", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--no-export", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--config", type=Path, help="Optional YAML config; CLI flags override it when provided.")
    return parser


def main() -> None:
    args = build_parser().parse_args(_argv_after_blender_separator())
    file_config = load_simple_yaml_config(args.config) if args.config else {}
    box_config = file_config.get("box", {}) if isinstance(file_config.get("box", {}), dict) else {}
    state_config = file_config.get("state", {}) if isinstance(file_config.get("state", {}), dict) else {}
    lod_config = file_config.get("lod", {}) if isinstance(file_config.get("lod", {}), dict) else {}
    if args.config and args.size == (600.0, 400.0, 400.0):
        args.size = (float(box_config.get("length", 600)), float(box_config.get("width", 400)), float(box_config.get("height", 400)))
    if args.config and args.state == "closed":
        args.state = str(state_config.get("type", args.state))
    if args.config and args.quality == "high":
        args.quality = str(lod_config.get("quality", args.quality))
    if args.config and args.lid_angle is None and "lidAngle" in state_config:
        args.lid_angle = float(state_config["lidAngle"])
    for index in range(max(args.count, 1)):
        config = KTYConfig(
            size=args.size,
            quality=args.quality,
            state=args.state,
            lid_angle=args.lid_angle,
            damage_level=max(0.0, min(1.0, args.damage_level)),
            empty_weight=args.empty_weight,
            seed=args.seed + index,
            instance_index=index,
            export=not args.no_export,
            render=not args.no_render,
        )
        KTY(config=config).generate().export()


if __name__ == "__main__":
    main()
