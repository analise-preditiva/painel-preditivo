import os
from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)


def carregar_dados_simulados():
    """
    Por enquanto usamos dados simulados.
    Depois você troca para ler Google Sheets / modelo preditivo real.
    """
    agora = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    dados = {
        "ultima_atualizacao": agora,
        "kpis": [
            {"nome": "Registros nas últimas 24h", "valor": 128},
            {"nome": "Eventos previstos hoje", "valor": 34},
            {"nome": "Bairros com risco alto", "valor": 7},
            {"nome": "Precisão do modelo (30 dias)", "valor": "91%"},
        ],
        "alertas": [
            {
                "titulo": "Praia do Canto • Noite",
                "descricao": "Aumento atípico de ocorrências nas últimas 3 semanas.",
                "nivel": "alto",
            },
            {
                "titulo": "Centro • Horário comercial",
                "descricao": "Risco de furtos acima da média histórica.",
                "nivel": "médio",
            },
        ],
    }
    return dados


@app.route("/")
def index():
    dados = carregar_dados_simulados()
    return render_template("index.html", dados=dados)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
