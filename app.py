from flask import Flask, render_template, request, jsonify
import json
import logging

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------------------
# ROTAS DE NAVEGAÇÃO ENTRE TELAS
# ------------------------------

@app.route("/")
def index():
    return render_template("index.html")   # Tela de login


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")   # Painel principal


@app.route("/bairros")
def bairros():
    return render_template("bairros.html")     # Módulo PREV-IA Bairros


@app.route("/rotas")
def rotas():
    return render_template("index2.html")      # Módulo Rotas / index2.html


# ------------------------------
# SAÚDE DA APLICAÇÃO
# ------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ------------------------------
# UPLOAD DE JSON
# ------------------------------

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


# ------------------------------
# MODO LOCAL
# ------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
