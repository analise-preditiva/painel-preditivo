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

# IDs das três planilhas (vêm das variáveis de ambiente)
FILE_IDS = {
    "data_fato": os.environ.get("DRIVE_DATA_FATO_ID"),
    "hora_fato": os.environ.get("DRIVE_HORA_FATO_ID"),
    "log_fato": os.environ.get("DRIVE_LOG_FATO_ID"),
}


# -------------------------------------------------------------------
# Conexão segura com o Google Drive via Service Account
# -------------------------------------------------------------------
def build_drive_service():
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
    if not file_id:
        raise RuntimeError("ID de arquivo do Drive não informado.")
    request = service.files().get_media(fileId=file_id)
    data = request.execute()
    df = pd.read_excel(BytesIO(data))
    return df


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
        raise KeyError(f"Coluna '{chave}' não encontrada em HORA/LOGRADOURO.")

    # Merge base única
    df = df_data.merge(df_hora, on=chave, how="left")
    df = df.merge(df_log, on=chave, how="left")

    # --- Normalizações ---

    # Data
    col_data = next
