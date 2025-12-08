from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload_json", methods=["POST"])
def upload_json():
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    try:
        data = json.load(file)
        return jsonify({"status": "ok", "data": data})
    except Exception as e:
        return jsonify({"error": f"Erro ao ler JSON: {str(e)}"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


