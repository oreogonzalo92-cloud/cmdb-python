#!/usr/bin/env python3
"""Herramienta para auditar y comparar archivos Excel de registros.

Detecta:
- IDs duplicados dentro de cada archivo.
- Campos vacíos en columnas seleccionadas (prioridad en archivo 1).
- Caracteres no permitidos en una o varias columnas de texto.
- Posibles errores de codificación (mojibake), ej: "fantasÃ­a".
- Novedades entre dos archivos cuando el ID es igual pero el nombre cambia.
- IDs nuevos o faltantes entre archivos.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Dict

import pandas as pd


DEFAULT_ALLOWED_NAME_REGEX = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .,'\-_/()&]+$"
MOJIBAKE_PATTERN = re.compile(r"(Ã.|Â.|\uFFFD)")


@dataclass
class AuditResult:
    duplicates_left: pd.DataFrame
    duplicates_right: pd.DataFrame
    empty_required_left: pd.DataFrame
    empty_required_right: pd.DataFrame
    invalid_chars_left: pd.DataFrame
    invalid_chars_right: pd.DataFrame
    mojibake_left: pd.DataFrame
    mojibake_right: pd.DataFrame
    changed_name: pd.DataFrame
    only_left: pd.DataFrame
    only_right: pd.DataFrame

    def to_summary(self) -> Dict[str, int]:
        return {
            "duplicados_archivo_1": len(self.duplicates_left),
            "duplicados_archivo_2": len(self.duplicates_right),
            "campos_vacios_obligatorios_archivo_1": len(self.empty_required_left),
            "campos_vacios_obligatorios_archivo_2": len(self.empty_required_right),
            "texto_con_caracteres_invalidos_archivo_1": len(self.invalid_chars_left),
            "texto_con_caracteres_invalidos_archivo_2": len(self.invalid_chars_right),
            "posible_mojibake_archivo_1": len(self.mojibake_left),
            "posible_mojibake_archivo_2": len(self.mojibake_right),
            "ids_con_nombre_distinto": len(self.changed_name),
            "ids_solo_en_archivo_1": len(self.only_left),
            "ids_solo_en_archivo_2": len(self.only_right),
        }


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split()).lower()


def load_excel(path: str, sheet: str | int = 0) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet)


def validate_columns(df: pd.DataFrame, required_cols: list[str], source_name: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"En {source_name} faltan columnas requeridas: {missing}")


def is_blank(value: object) -> bool:
    return pd.isna(value) or str(value).strip() == ""


def find_empty_required_fields(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    records: list[dict] = []

    for idx, row in df.iterrows():
        for col in cols:
            if is_blank(row.get(col)):
                records.append(
                    {
                        "fila_excel": idx + 2,
                        "columna": col,
                        "valor": row.get(col),
                    }
                )

    return pd.DataFrame(records)


def find_duplicates(df: pd.DataFrame, id_col: str) -> pd.DataFrame:
    dup_mask = df.duplicated(subset=[id_col], keep=False)
    out = df.loc[dup_mask].copy()
    if not out.empty:
        out = out.sort_values(by=[id_col])
    return out


def find_invalid_chars_in_columns(df: pd.DataFrame, cols: list[str], allowed_regex: str) -> pd.DataFrame:
    pattern = re.compile(allowed_regex)
    records: list[dict] = []

    for idx, row in df.iterrows():
        for col in cols:
            value = row.get(col)
            if pd.isna(value):
                continue
            raw = str(value)
            if pattern.fullmatch(raw) is None:
                records.append(
                    {
                        "fila_excel": idx + 2,
                        "columna": col,
                        "valor": raw,
                    }
                )

    return pd.DataFrame(records)


def find_mojibake_in_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    records: list[dict] = []

    for idx, row in df.iterrows():
        for col in cols:
            value = row.get(col)
            if pd.isna(value):
                continue
            raw = str(value)
            if MOJIBAKE_PATTERN.search(raw):
                records.append(
                    {
                        "fila_excel": idx + 2,
                        "columna": col,
                        "valor": raw,
                    }
                )

    return pd.DataFrame(records)


def compare_by_id_and_name(
    left: pd.DataFrame,
    right: pd.DataFrame,
    id_col: str,
    name_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    left_cmp = left[[id_col, name_col]].drop_duplicates(subset=[id_col]).copy()
    right_cmp = right[[id_col, name_col]].drop_duplicates(subset=[id_col]).copy()

    left_cmp["_name_norm"] = left_cmp[name_col].map(normalize_text)
    right_cmp["_name_norm"] = right_cmp[name_col].map(normalize_text)

    merged = left_cmp.merge(
        right_cmp,
        on=id_col,
        how="outer",
        suffixes=("_archivo_1", "_archivo_2"),
        indicator=True,
    )

    changed = merged[(merged["_merge"] == "both") & (merged["_name_norm_archivo_1"] != merged["_name_norm_archivo_2"])].copy()
    only_left = merged[merged["_merge"] == "left_only"].copy()
    only_right = merged[merged["_merge"] == "right_only"].copy()

    changed = changed[[id_col, f"{name_col}_archivo_1", f"{name_col}_archivo_2"]]
    only_left = only_left[[id_col, f"{name_col}_archivo_1"]]
    only_right = only_right[[id_col, f"{name_col}_archivo_2"]]
    return changed, only_left, only_right


def run_audit(
    file_left: str,
    file_right: str,
    id_col: str,
    name_col: str,
    text_check_cols: list[str],
    required_cols: list[str],
    allowed_name_regex: str = DEFAULT_ALLOWED_NAME_REGEX,
    sheet_left: str | int = 0,
    sheet_right: str | int = 0,
) -> AuditResult:
    left = load_excel(file_left, sheet_left)
    right = load_excel(file_right, sheet_right)

    all_required_for_schema = [id_col, name_col] + text_check_cols + required_cols
    validate_columns(left, all_required_for_schema, source_name=file_left)
    validate_columns(right, all_required_for_schema, source_name=file_right)

    duplicates_left = find_duplicates(left, id_col)
    duplicates_right = find_duplicates(right, id_col)

    empty_required_left = find_empty_required_fields(left, required_cols)
    empty_required_right = find_empty_required_fields(right, required_cols)

    invalid_chars_left = find_invalid_chars_in_columns(left, text_check_cols, allowed_name_regex)
    invalid_chars_right = find_invalid_chars_in_columns(right, text_check_cols, allowed_name_regex)

    mojibake_left = find_mojibake_in_columns(left, text_check_cols)
    mojibake_right = find_mojibake_in_columns(right, text_check_cols)

    changed_name, only_left, only_right = compare_by_id_and_name(left, right, id_col, name_col)

    return AuditResult(
        duplicates_left=duplicates_left,
        duplicates_right=duplicates_right,
        empty_required_left=empty_required_left,
        empty_required_right=empty_required_right,
        invalid_chars_left=invalid_chars_left,
        invalid_chars_right=invalid_chars_right,
        mojibake_left=mojibake_left,
        mojibake_right=mojibake_right,
        changed_name=changed_name,
        only_left=only_left,
        only_right=only_right,
    )


def save_report(result: AuditResult, output_path: str) -> None:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame([result.to_summary()]).to_excel(writer, sheet_name="resumen", index=False)
        result.empty_required_left.to_excel(writer, sheet_name="vacios_obligatorios_archivo_1", index=False)
        result.duplicates_left.to_excel(writer, sheet_name="duplicados_archivo_1", index=False)
        result.empty_required_right.to_excel(writer, sheet_name="vacios_obligatorios_archivo_2", index=False)
        result.duplicates_right.to_excel(writer, sheet_name="duplicados_archivo_2", index=False)
        result.invalid_chars_left.to_excel(writer, sheet_name="chars_invalidos_archivo_1", index=False)
        result.invalid_chars_right.to_excel(writer, sheet_name="chars_invalidos_archivo_2", index=False)
        result.mojibake_left.to_excel(writer, sheet_name="posible_mojibake_archivo_1", index=False)
        result.mojibake_right.to_excel(writer, sheet_name="posible_mojibake_archivo_2", index=False)
        result.changed_name.to_excel(writer, sheet_name="nombre_distinto_mismo_id", index=False)
        result.only_left.to_excel(writer, sheet_name="solo_archivo_1", index=False)
        result.only_right.to_excel(writer, sheet_name="solo_archivo_2", index=False)


def parse_cols(value: str) -> list[str]:
    return [c.strip() for c in value.split(",") if c.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compara dos Excel y detecta inconsistencias de calidad de datos.")
    parser.add_argument("archivo_1", help="Ruta del primer archivo Excel")
    parser.add_argument("archivo_2", help="Ruta del segundo archivo Excel")
    parser.add_argument("--id-col", default="id", help="Nombre de la columna ID (default: id)")
    parser.add_argument("--name-col", default="nombre", help="Nombre de la columna nombre (default: nombre)")
    parser.add_argument(
        "--text-check-cols",
        default="nombre",
        help="Columnas de texto a validar (separadas por coma)",
    )
    parser.add_argument(
        "--required-cols",
        default="",
        help="Columnas obligatorias para detectar vacíos (separadas por coma)",
    )
    parser.add_argument("--sheet-1", default=0, help="Nombre o índice de hoja en archivo 1 (default: 0)")
    parser.add_argument("--sheet-2", default=0, help="Nombre o índice de hoja en archivo 2 (default: 0)")
    parser.add_argument(
        "--allowed-name-regex",
        default=DEFAULT_ALLOWED_NAME_REGEX,
        help="Regex de caracteres permitidos para columnas de texto",
    )
    parser.add_argument("--output", default="reporte_auditoria.xlsx", help="Ruta del Excel de salida")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    text_check_cols = parse_cols(args.text_check_cols)
    required_cols = parse_cols(args.required_cols) or [args.id_col, args.name_col]

    result = run_audit(
        file_left=args.archivo_1,
        file_right=args.archivo_2,
        id_col=args.id_col,
        name_col=args.name_col,
        text_check_cols=text_check_cols,
        required_cols=required_cols,
        allowed_name_regex=args.allowed_name_regex,
        sheet_left=args.sheet_1,
        sheet_right=args.sheet_2,
    )

    save_report(result, args.output)
    summary = result.to_summary()
    print("Auditoría completada. Resumen:")
    print("(Primero revisa vacíos y duplicados del archivo 1)")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    print(f"Reporte generado en: {args.output}")


if __name__ == "__main__":
    main()
