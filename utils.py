import pandas as pd
from datetime import datetime
import math

# Funcion para extraer coordenadas de la foto (Movida a image_processing.py)
# Funcion para convertir imagen JPEG a PNG en memoria (Movida a image_processing.py)
def limpiar_y_convertir(valor, defecto="-"):
    if pd.isna(valor):
        return defecto

    # # Convertimos a string y limpiamos espacios
    # print("Original")
    # print(valor)
    valor = str(valor).strip()
    # print("Nuevo")
    # print(valor)

    # # Reemplazar puntos (miles) y luego comas (decimales)
    # valor = valor.replace(".", "").replace(",", ".")
    valor = valor.replace(",", "")

    try:
        return float(valor)
    except ValueError:
        return defecto

def calcular_costo_anual(frec, costo):
    """
    Calcula el costo anual basado en la frecuencia y el costo proporcionado.
    Args:
    - frec (str): La frecuencia del costo ('Mensual', 'Trimestral', 'Anual', 'Otro').
    - costo (float): El costo asociado con la frecuencia dada.
    Returns:
    - float or str: El costo anual calculado o "-" si el costo no puede ser calculado.
    """
    if pd.notna(frec) and pd.notna(costo) and frec != "-" and costo != "-":
        frec_lower = str(frec).lower()
        if 'mensual' in frec_lower:
            return round((costo * 12), 1)
        elif 'trimestral' in frec_lower:
            return round((costo * 4), 1)
        elif 'anual' in frec_lower or 'otro' in frec_lower: # Asumimos que 'Otro' es un costo único anual o ya anualizado
            return round(costo, 1)
    return "-"

def determinar_estado_mantenimiento_fila(row, columnas_a_evaluar):
    """Determina el estado de mantenimiento basado en varias columnas."""
    valores = row[columnas_a_evaluar]
    if all(pd.isnull(value) or value == '-' for value in valores): # Considerar '-' como nulo para esta lógica
        return '-'
    # Filtrar valores nulos o '-' antes de verificar 'Si' o 'No'
    valores_validos = [v for v in valores if pd.notnull(v) and v != '-']
    if not valores_validos: # Si después de filtrar no quedan valores, es '-'
        return '-'
    if all(value == 'Si' for value in valores_validos):
        return 'Si'
    elif all(value == 'No' for value in valores_validos):
        return 'No'
    else:
        return 'Parcial'

def calcular_anios_antiguedad(valor_anio):
    """Calcula años de antigüedad desde el año actual."""
    if pd.notnull(valor_anio) and valor_anio != '-':
        try:
            year = int(valor_anio)
            if year > 1000: # Heurística simple para validar año
                anio_actual = datetime.now().year
                return str(anio_actual - year) + ' años'
        except (ValueError, TypeError):
            return '-'
    return '-'

def determinar_estado_operativo_grupo(group, columna_estado='estadooperativo'):
    """Determina el estado operativo consolidado para un grupo."""
    estados = group[columna_estado].dropna().unique()
    if not list(estados) or all(e == '-' for e in estados):
        return '-'
    if all(e == 'Opera normal' for e in estados if e != '-'):
        return 'Opera normal'
    elif all(e == 'Inoperativo' for e in estados if e != '-'):
        return 'Inoperativo'
    # Si hay una mezcla o solo 'Opera limitado' (y no todos son 'Opera normal' o 'Inoperativo')
    elif 'Opera limitado' in estados or (('Opera normal' in estados and 'Inoperativo' in estados) and len(estados) > 1):
         return 'Opera limitado'
    elif 'Opera normal' in estados: # Si solo hay 'Opera normal' y quizás '-'
        return 'Opera normal'
    elif 'Inoperativo' in estados: # Si solo hay 'Inoperativo' y quizás '-'
        return 'Inoperativo'
    return 'Opera limitado' # Fallback, o si solo hay 'Opera limitado'

def evaluar_estado_operativo_alcantarillado(valores):
    """Evalúa el estado operativo para alcantarillado excluyendo ciertos valores."""
    valores_filtrados = [v for v in valores if pd.notnull(v) and v not in ["-", "No cuenta"]]
    if not valores_filtrados:
        return "-"
    if all(valor == "Opera normal" for valor in valores_filtrados):
        return "Opera normal"
    elif all(valor == "Inoperativo" for valor in valores_filtrados):
        return "Inoperativo"
    else:
        return "Opera limitado"

def formatear_valor(valor, defecto="-"):
    """Formatea un valor numérico en formato español a float o devuelve un valor por defecto."""
    if pd.isna(valor):
        return defecto

    # # Convertimos a string y limpiamos espacios
    # print("Original")
    # print(valor)
    valor = str(valor).strip()
    # print("Nuevo")
    # print(valor)

    # # Reemplazar puntos (miles) y luego comas (decimales)
    # valor = valor.replace(".", "").replace(",", ".")
    valor = valor.replace(",", "")

    try:
        return float(valor)
    except ValueError:
        return defecto

def obtener_valor_o_defecto(serie, defecto='-'):
    """Obtiene el primer valor de una serie o un valor por defecto."""
    if not serie.empty and pd.notna(serie.iloc[0]):
        return serie.iloc[0]
    return defecto