from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import gc
import osmnx as ox
import networkx as nx
import numpy as np
import cv2
import os
import random

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app)

# Increase OSMnx timeout/size limits for server use
ox.settings.max_query_area_size = 2500000000
ox.settings.timeout = 180 

# --- ROUTES ---
@app.route('/')
def home():
    # Flask looks for this file in the 'templates' folder
    return render_template('Index.html') 

@app.route('/api/get-route', methods=['POST'])
def get_route_api():
    del graph
    del route
    gc.collect()
    try:
        req = request.json
        print(f"\n🚀 Processing: {req.get('start')} -> {req.get('end')}")
        
        # Helper to parse coordinates
        def get_coords(q):
            try:
                parts = q.split(',')
                if len(parts) == 2: return (float(parts[0]), float(parts[1]))
            except: pass
            return ox.geocode(q)

        start_coords = get_coords(req.get('start'))
        end_coords = get_coords(req.get('end'))

        # Get the graph
        graph = get_safe_graph(start_coords, end_coords)
        
        # Find nearest nodes
        orig = ox.distance.nearest_nodes(graph, start_coords[1], start_coords[0])
        dest = ox.distance.nearest_nodes(graph, end_coords[1], end_coords[0])
        
        # Calculate Shortest Path
        try:
            route = nx.shortest_path(graph, orig, dest, weight='length')
            
            # Calculate Distance
            total_dist_meters = nx.path_weight(graph, route, weight='length')
            total_dist_km = round(total_dist_meters / 1000, 2)
            
        except nx.NetworkXNoPath:
            return jsonify({"error": "No route found between these points."}), 404
        except Exception as e:
            return jsonify({"error": f"Routing error: {str(e)}"}), 500

        # Process Route Segments
        segments = []
        stats = {"High": 0, "Moderate": 0, "Low": 0}
        hazards = {"Sharp Curve":0, "Poor Lighting":0, "Narrow Road":0, "Traffic Congestion":0, "Bad Visibility":0, "Known Blackspot":0, "High Speed Zone": 0, "Winding Road": 0}
        
        cv_score = analyze_image_cv()

        for i in range(len(route) - 1):
            u, v = route[i], route[i+1]
            
            # Get geometry of the road segment
            data = graph.get_edge_data(u, v)[0]
            if 'geometry' in data:
                xs, ys = data['geometry'].xy
                pos = list(zip(ys, xs))
            else:
                pos = [(graph.nodes[u]['y'], graph.nodes[u]['x']), (graph.nodes[v]['y'], graph.nodes[v]['x'])]

            # Analyze Risk
            risk, color, info = analyze_risk(u, v, graph, cv_score)
            
            # Update Stats
            stats[risk] += 1
            for r in info:
                if r in hazards: hazards[r] += 1
            
            segments.append({
                "positions": pos, 
                "color": color, 
                "risk": risk, 
                "info": ", ".join(info)
            })

        return jsonify({
            "segments": segments, 
            "stats": stats, 
            "hazards": hazards, 
            "distance": total_dist_km
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

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
            # Clip to avoid float errors going slightly beyond 1.0
            angle = np.arccos(np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0))
            total_turn += np.degrees(angle)
    return total_turn

# --- 2. COMPUTER VISION ENGINE ---
def analyze_image_cv():
    # Only run this if the file actually exists (prevents crashes on server)
    path = "test_road.jpg"
    if not os.path.exists(path): 
        return 0
    
    img = cv2.imread(path)
    if img is None: return 0
    
    # Simple Edge Density Calculation
    edges = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5,5), 0), 50, 150)
    score = (np.count_nonzero(edges) / edges.size) * 100
    
    if score > 5: return 20
    if score > 2: return 10
    return 0

# --- 3. RISK ENGINE ---
def analyze_risk(u, v, graph, cv_score):
    data = graph.get_edge_data(u, v)[0]
    risk = 0
    reasons = []

    # FACTOR 1: Curvature
    curve = calculate_curvature(data.get('geometry', None))
    if curve > 45: 
        risk += 30
        reasons.append("Sharp Curve")
    elif curve > 20: 
        risk += 10
        reasons.append("Winding Road")

    # FACTOR 2: Lanes / Width
    lanes = data.get('lanes', '2')
    if isinstance(lanes, list): lanes = lanes[0]
    try:
        if int(lanes) <= 1: 
            risk += 20
            reasons.append("Narrow Road")
            if random.random() > 0.7: reasons.append("Traffic Congestion")
    except: pass

    # FACTOR 3: Random Blackspot Injection (Simulation)
    if risk > 20 and random.random() > 0.8: 
        risk += 40
        reasons.append("Known Blackspot")

    # FACTOR 4: Highway Type
    hw = data.get('highway', '')
    if isinstance(hw, list): hw = hw[0]
    
    if hw in ['trunk', 'primary', 'motorway']: 
        risk += 10
        reasons.append("High Speed Zone")
    elif hw in ['track', 'unclassified', 'service']: 
        risk += 15
        reasons.append("Poor Lighting")

    # FACTOR 5: CV Score
    if cv_score > 0: 
        risk += cv_score
        reasons.append("Bad Visibility")

    # Classification
    if risk > 50: return "High", "#E11B23", reasons
    if risk > 20: return "Moderate", "#F5A623", reasons
    return "Low", "#20BD5F", ["Safe Route"]

# --- 4. ROUTING ENGINE ---
def get_safe_graph(start_coords, end_coords):
    mid_lat = (start_coords[0] + end_coords[0]) / 2
    mid_lon = (start_coords[1] + end_coords[1]) / 2
    
    # Calculate box size
    lat_diff = abs(start_coords[0] - end_coords[0]) * 111000
    lon_diff = abs(start_coords[1] - end_coords[1]) * 111000
    radius = (max(lat_diff, lon_diff) / 2) + 2000
    
    # CLAMP RADIUS for Server Stability
    # Render Free Tier has 512MB RAM. 20km radius might crash it. 
    # I reduced max radius slightly to 10km to be safe.
    radius = min(max(radius, 2500), 10000) 
    
    print(f" ⬇️ Downloading Map Radius: {int(radius)}m at {mid_lat}, {mid_lon}")
    return ox.graph_from_point((mid_lat, mid_lon), dist=radius, network_type='drive')

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # This block ensures it runs on Render (using PORT env var) AND locally
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)