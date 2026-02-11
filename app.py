from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import random
import gc
import requests
import sys

# Conditional imports with error handling
try:
    import osmnx as ox
    import networkx as nx
    import numpy as np
    DEPENDENCIES_LOADED = True
except ImportError as e:
    print(f"WARNING: Failed to import dependencies: {e}")
    DEPENDENCIES_LOADED = False

app = Flask(__name__)
CORS(app)

# OPTIMIZATION: Strict limits to prevent server timeout
if DEPENDENCIES_LOADED:
    try:
        ox.settings.max_query_area_size = 2500000000
        ox.settings.timeout = 180
    except Exception as e:
        print(f"Warning: Could not set OSMnx settings: {e}")

@app.route('/')
def home():
    try:
        return render_template('Index.html')
    except Exception as e:
        return f"Error loading template: {e}", 500

# Health check endpoint (useful for debugging)
@app.route('/health')
def health():
    return jsonify({
        "status": "running",
        "dependencies": DEPENDENCIES_LOADED,
        "python_version": sys.version,
        "env_vars": {
            "GROQ_API_KEY": "set" if os.environ.get("GROQ_API_KEY") else "not set",
            "GEMINI_API_KEY": "set" if os.environ.get("GEMINI_API_KEY") else "not set",
            "PORT": os.environ.get("PORT", "5000")
        }
    })

# --- UPGRADED: HYBRID CHATBOT ROUTE (Never Fails) ---
@app.route('/api/chat', methods=['POST'])
def chat_proxy():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # 1. Get API Key from Server Environment
        # Supports both GROQ_API_KEY and GEMINI_API_KEY
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        
        success = False
        result_text = ""

        # 2. Try Groq API First (Recommended - Fast & Free)
        if groq_key:
            models_to_try = [
                "llama-3.3-70b-versatile",
                "llama-3.1-70b-versatile",
                "mixtral-8x7b-32768"
            ]
            
            for model in models_to_try:
                print(f"🤖 Chatbot attempting Groq: {model}...")
                url = "https://api.groq.com/openai/v1/chat/completions"
                
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are SafeBot, a road safety AI assistant. Answer questions about road safety, routes, and navigation in 1-2 clear sentences."
                        },
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7
                }
                
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    if response.status_code == 200:
                        ai_data = response.json()
                        if "choices" in ai_data and len(ai_data["choices"]) > 0:
                            result_text = ai_data["choices"][0]["message"]["content"]
                            success = True
                            print(f"✅ Success with Groq {model}")
                            break
                    else:
                        print(f"⚠️ Groq {model} returned status {response.status_code}")
                except Exception as model_error:
                    print(f"⚠️ Groq {model} failed: {model_error}")
                    continue

        # 3. Fallback to Google Gemini (if Groq fails)
        if not success and gemini_key:
            models_to_try = [
                "gemini-2.0-flash-exp",
                "gemini-1.5-flash", 
                "gemini-1.5-flash-latest"
            ]
            
            for model in models_to_try:
                print(f"🤖 Chatbot attempting Gemini: {model}...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                
                payload = {
                    "contents": [{
                        "parts": [{"text": "You are SafeBot, a road safety AI. Answer in 1-2 sentences. User: " + user_message}]
                    }]
                }
                
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    if response.status_code == 200:
                        ai_data = response.json()
                        if "candidates" in ai_data and len(ai_data["candidates"]) > 0:
                            result_text = ai_data["candidates"][0]["content"]["parts"][0]["text"]
                            success = True
                            print(f"✅ Success with Gemini {model}")
                            break
                        else:
                            print(f"⚠️ Gemini {model} returned empty response")
                    else:
                        print(f"⚠️ Gemini {model} returned status {response.status_code}")
                except Exception as model_error:
                    print(f"⚠️ Gemini {model} failed: {model_error}")
                    continue

        # 4. FALLBACK: Internal Logic (If both APIs fail)
        if not success:
            print("⚠️ All AI APIs Unreachable. Switching to Internal Safety Logic.")
            msg = user_message.lower()
            if "hello" in msg or "hi" in msg or "hey" in msg:
                result_text = "Hello! I am SafeBot. I can help you find safe routes and analyze road risks."
            elif "route" in msg or "path" in msg or "navigate" in msg:
                result_text = "Use the inputs on the left to select a Start and Destination, then click 'Analyze Route'."
            elif "risk" in msg or "score" in msg or "safe" in msg or "danger" in msg:
                result_text = "I calculate safety scores based on road curvature, lighting, and accident history. A score above 80 is safe."
            elif "aqi" in msg or "pollution" in msg or "air" in msg:
                result_text = "Click the 'Check Live AQI' button on the map to see real-time pollution levels."
            elif "help" in msg or "emergency" in msg or "sos" in msg:
                result_text = "For emergencies, use the SOS button in the navbar or call 112 immediately."
            elif "thank" in msg:
                result_text = "You're welcome! Stay safe on the roads."
            else:
                result_text = "I am currently in Offline Safety Mode. I can assist with Routes, Risks, and Emergency contacts. How can I help you?"

        # 5. Return Response (Compatible with both Groq and Gemini formats)
        # Using Gemini format for consistency with frontend
        return jsonify({
            "candidates": [{
                "content": {
                    "parts": [{"text": result_text}]
                }
            }]
        })

    except Exception as e:
        print(f"Chat Critical Error: {e}")
        import traceback
        traceback.print_exc()
        # Even if Python crashes, return a polite JSON response
        return jsonify({
            "candidates": [{
                "content": {
                    "parts": [{"text": "System is experiencing difficulties. Please try again in a moment."}]
                }
            }]
        })

# ----------------------------------------------------------

@app.route('/api/get-route', methods=['POST'])
def get_route_api():
    if not DEPENDENCIES_LOADED:
        return jsonify({
            "error": "Server dependencies not loaded. Please check server logs."
        }), 500
    
    try:
        # 1. Force cleanup before we start
        gc.collect()
        
        req = request.json
        if not req:
            return jsonify({"error": "No JSON data received"}), 400
        
        start = req.get('start')
        end = req.get('end')
        
        if not start or not end:
            return jsonify({"error": "Missing start or end location"}), 400
            
        print(f"\n🚀 Processing: {start} -> {end}")
        
        def get_coords(q):
            try:
                # Try to parse as coordinates first
                parts = q.strip().split(',')
                if len(parts) == 2:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return (lat, lon)
            except:
                pass
            
            # Fallback to geocoding
            try:
                return ox.geocode(q)
            except Exception as e:
                print(f"Geocoding error for '{q}': {e}")
                return None

        start_coords = get_coords(start)
        end_coords = get_coords(end)

        if not start_coords or not end_coords:
            return jsonify({
                "error": "Invalid location coordinates. Please use format 'latitude,longitude' or a valid address."
            }), 400

        print(f"📍 Start: {start_coords}, End: {end_coords}")

        # 2. Calculate Distance
        d_lat = abs(start_coords[0] - end_coords[0]) * 111000
        d_lon = abs(start_coords[1] - end_coords[1]) * 111000 * np.cos(np.radians(start_coords[0]))
        dist_meters = (d_lat**2 + d_lon**2)**0.5
        
        print(f"📏 Distance: {dist_meters:.0f}m")
        
        # 3. Intelligent Radius Calculation
        radius = (dist_meters / 2) + 500
        
        # MEMORY WARNING: Clamp to prevent crashes
        if radius > 2500:
            radius = 2500
            print("⚠️ Radius clamped to 2.5km for memory safety.")
        
        if radius < 500:
            radius = 500

        mid_lat = (start_coords[0] + end_coords[0]) / 2
        mid_lon = (start_coords[1] + end_coords[1]) / 2
        
        print(f"🗺️ Downloading Map... (Radius: {int(radius)}m)")
        
        # 4. Download Graph with error handling
        try:
            graph = ox.graph_from_point(
                (mid_lat, mid_lon), 
                dist=radius, 
                network_type='drive', 
                simplify=True
            )
        except Exception as e:
            print(f"Graph download error: {e}")
            return jsonify({
                "error": f"Could not download map data for this area. Error: {str(e)}"
            }), 500
        
        # 5. Find nearest nodes
        try:
            orig = ox.distance.nearest_nodes(graph, start_coords[1], start_coords[0])
            dest = ox.distance.nearest_nodes(graph, end_coords[1], end_coords[0])
        except Exception as e:
            return jsonify({
                "error": f"Could not find nearest road nodes: {str(e)}"
            }), 500
        
        # 6. Calculate Path
        try:
            route = nx.shortest_path(graph, orig, dest, weight='length')
            total_dist_km = round(nx.path_weight(graph, route, weight='length') / 1000, 2)
        except nx.NetworkXNoPath:
            return jsonify({
                "error": "No road path found between these locations. Try points closer together or on connected roads."
            }), 404
        except Exception as e:
            return jsonify({
                "error": f"Route calculation error: {str(e)}"
            }), 500

        print(f"✅ Route found: {len(route)} nodes, {total_dist_km}km")

        # 7. Run Features (CV + Geometry)
        cv_score = analyze_image_cv()

        segments = []
        stats = {"High": 0, "Moderate": 0, "Low": 0}
        hazards = {
            "Sharp Curve": 0, 
            "Poor Lighting": 0, 
            "Narrow Road": 0, 
            "Traffic Congestion": 0, 
            "Bad Visibility": 0, 
            "Known Blackspot": 0, 
            "High Speed Zone": 0, 
            "Winding Road": 0
        }

        for i in range(len(route) - 1):
            u, v = route[i], route[i+1]
            edge_data = graph.get_edge_data(u, v)
            if not edge_data:
                continue
            data = edge_data[0]
            
            # Geometry Extraction
            if 'geometry' in data:
                xs, ys = data['geometry'].xy
                pos = list(zip(ys, xs))
            else:
                pos = [
                    (graph.nodes[u]['y'], graph.nodes[u]['x']), 
                    (graph.nodes[v]['y'], graph.nodes[v]['x'])
                ]

            # --- REAL RISK LOGIC ---
            risk = 0
            reasons = []

            # A. Curvature (Geometry Engine)
            curve = calculate_curvature(data.get('geometry', None))
            if curve > 45: 
                risk += 30
                reasons.append("Sharp Curve")
            elif curve > 20: 
                risk += 10
                reasons.append("Winding Road")

            # B. Infrastructure (Tags)
            lanes = data.get('lanes', '2')
            if isinstance(lanes, list): 
                lanes = lanes[0]
            try:
                lane_count = int(lanes)
                if lane_count <= 1: 
                    risk += 20
                    reasons.append("Narrow Road")
            except:
                pass

            hw = data.get('highway', '')
            if isinstance(hw, list): 
                hw = hw[0]
            if hw in ['trunk', 'primary', 'motorway']: 
                risk += 10
                reasons.append("High Speed Zone")
            elif hw in ['track', 'unclassified', 'service']: 
                risk += 15
                reasons.append("Poor Lighting")

            # C. Computer Vision Result
            if cv_score > 0: 
                risk += cv_score
                reasons.append("Bad Visibility")

            # Classification
            if risk > 50: 
                r_level, color = "High", "#E11B23"
            elif risk > 20: 
                r_level, color = "Moderate", "#F5A623"
            else: 
                r_level, color = "Low", "#20BD5F"

            stats[r_level] += 1
            for r in reasons: 
                if r in hazards: 
                    hazards[r] += 1
            
            segments.append({
                "positions": pos, 
                "color": color, 
                "risk": r_level, 
                "info": ", ".join(reasons) if reasons else "Normal road conditions"
            })

        # 8. Aggressive Cleanup
        del graph
        del route
        gc.collect()

        return jsonify({
            "segments": segments, 
            "stats": stats, 
            "hazards": hazards, 
            "distance": total_dist_km
        })

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

# --- 1. GEOMETRY ENGINE ---
def calculate_curvature(geometry):
    if not geometry: 
        return 0
    try:
        coords = list(geometry.coords)
        if len(coords) < 3: 
            return 0
        
        total_turn = 0
        for i in range(len(coords) - 2):
            p1, p2, p3 = np.array(coords[i]), np.array(coords[i+1]), np.array(coords[i+2])
            v1, v2 = p2 - p1, p3 - p2
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if norm1 > 0 and norm2 > 0:
                angle = np.arccos(np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0))
                total_turn += np.degrees(angle)
        return total_turn
    except Exception as e:
        print(f"Curvature calculation error: {e}")
        return 0

# --- 2. COMPUTER VISION ENGINE (LAZY LOADED) ---
def analyze_image_cv():
    try:
        import cv2
        
        # Check in multiple possible locations
        possible_paths = [
            "test_road.jpg",
            "static/test_road.jpg",
            os.path.join(os.path.dirname(__file__), "test_road.jpg"),
            os.path.join(os.path.dirname(__file__), "static", "test_road.jpg")
        ]
        
        path = None
        for p in possible_paths:
            if os.path.exists(p):
                path = p
                break
        
        if not path:
            print("⚠️ test_road.jpg not found, skipping CV analysis")
            return 0
        
        img = cv2.imread(path)
        if img is None:
            print(f"⚠️ Could not read image: {path}")
            return 0
        
        # Run Edge Detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5,5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        score = (np.count_nonzero(edges) / edges.size) * 100
        
        # Clear memory immediately
        del img, gray, blurred, edges
        gc.collect()
        
        if score > 5: 
            return 20
        if score > 2: 
            return 10
        return 0
        
    except ImportError:
        print("⚠️ OpenCV not installed, skipping CV analysis")
        return 0
    except Exception as e:
        print(f"CV Error: {e}")
        return 0

# --- MAIN ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting server on port {port}")
    print(f"📦 Dependencies loaded: {DEPENDENCIES_LOADED}")
    print(f"🔑 Groq API Key: {'✅ Set' if os.environ.get('GROQ_API_KEY') else '❌ Not set'}")
    print(f"🔑 Gemini API Key: {'✅ Set' if os.environ.get('GEMINI_API_KEY') else '❌ Not set'}")
    
    app.run(host='0.0.0.0', port=port, debug=False)