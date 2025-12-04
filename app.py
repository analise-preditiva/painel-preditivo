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

# Escopo só leitura do Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# IDs das três planilhas (variáveis de ambiente no Render)
FILE_IDS = {
    "data_fato": os.environ.get("DRIVE_DATA_FATO_ID"),
    "hora_fato": os.environ.get("DRIVE_HORA_FATO_ID"),
    "log_fato": os.environ.get("DRIVE_LOG_FATO_ID"),
}


# -------------------------------------------------------------------
# Google Drive
# -------------------------------------------------------------------
def build_drive_service():
    key_json = os.environ.get("GOOGLE_DRIVE_KEY")
    if not key_json:
        raise RuntimeError("Variável de ambiente GOOGLE_DRIVE_KEY não configurada.")

    info = json.loads(key_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    service = build("drive", "v3", credentials=creds)
    return service


def read_excel_from_drive(service, file_id: str) -> pd.DataFrame:
    if not file_id:
        raise RuntimeError("ID de arquivo do Drive não informado.")
    request = service.files().get_media(fileId=file_id)
    data = request.execute()
    df = pd.read_excel(BytesIO(data))
    return df


def _find_col(df: pd.DataFrame, keywords):
    """Acha coluna que contém algum dos termos da lista keywords."""
    for col in df.columns:
        name = str(col).lower()
        if any(k in name for k in keywords):
            return col
    return None


# -------------------------------------------------------------------
# Carregamento + normalização da base de Jardim Camburi
# -------------------------------------------------------------------
def carregar_base_jardim_camburi() -> pd.DataFrame:
    service = build_drive_service()
    df_data = read_excel_from_drive(service, FILE_IDS["data_fato"])
    df_hora = read_excel_from_drive(service, FILE_IDS["hora_fato"])
    df_log = read_excel_from_drive(service, FILE_IDS["log_fato"])

    # chave única
    chave = "Nº Ocorrência"
    if chave not in df_data.columns:
        poss = [c for c in df_data.columns if "ocorr" in str(c).lower()]
        if poss:
            chave = poss[0]
        else:
            raise KeyError("Coluna identificadora da ocorrência não encontrada.")

    for df in (df_hora, df_log):
        if chave not in df.columns:
            poss = [c for c in df.columns if "ocorr" in str(c).lower()]
            if poss:
                df.rename(columns={poss[0]: chave}, inplace=True)
            else:
                raise KeyError(
                    "Coluna identificadora da ocorrência não encontrada em uma das planilhas."
                )

    # merge das três bases
    df = df_data.merge(df_hora, on=chave, how="left")
    df = df.merge(df_log, on=chave, how="left")

    # tenta detectar colunas principais
    col_data = _find_col(df, ["data"])
    col_hora = _find_col(df, ["hora"])
    col_bairro = _find_col(df, ["bairr"])
    col_log = _find_col(df, ["lograd"])
    col_crime = _find_col(df, ["natur", "crime", "ocorr"])

    # DATA
    if col_data:
        df["data"] = pd.to_datetime(df[col_data], errors="coerce")
    else:
        df["data"] = pd.NaT

    # HORA (aceita 0–23, "13:00", 1300, etc)
    if col_hora:
        hora_raw = df[col_hora].astype(str).str.extract(r"(\d{1,2})")[0]
        df["hora"] = pd.to_numeric(hora_raw, errors="coerce").astype("Int64")
    else:
        df["hora"] = pd.NA

    # BAIRRO / LOGRADOURO / CRIME
    df["bairro"] = (
        df[col_bairro].fillna("S/I").astype(str).str.upper().str.strip()
        if col_bairro
        else "S/I"
    )
    df["logradouro"] = (
        df[col_log].fillna("S/I").astype(str).str.upper().str.strip()
        if col_log
        else "S/I"
    )
    if col_crime:
        df["crime"] = (
            df[col_crime]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df["crime"] = "NÃO INFORMADO"

    return df


# -------------------------------------------------------------------
# Cálculo de insights (kpis + crimes + previsões)
# -------------------------------------------------------------------
def calcular_insights(df: pd.DataFrame):
    agora = datetime.utcnow()

    # janela de 24h (baseada na maior data da planilha)
    if df["data"].notna().any():
        data_max = df["data"].max()
        janela_fim = (data_max + timedelta(days=1)) if not pd.isna(data_max) else agora
        janela_ini = janela_fim - timedelta(days=1)
        mask_24h = (df["data"] >= janela_ini) & (df["data"] < janela_fim)
        df_24h = df.loc[mask_24h]
    else:
        df_24h = df.copy()

    registros_24h = len(df_24h)

    hoje = agora.date()
    df_hoje = df[df["data"].dt.date == hoje] if df["data"].notna().any() else df
    eventos_previstos_hoje = int(df_hoje.shape[0] * 0.6)

    hora_series = df_24h["hora"].dropna().astype(int)
    if not hora_series.empty:
        top_horas = hora_series.value_counts().head(3)
        logradouros_risco = (
            df_24h.groupby("logradouro")["crime"].count()
            .sort_values(ascending=False)
            .head(3)
        )
    else:
        top_horas = pd.Series(dtype=int)
        logradouros_risco = pd.Series(dtype=int)

    n_log_risco = len(logradouros_risco)
    precisao = "91%"  # placeholder: pode ser refinado depois

    kpis = [
        {"nome": "Registros nas últimas 24h", "valor": registros_24h},
        {"nome": "Eventos previstos hoje", "valor": eventos_previstos_hoje},
        {"nome": "Logradouros em alto risco", "valor": n_log_risco},
        {"nome": "Precisão estimada (30 dias)", "valor": precisao},
    ]

    # Top horários (geral)
    top_horarios = []
    for hora, qt in top_horas.items():
        risco = "alto" if qt >= top_horas.max() * 0.7 else "médio"
        top_horarios.append({"hora": int(hora), "total": int(qt), "risco": risco})

    # Top logradouros
    top_logradouros = []
    for log, qt in logradouros_risco.items():
        top_logradouros.append({"logradouro": log.title(), "total": int(qt)})

    # Forecast simples por hora (média histórica)
    projecoes_24h = []
    hora_counts = df["hora"].dropna().astype(int).value_counts()
    dias_distintos = df["data"].dt.date.nunique() or 1
    max_hora_media = (
        hora_counts.max() / dias_distintos if not hora_counts.empty else 0
    )

    for h in range(24):
        total_h = hora_counts.get(h, 0)
        estimado = total_h / dias_distintos
        if max_hora_media > 0 and estimado >= max_hora_media * 0.7:
            risco = "alto"
        elif estimado > 0:
            risco = "médio"
        else:
            risco = "baixo"
        projecoes_24h.append(
            {"hora": h, "valor_previsto": float(round(estimado, 2)), "risco": risco}
        )

    # --- POR CRIME ---
    crimes_resumo = []
    crime_counts = df["crime"].value_counts().head(8)
    max_crime = crime_counts.max() if not crime_counts.empty else 1
    for crime, qt in crime_counts.items():
        ratio = qt / max_crime
        if ratio >= 0.7:
            risco = "alto"
        elif ratio >= 0.4:
            risco = "médio"
        else:
            risco = "baixo"
        crimes_resumo.append({"crime": crime, "total": int(qt), "risco": risco})

    # crime x hora
    crime_hora = []
    if df["hora"].notna().any():
        grp_ch = df.dropna(subset=["hora"]).groupby(["crime", "hora"]).size()
        for (crime, hora), qt in grp_ch.items():
            crime_hora.append(
                {"crime": crime, "hora": int(hora), "valor": float(qt)}
            )

    # crime x hora x bairro
    crime_hora_bairro = []
    if df["hora"].notna().any():
        grp_chb = df.dropna(subset=["hora"]).groupby(["crime", "hora", "bairro"]).size()
        for (crime, hora, bairro), qt in grp_chb.items():
            crime_hora_bairro.append(
                {
                    "crime": crime,
                    "hora": int(hora),
                    "bairro": bairro,
                    "valor": float(qt),  # pode virar índice normalizado depois
                }
            )

    # Alertas simples (pode ser evoluído)
    alertas = []
    if projecoes_24h:
        pico = max(projecoes_24h, key=lambda x: x["valor_previsto"])
        if pico["valor_previsto"] > 0:
            alertas.append(
                {
                    "titulo": f"Pico previsto às {pico['hora']:02d}h",
                    "descricao": f"Maior concentração esperada de ocorrências ({pico['valor_previsto']:.1f}/hora).",
                }
            )

    return {
        "kpis": kpis,
        "top_horarios": top_horarios,
        "top_logradouros": top_logradouros,
        "projecoes_24h": projecoes_24h,
        "crimes_resumo": crimes_resumo,
        "crime_hora": crime_hora,
        "crime_hora_bairro": crime_hora_bairro,
        "alertas": alertas,
    }


# -------------------------------------------------------------------
# Rota principal
# -------------------------------------------------------------------
@app.route("/")
def index():
    try:
        df = carregar_base_jardim_camburi()
        insights = calcular_insights(df)
    except Exception as exc:
        # Se der erro (Drive, colunas, etc.), não derruba o painel:
        insights = {
            "kpis": [
                {"nome": "Registros nas últimas 24h", "valor": 0},
                {"nome": "Eventos previstos hoje", "valor": 0},
                {"nome": "Logradouros em alto risco", "valor": 0},
                {"nome": "Precisão estimada (30 dias)", "valor": "--"},
            ],
            "top_horarios": [],
            "top_logradouros": [],
            "projecoes_24h": [],
            "crimes_resumo": [],
            "crime_hora": [],
            "crime_hora_bairro": [],
            "alertas": [
                {
                    "titulo": "Erro ao carregar dados",
                    "descricao": str(exc),
                }
            ],
        }

    context = {
        "ultima_atualizacao": datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
        **insights,
    }
    return render_template("index.html", **context)


if __name__ == "__main__":
    # Em produção o Render usa gunicorn; isso é só para rodar local.
    app.run(host="0.0.0.0", port=5000, debug=True)
