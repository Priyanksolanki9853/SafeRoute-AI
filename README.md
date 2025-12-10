# 🛡️ SafeRoute AI | AI-Powered Accident Prevention System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![AI](https://img.shields.io/badge/AI-Google%20Gemini-orange)
![Mapping](https://img.shields.io/badge/Mapping-OSMnx%20%7C%20Leaflet-blueviolet)
![Status](https://img.shields.io/badge/Status-Live-success)

> **Final Major Project 2025** > *Engineering safer futures by prioritizing survival over speed.*

---

## 📖 Overview

Conventional navigation apps (Google Maps, Waze) optimize for **time** and **distance**. They often route drivers through hazardous blackspots, narrow lanes, or unlit roads just to save a few seconds.

**SafeRoute AI** represents a paradigm shift in routing logic. By fusing satellite imagery, geometric vector analysis (road curvature), and real-time environmental data, we calculate a **Probabilistic Safety Score (0-100)** for every route. We don't just tell you the fastest way; we tell you the safest way.

---

## 🚀 Key Features

### 🧠 1. Geometric Risk Analysis
* Uses **OSMnx & NetworkX** to download real-world road networks.
* Calculates **Road Curvature** using vector math to identify sharp, dangerous turns.
* Detects infrastructure risks like **Narrow Roads**, **Poor Lighting**, and **High-Speed Zones**.

### 🤖 2. SafeBot (AI Assistant)
* Integrated **Google Gemini 2.5 Flash-Lite** LLM.
* Provides real-time advice on road safety, first aid protocols, and route details.
* **Smart Fallback System:** Automatically switches to an internal rule-based mode if the internet connection is unstable.

### 🌍 3. Live Environmental Data
* **Real-time AQI (Air Quality Index):** Fetched via Open-Meteo API to warn drivers of low visibility due to smog/pollution.
* **Weather Integration:** Live temperature and condition monitoring.

### 🆘 4. Emergency & Utility Suite
* **SOS Panic Button:** One-click access to National Emergency (112), Police (100), and Ambulance (102).
* **Simulated Computer Vision:** Analyzes road surface quality (Simulated for cloud optimization).
* **Dark/Light Mode:** Aesthetic UI with Glassmorphism design.

---

## 🛠️ Tech Stack

| Component | Technology Used |
|-----------|----------------|
| **Frontend** | HTML5, CSS3 (Glassmorphism), JavaScript (ES6) |
| **Mapping** | Leaflet.js, OpenStreetMap (OSM) |
| **Backend** | Python 3, Flask (RESTful API) |
| **Data & Graph** | OSMnx, NetworkX, NumPy, Pandas |
| **AI Model** | Google Gemini 2.5 Flash-Lite (via API) |
| **Weather API** | Open-Meteo API |
| **Deployment** | Render Cloud (Gunicorn Server) |

---

## ⚙️ Architecture & Optimization
Running complex AI and Graph computations on a free cloud tier (512MB RAM) required significant engineering optimization:

1.  **Dynamic Radius Calculation:** The backend calculates the exact distance between points and only downloads the specific map chunk needed (clamped to 2.5km) to prevent OOM (Out of Memory) crashes.
2.  **Lazy Loading:** Heavy libraries like `cv2` (OpenCV) are only imported into memory when specifically requested.
3.  **Garbage Collection:** Aggressive Python `gc.collect()` calls ensure memory is freed immediately after route generation.

---

## 📸 Screenshots

*(Add screenshots of your Dashboard, Route Analysis, and Chatbot here)*

---

## 💻 How to Run Locally

If you want to run this project on your own machine for full performance (unlimited range):

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/Priyanksolanki9853/accident-route-advisor.git](https://github.com/Priyanksolanki9853/accident-route-advisor.git)
    cd accident-route-advisor
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up API Key**
    * Create a `.env` file or set it in your terminal:
    * `export GEMINI_API_KEY="your_google_api_key_here"`

4.  **Run the Server**
    ```bash
    python app.py
    ```

5.  **Access the App**
    * Open your browser and go to: `http://127.0.0.1:5000`

---

## 🤝 Contact & Privacy

* **Developer:** [Your Name]
* **Contact:** [priyanksolanki9853@gmail.com](mailto:priyanksolanki9853@gmail.com)
* **Privacy Policy:** This application processes location data in real-time for routing purposes only. No user location history is stored on our servers.

---
*© 2025 SafeRoute AI. Designed for Safer Roads.*
