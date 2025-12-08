from flask import Flask, render_template, request, jsonify
import json
import logging

# Configuração básica do Flask
app = Flask(__name__)

# Limite de tamanho do upload (ex.: 10 MB)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

# Logger simples para ajudar a debugar no Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/")
def index():
    """
    Rota principal: carrega o painel (index.html dentro de /templates).
    """
    return render_template("index.html")


@app.route("/health")
def health():
    """
    Rota de saúde simples, útil para checagens do Render.
    """
    return jsonify({"status": "ok"}), 200


@app.route("/upload_json", methods=["POST"])
def upload_json():
    """
    Recebe um arquivo JSON via formulário (campo name="file"),
    valida e devolve o conteúdo para o frontend tratar.
    """
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    # Aceita apenas arquivos com extensão .json (opcional, mas ajuda)
    filename = file.filename or ""
    if not filename.lower().endswith(".json"):
        return jsonify({"error": "Envie um arquivo com extensão .json"}), 400

    try:
        data = json.load(file)

        # Log básico para você ver nos logs do Render
        logger.info("JSON recebido com sucesso. Tipo raiz: %s", type(data).__name__)

        # Aqui você só devolve o JSON bruto; o HTML/JS faz o resto
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
    # Em produção (Render) quem vai rodar é o gunicorn: app:app
    # Este bloco é mais para testes locais.
    app.run(host="0.0.0.0", port=5000, debug=True)
