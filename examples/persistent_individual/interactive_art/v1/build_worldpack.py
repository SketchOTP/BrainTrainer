"""Re-skin the Littleroot map geometry with the generated v1 tile atlas."""
from __future__ import annotations

from copy import deepcopy
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "world" / "rural-v4.json"
TARGET = ROOT / "worldpacks" / "rural-v8.json"
ART = "/assets/interactive-art/v1/terrain.png"
TILE = 32
ATLAS_COLUMNS = 8


def connected_components(points: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    remaining = set(points)
    groups = []
    while remaining:
        start = remaining.pop()
        group = {start}
        todo = [start]
        while todo:
            x, y = todo.pop()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    group.add(neighbor)
                    todo.append(neighbor)
        groups.append(sorted(group, key=lambda point: (point[1], point[0])))
    return sorted(groups, key=lambda group: (min(y for _, y in group), min(x for x, _ in group)))


def exterior_layout(original: dict) -> dict:
    town = original["MAP_LITTLEROOT_TOWN"]
    old = town["tiles"]
    width, height = town["width"], town["height"]
    coords = lambda predicate: {
        (i % width, i // width) for i, value in enumerate(old) if predicate(value)
    }
    houses = connected_components(coords(lambda value: 2559 <= value <= 2577))
    buildings = []
    for index, points in enumerate(houses):
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        buildings.append({
            "id": "starter-house" if index == 0 else "companion-workshop",
            "region": "MAP_LITTLEROOT_TOWN",
            "x": min(xs), "y": min(ys),
            "width": max(xs) - min(xs) + 1,
            "height": max(ys) - min(ys) + 1,
            "view_indices": [0, 1, 2, 3] if index == 0 else [4, 5, 6, 7],
            "door": {"x": 5, "y": 8} if index == 0 else {"x": 16, "y": 16},
        })
    placements = []
    def add(identity, x, y, *, atlas, row, frame_size=128, render=(1, 1), facing=0, fixed=False):
        placements.append({
            "identity": identity,
            "position": {"region": "MAP_LITTLEROOT_TOWN", "x": x, "y": y},
            "visual": {
                "atlas_url": f"/assets/interactive-art/v1/{atlas}.png",
                "row": row, "frame_size": frame_size,
                "render_size_cells": list(render),
                "frame": facing if fixed else None,
                "rotation_degrees": 0,
                "fixed_view": fixed,
            },
        })

    # A separate pond cutout sits over its blocked water footprint.
    placements.append({
        "identity": "town-pond",
        "position": {"region": "MAP_LITTLEROOT_TOWN", "x": 6, "y": 16.6},
        "visual": {"asset": "/assets/interactive-art/v1/pond.png",
            "source_size": [512, 305], "render_size_cells": [7, 4.16], "pivot": "bottom-center"},
    })
    rim = []
    for index in range(15):
        x = 0.65 + index * (23.7 / 14)
        rim.extend(((x, 1.3, index % 2, (index // 2) % 4),
                    (x, 22.5, (index // 3) % 2, (index // 3) % 4)))
    for index, y in enumerate((3, 5, 7, 9, 11, 13, 15, 17, 19, 21)):
        rim.extend(((0.65, y, index % 2, index % 4),
                    (24.35, y, (index + 1) % 2, (index + 1) % 4)))
    for i, (x, y, row, frame) in enumerate(rim):
        add(f"town-tree-{i}", x, y, atlas="trees", row=row, facing=frame,
            render=(2.0, 2.15), fixed=True)
    add("town-entry-sign", 12.2, 20.0, atlas="directional-outdoor", row=1,
        render=(0.8, 1.2))
    add("pond-bench", 7.4, 19.2, atlas="directional-outdoor", row=7,
        render=(1.35, 0.95))
    add("pond-lantern", 2.2, 18.0, atlas="directional-outdoor", row=0,
        render=(0.75, 1.35))
    add("pond-flowers-west", 2.4, 13.0, atlas="directional-outdoor", row=3,
        render=(0.9, 0.8))
    add("pond-flowers-east", 9.4, 13.0, atlas="directional-outdoor", row=3,
        render=(0.9, 0.8), facing=2)
    add("workshop-firewood", 19.1, 17.5, atlas="directional-outdoor", row=6,
        render=(1.0, 0.75))
    return {"buildings": buildings, "placements": placements}


def interior_layout(pack: dict) -> list[dict]:
    placements = []
    def add(region, identity, x, y, atlas, row, render, *, frame=None, rotation=0):
        visual = {"atlas_url": f"/assets/interactive-art/v1/{atlas}.png",
            "row": row, "frame_size": 128, "render_size_cells": list(render),
            "rotation_degrees": rotation}
        if frame is not None:
            visual["frame"] = frame
            visual["fixed_view"] = True
        placements.append({"identity": identity,
            "position": {"region": region, "x": x, "y": y}, "visual": visual})

    home = "MAP_LITTLEROOT_TOWN_BRENDANS_HOUSE_1F"
    add(home, "home-bookcase", 2.0, 3.0, "directional-furniture", 3, (0.95, 1.45))
    add(home, "home-desk", 5.0, 5.0, "directional-furniture", 2, (1.35, 1.0))
    add(home, "home-chair", 5.0, 6.0, "directional-furniture", 1, (0.9, 1.0))
    add(home, "home-coffee-mug", 6.0, 5.0, "directional-furniture", 6, (0.55, 0.55))
    add(home, "home-plant", 2.0, 6.0, "room-essentials", 0, (0.8, 1.0), frame=3)

    bedroom = "MAP_LITTLEROOT_TOWN_BRENDANS_HOUSE_2F"
    add(bedroom, "bedroom-bed", 4.0, 5.0, "room-essentials", 0, (1.5, 1.4), frame=0)
    add(bedroom, "bedroom-side-table", 2.0, 4.0, "room-essentials", 0, (0.9, 0.9), frame=3)
    add(bedroom, "bedroom-lamp", 2.0, 3.0, "room-essentials", 3, (0.8, 1.0), frame=0)

    workshop = "MAP_LITTLEROOT_COMPANION_WORKSHOP"
    add(workshop, "workshop-bookcase", 2.0, 3.0, "directional-furniture", 3, (0.95, 1.45))
    add(workshop, "workshop-desk", 5.0, 6.0, "directional-furniture", 2, (1.35, 1.0))
    add(workshop, "workshop-chair", 5.0, 7.0, "directional-furniture", 1, (0.9, 1.0))
    add(workshop, "workshop-computer", 6.0, 6.0, "directional-furniture", 5, (1.0, 0.9))
    add(workshop, "workshop-machine", 9.0, 5.0, "directional-furniture", 7, (1.25, 1.15))
    add(workshop, "workshop-books", 8.0, 9.0, "directional-furniture", 4, (0.75, 0.55))

    lab = "MAP_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB"
    add(lab, "lab-bookcase", 2.0, 3.0, "directional-furniture", 3, (0.95, 1.45))
    add(lab, "lab-desk", 5.0, 6.0, "directional-furniture", 2, (1.35, 1.0))
    add(lab, "lab-computer", 5.0, 6.0, "directional-furniture", 5, (1.0, 0.9))
    add(lab, "lab-chair", 5.0, 7.0, "directional-furniture", 1, (0.9, 1.0))
    add(lab, "lab-machine", 9.0, 5.0, "directional-furniture", 7, (1.25, 1.15))
    add(lab, "lab-books", 8.0, 9.0, "directional-furniture", 4, (0.75, 0.55))
    add(lab, "lab-box-1", 2.0, 9.0, "furniture", 0, (0.9, 0.9), frame=0)
    add(lab, "lab-box-2", 3.0, 9.0, "furniture", 0, (0.9, 0.9), frame=1)
    # The research pad is visibly separate from the room's repeating floor.
    add(workshop, "workshop-lab-door", 10.0, 8.0, "buildings", 2, (1.0, 1.7), frame=3)
    add(lab, "lab-workshop-door", 6.5, 12.0, "buildings", 2, (2.0, 1.7), frame=1)
    add(home, "home-exterior-door", 8.5, 8.0, "buildings", 2, (2.0, 1.7), frame=1)
    add(workshop, "workshop-exterior-door", 6.5, 12.0, "buildings", 2, (2.0, 1.7), frame=3)
    return placements


def path_tile(x: int, y: int, path: set[tuple[int, int]]) -> int:
    mask = sum((1 << bit) for bit, point in enumerate(
        ((x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y))) if point in path)
    if not mask:
        raise ValueError(f"isolated path cell at {(x, y)}")
    variant = (x * 7 + y * 11) % 4
    return 64 + (mask - 1) * 4 + variant


def grass_patch_tiles(width: int, height: int) -> list[int]:
    """Seed irregular, connected patches into the ordinary walkable grass."""
    rng = random.Random(0xC0FFEE)
    patches = [(rng.uniform(1.5, width - 1.5), rng.uniform(1.5, height - 1.5),
                rng.uniform(2.8, 5.0), rng.choice((1, 3, 5, 6))) for _ in range(10)]
    flowers = [(rng.uniform(2, width - 2), rng.uniform(2, height - 2),
                rng.uniform(.75, 1.4), rng.choice((2, 4, 7))) for _ in range(16)]
    tiles = []
    for y in range(height):
        for x in range(width):
            jitter = ((x * 17 + y * 31 + x * y * 7) % 13 - 6) / 9
            candidates = []
            for px, py, radius, tile in patches:
                distance = ((x - px) ** 2 + (y - py) ** 2) ** .5
                if distance <= radius + jitter:
                    candidates.append((distance / radius, tile))
            selected = min(candidates, default=(2, 0))[1]
            flower_jitter = ((x * 7 + y * 19 + x * y * 3) % 11 - 5) / 12
            flower_candidates = []
            for px, py, radius, tile in flowers:
                distance = ((x - px) ** 2 + (y - py) ** 2) ** .5
                if distance <= radius + flower_jitter:
                    flower_candidates.append((distance / radius, tile))
            if flower_candidates:
                selected = min(flower_candidates)[1]
            tiles.append(selected)
    return tiles


def make_pack() -> dict:
    source = json.loads(SOURCE.read_text())
    pack = deepcopy(source)
    pack["schema"] = "creature-habitat-world-v8"
    pack["tile_size"] = TILE
    pack["atlas_columns"] = ATLAS_COLUMNS
    pack["atlas_rows"] = 16
    pack["atlas_url"] = ART
    pack["art_model"] = "creature-habitat-art-v1"
    pack["path_model"] = "connected-trails-v1"
    pack["ground_model"] = "irregular-grass-patches-v1"
    pack["labels"].pop("MAP_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB", None)
    pack["labels"].pop("MAP_LITTLEROOT_TOWN_MAYS_HOUSE_1F", None)
    pack["labels"].pop("MAP_LITTLEROOT_TOWN_MAYS_HOUSE_2F", None)
    pack["home_regions"] = [
        "MAP_LITTLEROOT_TOWN",
        "MAP_LITTLEROOT_TOWN_BRENDANS_HOUSE_1F",
        "MAP_LITTLEROOT_TOWN_BRENDANS_HOUSE_2F",
        "MAP_LITTLEROOT_COMPANION_WORKSHOP",
    ]
    pack["scene_layout"] = exterior_layout(source["maps"])

    for region, scene in pack["maps"].items():
        width, height = scene["width"], scene["height"]
        count = width * height
        if region == "MAP_LITTLEROOT_TOWN":
            # One legible village lane ties together the house, farm aisle,
            # pond approach and workshop door. Door cells participate in the
            # edge masks so each visible trail reaches its threshold cleanly.
            path = {(5, y) for y in range(8, 11)}
            path.update((x, 10) for x in range(5, 12))
            path.update((11, y) for y in range(10, 21))
            path.update((16, y) for y in range(3, 12))
            path.update((x, 11) for x in range(11, 17))
            path.update((x, 17) for x in range(11, 17))
            path.add((16, 16))
            pond = {tuple(cell) for cell in scene.get("pond", [])}
            # A short branch reaches the clear east bank without painting a
            # trail across the blocked water footprint.
            path.update((x, 15) for x in range(9, 12))
            path.difference_update(pond)
            field = {(x, y) for x in range(12, 21) for y in range(4, 11)}
            field_walk = {(16, y) for y in range(4, 11)}
            tiles = grass_patch_tiles(width, height)
            walkable = [True] * count
            for building in pack["scene_layout"]["buildings"]:
                for by in range(building["y"], building["y"] + building["height"]):
                    for bx in range(building["x"], building["x"] + building["width"]):
                        walkable[by * width + bx] = False
                door = building["door"]
                walkable[door["y"] * width + door["x"]] = True
            for y in range(height):
                for x in range(width):
                    index = y * width + x
                    if (x, y) in field and (x, y) not in field_walk:
                        tiles[index] = 24 + ((x + y) % 2)
                    elif (x, y) in path:
                        tiles[index] = path_tile(x, y, path)
                    if x < 2 or x >= width - 2 or y < 2 or y >= height - 2:
                        walkable[index] = False
                    if (x, y) in pond:
                        walkable[index] = False
                        # The separate pond cutout carries the shoreline and water pixels.
                        # Keep the tile beneath its transparent margins as grass.
            scene["tiles"] = tiles
            scene["walkable"] = walkable
            scene["water_cells"] = [list(cell) for cell in sorted(pond, key=lambda p: (p[1], p[0]))]
            scene["field_cells"] = [list(cell) for cell in sorted(field, key=lambda p: (p[1], p[0]))]
            scene["field_walk_cells"] = [list(cell) for cell in sorted(field_walk, key=lambda p: (p[1], p[0]))]
            scene["path_cells"] = [list(cell) for cell in sorted(path, key=lambda p: (p[1], p[0]))]
            scene["connections"] = []
            scene["portals"] = [p for p in scene.get("portals", []) if p["destination"] in pack["home_regions"]]
        elif region.startswith("MAP_LITTLEROOT_TOWN_") or region == "MAP_LITTLEROOT_COMPANION_WORKSHOP":
            if "PROFESSOR" in region:
                floor_tiles, wall_base = (44, 45), 56
            elif "WORKSHOP" in region:
                floor_tiles, wall_base = (46,), 56
            else:
                floor_tiles, wall_base = (40, 41, 42, 43), 48
            tiles = [floor_tiles[(i % width + i // width) % len(floor_tiles)] for i in range(count)]
            walkable = [True] * count
            portal_cells = {(p["x"], p["y"]) for p in scene.get("portals", [])}
            for y in range(height):
                for x in range(width):
                    index = y * width + x
                    on_wall = x == 0 or x == width - 1 or y == 0 or y == height - 1
                    if on_wall and (x, y) not in portal_cells:
                        top, bottom = y == 0, y == height - 1
                        left, right = x == 0, x == width - 1
                        if top and left:tiles[index] = wall_base + 4
                        elif top and right:tiles[index] = wall_base + 5
                        elif bottom and left:tiles[index] = wall_base + 6
                        elif bottom and right:tiles[index] = wall_base + 7
                        elif top:tiles[index] = wall_base
                        elif bottom:tiles[index] = wall_base + 1
                        elif left:tiles[index] = wall_base + 2
                        else:tiles[index] = wall_base + 3
                        walkable[index] = False
            scene["tiles"] = tiles
            scene["walkable"] = walkable
            scene["connections"] = []
            if region == "MAP_LITTLEROOT_COMPANION_WORKSHOP":
                scene["portals"].append({
                    "x": 10, "y": 8, "direction": "north",
                    "destination": "MAP_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB",
                    "arrivals": [[10, 10]], "origin": "pond-wing-research-door",
                })
                tiles[8 * width + 10] = 47
            elif region == "MAP_LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB":
                scene["portals"] = [
                    {
                        "x": 6, "y": 12, "direction": "south",
                        "destination": "MAP_LITTLEROOT_COMPANION_WORKSHOP",
                        "arrivals": [[10, 8]], "origin": "pond-wing-research-door",
                    },
                    {
                        "x": 7, "y": 12, "direction": "south",
                        "destination": "MAP_LITTLEROOT_COMPANION_WORKSHOP",
                        "arrivals": [[10, 8]], "origin": "pond-wing-research-door",
                    },
                ]
        else:
            tiles = [0] * count
            walkable = [True] * count
            for y in range(height):
                for x in range(width):
                    if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                        walkable[y * width + x] = False
            scene["tiles"] = tiles
            scene["walkable"] = walkable
            scene["connections"] = []
        scene["tile_size"] = TILE
    pack["scene_layout"]["placements"].extend(interior_layout(pack))
    return pack


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    pack = make_pack()
    TARGET.write_text(json.dumps(pack, separators=(",", ":")) + "\n")
    print(json.dumps({
        "path": str(TARGET),
        "maps": len(pack["maps"]),
        "hash": __import__("hashlib").sha256(TARGET.read_bytes()).hexdigest(),
        "buildings": pack["scene_layout"]["buildings"],
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
