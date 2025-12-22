import base64
from io import BytesIO
from typing import List

import fitz
from PIL import Image

from .config import DPI, MAX_TILE_SIZE, TILE_OVERLAP
from .image_enhancer import enhance_scan_for_ocr


def extract_and_tile_pdf(pdf_path: str) -> List[str]:
    """Возвращает список base64-строк тайлов из PDF"""
    b64_tiles = []
    matrix = fitz.Matrix(DPI / 72.0, DPI / 72.0)

    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            mode = "RGB" if pix.n == 3 else "L" if pix.n == 1 else "RGB"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            if mode != "RGB":
                img = img.convert("RGB")

            img = enhance_scan_for_ocr(img)
            width, height = img.size

            tiles = []
            if width <= MAX_TILE_SIZE and height <= MAX_TILE_SIZE:
                tiles = [img]
            else:
                if height > width:
                    y = 0
                    while y < height:
                        y2 = min(y + MAX_TILE_SIZE, height)
                        tile = img.crop((0, y, width, y2))
                        tiles.append(tile)
                        if y2 == height:
                            break
                        y = y2 - TILE_OVERLAP
                else:
                    x = 0
                    while x < width:
                        x2 = min(x + MAX_TILE_SIZE, width)
                        tile = img.crop((x, 0, x2, height))
                        tiles.append(tile)
                        if x2 == width:
                            break
                        x = x2 - TILE_OVERLAP

            for tile in tiles:
                buf = BytesIO()
                tile.save(buf, format="PNG", optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                b64_tiles.append(b64)

    return b64_tiles
