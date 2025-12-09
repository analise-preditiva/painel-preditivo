from flask import Flask, render_template, request, jsonify
import json
import logging

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/")
def index():
    # Tela inicial / login
    return render_template("index.html", active_page="index")


@app.route("/dashboard")
def dashboard():
    # Painel principal PREV-IA Operações
    return render_template("dashboard.html", active_page="dashboard")


@app.route("/bairros")
def bairros():
    # Módulo PREV-IA Bairros
    return render_template("bairros.html", active_page="bairros")


@app.route("/index2")
def index2():
    # Você pode tratar como módulo Rotas, Ocorrências etc.
    return render_template("index2.html", active_page="index2")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/upload_json", methods=["POST"])
def upload_json():
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    filename = file.filename or ""
    if not filename.lower().endswith(".json"):
        return jsonify({"error": "Envie um arquivo com extensão .json"}), 400

    try:
        data = json.load(file)
        logger.info("JSON recebido com sucesso. Tipo raiz: %s", type(data).__name__)

        return jsonify({
            "status": "ok",
            "data": data
        }), 200

    except json.JSONDecodeError as e:
        logger.exception("Erro de parsing do JSON")
        return jsonify({
            "error": "Arquivo não é um JSON válido.",
            "detalhe": str(e)
        }), 400

    except Exception as e:
        logger.exception("Erro inesperado ao processar JSON")
        return jsonify({
            "error": "Erro inesperado ao ler o JSON.",
            "detalhe": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
