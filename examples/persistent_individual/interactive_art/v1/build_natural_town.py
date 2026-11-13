"""Create the irregular Littleroot layout from the preserved scoped-town pack."""
from __future__ import annotations

from copy import deepcopy
import json
import random
from pathlib import Path

from build_worldpack import make_pack, path_tile, grass_patch_tiles

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "worldpacks" / "rural-v9.json"

PLOTS = [
    {"x": 13, "y": 5, "kind": "oran"},
    {"x": 19, "y": 5, "kind": "pecha"},
    {"x": 15, "y": 6, "kind": "oran"},
    {"x": 20, "y": 7, "kind": "pecha"},
    {"x": 13, "y": 10, "kind": "oran"},
    {"x": 18, "y": 10, "kind": "pecha"},
]

TRAILS = (
    # One winding village walk joins the house, pond edge and workshop.
    ((5, 8), (5, 9), (6, 9), (7, 9), (7, 10), (8, 10), (9, 10),
     (10, 11), (11, 11), (11, 12), (12, 12), (12, 13), (12, 14),
     (12, 15), (12, 16), (12, 17), (13, 17), (14, 18), (15, 18),
     (16, 17), (16, 16)),
    # A short curved spur enters the farm without cutting across every row.
    ((9, 10), (10, 9), (11, 9), (12, 8), (13, 8), (14, 8), (14, 7)),
    # A small loop reaches the pond bench and the open southern clearing.
    ((12, 15), (11, 15), (10, 15), (9, 16), (8, 17), (7, 18), (7, 19)),
    ((12, 17), (12, 18), (12, 19), (13, 20), (14, 20), (15, 21)),
)

TREE_SITES = (
    (0.8, 2.4), (2.0, 2.7), (4.7, 2.1), (7.1, 2.7), (9.4, 2.2),
    (12.2, 2.8), (14.7, 2.2), (17.1, 2.8), (19.4, 2.2), (22.0, 2.8), (24.3, 2.3),
    (0.8, 5.0), (1.3, 8.2), (0.8, 11.0), (1.4, 13.0), (0.8, 16.1), (1.4, 19.3),
    (24.3, 4.8), (23.8, 7.7), (24.3, 10.8), (23.8, 13.2), (24.3, 16.4), (23.8, 19.0),
    (2.0, 21.8), (4.7, 21.2), (7.0, 22.0), (9.6, 21.4), (12.0, 22.0),
    (15.4, 21.3), (18.0, 22.0), (20.8, 21.3), (23.7, 21.8),
)


def add_path(target: set[tuple[int, int]], points: tuple[tuple[int, int], ...]) -> None:
    for start, end in zip(points, points[1:]):
        x, y = start
        tx, ty = end
        while x != tx:
            target.add((x, y))
            x += 1 if tx > x else -1
        while y != ty:
            target.add((x, y))
            y += 1 if ty > y else -1
        target.add((x, y))


def tree_rim(placements: list[dict]) -> list[dict]:
    keep = [item for item in placements if not item["identity"].startswith("town-tree-")]
    rng = random.Random(0xE63A1D)
    for index, (x, y) in enumerate(TREE_SITES):
        row = rng.choice((0, 0, 1, 1, 3))
        frame = rng.randrange(2 if row == 3 else 4)
        render = (round(rng.uniform(1.65, 2.25), 2), round(rng.uniform(1.85, 2.55), 2))
        keep.append({
            "identity": f"town-tree-{index}",
            "position": {"region": "MAP_LITTLEROOT_TOWN",
                "x": round(x + rng.uniform(-0.18, 0.18), 2),
                "y": round(y + rng.uniform(-0.16, 0.16), 2)},
            "visual": {"atlas_url": "/assets/interactive-art/v1/trees.png",
                "row": row, "frame_size": 128, "render_size_cells": list(render),
                "frame": frame, "rotation_degrees": 0, "fixed_view": True},
        })
    return keep


def field_mask(width: int, height: int, path: set[tuple[int, int]]) -> set[tuple[int, int]]:
    field = set()
    for plot in PLOTS:
        px, py = plot["x"], plot["y"]
        for dy in range(-1, 2):
            for dx in range(-2, 3):
                if dx * dx / 4 + dy * dy <= 1.15:
                    cell = (px + dx, py + dy)
                    if (2 <= cell[0] < width - 2 and 2 <= cell[1] < height - 2
                            and cell not in path):
                        field.add(cell)
    return field


def make_natural_pack(trails: tuple = TRAILS) -> dict:
    pack = deepcopy(make_pack())
    town = pack["maps"]["MAP_LITTLEROOT_TOWN"]
    width, height = town["width"], town["height"]
    path: set[tuple[int, int]] = set()
    for trail in trails:
        add_path(path, trail)
    pond = {tuple(cell) for cell in town.get("pond", [])}
    path.difference_update(pond)
    for plot in PLOTS:
        if (plot["x"], plot["y"]) in path or (plot["x"], plot["y"]) in pond:
            raise ValueError(f"berry plot overlaps a trail or water: {plot}")

    tiles = grass_patch_tiles(width, height)
    walkable = [True] * (width * height)
    for building in pack["scene_layout"]["buildings"]:
        for y in range(building["y"], building["y"] + building["height"]):
            for x in range(building["x"], building["x"] + building["width"]):
                walkable[y * width + x] = False
        door = building["door"]
        walkable[door["y"] * width + door["x"]] = True
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if (x, y) in path:
                tiles[index] = path_tile(x, y, path)
            if x < 2 or x >= width - 2 or y < 2 or y >= height - 2:
                walkable[index] = False
            if (x, y) in pond:
                walkable[index] = False

    town["tiles"] = tiles
    town["walkable"] = walkable
    town["water_cells"] = [list(cell) for cell in sorted(pond, key=lambda point: (point[1], point[0]))]
    field = field_mask(width, height, path)
    town["field_cells"] = [list(cell) for cell in sorted(field, key=lambda point: (point[1], point[0]))]
    field_walk = {(x, y) for x, y in path if 11 <= x <= 20 and 4 <= y <= 10}
    town["field_walk_cells"] = [list(cell) for cell in sorted(field_walk, key=lambda point: (point[1], point[0]))]
    town["path_cells"] = [list(cell) for cell in sorted(path, key=lambda point: (point[1], point[0]))]
    town["berries"] = PLOTS
    town["connections"] = []
    town["portals"] = [portal for portal in town.get("portals", [])
        if portal["destination"] in pack["home_regions"]]
    pack["scene_layout"]["placements"] = tree_rim(pack["scene_layout"]["placements"])
    pack["schema"] = "creature-habitat-world-v9"
    pack["path_model"] = "winding-connected-trails-v2"
    pack["ground_model"] = "natural-grass-and-rounded-garden-soil-v2"
    pack["farm_model"] = "irregular-berry-layout-v1"
    pack["garden_art"] = {
        "growth_atlas": "/assets/interactive-art/v1/berry-growth.png",
        "soil_atlas": "/assets/interactive-art/v1/garden-soil.png",
        "growth_model": "berry-tree-growth-v1",
    }
    return pack


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    pack = make_natural_pack()
    TARGET.write_text(json.dumps(pack, separators=(",", ":")) + "\n")
    print(json.dumps({
        "path": str(TARGET),
        "maps": len(pack["maps"]),
        "berries": pack["maps"]["MAP_LITTLEROOT_TOWN"]["berries"],
        "path_cells": len(pack["maps"]["MAP_LITTLEROOT_TOWN"]["path_cells"]),
        "hash": __import__("hashlib").sha256(TARGET.read_bytes()).hexdigest(),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
