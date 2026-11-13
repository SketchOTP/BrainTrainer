"""Build v10 with a connected walk that reaches the pond without crossing water."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from build_natural_town import TRAILS, make_natural_pack

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "worldpacks" / "rural-v10.json"

TRAILS_V10 = (
    TRAILS[0],
    TRAILS[1],
    # Reach the pond's northeast bank from the main walk, staying on land.
    ((12, 15), (11, 15), (10, 15), (10, 14), (10, 13), (10, 12), (9, 12)),
    TRAILS[3],
)


def validate_connected_town(pack: dict) -> int:
    town = pack["maps"]["MAP_LITTLEROOT_TOWN"]
    width = town["width"]
    paths = {tuple(cell) for cell in town["path_cells"]}
    pond = {tuple(cell) for cell in town["pond"]}
    if not paths or paths & pond:
        raise ValueError("the town path must be present and stay outside the pond")
    remaining = set(paths)
    stack = [remaining.pop()]
    while stack:
        x, y = stack.pop()
        for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if neighbor in remaining:
                remaining.remove(neighbor)
                stack.append(neighbor)
    if remaining:
        raise ValueError(f"disconnected path cells remain: {sorted(remaining)}")
    for building in pack["scene_layout"]["buildings"]:
        door = (building["door"]["x"], building["door"]["y"])
        if door not in paths:
            raise ValueError(f"door {building['id']} is not connected to a path")
    if (9, 12) not in paths or (9, 13) not in pond:
        raise ValueError("the walk must reach the northeast pond bank")
    if any(not town["walkable"][y * width + x] for x, y in paths):
        raise ValueError("a path cell is blocked")
    if any(town["walkable"][y * width + x] for x, y in pond):
        raise ValueError("pond tiles must remain non-walkable")
    return len(paths)


def main() -> None:
    pack = make_natural_pack(trails=TRAILS_V10)
    pack["schema"] = "creature-habitat-world-v10"
    pack["path_model"] = "pond-connected-winding-trails-v3"
    path_cells = validate_connected_town(pack)
    TARGET.write_text(json.dumps(pack, separators=(",", ":")) + "\n")
    print(json.dumps({
        "path": str(TARGET),
        "map_count": len(pack["maps"]),
        "path_cells": path_cells,
        "sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
