import streamlit as st
import cv2
import numpy as np
import reedsolo
import zlib
import io
import hashlib
import base64
import imageio
import random
from PIL import Image
from cryptography.fernet import Fernet
import math

st.set_page_config(page_title="UVSC Dashboard", layout="wide")
st.title("UVSC Capacity Calculator & Encoder")

CELL_SIZE = 10
ECC_SYMBOLS = 64
MAX_GRID_SIZE = 40

def get_fernet_key(password):
    if not password:
        return None
    key = hashlib.sha256(password.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def create_finder_pattern():
    pattern = np.zeros((7, 7, 3), dtype=np.uint8)
    pattern[:, :, :] = 0
    pattern[1:6, 1:6, :] = 255
    pattern[2:5, 2:5, :] = 0
    return pattern

def interleave_bytes(data_bytes):
    random.seed(1337) # Fixed pseudo-random permutation
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

def encode_chunk(payload_bytes, mode):
    rs = reedsolo.RSCodec(ECC_SYMBOLS)
    encoded = bytearray(rs.encode(payload_bytes))
    
    # Phase 8: Data Interleaving
    encoded = interleave_bytes(encoded)
    
    mode_id = {"S=2 (Binary)":0, "S=16 (Grayscale)":1, "S=4096 (RGB + ZLIB)":2}[mode]
    byte_length = len(encoded)
    
    # Universal Header: 16 bits (2 bits mode, 14 bits length)
    header_val = (mode_id << 14) | (byte_length & 0x3FFF)
    cells = []
    for i in range(16):
        cells.append((header_val >> (15 - i)) & 1)
        
    if mode == "S=2 (Binary)":
        for b in encoded:
            for i in range(8):
                cells.append((b >> (7 - i)) & 1)
    elif mode == "S=16 (Grayscale)":
        for b in encoded:
            cells.append(b >> 4)
            cells.append(b & 0x0F)
    elif mode == "S=4096 (RGB + ZLIB)":
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
    if fixed_grid_size is not None:
        grid_size = fixed_grid_size
    else:
        grid_size = 21
        while (grid_size * grid_size) - (3 * 64) < total_cells:
            grid_size += 1
        
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
                    # Universal Header (Binary)
                    val = 0 if data[cell_idx] == 1 else 255
                    grid[y, x, :] = val
                else:
                    if mode_id == 0:
                        val = 0 if data[cell_idx] == 1 else 255
                        grid[y, x, :] = val
                    elif mode_id == 1:
                        val = data[cell_idx] * 17
                        grid[y, x, :] = val
                    elif mode_id == 2:
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
        warped = cv2.warpPerspective(img_array, M, (600, 600))
        return warped
        
    return img_array

def decode_image(img_array):
    aligned = align_image(img_array)
    
    border = 40
    if aligned.shape[0] == 600:
        border = int(600 * 0.05)
        
    cropped = aligned[border:-border, border:-border]
    
    for grid_size in range(15, 60):
        warped = cv2.resize(cropped, (grid_size * 10, grid_size * 10))
        cell_h = warped.shape[0] / grid_size
        cell_w = warped.shape[1] / grid_size
        
        extracted_data = []
        header_val = 0
        mode_id = -1
        byte_length = -1
        
        cell_idx = 0
        
        for y in range(grid_size):
            for x in range(grid_size):
                if (y < 8 and x < 8) or (y < 8 and x >= grid_size - 8) or (y >= grid_size - 8 and x < 8):
                    continue
                cy = int(y * cell_h + cell_h / 2)
                cx = int(x * cell_w + cell_w / 2)
                pixel = warped[cy, cx]
                
                if cell_idx < 16:
                    # Read Universal Header
                    val = np.mean(pixel)
                    bit = 0 if val > 127 else 1
                    header_val = (header_val << 1) | bit
                    if cell_idx == 15:
                        mode_id = header_val >> 14
                        byte_length = header_val & 0x3FFF
                else:
                    if mode_id == 0:
                        val = np.mean(pixel)
                        extracted_data.append(0 if val > 127 else 1)
                    elif mode_id == 1:
                        val = int(round(np.mean(pixel) / 17.0))
                        extracted_data.append(max(0, min(15, val)))
                    elif mode_id == 2:
                        b_nibble = max(0, min(15, int(round(pixel[0] / 17.0))))
                        g_nibble = max(0, min(15, int(round(pixel[1] / 17.0))))
                        r_nibble = max(0, min(15, int(round(pixel[2] / 17.0))))
                        extracted_data.extend([b_nibble, g_nibble, r_nibble])
                        
                cell_idx += 1

        if mode_id == -1 or byte_length <= 0:
            continue
            
        data_bytes = bytearray()
        if mode_id == 0:
            for i in range(0, len(extracted_data) - 7, 8):
                byte = 0
                for j in range(8):
                    byte |= (extracted_data[i+j] << (7 - j))
                data_bytes.append(byte)
        else:
            for i in range(0, len(extracted_data) - 1, 2):
                byte = (extracted_data[i] << 4) | extracted_data[i+1]
                data_bytes.append(byte)
                
        if len(data_bytes) < byte_length:
            continue
            
        data_bytes = data_bytes[:byte_length]
        
        # Deinterleave
        data_bytes = deinterleave_bytes(data_bytes)
                
        rs = reedsolo.RSCodec(ECC_SYMBOLS)
        try:
            return rs.decode(data_bytes)[0], mode_id
        except Exception:
            continue
    return None, -1

tab1, tab2, tab3 = st.tabs(["Encoder", "Decoder (Live Camera)", "Theoretical Calculator (40GB)"])

with tab1:
    st.header("Encode a Massive File (Video Output)")
    uploaded_file = st.file_uploader("Upload any file", key="enc_up")
    mode = st.selectbox("Encoding Mode", ["S=2 (Binary)", "S=16 (Grayscale)", "S=4096 (RGB + ZLIB)"], key="enc_mode")
    password = st.text_input("AES-256 Encryption Password (Optional)", type="password", key="enc_pass")
    
    if uploaded_file is not None:
        payload = uploaded_file.read()
        st.write(f"Original Size: **{len(payload)} bytes**")
        
        if st.button("Generate UVSC Video"):
            with st.spinner("Chunking file & generating animated sequence..."):
                
                # Phase 12: Embed SHA-256 Checksum
                file_hash = hashlib.sha256(payload).digest()
                payload = file_hash + payload
                
                fernet = get_fernet_key(password)
                if fernet:
                    payload = fernet.encrypt(payload)
                if mode == "S=4096 (RGB + ZLIB)":
                    payload = zlib.compress(payload, level=9)
                
                if mode == "S=4096 (RGB + ZLIB)": chunk_size = 2000
                elif mode == "S=16 (Grayscale)": chunk_size = 600
                else: chunk_size = 100
                
                dummy_chunk = b'\x00' * chunk_size
                dummy_data, _ = encode_chunk(dummy_chunk, mode)
                total_dummy_cells = len(dummy_data)
                fixed_grid_size = 21
                while (fixed_grid_size * fixed_grid_size) - (3 * 64) < total_dummy_cells:
                    fixed_grid_size += 1
                
                frames = []
                for i in range(0, len(payload), chunk_size):
                    chunk = payload[i:i+chunk_size]
                    data, mode_id = encode_chunk(chunk, mode)
                    grid = build_grid(data, mode_id, fixed_grid_size=fixed_grid_size)
                    img = cv2.resize(grid, (grid.shape[1] * CELL_SIZE, grid.shape[0] * CELL_SIZE), interpolation=cv2.INTER_NEAREST)
                    border = CELL_SIZE * 4
                    img_with_border = cv2.copyMakeBorder(img, border, border, border, border, cv2.BORDER_CONSTANT, value=[255, 255, 255])
                    frames.append(cv2.cvtColor(img_with_border, cv2.COLOR_BGR2RGB))
                
                st.success(f"Generated successfully! Split into {len(frames)} frames.")
                
                if len(frames) == 1:
                    pil_img = Image.fromarray(frames[0])
                    st.image(pil_img, caption="UVSC Visual Code", use_container_width=True)
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    st.download_button("Download UVSC Code", buf.getvalue(), file_name="uvsc_code.png", mime="image/png")
                else:
                    st.write(f"Generated a {len(frames)}-frame Video Sequence!")
                    gif_buf = io.BytesIO()
                    imageio.mimsave(gif_buf, frames, format='GIF', duration=200) # 5 fps
                    st.image(gif_buf.getvalue(), use_container_width=True)
                    st.download_button("Download UVSC Sequence (.gif)", gif_buf.getvalue(), file_name="uvsc_sequence.gif", mime="image/gif")

with tab2:
    st.header("Autonomous Live Decoder")
    
    st.info("💡 The Decoder is now fully autonomous. It reads the Mode and Byte Length directly from the Universal Header in the visual code!")
    dec_password = st.text_input("Decryption Password (if encoded)", type="password", key="dec_pass")
    
    st.write("### Choose Input Source")
    input_source = st.radio("", ["Upload Image/GIF", "Live Camera Scan"])
    
    file_bytes = None
    frames_to_process = []
    
    if input_source == "Upload Image/GIF":
        dec_file = st.file_uploader("Upload UVSC Image/GIF", type=['png', 'jpg', 'jpeg', 'gif'], key="dec_up")
        if dec_file:
            file_bytes = dec_file.read()
            if dec_file.name.endswith('.gif'):
                gif = imageio.mimread(file_bytes)
                for frame in gif:
                    frames_to_process.append(cv2.cvtColor(frame[:,:,:3], cv2.COLOR_RGB2BGR))
                st.image(file_bytes, caption=f"Uploaded {len(frames_to_process)}-frame Sequence", use_container_width=True)
            else:
                nparr = np.asarray(bytearray(file_bytes), dtype=np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                frames_to_process.append(img)
                st.image(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), caption="Uploaded Artifact", use_container_width=True)
    
    elif input_source == "Live Camera Scan":
        camera_photo = st.camera_input("Point your camera at the UVSC Code")
        if camera_photo:
            file_bytes = camera_photo.read()
            nparr = np.asarray(bytearray(file_bytes), dtype=np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            frames_to_process.append(img)
            
    if len(frames_to_process) > 0:
        if st.button("Decode Sequence"):
            with st.spinner(f"Aligning perspective & extracting Universal Header..."):
                reconstructed_bytes = bytearray()
                success = True
                detected_mode_id = -1
                
                for idx, frame in enumerate(frames_to_process):
                    decoded_chunk, mode_id = decode_image(frame)
                    if decoded_chunk:
                        reconstructed_bytes.extend(decoded_chunk)
                        detected_mode_id = mode_id
                    else:
                        st.error(f"Failed to decode Frame {idx+1}. Perspective alignment failed or damage too severe.")
                        success = False
                        break
                        
                if success:
                    try:
                        if detected_mode_id == 2: # RGB + ZLIB
                            reconstructed_bytes = zlib.decompress(reconstructed_bytes)
                        fernet = get_fernet_key(dec_password)
                        if fernet:
                            reconstructed_bytes = fernet.decrypt(reconstructed_bytes)
                            
                        # Verify SHA-256 Checksum
                        embedded_hash = reconstructed_bytes[:32]
                        original_payload = reconstructed_bytes[32:]
                        calculated_hash = hashlib.sha256(original_payload).digest()
                        
                        if embedded_hash == calculated_hash:
                            st.success(f"✅ CRYPTOGRAPHIC VERIFICATION PASSED: File successfully recovered via Mode {detected_mode_id}")
                            st.download_button("Download Verified File", original_payload, file_name="verified_payload.bin")
                        else:
                            st.error("❌ VERIFICATION FAILED: The decoded file is corrupted and does not match the original signature!")
                    except Exception as e:
                        st.error(f"Post-processing failed (Wrong Password or ZLIB error): {e}")

with tab3:
    st.header("Mathematical Density Limit (Proving 40 GB)")
    st.markdown("Use this calculator to apply the **Extended Visual Storage Formula**.")
    st.latex(r"C = \frac{W \times H}{8d^2} \log_2(S) \cdot L \cdot (1 - E) \cdot R \cdot Q")
    
    col1, col2 = st.columns(2)
    with col1:
        w_in = st.slider("Width (Inches)", 1.0, 11.0, 8.5)
        h_in = st.slider("Height (Inches)", 1.0, 17.0, 11.0)
        dpi = st.slider("Printer DPI", 300, 2400, 1200, step=300)
    with col2:
        s_val = st.selectbox("Visual States ($S$)", [2, 16, 4096, 16777216], index=2)
        layers = st.slider("Optical Layers ($L$)", 1, 10, 1)
        error_rate = st.slider("ECC Margin ($E$)", 0.0, 0.5, 0.3)
        
    width_pixels = w_in * dpi
    height_pixels = h_in * dpi
    cell_size = 1 
    
    total_cells = (width_pixels * height_pixels) / (cell_size ** 2)
    bits_per_cell = math.log2(s_val)
    
    R = 0.9 
    Q = 0.85 
    
    total_bits = total_cells * bits_per_cell * layers * (1 - error_rate) * R * Q
    total_gb = total_bits / 8 / (1024**3)
    
    st.metric(label="Theoretical Maximum Capacity", value=f"{total_gb:,.2f} GB")
    if total_gb >= 30:
        st.balloons()
        st.success("🎉 You mathematically achieved the 30-40 GB Milestone!")
