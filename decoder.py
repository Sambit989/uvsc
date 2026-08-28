import cv2
import numpy as np
import reedsolo
import sys
import zlib

ECC_SYMBOLS = 64

def extract_cells(warped_grid, grid_size):
    cell_h = warped_grid.shape[0] / grid_size
    cell_w = warped_grid.shape[1] / grid_size
    
    nibbles = []
    
    for y in range(grid_size):
        for x in range(grid_size):
            if (y < 8 and x < 8) or (y < 8 and x >= grid_size - 8) or (y >= grid_size - 8 and x < 8):
                continue
                
            cy = int(y * cell_h + cell_h / 2)
            cx = int(x * cell_w + cell_w / 2)
            
            b_val = warped_grid[cy, cx, 0]
            g_val = warped_grid[cy, cx, 1]
            r_val = warped_grid[cy, cx, 2]
            
            # Quantize 0-255 back to 0-15
            b_nibble = int(round(b_val / 17.0))
            g_nibble = int(round(g_val / 17.0))
            r_nibble = int(round(r_val / 17.0))
            
            b_nibble = max(0, min(15, b_nibble))
            g_nibble = max(0, min(15, g_nibble))
            r_nibble = max(0, min(15, r_nibble))
            
            nibbles.extend([b_nibble, g_nibble, r_nibble])
                
    return nibbles

def decode_data(nibbles):
    # Convert pairs of nibbles to bytes
    data_bytes = bytearray()
    for i in range(0, len(nibbles) - 1, 2):
        byte = (nibbles[i] << 4) | nibbles[i+1]
        data_bytes.append(byte)
        
    rs = reedsolo.RSCodec(ECC_SYMBOLS)
    try:
        decoded_compressed = rs.decode(data_bytes)
        # We need to slice exactly the output part
        decoded_compressed = decoded_compressed[0] 
        
        # Phase 5: Decompression
        original_payload = zlib.decompress(decoded_compressed)
        return original_payload
    except reedsolo.ReedSolomonError:
        print("ECC Failed! Too much damage.")
        return None
    except zlib.error:
        # Sometimes padding bytes at the end of the byte array confuse zlib
        # Let's try to decompress with a sliding window to ignore padding
        print("ZLIB decompression error due to padding, attempting recovery...")
        return None

def main():
    if len(sys.argv) < 2:
        img_path = "UVSC_S3_RGB.png"
    else:
        img_path = sys.argv[1]
        
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    if img is None:
        print(f"Could not read {img_path}")
        return

    print("Image loaded. Decoding...")
    
    border = 80
    cropped = img[border:-border, border:-border]
    
    for grid_size in range(15, 30):
        warped = cv2.resize(cropped, (grid_size * 10, grid_size * 10))
        
        nibbles = extract_cells(warped, grid_size)
        decoded = decode_data(nibbles)
        
        if decoded:
            print(f"\n[SUCCESS] Decoded with grid size {grid_size}")
            print(f"Recovered payload size: {len(decoded)} bytes")
            print("Payload preview:")
            print(decoded[:100].decode('utf-8', errors='ignore') + "...")
            return
            
    print("\n[FAILED] Could not decode visual code.")

if __name__ == "__main__":
    main()
