import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
shared_state = {"site_id": 9184}  # Default to Tallkrogen

@app.route('/stations')
def get_stations():
    lookup_url = "https://transport.integration.sl.se/v1/sites"

    headers = {
        "Accept": "application/json",
        # Uncomment and modify if you need an API key
        # "Authorization": "Bearer YOUR_API_KEY"
    }

    response = requests.get(lookup_url, headers=headers)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch station data'}), 500

    data = response.json()

    # Extract only 'id' and 'name'
    stations = [{'id': s['id'], 'name': s['name']} for s in data]
    stations.sort(key=lambda s: s['name'].lower()) # Alphabetical order
    return jsonify(stations)

@app.route("/")
def serve_html():
    return send_from_directory(".", "station_selector.html")

@app.route("/set-site", methods=["POST"])
def set_site():
    data = request.json
    try:
        shared_state["site_id"] = int(data["site_id"])
        return jsonify({"status": "success", "site_id": shared_state["site_id"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/get-site")
def get_site():
    return jsonify({"site_id": shared_state["site_id"]})

@app.route("/set-transport-modes", methods=["POST"])
def set_transport_modes():
    data = request.json
    try:
        shared_state["transport_modes"] = data["transport_modes"]
        return jsonify({"status": "success", "transport_modes": shared_state["transport_modes"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/get-transport-modes")
def get_transport_modes():
    return jsonify({"transport_modes": shared_state.get("transport_modes", ["METRO"])})

# Initialize default transport modes
shared_state["transport_modes"] = ["METRO"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
