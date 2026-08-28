# Ultra-Dense Visual Storage Code (UVSC)

**UVSC** is an advanced optical data storage research project. It transcends traditional QR codes by fundamentally treating physical visual space as an ultra-high-density storage medium. The project mathematically proves that by stacking multi-level visual states (RGB), lossless compression, cryptography, and time-domain sequencing, it is possible to store massive files entirely as visual light—bypassing the need for URLs, cloud storage, or internet connections.

---

## 🚀 Features

The UVSC architecture successfully implements every phase of modern high-density optical storage:

- **Mathematical Density Scaling:** Supports `S=2` (Binary), `S=16` (Grayscale), and `S=4096` (RGB) encoding modes to exponentially increase capacity.
- **Time-Domain Video Sequencing ($L$ Layers):** Bypasses spatial capacity limits by chunking massive files into animated `.gif` video sequences (flashing visual codes).
- **Lossless Compression:** Integrates `zlib` to shrink payloads before physical encoding.
- **Military-Grade Security:** Optional AES-256 encryption using SHA-256 derived passwords via `cryptography`.
- **Industrial Error Correction:** Uses Reed-Solomon (`reedsolo`) ECC to scrub optical damage, camera blur, glare, and missing pixels.
- **Mathematical Data Interleaving:** Violently shuffles the byte array across the physical grid to protect against concentrated physical scratches.
- **Cryptographic Verification:** Automatically injects a SHA-256 fingerprint into the payload to guarantee bit-for-bit perfect reconstruction.
- **Autonomous Live Camera Scanning:** Features a built-in OpenCV 4-Point Perspective Warp engine to flatten and scan physical photos via webcam in real-time.

---

## 🧮 The Extended Visual Storage Formula

The project revolves around pushing the limits of this core equation:

$$ C_{\rm GB} = \frac{ W H }{ 8d^2(10^9) } \log_2(S) L (1-E) R Q $$

Where:
- $W \times H$ = Physical Area
- $d$ = Minimum cell size
- $S$ = Visual States (e.g., 4096 for RGB)
- $L$ = Optical Layers (Video frames)
- $E$ = ECC Overhead (Reed-Solomon)
- $R \times Q$ = Optical/Quantization Reliability (OpenCV Alignment)

---

## 🛠️ Installation & Setup

1. **Clone/Download the repository**
2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate # On Mac/Linux
   ```
3. **Install the required dependencies:**
   ```bash
   pip install streamlit opencv-python numpy reedsolo cryptography imageio pillow
   ```
4. **Run the Interactive Research Dashboard:**
   ```bash
   streamlit run app.py
   ```

---

## 🖥️ Using the Dashboard

The dashboard runs locally in your browser at `http://localhost:8501`.

### Tab 1: The Encoder
Upload any file (text, images, PDFs, etc.). Select your encoding mode and optional password. The engine will compress, encrypt, interleave, and encode the file into a UVSC grid. If the file is massive, it will generate an animated `.gif` video sequence! You can download the generated visual artifact.

### Tab 2: The Autonomous Decoder
Upload the `.png` or `.gif` artifact, OR select **Live Camera Scan** to point your webcam at a physical screen/paper. The decoder will automatically read the Universal Binary Header, configure its extraction engine, warp the perspective, scrub the damage, and download the exact original file!

### Tab 3: The 40GB Prover
An interactive mathematical calculator that lets you slide variables (Printer DPI, Paper Size, Visual States) to mathematically prove the feasibility of storing 30–40 GB of data on a single sheet of physical paper.

---

## 🔬 Scientific Honesty & Reality
While a 4K digital image can technically hold megabytes of data, *physical optical recovery* is constrained by the camera's resolution, lens MTF, and ambient lighting. This software uses **Computer Vision (OpenCV)** and **Error Correction (Reed-Solomon)** to bridge the gap between theoretical math and messy physical reality.

*Developed as a mathematical proof-of-concept for Ultra-Dense Visual Storage.*
