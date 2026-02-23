import pandas as pd

from excel_audit import (
    compare_by_id_and_name,
    find_duplicates,
    find_empty_required_fields,
    find_invalid_chars_in_columns,
    find_mojibake_in_columns,
)


def test_find_duplicates():
    df = pd.DataFrame(
        {
            "id": [1, 2, 2, 3],
            "nombre": ["Ana", "Luis", "Luis 2", "Marta"],
        }
    )
    duplicates = find_duplicates(df, "id")
    assert len(duplicates) == 2
    assert set(duplicates["id"].tolist()) == {2}


def test_find_empty_required_fields():
    df = pd.DataFrame(
        {
            "RUT/NIT": ["123", "", None],
            "Razon Social": ["Empresa A", "Empresa B", "  "],
        }
    )
    missing = find_empty_required_fields(df, ["RUT/NIT", "Razon Social"])
    assert len(missing) == 3


def test_find_invalid_chars_in_columns():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "nombre": ["Ana", "Lui$", "Marta"],
            "Razon Social": ["Empresa A", "Empresa B", "Empr€sa C"],
        }
    )
    invalid = find_invalid_chars_in_columns(df, ["nombre", "Razon Social"], r"^[A-Za-z ]+$")
    assert len(invalid) == 2


def test_find_mojibake_in_columns():
    df = pd.DataFrame(
        {
            "Nombre fantasía": ["Normal", "fantasÃ­a"],
            "Razon Social": ["OK", "Texto bien"],
        }
    )
    mojibake = find_mojibake_in_columns(df, ["Nombre fantasía", "Razon Social"])
    assert len(mojibake) == 1
    assert mojibake.iloc[0]["columna"] == "Nombre fantasía"


def test_compare_by_id_and_name_detects_changes_and_missing():
    left = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "nombre": ["Ana", "Luis", "Mario"],
        }
    )
    right = pd.DataFrame(
        {
            "id": [1, 2, 4],
            "nombre": ["Ana", "Luisa", "Carla"],
        }
    )

    changed, only_left, only_right = compare_by_id_and_name(left, right, "id", "nombre")

    assert len(changed) == 1
    assert changed.iloc[0]["id"] == 2
    assert len(only_left) == 1 and only_left.iloc[0]["id"] == 3
    assert len(only_right) == 1 and only_right.iloc[0]["id"] == 4
