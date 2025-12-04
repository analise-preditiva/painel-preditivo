from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    """
    Rota principal do painel.
    Aqui depois vamos colocar os dados da planilha e as previsões.
    """
    titulo = "Painel Preditivo"
    mensagem = "Seu painel Flask está rodando no Render. Depois vamos ligar isso na planilha do Google."
    return render_template("index.html", titulo=titulo, mensagem=mensagem)


@app.route("/health")
def health():
    """
    Rota simples de saúde do sistema (útil para testar se está no ar).
    """
    return {"status": "ok", "app": "painel-preditivo"}


# Esse bloco só é usado se você rodar localmente com `python app.py`
if __name__ == "__main__":
    # Em produção (Render) quem vai rodar é o gunicorn, usando `app:app`
    app.run(host="0.0.0.0", port=5000, debug=True)
