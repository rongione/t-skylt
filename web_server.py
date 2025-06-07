from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
shared_state = {"site_id": 9184}  # Default to Tallkrogen

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
