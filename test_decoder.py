import cv2
import numpy as np
import reedsolo
import zlib
import io
import hashlib
import random
from PIL import Image

def create_finder_pattern():
    pattern = np.zeros((7, 7, 3), dtype=np.uint8)
    pattern[:, :, :] = 0
    pattern[1:6, 1:6, :] = 255
    pattern[2:5, 2:5, :] = 0
    return pattern

def interleave_bytes(data_bytes):
    random.seed(1337)
    indices = list(range(len(data_bytes)))
    random.shuffle(indices)
    return bytearray([data_bytes[i] for i in indices])

def deinterleave_bytes(data_bytes):
    random.seed(1337)
    indices = list(range(len(data_bytes)))
    random.shuffle(indices)
    deinterleaved = bytearray(len(data_bytes))
    for i, orig_idx in enumerate(indices):
        deinterleaved[orig_idx] = data_bytes[i]
    return deinterleaved

ECC_SYMBOLS = 64

def encode_chunk(payload_bytes, mode):
    rs = reedsolo.RSCodec(ECC_SYMBOLS)
    encoded = bytearray(rs.encode(payload_bytes))
    encoded = interleave_bytes(encoded)
    mode_id = {"S=2 (Binary)":0, "S=16 (Grayscale)":1, "S=4096 (RGB + ZLIB)":2}[mode]
    byte_length = len(encoded)
    header_val = (mode_id << 14) | (byte_length & 0x3FFF)
    cells = []
    for i in range(16):
        cells.append((header_val >> (15 - i)) & 1)
    if mode == "S=4096 (RGB + ZLIB)":
        nibbles = []
        for b in encoded:
            nibbles.append(b >> 4)
            nibbles.append(b & 0x0F)
        while len(nibbles) % 3 != 0:
            nibbles.append(0)
        for i in range(0, len(nibbles), 3):
            cells.append((nibbles[i], nibbles[i+1], nibbles[i+2]))
    return cells, mode_id

def build_grid(data, mode_id, fixed_grid_size=None):
    total_cells = len(data)
    grid_size = fixed_grid_size
    grid = np.ones((grid_size, grid_size, 3), dtype=np.uint8) * 255
    fp = create_finder_pattern()
    grid[0:7, 0:7] = fp
    grid[0:7, grid_size-7:grid_size] = fp
    grid[grid_size-7:grid_size, 0:7] = fp
    cell_idx = 0
    for y in range(grid_size):
        for x in range(grid_size):
            if (y < 8 and x < 8) or (y < 8 and x >= grid_size - 8) or (y >= grid_size - 8 and x < 8):
                continue
            if cell_idx < total_cells:
                if cell_idx < 16:
                    val = 0 if data[cell_idx] == 1 else 255
                    grid[y, x, :] = val
                else:
                    b, g, r = data[cell_idx]
                    grid[y, x, 0] = b * 17
                    grid[y, x, 1] = g * 17
                    grid[y, x, 2] = r * 17
                cell_idx += 1
            else:
                grid[y, x, :] = 0
    return grid

def align_image(img_array):
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img_array
    c = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.02 * peri, True)
    print("align_image found points:", len(approx))
    if len(approx) == 4:
        pts = approx.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        dst = np.array([[0, 0], [600, 0], [600, 600], [0, 600]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img_array, M, (600, 600))
    return img_array

payload = b"Hello, World! " * 10
mode = "S=4096 (RGB + ZLIB)"
data, mode_id = encode_chunk(payload, mode)
total_cells = len(data)
fixed_grid_size = 21
while (fixed_grid_size * fixed_grid_size) - (3 * 64) < total_cells:
    fixed_grid_size += 1

grid = build_grid(data, mode_id, fixed_grid_size=fixed_grid_size)
CELL_SIZE = 10
img = cv2.resize(grid, (grid.shape[1] * CELL_SIZE, grid.shape[0] * CELL_SIZE), interpolation=cv2.INTER_NEAREST)
img_with_border = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=[255, 255, 255])
frames = [cv2.cvtColor(img_with_border, cv2.COLOR_BGR2RGB)]

# DECODE
img_array = cv2.cvtColor(frames[0], cv2.COLOR_RGB2BGR)
aligned = align_image(img_array)

print("Aligned shape:", aligned.shape)

border = 40
if aligned.shape[0] == 600:
    border = int(600 * 0.05)
    
cropped = aligned[border:-border, border:-border]
print("Cropped shape:", cropped.shape)
