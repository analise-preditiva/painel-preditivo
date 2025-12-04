from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)


def carregar_dados_simulados():
    """
    Por enquanto usamos dados simulados.
    Depois vamos trocar essa função para ler a planilha do Google
    e rodar o modelo preditivo de verdade.
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
                "nivel": "alto",
                "mensagem": "Pico de ocorrências previsto entre 18h e 22h."
            },
            {
                "nivel": "médio",
                "mensagem": "Concentrar recursos em Centro e Praia do Canto."
            },
        ],
        "previsoes": [
            {"periodo": "Hoje", "incidentes": 40, "tendencia": "↑"},
            {"periodo": "Amanhã", "incidentes": 32, "tendencia": "↓"},
            {"periodo": "Próximos 7 dias", "incidentes": 210, "tendencia": "→"},
        ],
    }
    return dados


@app.route("/")
def index():
    dados = carregar_dados_simulados()
    return render_template("index.html", dados=dados)


@app.route("/health")
def health():
    return {"status": "ok", "app": "painel-preditivo"}


if __name__ == "__main__":
    # Apenas para rodar localmente; no Render quem roda é o gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)
