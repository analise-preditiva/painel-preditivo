from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)


def carregar_dados_simulados():
    """
    Neste momento: só dados simulados.
    Depois vamos trocar:
      - leitura de planilha Google Sheets
      - saída real do modelo preditivo
    """
    agora = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

    dados = {
        "ultima_atualizacao": agora,

        # KPIs de visão rápida
        "kpis": [
            {"nome": "Registros nas últimas 24h", "valor": 128},
            {"nome": "Eventos previstos hoje", "valor": 34},
            {"nome": "Bairros em risco alto", "valor": 7},
            {"nome": "Precisão do modelo (30 dias)", "valor": "91%"},
        ],

        # Alertas principais
        "alertas": [
            {
                "nivel": "alto",
                "mensagem": "Pico de ocorrências previsto entre 18h e 22h."
            },
            {
                "nivel": "medio",
                "mensagem": "Concentrar recursos em Centro e Praia do Canto."
            },
            {
                "nivel": "baixo",
                "mensagem": "Manter monitoramento em Jardim Camburi e Bento Ferreira."
            },
        ],

        # Previsão agregada por horizonte
        "previsoes": [
            {"periodo": "Hoje", "incidentes": 40, "tendencia": "↑ forte"},
            {"periodo": "Amanhã", "incidentes": 32, "tendencia": "↓ leve"},
            {"periodo": "Próximos 7 dias", "incidentes": 210, "tendencia": "→ estável"},
        ],

        # Risco por faixa de horário (visão “timeline”)
        "risco_horario": [
            {"faixa": "06h–09h", "risco": "baixo"},
            {"faixa": "09h–12h", "risco": "baixo"},
            {"faixa": "12h–15h", "risco": "medio"},
            {"faixa": "15h–18h", "risco": "medio"},
            {"faixa": "18h–22h", "risco": "alto"},
            {"faixa": "22h–02h", "risco": "alto"},
            {"faixa": "02h–06h", "risco": "medio"},
        ],

        # Top bairros em risco
        "top_bairros": [
            {"bairro": "Centro", "incidentes": 12, "tendencia": "↑"},
            {"bairro": "Praia do Canto", "incidentes": 9, "tendencia": "↑"},
            {"bairro": "Jardim Camburi", "incidentes": 7, "tendencia": "→"},
            {"bairro": "Maruípe", "incidentes": 5, "tendencia": "↓"},
        ],

        # Possíveis anomalias detectadas pelo modelo
        "anomalias": [
            {
                "impacto": "alto",
                "descricao": "Aumento incomum de furtos de veículo no Centro nas últimas 48h."
            },
            {
                "impacto": "medio",
                "descricao": "Chamados acima da média em Jardim Camburi no período da manhã."
            },
        ],

        # Recomendações operacionais sugeridas
        "acoes_recomendadas": [
            {
                "prioridade": "alta",
                "titulo": "Reforçar patrulhamento em Centro e Praia do Canto",
                "janela": "18h–22h",
            },
            {
                "prioridade": "media",
                "titulo": "Criar ponto-base móvel em Jardim Camburi",
                "janela": "06h–09h",
            },
            {
                "prioridade": "baixa",
                "titulo": "Planejar operação preventiva para o fim de semana",
                "janela": "Próximos 7 dias",
            },
        ],

        # Resumo da operação hoje (pode ligar depois nas suas escalas)
        "operacao_hoje": {
            "viaturas": 18,
            "pontos_quentes": 6,
            "turno_critico": "18h–22h",
            "comentario": "Turno noturno concentra ~60% do risco previsto para hoje.",
        },
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
    app.run(host="0.0.0.0", port=5000, debug=True)
