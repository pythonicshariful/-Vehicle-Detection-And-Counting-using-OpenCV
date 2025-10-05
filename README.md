Vehicle Detection and Counting

This project detects moving vehicles using background subtraction and counts vehicles that cross a horizontal line in the frame.

Files
- `main.ipynb` - Jupyter notebook with the video-processing loop (updated to include counting logic).
- `vehicle_counter.py` - Standalone script you can run to process `video.mp4` and show a live count.
- `requirements.txt` - Python dependencies.

Quick start
1. (Optional) Create a virtual environment and activate it.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the script:

```powershell
python vehicle_counter.py --video video.mp4
```

Notes and next steps
- The tracker is a simple centroid-based tracker; for high-accuracy counting consider using a proper multi-object tracker (e.g., SORT) or deep learning based detector.
- Tweak `min_contour_area` and `line_position` for your camera/view.
"# -Vehicle-Detection-And-Counting-using-OpenCV" 
