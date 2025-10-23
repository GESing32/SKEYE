# SKEYE | NDVI Vision and User Interface System
University of Kentucky – Computer Engineering Senior Design (CPE490/491)
Subsystem: Vision and User Interface
Author: Alessandra Lozano

-----------------------------------------------------------------------
PROJECT OVERVIEW
-----------------------------------------------------------------------
This subsystem detects nitrogen deficiency in crops using multispectral
drone imagery and presents results through a Flutter-based user interface.
The backend is a FastAPI Python server that computes NDVI/NDRE indices
from Near-Infrared (NIR) and Red channel images. TensorFlow, OpenCV, and
NumPy are used for processing, while the UI provides NDVI visualization,
mission-planning layouts, and coordinate-based geostitch previews.

-----------------------------------------------------------------------
DATA FLOW
-----------------------------------------------------------------------
Flutter or Web UI  -->  FastAPI Server  -->  NDVI ML Engine
 - Upload NIR + Red images            - Receives uploads
 - View NDVI maps & statistics        - Computes NDVI
 - Tabs: NDVI, Planning, Stitching    - Returns PNG + JSON

-----------------------------------------------------------------------
REPOSITORY STRUCTURE
-----------------------------------------------------------------------
drone_app_files/
│
├── flutter/                   # Flutter frontend project
│   ├── lib/                   # Flutter source files
│   ├── pubspec.yaml           # Flutter dependencies
│   └── ...                    # Flutter assets / widgets
│
├── lib/                       # Shared Flutter modules
│
├── ndvi_web/                  # NDVI web and backend system
│   ├── web/
│   │   └── index.html         # Web UI (NDVI interface)
│   │
│   ├── server/
│   │   ├── server.py          # FastAPI backend
│   │   ├── drone_vision_ML.py # CNN training utilities
│   │   ├── training_script_dd1.py # NDVI + NDRE training script
│   │   └── ndvi_ndre_cnn_model_balanced.h5 # Trained model
│   │
│   ├── requirements.txt       # Python dependencies
│   └── ndvi_predictions.csv   # Example output
│
└── README.md

-----------------------------------------------------------------------
DATA STRUCTURE
-----------------------------------------------------------------------
Spectral_Images1/
│
├── Near_Infrared_Channel/
│   ├── Train_Images/
│   └── Test_Images/
│
├── Red_Channel/
│   ├── Train_Images/
│   └── Test_Images/
│
├── Red_Edge_Channel/          # Optional for NDRE model
│   ├── Train_Images/
│   └── Test_Images/
│
└── Labels/
    ├── Train_labels.csv
    └── Test_labels.csv

Each label file follows the format:
filename, xmin, ymin, xmax, ymax, class
example:
potato_001.jpg, 34, 42, 310, 295, healthy

-----------------------------------------------------------------------
RUNNING THE PROJECT (FULL PIPELINE)
-----------------------------------------------------------------------

1. Clone the repository
   git clone https://github.com/GESing32/SKEYE.git
   cd SKEYE
   git checkout User-Interface

2. Set up the Python environment
   cd drone_app_files
   python -m venv crops-env
   .\crops-env\Scripts\Activate.ps1

3. Install backend dependencies
   pip install -r ndvi_web/requirements.txt

4. Run the FastAPI backend
   uvicorn ndvi_web.server.server:app --reload

   Expected output:
   Uvicorn running on http://127.0.0.1:8000

   Keep this terminal open for backend communication.

5. Run the Flutter frontend (Option A: Flutter web)
   cd flutter
   flutter run -d chrome

   This launches the UI in Chrome and connects to http://127.0.0.1:8000

6. Run the HTML web interface (Option B - easiest in my opinion)
   cd ndvi_web/web
   python -m http.server 5500
   Open browser: http://localhost:5500/index.html

   In the UI, ensure the API field says:
   http://127.0.0.1:8000

7. Upload data
   - Select NIR image and corresponding Red image
   - Click "Compute NDVI"
   - NDVI map + statistics (mean, min, max, shape) will appear

8. Optional model training
   python ndvi_web/server/training_script_dd1.py

   Output: ndvi_ndre_cnn_model_balanced.h5

9. Data output examples
   NDVI JSON:
   {
     "mean": 0.54,
     "min": -0.22,
     "max": 0.88,
     "shape": [416, 416]
   }

   NDVI image:
   Base64 PNG, automatically displayed in browser

-----------------------------------------------------------------------
UI LAYOUT DESCRIPTION
-----------------------------------------------------------------------
WELCOME PAGE
 - Overview of SKEYE and how to use interface

NDVI DETECTION TAB
 - Upload NIR + Red images
 - Compute NDVI and visualize vegetation health
 - Displays mean, min, max NDVI

AUTONOMOUS PLANNING TAB
 - Grid-based mission planning layout
 - Placeholder boxes: Mission Map, Route Path, Flight Parameters

GEO-STITCHING TAB
 - Coordinate-based layout for image alignment
 - Placeholder boxes: Coordinate Import, Grid Map, Projection, Alignment, Export

-----------------------------------------------------------------------
DESIGN CHOICES
-----------------------------------------------------------------------
- Flutter chosen for cross-platform UI (web + desktop)
- FastAPI used for efficient asynchronous image processing
- Tabbed layout mirrors subsystem separation (Vision, Flight, Mapping)
- Grid backgrounds mimic drone mission grids and geospatial alignment
- Dark theme highlights NDVI red-green gradients
- Modular folder structure for scalability and integration

-----------------------------------------------------------------------
TESTING VERIFICATION
-----------------------------------------------------------------------
Requirement   | Description                            | Result
--------------|----------------------------------------|---------
ER#7          | Data analysis accuracy ≥ 90%           | Achieved 90% on potato dataset
ER#8          | Multispectral image capture functional  | Verified
ER#11         | Drone weight ≤ 4.6 lbs                 | Passed
ER#16         | Nitrogen model accuracy ≥ 75%          | 90% accuracy
ER#17         | Budget under $8,000                    | Total: $4,950

-----------------------------------------------------------------------
FUTURE ENHANCEMENTS
-----------------------------------------------------------------------
- Integrate real-time telemetry and mission upload to drone
- Implement true coordinate-based geostitching
- Add onboard NDVI computation for live feedback
- Expand model for multiple vegetation indices (NDRE, SAVI)
- Field data logging and cloud analytics dashboard

-----------------------------------------------------------------------
CONTACT
-----------------------------------------------------------------------
Author: Alessandra Lozano
Subsystem: Vision & User Interface
Email: your-email@uky.edu

-----------------------------------------------------------------------
LICENSE
-----------------------------------------------------------------------
Developed for educational use under the University of Kentucky
Senior Design Program 2025.
© 2025 Team SKEYE. All rights reserved.
