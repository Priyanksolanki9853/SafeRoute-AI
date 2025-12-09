from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import osmnx as ox
import networkx as nx
import numpy as np
# Note: cv2 is NOT imported globally to save startup RAM
import os
import random
import gc

app = Flask(__name__)
CORS(app)

# OPTIMIZATION: Strict limits to prevent server timeout
ox.settings.max_query_area_size = 2500000000
ox.settings.timeout = 180 

@app.route('/')
def home():
    # Securely fetch the key from Render's Environment Variables
    api_key = os.environ.get("GEMINI_API_KEY", "") 
    return render_template('Index.html', gemini_key=api_key)

@app.route('/api/get-route', methods=['POST'])
def get_route_api():
    try:
        # 1. Force cleanup before we start
        gc.collect()
        
        req = request.json
        print(f"\n🚀 Processing: {req.get('start')} -> {req.get('end')}")
        
        def get_coords(q):
            try:
                parts = q.split(',')
                if len(parts) == 2: return (float(parts[0]), float(parts[1]))
            except: pass
            return ox.geocode(q)

        start_coords = get_coords(req.get('start'))
        end_coords = get_coords(req.get('end'))

        if not start_coords or not end_coords:
            return jsonify({"error": "Invalid location coordinates."}), 400

        # 2. Calculate Distance
        d_lat = abs(start_coords[0] - end_coords[0]) * 111000
        d_lon = abs(start_coords[1] - end_coords[1]) * 111000
        dist_meters = (d_lat**2 + d_lon**2)**0.5
        
        # 3. Intelligent Radius Calculation
        # We need enough map to find a path, but not too much to crash RAM
        radius = (dist_meters / 2) + 400
        
        # MEMORY WARNING:
        # If radius > 2000m, 512MB RAM might fail with CV2 enabled.
        # We clamp it to 2500m. If you need longer routes, run locally.
        if radius > 2500:
            radius = 2500
            print("⚠️ Radius clamped to 2.5km for memory safety.")

        mid_lat = (start_coords[0] + end_coords[0]) / 2
        mid_lon = (start_coords[1] + end_coords[1]) / 2
        
        print(f"Downloading Map... (Radius: {int(radius)}m)")
        
        # 4. Download Graph
        graph = ox.graph_from_point((mid_lat, mid_lon), dist=radius, network_type='drive', simplify=True)
        
        orig = ox.distance.nearest_nodes(graph, start_coords[1], start_coords[0])
        dest = ox.distance.nearest_nodes(graph, end_coords[1], end_coords[0])
        
        # 5. Calculate Path
        try:
            route = nx.shortest_path(graph, orig, dest, weight='length')
            total_dist_km = round(nx.path_weight(graph, route, weight='length') / 1000, 2)
        except nx.NetworkXNoPath:
            return jsonify({"error": "No road path found. Try points closer together."}), 404

        # 6. Run Features (CV + Geometry)
        cv_score = analyze_image_cv() # Calls the "Lazy Loaded" function

        segments = []
        stats = {"High": 0, "Moderate": 0, "Low": 0}
        hazards = {"Sharp Curve":0, "Poor Lighting":0, "Narrow Road":0, "Traffic Congestion":0, "Bad Visibility":0, "Known Blackspot":0, "High Speed Zone":0, "Winding Road":0}

        for i in range(len(route) - 1):
            u, v = route[i], route[i+1]
            data = graph.get_edge_data(u, v)[0]
            
            # Geometry Extraction
            if 'geometry' in data:
                xs, ys = data['geometry'].xy
                pos = list(zip(ys, xs))
            else:
                pos = [(graph.nodes[u]['y'], graph.nodes[u]['x']), (graph.nodes[v]['y'], graph.nodes[v]['x'])]

            # --- REAL RISK LOGIC RESTORED ---
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
            if isinstance(lanes, list): lanes = lanes[0]
            try:
                if int(lanes) <= 1: 
                    risk += 20; reasons.append("Narrow Road")
            except: pass

            hw = data.get('highway', '')
            if isinstance(hw, list): hw = hw[0]
            if hw in ['trunk', 'primary', 'motorway']: 
                risk += 10; reasons.append("High Speed Zone")
            elif hw in ['track', 'unclassified', 'service']: 
                risk += 15; reasons.append("Poor Lighting")

            # C. Computer Vision Result
            if cv_score > 0: 
                risk += cv_score
                reasons.append("Bad Visibility")

            # Classification
            if risk > 50: r_level, color = "High", "#E11B23"
            elif risk > 20: r_level, color = "Moderate", "#F5A623"
            else: r_level, color = "Low", "#20BD5F"

            stats[r_level] += 1
            for r in reasons: 
                if r in hazards: hazards[r] += 1
            
            segments.append({"positions": pos, "color": color, "risk": r_level, "info": ", ".join(reasons)})

        # 7. Aggressive Cleanup
        del graph
        del route
        gc.collect() # Free up RAM immediately

        return jsonify({
            "segments": segments, 
            "stats": stats, 
            "hazards": hazards, 
            "distance": total_dist_km
        })

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

# --- 1. GEOMETRY ENGINE ---
def calculate_curvature(geometry):
    if not geometry: return 0 
    coords = list(geometry.coords)
    if len(coords) < 3: return 0
    total_turn = 0
    for i in range(len(coords) - 2):
        p1, p2, p3 = np.array(coords[i]), np.array(coords[i+1]), np.array(coords[i+2])
        v1, v2 = p2 - p1, p3 - p2
        norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if norm1 > 0 and norm2 > 0:
            angle = np.arccos(np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0))
            total_turn += np.degrees(angle)
    return total_turn

# --- 2. COMPUTER VISION ENGINE (LAZY LOADED) ---
def analyze_image_cv():
    # We import cv2 HERE inside the function.
    # This means Python only loads the heavy library when this function runs,
    # and not at the start of the app. This saves startup RAM.
    try:
        import cv2
        
        path = "test_road.jpg"
        if not os.path.exists(path): return 0
        
        img = cv2.imread(path)
        if img is None: return 0
        
        # Run Edge Detection
        edges = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5,5), 0), 50, 150)
        score = (np.count_nonzero(edges) / edges.size) * 100
        
        # Clear memory immediately
        del img
        del edges
        gc.collect()
        
        if score > 5: return 20
        if score > 2: return 10
        return 0
    except ImportError:
        print("OpenCV not installed or failed to load.")
        return 0
    except Exception as e:
        print(f"CV Error: {e}")
        return 0

# --- MAIN ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)