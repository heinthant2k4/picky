

# 🤖 Dobot Cube Stacking Competition System

An **integrated robotics and computer vision project** that uses a Dobot robotic arm to participate in a **cube stacking competition**.
This system combines **robot control**, **vision-based grid detection**, and **competition strategy execution**, with tools for **testing**, **calibration**, and **practice**.

---

## ✨ Features

* **Competition Mode**

  * Initialize robot and vision system
  * Capture grid colors with camera
  * Suggest stacking strategies or allow manual input
  * Execute stacking sequence with retries and performance feedback

* **Practice Mode**

  * Test robot movements, vision, and pickup sequences
  * Perform calibration safely

* **Vision System**

  * Adaptive color detection using HSV ranges
  * Lighting analysis and validation
  * Interactive grid detection for 3×3 playfield

* **Robot Control**

  * Error-handled connection with retry
  * Safe calibration loading/creation
  * Adaptive stacking (fast/slow speed profiles, suction retries, gentle release for higher levels)
  * Emergency stop and safe position handling

* **Testing & Calibration Tools**

  * Robot and camera connectivity tests
  * Interactive calibration with gap measurement
  * Position monitoring with safety alerts
  * Color detection validation
  * Comprehensive system health test

---

## 📂 Project Structure

```
.
├── competition_controller.py        # Main entry point (competition & practice modes)
├── testing_and_calibration_tools.py # Standalone utilities for testing/calibration
├── dobot_controller.py              # Robot control module (Dobot API wrapper)
├── vision_system.py                 # Vision detection module for color grids
├── calibration.json                 # Generated after calibration (stores home/gap)
├── vision_config.json               # Vision configuration (color thresholds)
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/heinthant2k4/picky.git
cd picky
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install system requirements

* **Linux/macOS**:

  * Ensure `/dev/ttyUSB0` permissions are set for the Dobot:

    ```bash
    sudo chmod 666 /dev/ttyUSB0
    ```
* **Windows**:

  * Install appropriate USB drivers for Dobot.

### 5. Verify installation

Run the system test utility:

```bash
python testing_and_calibration_tools.py
```

---

## 📦 Dependencies

Your `requirements.txt` should include:

```
opencv-python
numpy
pydobot
```

(You can extend this as needed.)

---

## 🚀 Usage

### Start Competition

```bash
python competition_controller.py
```

* **Mode 1**: Competition
* **Mode 2**: Practice

### Run Testing & Calibration Tools

```bash
python testing_and_calibration_tools.py
```

Menu options:

1. Comprehensive System Test
2. Test Robot Connection
3. Test Camera Connection
4. Interactive Calibration
5. Position Monitor
6. Color Detection Test

---

## 🔧 Calibration Workflow

1. Run interactive calibration:

   ```bash
   python testing_and_calibration_tools.py
   ```

   → Choose option **4**.
2. Position the robot at the **HOME** (center grid, safe height).
3. Move robot to **GAP reference position** (1 block right, forward, 1 block height up).
4. Save calibration → generates `calibration.json`.
5. Calibration is auto-loaded by the system.

---

## 📸 Vision System

* Uses OpenCV to capture camera input and detect colored cubes.
* Supported colors: **Red, Green, Blue, Yellow**.
* Runs adaptive HSV detection with lighting analysis.
* Displays a live preview with overlays, grid labeling, and stability tracking.

---

## 🏆 Competition Flow

1. **Initialize system** (robot & vision)
2. **Capture grid** (camera detects cube colors)
3. **Strategy input**

   * Accept AI suggestion (prioritizes most available colors)
   * Or enter manually (bottom → top)
4. **Execute stacking sequence**

   * Robot picks cubes from grid and stacks tower of 4
   * Automatic retry on failed pickups
5. **Results summary**

   * Success rate
   * Time taken
   * Performance feedback

---

## ⚠️ Safety Notes

* Always supervise the robot during operation.
* Ensure workspace is clear before starting.
* Use **Practice Mode** for testing before competitions.
* Use **Ctrl+C** to safely interrupt execution (triggers emergency stop).

---

## 🛠 Troubleshooting

* **Robot not connecting**

  * Check USB cable and permissions (`sudo chmod 666 /dev/ttyUSB0`).
  * Ensure no other programs are using the Dobot.

* **Camera not detected**

  * Try different camera indices (0, 1, 2).
  * Check OpenCV installation (`pip install opencv-python`).

* **Color detection inaccurate**

  * Adjust lighting in environment.
  * Edit `vision_config.json` for HSV ranges.

* **Blocks not stacking correctly**

  * Re-run calibration.
  * Verify `calibration.json` has realistic values for `home` and `gap`.

## 📜 License

MIT License – feel free to use and modify.

---
