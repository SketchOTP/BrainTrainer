"""Build compact runtime atlases from the preserved generated originals."""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "runtime"


def clean_alpha(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    alpha = image.getchannel("A").point(lambda value: 255 if value >= 96 else 0)
    image.putalpha(alpha)
    return image


def cutout_atlas(source: str, columns: int, rows: int, cell: int = 128) -> Image.Image:
    image = Image.open(ROOT / source).convert("RGBA")
    atlas = Image.new("RGBA", (columns * cell, rows * cell), (0, 0, 0, 0))
    inset = max(2, round(min(image.width / columns, image.height / rows) * 0.008))
    for row in range(rows):
        top = round(row * image.height / rows) + inset
        bottom = round((row + 1) * image.height / rows) - inset
        for column in range(columns):
            left = round(column * image.width / columns) + inset
            right = round((column + 1) * image.width / columns) - inset
            sprite = clean_alpha(image.crop((left, top, right, bottom)))
            sprite.putalpha(_retain_components(sprite.getchannel("A")))
            bounds = sprite.getchannel("A").getbbox()
            if bounds is None:
                continue
            sprite = sprite.crop(bounds)
            available = cell - 12
            scale = min(available / sprite.width, available / sprite.height)
            size = (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale)))
            sprite = sprite.resize(size, Image.Resampling.NEAREST)
            x = column * cell + (cell - sprite.width) // 2
            y = row * cell + (cell - sprite.height) // 2
            atlas.alpha_composite(sprite, (x, y))
    return atlas


def connected_component_atlas(source: str, columns: int, rows: int,
                              row_boundaries: tuple[int, ...], cell: int = 128) -> Image.Image:
    """Pack complete sprites from a generated sheet whose rows overlap their nominal grid."""
    image = Image.open(ROOT / source).convert("RGBA")
    alpha = clean_alpha(image).getchannel("A")
    mask_pixels = alpha.load()
    width, height = image.size
    atlas = Image.new("RGBA", (columns * cell, rows * cell), (0, 0, 0, 0))
    seen = bytearray(width * height)
    components = []
    for y in range(height):
        for x in range(width):
            start = y * width + x
            if seen[start] or not mask_pixels[x, y]:
                continue
            seen[start] = 1
            pending = [start]
            pixels = []
            min_x = max_x = x
            min_y = max_y = y
            while pending:
                index = pending.pop()
                px, py = index % width, index // width
                pixels.append(index)
                min_x, max_x = min(min_x, px), max(max_x, px)
                min_y, max_y = min(min_y, py), max(max_y, py)
                for ny in range(max(0, py - 1), min(height, py + 2)):
                    for nx in range(max(0, px - 1), min(width, px + 2)):
                        neighbor = ny * width + nx
                        if not seen[neighbor] and mask_pixels[nx, ny]:
                            seen[neighbor] = 1
                            pending.append(neighbor)
            if len(pixels) < 256:
                continue
            center_x = (min_x + max_x + 1) / 2
            center_y = (min_y + max_y + 1) / 2
            column = min(columns - 1, int(center_x * columns / width))
            row = 0
            while row < len(row_boundaries) and center_y >= row_boundaries[row]:
                row += 1
            if row >= rows:
                raise ValueError(f"sprite lies outside atlas rows in {source}: {(min_x, min_y, max_x, max_y)}")
            component = Image.new("L", (max_x - min_x + 1, max_y - min_y + 1), 0)
            component_pixels = component.load()
            for index in pixels:
                component_pixels[index % width - min_x, index // width - min_y] = 255
            sprite = image.crop((min_x, min_y, max_x + 1, max_y + 1)).convert("RGBA")
            sprite.putalpha(component)
            available = cell - 12
            scale = min(available / sprite.width, available / sprite.height)
            size = (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale)))
            sprite = sprite.resize(size, Image.Resampling.NEAREST)
            x = column * cell + (cell - sprite.width) // 2
            y = row * cell + (cell - sprite.height) // 2
            atlas.alpha_composite(sprite, (x, y))
            components.append((row, column))
    expected = {(row, column) for row in range(rows) for column in range(columns)}
    if set(components) != expected or len(components) != len(expected):
        raise ValueError(f"incomplete or overlapping sprite components in {source}: {components}")
    return atlas


def tile_atlas(source: str, columns: int = 8, rows: int = 8, tile: int = 32) -> Image.Image:
    image = Image.open(ROOT / source).convert("RGBA")
    atlas = Image.new("RGBA", (columns * tile, rows * tile), (0, 0, 0, 255))
    # The source atlas uses dark cell dividers; remove those before resizing so
    # adjacent terrain tiles do not inherit a false grid or seam.
    inset = max(5, round(min(image.width / columns, image.height / rows) * 0.032))
    for row in range(rows):
        top = round(row * image.height / rows) + inset
        bottom = round((row + 1) * image.height / rows) - inset
        for column in range(columns):
            left = round(column * image.width / columns) + inset
            right = round((column + 1) * image.width / columns) - inset
            tile_image = image.crop((left, top, right, bottom))
            tile_image = tile_image.resize((tile, tile), Image.Resampling.NEAREST)
            atlas.alpha_composite(tile_image, (column * tile, row * tile))
    return atlas


def wood_floor(variant: int, size: int = 32) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    pixels = image.load()
    # Every tile shares the same plank edges. Variants only change low-contrast
    # grain inside the boards, so the map grid cannot show up as a checkerboard.
    base = (158, 111, 74)
    plank = (126, 84, 58)
    seam = (105, 73, 52)
    highlight = (190, 144, 98)
    for y in range(size):
        py = y % 31
        band = py // 8
        for x in range(size):
            px = x % 31
            grain = ((px * 7 + py * 11 + variant * 13) % 37) == 0
            color = base
            if py % 8 == 0 or py == 30:
                color = seam
            elif py % 8 == 1:
                color = highlight
            elif grain and 2 < px < 29:
                color = tuple(max(0, channel - 9) for channel in base)
            elif 2 < px < 29 and (px + band * 5 + variant * 3) % 17 == 0 and 2 < py % 8 < 7:
                color = plank
            pixels[x, y] = (*color, 255)
    return image


def stone_floor(base: tuple[int, int, int], variant: int, size: int = 32) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    pixels = image.load()
    grout = tuple(max(0, channel - 52) for channel in base)
    light = tuple(min(255, channel + 32) for channel in base)
    shade = tuple(max(0, channel - 22) for channel in base)
    for y in range(size):
        for x in range(size):
            local_x, local_y = x % 16, y % 16
            if local_x in (0, 15) or local_y in (0, 15):
                color = grout
            elif local_x == 1 or local_y == 1:
                color = light
            elif local_x == 14 or local_y == 14:
                color = shade
            elif (x * 3 + y * 5 + variant * 7) % 37 == 0:
                color = light
            else:
                color = base
            pixels[x, y] = (*color, 255)
    return image


def trail_tile(grass: Image.Image, mask: int, variant: int, size: int = 32) -> Image.Image:
    """Draw one dirt-path connection mask with identical, joinable edge profiles.

    Direction bits are north/east/south/west. Every connected edge uses the
    same centered cross-section, so adjoining cells meet without a notch even
    when a trail turns, branches or ends at a doorway.
    """
    result = grass.convert("RGBA").copy()
    center = size // 2
    edge_points = ((center, 0), (size - 1, center), (center, size - 1), (0, center))
    connections = [bit for bit in range(4) if mask & (1 << bit)]
    if not connections:
        return result

    def vector(bit: int) -> tuple[int, int]:
        return ((0, -1), (1, 0), (0, 1), (-1, 0))[bit]

    def centerline() -> list[tuple[int, int]]:
        degree = len(connections)
        if degree == 2 and (connections[0] - connections[1]) % 2 == 1:
            # A curved Bezier keeps a turn rounded instead of making the
            # elbow look like two square strips butted together.
            start_bit, end_bit = connections
            start, end = edge_points[start_bit], edge_points[end_bit]
            sx, sy = vector(start_bit)
            ex, ey = vector(end_bit)
            p1 = (start[0] - sx * 8, start[1] - sy * 8)
            p2 = (end[0] - ex * 8, end[1] - ey * 8)
            points = []
            for step in range(25):
                t = step / 24
                u = 1 - t
                x = u**3 * start[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*end[0]
                y = u**3 * start[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*end[1]
                points.append((round(x), round(y)))
            return points
        if degree == 2:
            return [edge_points[connections[0]], edge_points[connections[1]]]
        if degree == 1:
            return [(center, center), edge_points[connections[0]]]
        # Junctions are drawn as a rounded central clearing with spokes.
        return []

    route = centerline()
    border = Image.new("L", (size, size), 0)
    soil = Image.new("L", (size, size), 0)
    highlight = Image.new("L", (size, size), 0)
    if route:
        for layer, width in ((border, 18), (soil, 14), (highlight, 6)):
            ImageDraw.Draw(layer).line(route, fill=255, width=width, joint="curve")
    else:
        for bit in connections:
            route = [(center, center), edge_points[bit]]
            for layer, width in ((border, 18), (soil, 14), (highlight, 6)):
                ImageDraw.Draw(layer).line(route, fill=255, width=width)
    for layer, radius in ((border, 9), (soil, 7), (highlight, 3)):
        ImageDraw.Draw(layer).ellipse((center-radius, center-radius,
                                       center+radius, center+radius), fill=255)

    outline_color = (127, 91, 58, 255)
    soil_color = (187, 141, 88, 255)
    light_color = (207, 163, 108, 255)
    result.paste(outline_color, (0, 0, size, size), border)
    result.paste(soil_color, (0, 0, size, size), soil)
    result.paste(light_color, (0, 0, size, size), highlight)

    # Quiet pixel flecks keep long paths from reading as flat strips. Keep
    # texture away from the tile boundary so all rotations and variants join.
    pixels = result.load()
    soil_pixels = soil.load()
    for y in range(5, size - 5):
        for x in range(5, size - 5):
            if not soil_pixels[x, y]:
                continue
            noise = (x * 29 + y * 17 + variant * 31 + mask * 13) % 67
            if noise == 0:
                pixels[x, y] = (151, 111, 68, 255)
            elif noise == 3:
                pixels[x, y] = (219, 176, 119, 255)

    # Pillow clips a thick stroke asymmetrically when its endpoint lands on
    # the tile border. Stamp the final two pixel columns/rows from one shared
    # cross-section to prevent a hairline jog at horizontal/vertical joins.
    for bit in connections:
        if bit in (1, 3):
            edge_x = size - 1 if bit == 1 else 0
            for depth in range(2):
                x = edge_x - depth if bit == 1 else edge_x + depth
                for offset in range(-11, 12):
                    y = center + offset
                    color = (207, 163, 108, 255) if abs(offset) <= 2 else (
                        (187, 141, 88, 255) if abs(offset) <= 6 else outline_color)
                    pixels[x, y] = color
        else:
            edge_y = 0 if bit == 0 else size - 1
            for depth in range(2):
                y = edge_y + depth if bit == 0 else edge_y - depth
                for offset in range(-11, 12):
                    x = center + offset
                    color = (207, 163, 108, 255) if abs(offset) <= 2 else (
                        (187, 141, 88, 255) if abs(offset) <= 6 else outline_color)
                    pixels[x, y] = color
    return result


def interior_wall(material: str, edge: str, size: int = 32) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    pixels = image.load()
    if material == "house":
        base, light, dark, trim = (211, 184, 143), (229, 208, 174), (92, 66, 54), (145, 101, 69)
    else:
        base, light, dark, trim = (132, 126, 157), (173, 164, 187), (64, 61, 83), (97, 87, 119)
    for y in range(size):
        for x in range(size):
            px, py = x % 31, y % 31
            fleck = ((px * 5 + py * 9 + (3 if material == "house" else 11)) % 47) == 0
            color = light if ((px // 8 + py // 8) % 5 == 0 and fleck) else base
            pixels[x, y] = (*color, 255)

    draw = ImageDraw.Draw(image)
    if edge in ("top", "top-left", "top-right"):
        draw.line((0, 0, 31, 0), fill=dark)
        draw.rectangle((0, 26, 31, 31), fill=trim)
        draw.line((0, 26, 31, 26), fill=light)
    if edge in ("bottom", "bottom-left", "bottom-right"):
        draw.line((0, 31, 31, 31), fill=dark)
        draw.rectangle((0, 0, 31, 5), fill=trim)
        draw.line((0, 5, 31, 5), fill=light)
    if edge in ("left", "top-left", "bottom-left"):
        draw.line((0, 0, 0, 31), fill=dark)
        draw.rectangle((26, 0, 31, 31), fill=trim)
        draw.line((26, 0, 26, 31), fill=light)
    if edge in ("right", "top-right", "bottom-right"):
        draw.line((31, 0, 31, 31), fill=dark)
        draw.rectangle((0, 0, 5, 31), fill=trim)
        draw.line((5, 0, 5, 31), fill=light)
    # Small inset panel seams avoid repeating a fixture or window as wall texture.
    if edge in ("top", "bottom"):
        draw.line((10, 9, 10, 22), fill=trim)
        draw.line((21, 9, 21, 22), fill=light)
    elif edge in ("left", "right"):
        draw.line((9, 10, 22, 10), fill=trim)
        draw.line((9, 21, 22, 21), fill=light)
    if edge in ("top-left", "top-right", "bottom-left", "bottom-right"):
        # Corners must meet the matching straight wall on both adjoining sides.
        # Copy their boundary pixels so the baseboard turns cleanly without a
        # one-cell double-width stripe or a color break at the room corners.
        if edge.startswith("top"):
            horizontal = interior_wall(material, "top", size)
            horizontal_side = 0 if edge == "top-left" else size - 1
            corner_side = size - 1 if edge == "top-left" else 0
            side_name = "left" if edge == "top-left" else "right"
            vertical = interior_wall(material, side_name, size)
            side_column = 0 if edge == "top-left" else size - 1
            for y in range(size):
                pixels[corner_side, y] = horizontal.getpixel((horizontal_side, y))
                pixels[0 if edge == "top-left" else size - 1, y] = vertical.getpixel((side_column, y))
            for x in range(size):
                pixels[x, size - 1] = vertical.getpixel((x, 0))
                pixels[x, 0] = horizontal.getpixel((x, 0))
        else:
            horizontal = interior_wall(material, "bottom", size)
            horizontal_side = 0 if edge == "bottom-left" else size - 1
            corner_side = size - 1 if edge == "bottom-left" else 0
            side_name = "left" if edge == "bottom-left" else "right"
            vertical = interior_wall(material, side_name, size)
            side_column = 0 if edge == "bottom-left" else size - 1
            for y in range(size):
                pixels[corner_side, y] = horizontal.getpixel((horizontal_side, y))
                pixels[0 if edge == "bottom-left" else size - 1, y] = vertical.getpixel((side_column, y))
            for x in range(size):
                pixels[x, 0] = vertical.getpixel((x, size - 1))
                pixels[x, size - 1] = horizontal.getpixel((x, size - 1))
    return image


def compose_interior_tiles(atlas: Image.Image, size: int = 32) -> Image.Image:
    """Replace composite fixture cells and add edge-matched town path tiles."""
    floors = [wood_floor(i, size) for i in range(4)]
    floors.extend((stone_floor((215, 202, 174), 0, size),
                   stone_floor((215, 202, 174), 1, size),
                   stone_floor((137, 128, 158), 2, size)))
    wall_specs = [
        ("house", "top"), ("house", "bottom"), ("house", "left"), ("house", "right"),
        ("house", "top-left"), ("house", "top-right"), ("house", "bottom-left"), ("house", "bottom-right"),
        ("workshop", "top"), ("workshop", "bottom"), ("workshop", "left"), ("workshop", "right"),
        ("workshop", "top-left"), ("workshop", "top-right"), ("workshop", "bottom-left"), ("workshop", "bottom-right"),
    ]
    walls = [interior_wall(material, edge, size) for material, edge in wall_specs]
    # A quiet threshold tile replaces the old atlas' unrelated decorative sliver.
    threshold = stone_floor((112, 96, 135), 0, size)
    threshold_draw = ImageDraw.Draw(threshold)
    threshold_draw.rectangle((7, 7, 24, 24), fill=(137, 111, 164), outline=(76, 64, 96), width=2)
    threshold_draw.rectangle((11, 11, 20, 20), fill=(179, 157, 202), outline=(112, 93, 145), width=1)
    threshold_draw.point((15, 15), fill=(230, 211, 245))
    for index, tile in enumerate(floors, start=40):
        atlas.alpha_composite(tile, ((index % 8) * size, (index // 8) * size))
    atlas.alpha_composite(threshold, ((47 % 8) * size, (47 // 8) * size))
    for index, tile in enumerate(walls, start=48):
        atlas.alpha_composite(tile, ((index % 8) * size, (index // 8) * size))

    # Keep the established 0-63 tiles stable for old checkpoints. New path
    # masks live in rows 8-15, beyond the current floor and wall atlas.
    expanded = Image.new("RGBA", (8 * size, 16 * size), (0, 0, 0, 255))
    expanded.alpha_composite(atlas, (0, 0))
    grass = atlas.crop((0, 0, size, size))
    for mask in range(1, 16):
        for variant in range(4):
            tile = trail_tile(grass, mask, variant, size)
            index = 64 + (mask - 1) * 4 + variant
            expanded.alpha_composite(tile, ((index % 8) * size, (index // 8) * size))
    return expanded


def pond_asset(source: str) -> Image.Image:
    image = clean_alpha(Image.open(ROOT / source))
    bounds = image.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError("pond source has no visible pixels")
    image = image.crop(bounds)
    target_width = 512
    target_height = round(image.height * target_width / image.width)
    return image.resize((target_width, target_height), Image.Resampling.NEAREST)


FURNITURE_FACINGS = (
    ("wooden-stool", 0.85, 0.85),
    ("cushioned-chair", 0.9, 1.0),
    ("writing-desk", 1.35, 1.0),
    ("bookcase-tall", 0.95, 1.45),
    ("books-stack", 0.75, 0.55),
    ("desktop-computer", 1.0, 0.9),
    ("coffee-mug", 0.55, 0.55),
    ("research-machine", 1.25, 1.15),
)
OUTDOOR_FACINGS = (
    ("garden-lantern", 0.75, 1.35),
    ("wooden-sign", 1.0, 1.2),
    ("garden-boulder", 0.9, 0.7),
    ("flower-bush", 1.0, 0.85),
    ("berry-shrub", 1.0, 0.85),
    ("water-trough", 1.3, 0.9),
    ("firewood-stack", 1.0, 0.85),
    ("garden-bench", 1.35, 0.95),
)


def _retain_components(mask: Image.Image, minimum_pixels: int = 256) -> Image.Image:
    """Drop only tiny detached cutout noise; retain shadows and disconnected sprite parts."""
    width, height = mask.size
    pixels = mask.load()
    seen = bytearray(width * height)
    retained: list[int] = []
    for y in range(height):
        for x in range(width):
            start = y * width + x
            if seen[start] or not pixels[x, y]:
                continue
            seen[start] = 1
            pending = [start]
            component = []
            while pending:
                current = pending.pop()
                component.append(current)
                cx, cy = current % width, current // width
                for ny in range(max(0, cy - 1), min(height, cy + 2)):
                    for nx in range(max(0, cx - 1), min(width, cx + 2)):
                        neighbor = ny * width + nx
                        if not seen[neighbor] and pixels[nx, ny]:
                            seen[neighbor] = 1
                            pending.append(neighbor)
            if len(component) >= minimum_pixels:
                retained.extend(component)
    result = Image.new("L", mask.size, 0)
    output = result.load()
    for index in retained:
        output[index % width, index // width] = 255
    return result


def directional_atlas(source: str, rows: tuple, cell: int = 128) -> Image.Image:
    """Pack alpha-cut front/right/back/left views without color-based pixel removal."""
    image = Image.open(ROOT / source).convert("RGBA")
    columns = 4
    atlas = Image.new("RGBA", (columns * cell, len(rows) * cell), (0, 0, 0, 0))
    for row, _asset in enumerate(rows):
        cleaned_views = []
        for column in range(columns):
            bounds = (
                round(column * image.width / columns),
                round(row * image.height / len(rows)),
                round((column + 1) * image.width / columns),
                round((row + 1) * image.height / len(rows)),
            )
            frame = clean_alpha(image.crop(bounds))
            alpha = _retain_components(frame.getchannel("A"))
            frame.putalpha(alpha)
            bbox = alpha.getbbox()
            if bbox is None:
                raise ValueError(f"empty directional view {source} row={row} facing={column}")
            cleaned_views.append(frame.crop(bbox))

        available = cell - 14
        widest = max(view.width for view in cleaned_views)
        tallest = max(view.height for view in cleaned_views)
        scale = min(available / widest, available / tallest)
        for column, view in enumerate(cleaned_views):
            size = (max(1, round(view.width * scale)), max(1, round(view.height * scale)))
            sprite = view.resize(size, Image.Resampling.NEAREST)
            # The bottom-center pivot remains fixed as the creature turns.
            x = column * cell + (cell - sprite.width) // 2
            y = row * cell + cell - 7 - sprite.height
            atlas.alpha_composite(sprite, (x, y))
    return atlas


def prop_catalog() -> dict:
    return {
        "schema": "creature-habitat-prop-art-v1",
        "art_only": True,
        "facing_order": ["front", "right", "back", "left"],
        "world_facing_columns": {"south": 0, "east": 1, "north": 2, "west": 3},
        "frame_size": 128,
        "pivot": "bottom-center",
        "assets": {
            **{
                name: {"atlas": "directional-furniture.png", "row": index,
                       "atlas_url": "/assets/interactive-art/v1/directional-furniture.png",
                       "frame_size": 128,
                       "render_size_cells": [width, height]}
                for index, (name, width, height) in enumerate(FURNITURE_FACINGS)
            },
            **{
                name: {"atlas": "directional-outdoor.png", "row": index,
                       "atlas_url": "/assets/interactive-art/v1/directional-outdoor.png",
                       "frame_size": 128,
                       "render_size_cells": [width, height]}
                for index, (name, width, height) in enumerate(OUTDOOR_FACINGS)
            },
        },
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    products = {
        "furniture.png": cutout_atlas("furniture-source.png", 4, 4),
        "room-essentials.png": cutout_atlas("room-essentials-source.png", 4, 4),
        "directional-furniture.png": directional_atlas("directional-furniture-source.png", FURNITURE_FACINGS),
        "directional-outdoor.png": directional_atlas("directional-outdoor-source.png", OUTDOOR_FACINGS),
        "outdoor-props.png": cutout_atlas("outdoor-props-source.png", 4, 4),
        "trees.png": cutout_atlas("trees-source.png", 4, 4),
        "buildings.png": connected_component_atlas(
            "building-facings-source.png", 4, 4, row_boundaries=(350, 690, 1000)
        ),
        "building-gallery.png": cutout_atlas("buildings-source.png", 4, 4),
        "actions.png": cutout_atlas("actions-source.png", 4, 4),
        "manipulation.png": cutout_atlas("manipulation-character-source.png", 4, 4),
        "berry-growth.png": cutout_atlas("berry-growth-source.png", 4, 3),
        "garden-soil.png": cutout_atlas("garden-soil-source.png", 2, 2),
        "terrain.png": compose_interior_tiles(tile_atlas("terrain-source.png")),
        "pond.png": pond_asset("pond-source.png"),
    }
    manifest = {"model": "creature-habitat-runtime-art-v1", "assets": {}}
    for name, image in products.items():
        path = OUT / name
        image.save(path, optimize=True)
        manifest["assets"][name] = {
            "width": image.width,
            "height": image.height,
            "sha256": sha256(path.read_bytes()).hexdigest(),
        }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "props.json").write_text(json.dumps(prop_catalog(), indent=2) + "\n")
    manifest["catalog"] = {
        "path": "props.json",
        "sha256": sha256((OUT / "props.json").read_bytes()).hexdigest(),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({name: (image.width, image.height) for name, image in products.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
