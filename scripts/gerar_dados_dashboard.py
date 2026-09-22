from __future__ import annotations

import argparse
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

APP_NAME = "Dashboard de Acompanhamento de Pedidos"
SHEET_NAME = "Principal"
OUTPUT_NAME = "ordens_santana.json.gz"
MANIFEST_NAME = "manifest.json"
MIN_COLUMNS = 86

CRITICAL_COLUMNS = {
    "ordem": "B - Ordem de venda",
    "quantidade": "K - Quantidade",
    "status": "L - Status",
    "dia": "BA - Dia",
    "mes": "BB - Mês",
    "ano": "BC - Ano",
    "mes_mapa": "BD - Mês do mapa",
    "responsavel": "CH - Responsável",
}

# Posições físicas das colunas no Excel (1-based).
# O script usa a posição para não depender de pequenas alterações nos nomes.
COL = {
    "tipo_operacao": 1,       # A - desconsiderado
    "ordem": 2,               # B - Ordem de venda / pedido
    "segmento": 4,            # D - Segmentação
    "canal_digital": 8,       # H - Canal digital
    "data_criacao": 9,        # I - referência original
    "status": 12,             # L - Status do pedido
    "cliente": 13,            # M - Cliente
    "transportadora": 15,     # O - Nome2 / Transportadora
    "condicao_entrega": 16,   # P - Condição de entrega
    "estado": 43,             # AQ - Estado
    "devolucao": 47,          # AU - Devolução
    "deposito": 30,           # AD - Depósito lógico
    "quantidade": 11,         # K - Quantidade
    "dia": 53,                # BA - Dia
    "mes": 54,                # BB - Mês
    "ano": 55,                # BC - Ano
    "mes_mapa": 56,           # BD - Mês usado no mapa; fallback para BB
    "canal": 80,              # CB - Canal da tabela detalhada
    "responsavel": 86,       # CH - Responsável
}


def clean(value, default="Não informado") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    if isinstance(value, (bool, np.bool_)):
        return "Sim" if value else default
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "nat", "none"} else default


def number(value, default=0):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        text = str(value).strip().replace(".", "").replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return default


def integer(value):
    value = number(value, None)
    if value is None or pd.isna(value):
        return None
    return int(value)


def month_number(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (pd.Timestamp, datetime)):
        # Excel pode interpretar uma coluna de mês como uma data 1900-01-N.
        if value.year in (1899, 1900) and 1 <= value.day <= 12:
            return int(value.day)
        return int(value.month)

    text = str(value).strip().upper()
    months = {
        "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
        "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
        "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
        "NOVEMBRO": 11, "DEZEMBRO": 12,
    }
    if text in months:
        return months[text]
    try:
        n = float(text.replace(",", "."))
        if 1 <= n <= 12:
            return int(n)
    except ValueError:
        pass
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.notna(parsed):
        if parsed.year in (1899, 1900) and 1 <= parsed.day <= 12:
            return int(parsed.day)
        return int(parsed.month)
    return None


def build_date(day, month, year):
    d, m, y = integer(day), month_number(month), integer(year)
    if d is None or m is None or y is None:
        return None
    try:
        return datetime(y, m, d).strftime("%Y-%m-%d")
    except ValueError:
        return None


def excel_col(n):
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def get_col(df, position):
    return df.iloc[:, position - 1]


def find_source_file(explicit_file=None, folder=None):
    if explicit_file:
        source = Path(explicit_file).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {source}")
        if source.suffix.lower() != ".xlsx":
            raise ValueError(f"O arquivo informado não é .xlsx: {source.name}")
        return source

    search_folder = Path(folder or Path(__file__).resolve().parents[1]).resolve()
    candidates = [
        p for p in search_folder.glob("*.xlsx")
        if not p.name.startswith("~$")
        and not any(term in p.stem.lower() for term in ("tratado", "teste", "backup", "temporario", "temp"))
    ]

    if not candidates:
        raise FileNotFoundError(
            f"Nenhum .xlsx encontrado em {search_folder}. "
            "Informe o arquivo ou coloque o Excel na pasta do dashboard."
        )

    # O arquivo operacional do ACPTO deve ser identificado pelo nome base.
    # Entre cópias do mesmo arquivo, usa a mais recentemente modificada.
    operational = [
        p for p in candidates
        if "acpto de ordens" in p.stem.lower()
        and "santana" in p.stem.lower()
    ]

    pool = operational or candidates
    return max(pool, key=lambda p: p.stat().st_mtime)


def validate_columns(df):
    required = max(COL.values())

    if len(df.columns) < required:
        raise ValueError(
            f"A aba '{SHEET_NAME}' possui {len(df.columns)} colunas, "
            f"mas o processamento precisa chegar até {excel_col(required)} ({required})."
        )

    missing_positions = [
        f"{excel_col(pos)} ({pos})"
        for pos in COL.values()
        if pos > len(df.columns)
    ]

    if missing_positions:
        raise ValueError(
            "Posições de colunas ausentes: " + ", ".join(missing_positions)
        )


def is_empty(value):
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"", "nan", "nat", "none"}


def validate_critical_data(df):
    warnings = []

    for key, description in CRITICAL_COLUMNS.items():
        series = get_col(df, COL[key])
        valid = sum(not is_empty(v) for v in series)

        if valid == 0:
            raise ValueError(
                f"Validação interrompida: {description} está completamente vazio."
            )

        empty = len(series) - valid
        if empty:
            warnings.append(f"{description}: {empty:,} células vazias.")

    invalid_qty = 0
    for value in get_col(df, COL["quantidade"]):
        if is_empty(value):
            continue
        if number(value, None) is None:
            invalid_qty += 1

    if invalid_qty:
        warnings.append(
            f"K - Quantidade: {invalid_qty:,} valores não numéricos serão convertidos para 0."
        )

    valid_dates = 0
    for day, month, year in zip(
        get_col(df, COL["dia"]),
        get_col(df, COL["mes"]),
        get_col(df, COL["ano"]),
    ):
        if build_date(day, month, year):
            valid_dates += 1

    if valid_dates == 0:
        raise ValueError("Nenhuma data válida foi encontrada usando BA + BB + BC.")

    invalid_dates = len(df) - valid_dates
    if invalid_dates:
        warnings.append(
            f"BA + BB + BC: {invalid_dates:,} registros sem data válida para SLA."
        )

    ordem = get_col(df, COL["ordem"]).map(clean)
    duplicated_lines = int(ordem.duplicated(keep=False).sum())

    if duplicated_lines:
        groups = int(ordem[ordem.duplicated(keep=False)].nunique())
        warnings.append(
            f"B - Ordem de venda: {duplicated_lines:,} linhas participam de {groups:,} grupos duplicados. Nenhuma linha foi removida."
        )

    return warnings, {
        "datas_validas": valid_dates,
        "datas_invalidas": invalid_dates,
        "quantidades_invalidas": invalid_qty,
        "linhas_em_ordens_duplicadas": duplicated_lines,
    }


def generate_records(df):
    s = {name: get_col(df, pos) for name, pos in COL.items()}
    month_map = s["mes_mapa"].copy()
    empty = month_map.isna() | month_map.astype(str).str.strip().eq("")
    month_map.loc[empty] = s["mes"].loc[empty]

    month_names = [
        "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
        "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
    ]

    normalized_month_map = []
    for value in month_map:
        n = month_number(value)
        normalized_month_map.append(month_names[n - 1] if n else clean(value))

    records = []
    for i in range(len(df)):
        qty = number(s["quantidade"].iloc[i], 0)
        qty = int(qty) if float(qty).is_integer() else qty
        records.append({
            "tipoOperacao": clean(s["tipo_operacao"].iloc[i]),
            "ordem": clean(s["ordem"].iloc[i]),
            "cliente": clean(s["cliente"].iloc[i]),
            "segmento": clean(s["segmento"].iloc[i]),
            "canalDigital": clean(s["canal_digital"].iloc[i]),
            "status": clean(s["status"].iloc[i]),
            "quantidade": qty,
            "transportadora": clean(s["transportadora"].iloc[i]),
            "condicaoEntrega": clean(s["condicao_entrega"].iloc[i]),
            "depositoLogico": clean(s["deposito"].iloc[i]),
            "devolucao": clean(s["devolucao"].iloc[i]),
            "responsavel": clean(s["responsavel"].iloc[i]),
            "estado": clean(s["estado"].iloc[i]),
            "canal": clean(s["canal"].iloc[i]),
            "data": build_date(s["dia"].iloc[i], s["mes"].iloc[i], s["ano"].iloc[i]),
            "dia": integer(s["dia"].iloc[i]),
            "mes": month_number(s["mes"].iloc[i]),
            "mesMapa": normalized_month_map[i],
            "ano": integer(s["ano"].iloc[i]),
            "dataOrigemColunaI": clean(s["data_criacao"].iloc[i]),
        })
    return records


def generate(source, output_dir):
    print(f"\n{APP_NAME}\n{'=' * len(APP_NAME)}")
    print(f"Arquivo: {source}")
    print(f"Aba utilizada: {SHEET_NAME}")

    xls = pd.ExcelFile(source, engine="openpyxl")
    if SHEET_NAME not in xls.sheet_names:
        raise ValueError(
            f"A aba '{SHEET_NAME}' não foi encontrada. Abas: {', '.join(xls.sheet_names)}"
        )

    # SOMENTE Principal. Abas ocultas/secundárias são ignoradas.
    df = pd.read_excel(source, sheet_name=SHEET_NAME, engine="openpyxl", dtype=object)
    validate_columns(df)
    warnings, validation = validate_critical_data(df)

    print(f"Registros lidos: {len(df):,}")
    print(f"Colunas lidas: {len(df.columns)}")
    print(f"Datas válidas: {validation['datas_validas']:,}")
    print(f"Datas inválidas: {validation['datas_invalidas']:,}")
    print(f"Quantidades inválidas: {validation['quantidades_invalidas']:,}")
    print(f"Linhas em ordens duplicadas: {validation['linhas_em_ordens_duplicadas']:,}")
    for warning in warnings:
        print(f"AVISO: {warning}")

    records = generate_records(df)
    if not records:
        raise ValueError("Nenhum registro foi gerado.")

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / OUTPUT_NAME
    generated_at = datetime.now().astimezone()

    payload = {
        "schema_version": 4,
        "source_sheet": SHEET_NAME,
        "generated_at": generated_at.isoformat(),
        "records": records,
    }
    with gzip.open(target, "wt", encoding="utf-8", compresslevel=9) as file:
        json.dump(payload, file, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    if not target.exists() or target.stat().st_size <= 0:
        raise RuntimeError(f"O JSON.GZ não foi criado corretamente: {target}")

    with gzip.open(target, "rt", encoding="utf-8") as check_file:
        check_payload = json.load(check_file)

    if not isinstance(check_payload.get("records"), list):
        raise RuntimeError("Validação final falhou: records não é uma lista.")

    if len(check_payload["records"]) != len(records):
        raise RuntimeError("Validação final falhou: quantidade de registros do JSON diverge da geração.")

    stat = source.stat()
    pedidos = len(records)
    unidades = sum(float(r["quantidade"] or 0) for r in records)
    devolucoes = sum(str(r["devolucao"]).strip().upper() == "SIM" for r in records)
    datas_validas = sum(bool(r["data"]) for r in records)

    manifest = {
        "atualizado_em": generated_at.isoformat(),
        "arquivo_origem": source.name,
        "caminho_origem": str(source),
        "aba_origem": SHEET_NAME,
        "ultima_modificacao_arquivo": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
        "registros": pedidos,
        "unidades": unidades,
        "devolucoes": devolucoes,
        "datas_validas": datas_validas,
        "responsaveis": len({r["responsavel"] for r in records}),
        "transportadoras": len({r["transportadora"] for r in records}),
        "status_distintos": len({r["status"] for r in records}),
        "tipos_operacao_distintos": len({r["tipoOperacao"] for r in records}),
        "colunas_origem": len(df.columns),
        "arquivo_dados": OUTPUT_NAME,
        "observacao": "Somente a aba Principal é considerada. As demais abas, inclusive ocultas, são ignoradas.",
        "validacao": {
            "estrutura_ok": True,
            "json_reaberto_com_sucesso": True,
            "registros_json": len(check_payload["records"]),
            "datas_validas": validation["datas_validas"],
            "datas_invalidas": validation["datas_invalidas"],
            "quantidades_invalidas": validation["quantidades_invalidas"],
            "linhas_em_ordens_duplicadas": validation["linhas_em_ordens_duplicadas"],
            "avisos": warnings,
        },
        "mapeamento": {excel_col(pos): name for name, pos in COL.items()},
    }
    (output_dir / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCONVERSÃO CONCLUÍDA")
    print(f"Pedidos/registros : {pedidos:,}")
    print(f"Unidades          : {unidades:,.0f}")
    print(f"Devoluções = SIM  : {devolucoes:,}")
    print(f"Datas válidas     : {datas_validas:,}")
    print(f"JSON.GZ           : {target}")
    return target


def main():
    parser = argparse.ArgumentParser(
        description="Converte o Excel atualizado da aba Principal para o JSON.GZ do dashboard."
    )
    parser.add_argument("arquivo", nargs="?", help="Caminho do Excel atualizado")
    parser.add_argument("--pasta-excel", help="Pasta para busca automática do Excel")
    parser.add_argument("--saida", default=None, help="Pasta de saída; padrão: dashboard/data")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parents[1]
    output_dir = Path(args.saida).expanduser().resolve() if args.saida else project_dir / "data"

    try:
        source = find_source_file(args.arquivo, args.pasta_excel)
        generate(source, output_dir)
    except Exception as exc:
        print("\nERRO")
        print(f"{type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
