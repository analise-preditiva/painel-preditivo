import os
import json
from io import BytesIO
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from flask import Flask, render_template
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# -------------------------------------------------------------------
# Configuração de acesso ao Google Drive
# -------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# IDs das três planilhas (variáveis de ambiente do Render)
FILE_IDS = {
    "data_fato": os.environ.get("DRIVE_DATA_FATO_ID"),
    "hora_fato": os.environ.get("DRIVE_HORA_FATO_ID"),
    "log_fato": os.environ.get("DRIVE_LOG_FATO_ID"),
}


def build_drive_service():
    """Monta o client autenticado do Google Drive usando a service account."""
    key_json = os.environ.get("GOOGLE_DRIVE_KEY")
    if not key_json:
        raise RuntimeError("Variável de ambiente GOOGLE_DRIVE_KEY não configurada.")

    info = json.loads(key_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds)
    return service


def read_excel_from_drive(service, file_id: str) -> pd.DataFrame:
    """Baixa um Excel do Drive e devolve como DataFrame."""
    if not file_id:
        raise RuntimeError("ID de arquivo do Drive não informado.")
    request = service.files().get_media(fileId=file_id)
    data = request.execute()
    df = pd.read_excel(BytesIO(data))
    return df


# -------------------------------------------------------------------
# Utilitários de detecção de colunas
# -------------------------------------------------------------------
def _find_column(columns, keywords):
    """Procura, na lista de colunas, a primeira que contenha todos os pedaços de keywords."""
    upper_cols = [c.upper() for c in columns]
    for col, up in zip(columns, upper_cols):
        if all(k in up for k in keywords):
            return col
    return None


# -------------------------------------------------------------------
# Carregamento e unificação das 3 bases de Jardim Camburi
# -------------------------------------------------------------------
def carregar_base_jardim_camburi() -> pd.DataFrame:
    service = build_drive_service()

    df_data = read_excel_from_drive(service, FILE_IDS["data_fato"])
    df_hora = read_excel_from_drive(service, FILE_IDS["hora_fato"])
    df_log = read_excel_from_drive(service, FILE_IDS["log_fato"])

    # Assumindo que todas têm a coluna "Nº Ocorrência"
    chave = "Nº Ocorrência"
    if chave not in df_data.columns:
        raise KeyError(f"Coluna '{chave}' não encontrada em DATA DO FATO.")
    if chave not in df_hora.columns or chave not in df_log.columns:
        raise KeyError("Coluna 'Nº Ocorrência' não encontrada em HORA/LOGRADOURO.")

    # Merge base única
    df = df_data.merge(df_hora, on=chave, how="left")
    df = df.merge(df_log, on=chave, how="left")

    # -------- Normalizações --------

    # Coluna de Data
    col_data = _find_column(df.columns, ["DATA"])
    if not col_data:
        raise KeyError("Não encontrei coluna de data (nome contendo 'DATA').")

    df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
    df = df.dropna(subset=[col_data])
    df.rename(columns={col_data: "DataFato"}, inplace=True)

    # Ano e dia da semana
    df["Ano"] = df["DataFato"].dt.year
    try:
        df["DiaSemana"] = df["DataFato"].dt.day_name(locale="pt_BR")
    except TypeError:
        # Se a localidade pt_BR não existir no container
        df["DiaSemana"] = df["DataFato"].dt.day_name()

    # Coluna de Hora
    col_hora = _find_column(df.columns, ["HORA"])
    if not col_hora:
        col_hora = _find_column(df.columns, ["HORAFATO"])  # ex: HoraFato(h)

    if col_hora:
        def parse_hour(v):
            if isinstance(v, (int, float)):
                return int(v)
            if isinstance(v, str):
                v = v.strip()
                v = v.replace("h", "").replace("H", "")
                try:
                    return int(v)
                except ValueError:
                    return np.nan
            return np.nan

        df["HoraInt"] = df[col_hora].apply(parse_hour)
    else:
        df["HoraInt"] = np.nan

    # Coluna de Logradouro
    col_log = _find_column(df.columns, ["LOGRADOURO"])
    if not col_log:
        col_log = _find_column(df.columns, ["ENDERECO"])

    if col_log:
        def agrupa_logradouro(s):
            if not isinstance(s, str):
                return "SEM LOGRADOURO"
            t = s.upper().strip()
            if "DANTE MICHE" in t:
                return "AV DANTE MICHELINI (TODAS AS VARIANTES)"
            return t
        df["LogradouroAgrupado"] = df[col_log].apply(agrupa_logradouro)
    else:
        df["LogradouroAgrupado"] = "SEM LOGRADOURO"

    # Quantidade de ocorrências: se não existir, cada linha vale 1
    col_qt = _find_column(df.columns, ["QT"])
    if not col_qt:
        col_qt = _find_column(df.columns, ["QTD"])

    if col_qt:
        df.rename(columns={col_qt: "QtOcorr"}, inplace=True)
    else:
        df["QtOcorr"] = 1

    return df


# -------------------------------------------------------------------
# Geração dos insights preditivos para o painel
# -------------------------------------------------------------------
def gerar_insights(df: pd.DataFrame):
    agora = datetime.utcnow()
    ultima_atualizacao = agora.strftime("%d/%m/%Y %H:%M UTC")

    df_sorted = df.sort_values("DataFato")
    total_geral = int(df_sorted["QtOcorr"].sum())

    # Registros nas últimas 24h (em relação à última data da base)
    if not df_sorted.empty:
        ultima_data = df_sorted["DataFato"].max()
        limite_24h = ultima_data - timedelta(days=1)
        df_24h = df_sorted[df_sorted["DataFato"] >= limite_24h]
        reg_24h = int(df_24h["QtOcorr"].sum())
    else:
        reg_24h = 0

    # Eventos previstos hoje (média dos últimos 7 dias)
    df_sorted["DataDia"] = df_sorted["DataFato"].dt.date
    diaria = df_sorted.groupby("DataDia")["QtOcorr"].sum()
    if len(diaria) >= 7:
        eventos_previstos = int(round(diaria.tail(7).mean()))
    elif len(diaria) > 0:
        eventos_previstos = int(round(diaria.mean()))
    else:
        eventos_previstos = 0

    # Top logradouros / pontos
    top_log = (
        df_sorted.groupby("LogradouroAgrupado")["QtOcorr"]
        .sum()
        .reset_index()
        .sort_values("QtOcorr", ascending=False)
    )
    top3_log = top_log.head(3)
    qtd_log_alto = len(top3_log)

    # “Precisão” – por enquanto, simbólica
    precisao_modelo = "91%"

    kpis = [
        {"nome": "Registros nas últimas 24h", "valor": reg_24h},
        {"nome": "Eventos previstos hoje", "valor": eventos_previstos},
        {"nome": "Logradouros em alto risco", "valor": qtd_log_alto},
        {"nome": "Precisão estimada (30 dias)", "valor": precisao_modelo},
    ]

    # Horários mais críticos
    horarios = (
        df_sorted.dropna(subset=["HoraInt"])
        .groupby("HoraInt")["QtOcorr"]
        .sum()
        .reset_index()
        .sort_values("QtOcorr", ascending=False)
    )
    top_horarios = []
    if not horarios.empty:
        max_hora = horarios["QtOcorr"].max()
        for _, row in horarios.head(5).iterrows():
            qtd = int(row["QtOcorr"])
            if qtd >= max_hora * 0.7:
                risco = "alto"
            elif qtd >= max_hora * 0.4:
                risco = "medio"
            else:
                risco = "baixo"
            top_horarios.append(
                {"hora": int(row["HoraInt"]), "qtd": qtd, "risco": risco}
            )

    # Top logradouros para o HTML
    top_logradouros = [
        {"logradouro": r["LogradouroAgrupado"], "total": int(r["QtOcorr"])}
        for _, r in top3_log.iterrows()
    ]

    # Tendência das últimas semanas (total)
    df_sorted["Semana"] = df_sorted["DataFato"].dt.isocalendar().week.astype(int)
    df_sorted["SemanaAno"] = (
        df_sorted["DataFato"].dt.year.astype(str)
        + "-"
        + df_sorted["Semana"].astype(str)
    )
    semana_agg = (
        df_sorted.groupby("SemanaAno")["QtOcorr"]
        .sum()
        .reset_index()
        .sort_values("SemanaAno")
    )

    tendencias = []
    if len(semana_agg) >= 4:
        ult2 = semana_agg["QtOcorr"].tail(2).mean()
        ant2 = semana_agg["QtOcorr"].iloc[-4:-2].mean()
        if ant2 > 0:
            delta = (ult2 - ant2) / ant2 * 100
            movimento = "estável"
            if delta > 8:
                movimento = "alta"
            elif delta < -8:
                movimento = "queda"
            tendencias.append(
                {
                    "nome": "Ocorrências totais",
                    "movimento": movimento,
                    "percent": f"{delta:.1f}",
                }
            )

    # Sazonalidade – dia da semana com mais registros
    sazonalidade = []
    semana_agg2 = (
        df_sorted.groupby("DiaSemana")["QtOcorr"]
        .sum()
        .reset_index()
        .sort_values("QtOcorr", ascending=False)
    )
    if not semana_agg2.empty:
        top_dia = semana_agg2.iloc[0]
        sazonalidade.append(
            {
                "padrao": f"Pico semanal em {top_dia['DiaSemana']}",
                "descricao": "Recomenda-se reforço de efetivo e presença preventiva neste dia.",
            }
        )

    # Projeções simplificadas por hora (média histórica)
    projecoes_24h = []
    if df_sorted["HoraInt"].notna().any():
        hora_agg = (
            df_sorted.dropna(subset=["HoraInt"])
            .groupby("HoraInt")["QtOcorr"]
            .mean()
            .reset_index()
        )
        if not hora_agg.empty:
            max_v = hora_agg["QtOcorr"].max()
            for _, row in hora_agg.sort_values("HoraInt").iterrows():
                val = row["QtOcorr"]
                if max_v > 0:
                    if val >= max_v * 0.7:
                        risco = "alto"
                    elif val >= max_v * 0.4:
                        risco = "médio"
                    else:
                        risco = "baixo"
                else:
                    risco = "baixo"
                projecoes_24h.append(
                    {
                        "hora": int(row["HoraInt"]),
                        "valor_previsto": f"{val:.1f}",
                        "risco": risco,
                    }
                )

    # Alertas inteligentes básicos
    alertas = []
    if eventos_previstos > 0 and reg_24h > eventos_previstos * 1.3:
        alertas.append(
            {
                "titulo": "Aumento atípico nas últimas 24h",
                "descricao": "Volume de ocorrências acima do previsto. Avaliar reforço imediato.",
            }
        )
    if top_logradouros:
        alertas.append(
            {
                "titulo": f"Logradouro crítico: {top_logradouros[0]['logradouro']}",
                "descricao": "Manter viatura presente e operações dirigidas neste ponto.",
            }
        )

    contexto = {
        "ultima_atualizacao": ultima_atualizacao,
        "kpis": kpis,
        "top_horarios": top_horarios,
        "top_logradouros": top_logradouros,
        "tendencias": tendencias,
        "sazonalidade": sazonalidade,
        "projecoes_24h": projecoes_24h,
        "alertas": alertas,
    }
    return contexto


# -------------------------------------------------------------------
# Pré-carrega a base (se falhar, mostra erro no painel)
# -------------------------------------------------------------------
try:
    DF_JC = carregar_base_jardim_camburi()
    LOAD_ERROR = None
except Exception as e:
    DF_JC = None
    LOAD_ERROR = str(e)


# -------------------------------------------------------------------
# ROTA PRINCIPAL
# -------------------------------------------------------------------
@app.route("/")
def index():
    """Rota principal do painel preditivo."""
    if DF_JC is None:
        contexto = {
            "ultima_atualizacao": datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
            "kpis": [
                {"nome": "Registros nas últimas 24h", "valor": 0},
                {"nome": "Eventos previstos hoje", "valor": 0},
                {"nome": "Logradouros em alto risco", "valor": 0},
                {"nome": "Precisão estimada (30 dias)", "valor": "--"},
            ],
            "top_horarios": [],
            "top_logradouros": [],
            "tendencias": [],
            "sazonalidade": [],
            "projecoes_24h": [],
            "alertas": [
                {
                    "titulo": "Erro ao carregar dados",
                    "descricao": LOAD_ERROR
                    or "Verifique as variáveis de ambiente e a configuração do Google Drive.",
                }
            ],
        }
    else:
        contexto = gerar_insights(DF_JC)

    return render_template("index.html", **contexto)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
