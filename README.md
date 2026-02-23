# cmdb-python

Herramienta en Python para comparar dos archivos Excel y detectar novedades de calidad de datos.

## ¿Qué valida?

### Prioridad 1 (lo que pediste primero)

- Campos vacíos en columnas obligatorias del **archivo 1**.
- Registros duplicados por columna llave en el **archivo 1**.

### Validaciones adicionales

- Duplicados en archivo 2.
- Caracteres no permitidos en una o varias columnas de texto.
- Posibles problemas de codificación (mojibake), por ejemplo `fantasÃ­a`.
- Mismo ID con `nombre` distinto entre archivo 1 y archivo 2.
- IDs que están solo en uno de los archivos.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso recomendado para tu estructura (enfocado en vacíos + duplicados en archivo 1)

```bash
python excel_audit.py base_anterior.xlsx base_nueva.xlsx \
  --id-col "RUT/NIT" \
  --name-col "Razon Social" \
  --required-cols "RUT/NIT,Razon Social,Pais,Tipo Organizacion" \
  --text-check-cols "Razon Social,Nombre fantasía,Nemotecnico,Nombre Contacto,Ciudad" \
  --output reporte_clientes.xlsx
```

## ¿Cómo leer el reporte?

Primero abre estas hojas:

1. `vacios_obligatorios_archivo_1`
2. `duplicados_archivo_1`

Luego revisa el resto (`chars_invalidos_*`, `posible_mojibake_*`, etc.).

## ¿Cómo hacer las pruebas?

### 1) Prueba rápida de sintaxis

```bash
python -m py_compile excel_audit.py test_excel_audit.py
```

### 2) Pruebas unitarias

```bash
pytest -q
```

## Salida

Genera un Excel con hojas:

- `resumen`
- `vacios_obligatorios_archivo_1`
- `duplicados_archivo_1`
- `vacios_obligatorios_archivo_2`
- `duplicados_archivo_2`
- `chars_invalidos_archivo_1`
- `chars_invalidos_archivo_2`
- `posible_mojibake_archivo_1`
- `posible_mojibake_archivo_2`
- `nombre_distinto_mismo_id`
- `solo_archivo_1`
- `solo_archivo_2`
