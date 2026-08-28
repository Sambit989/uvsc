import cv2
import numpy as np
import reedsolo
import sys
import zlib

# Configuration (Stage 4: Damaged RGB)
CELL_SIZE = 20
ECC_SYMBOLS = 64

def create_finder_pattern():
    # 7x7 standard finder pattern (B,G,R)
    # Finder patterns should be high contrast (black and white) so they are easy to find
    pattern = np.zeros((7, 7, 3), dtype=np.uint8)
    pattern[:, :, :] = 0  # Black background
    pattern[1:6, 1:6, :] = 255  # White inner square
    pattern[2:5, 2:5, :] = 0  # Black center dot
    return pattern

def encode_data(data_bytes):
    # Phase 5: Compression
    compressed = zlib.compress(data_bytes, level=9)
    print(f"Compressed size: {len(compressed)} bytes (Original: {len(data_bytes)} bytes)")
    
    # Apply Reed-Solomon Error Correction
    rs = reedsolo.RSCodec(ECC_SYMBOLS)
    encoded_bytes = rs.encode(compressed)
    
    # Convert bytes to 4-bit nibbles (0-15)
    nibbles = []
    for b in encoded_bytes:
        nibbles.append(b >> 4)
        nibbles.append(b & 0x0F)
        
    # Group into cells (3 nibbles per cell for B, G, R)
    # Pad with 0 if length is not divisible by 3
    while len(nibbles) % 3 != 0:
        nibbles.append(0)
        
    cells = []
    for i in range(0, len(nibbles), 3):
        cells.append((nibbles[i], nibbles[i+1], nibbles[i+2]))
        
    return cells

def build_grid(cells):
    total_cells = len(cells)
    
    # Grid size calculation
    grid_size = 21
    while (grid_size * grid_size) - (3 * 64) < total_cells:
        grid_size += 1
        
    grid = np.ones((grid_size, grid_size, 3), dtype=np.uint8) * 255 # White background
    
    # Place Finder Patterns
    fp = create_finder_pattern()
    grid[0:7, 0:7] = fp
    grid[0:7, grid_size-7:grid_size] = fp
    grid[grid_size-7:grid_size, 0:7] = fp
    
    # Fill Data
    cell_idx = 0
    for y in range(grid_size):
        for x in range(grid_size):
            if (y < 8 and x < 8) or (y < 8 and x >= grid_size - 8) or (y >= grid_size - 8 and x < 8):
                continue
                
            if cell_idx < total_cells:
                # Map 3 nibbles to BGR
                b_nibble, g_nibble, r_nibble = cells[cell_idx]
                grid[y, x, 0] = b_nibble * 17
                grid[y, x, 1] = g_nibble * 17
                grid[y, x, 2] = r_nibble * 17
                cell_idx += 1
            else:
                grid[y, x, :] = 0
                
    return grid

def main():
    if len(sys.argv) < 2:
        # A large string to show compression working
        payload_str = "UVSC Stage 3! " * 50
        payload = payload_str.encode('utf-8')
    else:
        with open(sys.argv[1], 'rb') as f:
            payload = f.read()

    print(f"Payload size: {len(payload)} bytes")
    cells = encode_data(payload)
    print(f"Encoded cells (with ECC & Compression): {len(cells)} cells")
    print(f"Mathematical Capacity Increase: 12x Density over Stage 1 (plus ZLIB multiplier)")
    
    grid = build_grid(cells)
    print(f"Grid dimensions: {grid.shape[0]}x{grid.shape[1]}")
    
    img = cv2.resize(grid, (grid.shape[1] * CELL_SIZE, grid.shape[0] * CELL_SIZE), interpolation=cv2.INTER_NEAREST)
    border = CELL_SIZE * 4
    img_with_border = cv2.copyMakeBorder(img, border, border, border, border, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    cv2.imwrite("UVSC_S3_RGB.png", img_with_border)
    print("Saved UVSC_S3_RGB.png")

if __name__ == "__main__":
    main()
