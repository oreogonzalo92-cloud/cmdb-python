# cmdb-python

Herramienta en Python para comparar dos archivos Excel y detectar novedades de calidad de datos.

## ¿Qué valida?

- Registros duplicados por columna llave (ejemplo: `RUT/NIT`) dentro de cada archivo.
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

## Uso base

```bash
python excel_audit.py archivo_1.xlsx archivo_2.xlsx --id-col id --name-col nombre --output reporte_auditoria.xlsx
```

## Uso recomendado para tu estructura (ejemplo real)

Si tus columnas se llaman como en tu muestra (`Razon Social`, `Nombre fantasía`, `RUT/NIT`):

```bash
python excel_audit.py base_anterior.xlsx base_nueva.xlsx \
  --id-col "RUT/NIT" \
  --name-col "Razon Social" \
  --text-check-cols "Razon Social,Nombre fantasía,Nemotecnico,Nombre Contacto,Ciudad" \
  --output reporte_clientes.xlsx
```

### Opciones útiles

- `--sheet-1` y `--sheet-2`: hoja de cada Excel (nombre o índice).
- `--allowed-name-regex`: regex para definir qué caracteres están permitidos en columnas de texto.

## ¿Cómo hacer las pruebas?

### 1) Prueba rápida de sintaxis

```bash
python -m py_compile excel_audit.py test_excel_audit.py
```

Si no imprime errores, la sintaxis está correcta.

### 2) Pruebas unitarias

```bash
pytest -q
```

Estas pruebas validan:

- Detección de IDs duplicados.
- Detección de caracteres inválidos en múltiples columnas.
- Detección de texto posiblemente mal codificado (`fantasÃ­a`).
- Detección de cambios de nombre para el mismo ID y diferencias de presencia entre archivos.

## Salida

Genera un Excel con hojas:

- `resumen`
- `duplicados_archivo_1`
- `duplicados_archivo_2`
- `chars_invalidos_archivo_1`
- `chars_invalidos_archivo_2`
- `posible_mojibake_archivo_1`
- `posible_mojibake_archivo_2`
- `nombre_distinto_mismo_id`
- `solo_archivo_1`
- `solo_archivo_2`
