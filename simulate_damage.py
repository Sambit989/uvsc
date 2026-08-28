import cv2
import numpy as np
import sys

def apply_damage(img_path, output_path):
    img = cv2.imread(img_path)
    if img is None:
        print(f"Could not read {img_path}")
        return

    print("Original image loaded.")
    
    # 1. Add Gaussian Blur (Simulating out-of-focus camera)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    print("Applied Gaussian Blur.")
    
    # 2. Add Gaussian Noise (Simulating smartphone camera grain)
    noise = np.zeros(img.shape, np.uint8)
    cv2.randn(noise, 0, 5) # Variance 5
    noisy = cv2.add(blur, noise)
    print("Applied Gaussian Noise.")
    
    # 3. Save with JPEG Compression (Simulating photo compression artifacts)
    # JPEG Quality 90
    cv2.imwrite(output_path, noisy, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    print(f"Saved damaged image to {output_path} (JPEG Quality 90)")

def main():
    if len(sys.argv) < 3:
        print("Usage: python simulate_damage.py <input.png> <output.jpg>")
    else:
        apply_damage(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
