"""
InfraGuard Sample Asset Generator
Generates sample inspection telemetry CSV and demonstration inspection imagery
across Roads, Bridges, Pipelines, and Power Grids into data/sample/.
"""

import math
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image, ImageDraw

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def generate_telemetry_csv():
    base_time = datetime.utcnow()
    start_lat = 11.6643
    start_lng = 78.1460
    
    samples = 150
    rows = ["timestamp,lat,lng,speed_kmh,accel_x,accel_y,accel_z,vibration_level"]
    curr_lat, curr_lng = start_lat, start_lng
    
    for i in range(samples):
        t = base_time + timedelta(seconds=i * 0.1)
        speed = 45.0 + math.sin(i * 0.05) * 5.0
        curr_lat += 0.00004
        curr_lng += 0.00006
        
        # Simulated pothole impact at index 55-65
        if 55 <= i <= 65:
            az = round(4.8 + math.sin(i) * 2.2, 3)
            vib = round(3.4 + math.sin(i) * 1.5, 3)
        # Simulated bridge joint bump at index 110-118
        elif 110 <= i <= 118:
            az = round(2.9 + math.cos(i) * 1.4, 3)
            vib = round(2.2 + math.cos(i) * 0.9, 3)
        else:
            az = round(0.15 + (math.sin(i * 0.3) * 0.25), 3)
            vib = round(0.35 + (math.cos(i * 0.2) * 0.15), 3)

        ax = round(math.sin(i * 0.1) * 0.1, 3)
        ay = round(math.cos(i * 0.1) * 0.1, 3)

        rows.append(f"{t.isoformat()},{curr_lat:.6f},{curr_lng:.6f},{speed:.1f},{ax},{ay},{az},{vib}")

    csv_path = SAMPLE_DIR / "nh544_salem_inspection_telemetry.csv"
    csv_path.write_text("\n".join(rows), encoding="utf-8")
    print(f"Generated sample telemetry CSV: {csv_path.name}")

def generate_sample_images():
    # 1. Road Pothole
    img_road = Image.new("RGB", (640, 480), color="#374151")
    draw_road = ImageDraw.Draw(img_road)
    # Road markings
    for y in range(0, 480, 50):
        draw_road.rectangle([315, y, 325, y + 30], fill="#fef08a")
    # Pothole cavity
    draw_road.ellipse([260, 200, 400, 300], fill="#111827", outline="#000000", width=3)
    # Radiating cracks
    draw_road.line([(260, 250), (200, 270), (160, 250)], fill="#0f172a", width=3)
    draw_road.line([(400, 250), (460, 230), (510, 260)], fill="#0f172a", width=3)
    img_road.save(SAMPLE_DIR / "sample_road_pothole.jpg", "JPEG", quality=90)

    # 2. Bridge Concrete Crack & Spall
    img_bridge = Image.new("RGB", (640, 480), color="#94a3b8")
    draw_bridge = ImageDraw.Draw(img_bridge)
    # Pier joints
    draw_bridge.rectangle([0, 100, 640, 110], fill="#475569")
    # Severe concrete spalling & exposed rebar
    draw_bridge.polygon([(220, 180), (440, 170), (460, 310), (200, 330)], fill="#475569", outline="#1e293b", width=2)
    # Rebar grid (rusty orange)
    draw_bridge.line([(250, 200), (250, 300)], fill="#ea580c", width=5)
    draw_bridge.line([(310, 195), (310, 295)], fill="#ea580c", width=5)
    draw_bridge.line([(370, 190), (370, 305)], fill="#ea580c", width=5)
    draw_bridge.line([(230, 230), (430, 220)], fill="#c2410c", width=5)
    draw_bridge.line([(230, 270), (430, 265)], fill="#c2410c", width=5)
    img_bridge.save(SAMPLE_DIR / "sample_bridge_spall.jpg", "JPEG", quality=90)

    # 3. Pipeline Internal CCTV Crack
    img_pipe = Image.new("RGB", (640, 480), color="#1e293b")
    draw_pipe = ImageDraw.Draw(img_pipe)
    # Circular pipe perspective
    for r in range(230, 50, -35):
        draw_pipe.ellipse([320 - r, 240 - r, 320 + r, 240 + r], outline="#475569", width=2)
    # Circumferential fracture
    draw_pipe.arc([160, 80, 480, 400], start=30, end=170, fill="#f87171", width=5)
    draw_pipe.line([(220, 340), (200, 420)], fill="#ef4444", width=4)
    img_pipe.save(SAMPLE_DIR / "sample_pipeline_fracture.jpg", "JPEG", quality=90)

    # 4. Power Grid Insulator String
    img_grid = Image.new("RGB", (640, 480), color="#60a5fa")  # Sky background
    draw_grid = ImageDraw.Draw(img_grid)
    # Transmission crossarm steel lattice
    draw_grid.polygon([(200, 60), (440, 60), (420, 100), (220, 100)], fill="#334155")
    # Ceramic insulator discs
    for y in range(100, 320, 35):
        fill_col = "#e2e8f0"
        if y == 205:  # Broken flashover disc
            fill_col = "#7f1d1d"
            draw_grid.ellipse([275, y, 365, y + 25], fill=fill_col, outline="#000000", width=2)
            draw_grid.polygon([(290, y), (310, y + 20), (325, y - 5)], fill="#fef08a")  # flash mark
        else:
            draw_grid.ellipse([280, y, 360, y + 25], fill=fill_col, outline="#475569", width=2)
    # Suspended conductor line
    draw_grid.line([(0, 330), (320, 335), (640, 330)], fill="#0f172a", width=6)
    img_grid.save(SAMPLE_DIR / "sample_powergrid_insulator.jpg", "JPEG", quality=90)

    print("Generated 4 sector sample inspection images in data/sample/.")

if __name__ == "__main__":
    generate_telemetry_csv()
    generate_sample_images()
