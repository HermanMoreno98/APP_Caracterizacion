# Flask y dependencias web
from flask import Flask, render_template, send_file, redirect, url_for

# Crear la aplicación Flask
application = Flask(__name__)
app = application

# Resto de importaciones
import pandas as pd
from docxtpl import DocxTemplate, InlineImage, RichText
import glob
import datetime as dt
from docx.shared import Inches
import math
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import warnings
from datetime import datetime
from babel.dates import format_date
import numpy as np
#import pyshorteners #short url
from natsort import natsorted
import os
from PIL import Image, ExifTags
from io import BytesIO
warnings.filterwarnings("ignore") # Ignorar todos los warnings
import generarInforme as cp
import generarInforme_sin_prestador as sp
from functools import reduce
import requests
from msal import PublicClientApplication, ConfidentialClientApplication
from urllib.parse import quote
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
from dotenv import load_dotenv
import jwt

# Cargar variables de entorno
load_dotenv()

# Verificar variables de entorno
required_env_vars = ["TENANT_ID", "CLIENT_ID", "CLIENT_SECRET", "RESOURCE"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise Exception(f"Faltan las siguientes variables de entorno: {', '.join(missing_vars)}")

print("Variables de entorno cargadas correctamente")

import os
import shutil
import atexit


# # Ejemplo de uso
# prestador_id = "P-09722-B4T9H"










############################################# II. Filtrando un prestador #############################################
######################################################################################################################


# Configuración Dataverse

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
RESOURCE = os.getenv("RESOURCE")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = [f"{RESOURCE}/.default"]  # Simplificando a un solo scope

SCOPES_SHAREPOINT = ["https://graph.microsoft.com/.default"]


def obtener_datos_relacionados(prestador_id, columnas, propiedad_navegacion,token):
    """
    Consulta la tabla de prestadores por ID y expande los registros relacionados.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }

    select_expand = ",".join(columnas)
    expand = f"{propiedad_navegacion}($select={select_expand})"
    expand_encoded = quote(expand, safe="=(),$")
    
    url = f"{RESOURCE}/api/data/v9.2/cr217_prestadors({prestador_id})?$expand={expand_encoded}"

    print(f"🔗 Consultando URL: {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if propiedad_navegacion in data:
        registros = data[propiedad_navegacion]
        print(f"✅ {len(registros)} registros encontrados en la relación '{propiedad_navegacion}'")
        return registros
    else:
        print(f"⚠️ No se encontraron registros en la relación '{propiedad_navegacion}'")
        return []

# =====================================
# 🔍 Función para buscar prestador por código y obtener datos relacionados
def obtener_relacion_por_codigo(prestador_id, columnas, propiedad_navegacion,token):
    """
    Busca el ID del prestador usando su código y obtiene los datos relacionados desde el expand.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }

    filtro = f"cr217_codigodeprestador eq '{prestador_id}'"
    filtro_encoded = quote(filtro, safe="'= ")
    
    url = f"{RESOURCE}/api/data/v9.2/cr217_prestadors?$select=cr217_prestadorid&$filter={filtro_encoded}"

    print(f"🔍 Buscando ID del prestador con código '{prestador_id}'...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if not data["value"]:
        print("❌ Prestador no encontrado.")
        return []

    prestador_id = data["value"][0]["cr217_prestadorid"]
    print(f"✅ ID encontrado: {prestador_id}")

    return obtener_datos_relacionados(prestador_id, columnas, propiedad_navegacion,token)

# ===============================
# 🧪 Ejemplo de uso

# codigo = "P-09692-G4F6W"
# columnas = ["cr217_nombredelafuente","cr217_cuentaconlicenciauso", "createdon"]
# propiedad_navegacion = "cr217_cr217_fuente_Prestador_cr217_prestador"

# datos = obtener_relacion_por_codigo(codigo, columnas, propiedad_navegacion,token)

# print(datos)
def obtener_elementos_por_sistema(sistema_id, tipo_sistema, entidad_relacion, campos, token):
    """
    tipo_sistema: "agua" o "alcantarillado"
    entidad_relacion: sufijo de la relación (por ejemplo: "c", "r", etc.)
    """
    entidad_padre = {
        "agua": "cr217_sistemadeaguas",
        "alcantarillado": "cr217_sistemadealcantarillados"
    }[tipo_sistema]

    expand_rel = {
        "agua": f"cr217_Sistemadeagua_cr217_Sistemadeagua_{entidad_relacion}",
        "alcantarillado": f"cr217_Sistemadealcantarillado_cr217_{entidad_relacion}"
    }[tipo_sistema]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }

    campos_select = ",".join(campos)
    url = (
        f"{RESOURCE}/api/data/v9.2/{entidad_padre}({sistema_id})"
        f"?$expand={expand_rel}($select={campos_select})"
    )

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get(expand_rel, [])

def obtener_sistemas(prestador_id, tipo_sistema, token):
    entidad_expand = {
        "agua": "cr217_cr217_sistemadeagua_Prestador_cr217_prest",
        "alcantarillado": "cr217_cr217_sistemadealcantarillado_Prestador_c"
    }[tipo_sistema]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }

    url = (
        f"{RESOURCE}/api/data/v9.2/cr217_prestadors({prestador_id})"
        f"?$expand={entidad_expand}($select=cr217_sistemade{tipo_sistema}id,cr217_codigodesistemade{tipo_sistema})"
    )

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get(entidad_expand, [])


def generar_df_elementos_relacionados(codigo_prestador, tipo_sistema, entidad_relacion, campos, nombres_columnas,token):
    """
    tipo_sistema: "agua" o "alcantarillado"
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }

    # Obtener ID del prestador
    filtro = quote(f"cr217_codigodeprestador eq '{codigo_prestador}'", safe="'= ")
    url = f"{RESOURCE}/api/data/v9.2/cr217_prestadors?$select=cr217_prestadorid&$filter={filtro}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if not data["value"]:
        print("❌ Prestador no encontrado.")
        return pd.DataFrame()

    prestador_id = data["value"][0]["cr217_prestadorid"]

    # Obtener sistemas de agua o alcantarillado
    sistemas = obtener_sistemas(prestador_id, tipo_sistema, token)

    registros = []
    for sistema in sistemas:
        sistema_id = sistema.get(f"cr217_sistemade{tipo_sistema}id")
        codigo_sistema = sistema.get(f"cr217_codigodesistemade{tipo_sistema}", "")

        elementos = obtener_elementos_por_sistema(sistema_id, tipo_sistema, entidad_relacion, campos, token)

        for elemento in elementos:
            fila = {
                "codigodeprestador": codigo_prestador,
                f"codigodesistemade{tipo_sistema}": codigo_sistema
            }
            for i, campo in enumerate(campos):
                # Si es opción global, trae el valor formateado
                if campo + "@OData.Community.Display.V1.FormattedValue" in elemento:
                    fila[nombres_columnas[i]] = elemento.get(f"{campo}@OData.Community.Display.V1.FormattedValue", "")
                else:
                    fila[nombres_columnas[i]] = elemento.get(campo, "")
            registros.append(fila)

    return pd.DataFrame(registros)

def obtener_prestador_id(codigo_prestador, token):
    """
    Obtiene el ID del prestador a partir de su código.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }
    # Obtener ID del prestador
    filtro = quote(f"cr217_codigodeprestador eq '{codigo_prestador}'", safe="'= ")
    url = f"{RESOURCE}/api/data/v9.2/cr217_prestadors?$select=cr217_prestadorid&$filter={filtro}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if not data["value"]:
        print("❌ Prestador no encontrado.")
        return pd.DataFrame()

    prestador_id = data["value"][0]["cr217_prestadorid"]
    
    return prestador_id

def obtener_df_relaciones_prestador(codigo_prestador, relaciones_config, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }

    prestador_id = obtener_prestador_id(codigo_prestador, token)
    
    # Verificar si se incluyó config del prestador
    prestador_config = relaciones_config.get("__prestador__", {})
    campos_prestador = prestador_config.get("campos", [])
    nombres_prestador = prestador_config.get("nombres_columnas", [])

    # Construir partes del $select y $expand
    expand_parts = []
    for rel_name, config in relaciones_config.items():
        if rel_name == "__prestador__":
            continue  # No incluir en $expand
        campos = config["campos"]
        campos_select = ",".join(campos)
        expand_parts.append(f"{rel_name}($select={campos_select})")

    expand_string = ",".join(expand_parts)
    select_string = ",".join(campos_prestador)

    url = f"{RESOURCE}/api/data/v9.2/cr217_prestadors({prestador_id})"
    if select_string or expand_string:
        url += "?"
        if select_string:
            url += f"$select={select_string}"
        if expand_string:
            url += f"&$expand={expand_string}" if select_string else f"$expand={expand_string}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    resultados = {}
    
    # === Extraer datos del prestador principal ===
    if campos_prestador:
        prestador_row = {}
        for i, campo in enumerate(campos_prestador):
            col_name = nombres_prestador[i]
            formatted_key = f"{campo}@OData.Community.Display.V1.FormattedValue"
            if formatted_key in data:
                prestador_row[col_name] = data[formatted_key]
            else:
                prestador_row[col_name] = data.get(campo, "")
        prestador_row["codigodeprestador"] = codigo_prestador
        resultados["prestador"] = pd.DataFrame([prestador_row])
    
    # === Procesar relaciones ===
    for rel_name, config in relaciones_config.items():
        campos = config["campos"]
        nombres_columnas = config["nombres_columnas"]

        registros = []

        relacion_datos = data.get(rel_name)
        if isinstance(relacion_datos, dict):
            relacion_datos = [relacion_datos]
        elif not isinstance(relacion_datos, list):
            relacion_datos = []

        for item in relacion_datos:
            fila = {}
            if isinstance(item, dict):
                for i, campo in enumerate(campos):
                    formatted_key = f"{campo}@OData.Community.Display.V1.FormattedValue"
                    if formatted_key in item:
                        fila[nombres_columnas[i]] = item.get(formatted_key, "")
                    else:
                        fila[nombres_columnas[i]] = item.get(campo, "")
            else:
                if len(nombres_columnas) == 1:
                    fila[nombres_columnas[0]] = item
                else:
                    fila = {col: "" for col in nombres_columnas}
                    fila[nombres_columnas[0]] = item
            registros.append(fila)


        df = pd.DataFrame(registros)
        df.insert(0, "codigodeprestador", codigo_prestador)
        resultados[rel_name] = df

    return resultados

# Funcion para obtener informacion de poblacion servida del prestador
def obtener_df_prestador_simple(codigo_prestador, token, campos, nombres_columnas):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
    }
    
    prestador_id = obtener_prestador_id(codigo_prestador, token)

    url = (
        f"{RESOURCE}/api/data/v9.2/cr217_prestadors({prestador_id})"
        "?$select=cr217_codigodeprestador"
        "&$expand=cr217_Prestador_cr217_Prestador_cr217_Pob($expand=cr217_Centropoblado($select=cr217_codigodecentropoblado))"
    )

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    registros = []

    relacion_datos = data.get("cr217_Prestador_cr217_Prestador_cr217_Pob", [])
    if not isinstance(relacion_datos, list):
        relacion_datos = [relacion_datos]

    for item in relacion_datos:
        fila = {}
        if isinstance(item, dict):
            for i, campo in enumerate(campos):
                formatted_key = f"{campo}@OData.Community.Display.V1.FormattedValue"
                if formatted_key in item:
                    fila[nombres_columnas[i]] = item.get(formatted_key, "")
                else:
                    fila[nombres_columnas[i]] = item.get(campo, "")
            cod_centro = (
                item.get("cr217_Centropoblado", {})
                    .get("cr217_codigodecentropoblado", "")
            )
            fila["centropoblado"] = cod_centro
        else:
            if len(nombres_columnas) == 1:
                fila[nombres_columnas[0]] = item
            else:
                fila = {col: "" for col in nombres_columnas}
                fila[nombres_columnas[0]] = item
        registros.append(fila)

    df = pd.DataFrame(registros)
    df.insert(0, "codigodeprestador", codigo_prestador)

    return df

# Modificar la función get_token para manejar ambos entornos
def get_token():
    try:
        print("\n=== Iniciando obtención de token ===")
        
        # Verificar si estamos en Render
        is_production = os.environ.get("RENDER") == "true"
        print(f"🌍 Entorno: {'Producción (Render)' if is_production else 'Desarrollo (Local)'}")
        
        # Verificar variables de entorno según el entorno
        if is_production:
            if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, RESOURCE]):
                raise ValueError("En producción se requieren todas las variables de entorno")
        else:
            if not all([TENANT_ID, CLIENT_ID, RESOURCE]):
                raise ValueError("Faltan variables de entorno necesarias para la autenticación")
            
        print("✅ Variables de entorno verificadas")
        print(f"🔐 Tenant ID: {TENANT_ID[:5]}...")
        print(f"👤 Client ID: {CLIENT_ID[:5]}...")
        print(f"🌐 Resource: {RESOURCE}")
        
        if is_production:
            # Usar autenticación con credenciales en producción
            print("🔒 Usando autenticación con credenciales de cliente")
            app = ConfidentialClientApplication(
                CLIENT_ID,
                authority=AUTHORITY,
                client_credential=CLIENT_SECRET
            )
            result = app.acquire_token_for_client(scopes=SCOPE)
        else:
            # Usar autenticación interactiva en desarrollo
            print("🔑 Usando autenticación interactiva")
            app = PublicClientApplication(
                CLIENT_ID,
                authority=AUTHORITY
            )
            
            # Intentar obtener el token del caché primero
            accounts = app.get_accounts()
            if accounts:
                print("📝 Intentando usar token en caché...")
                result = app.acquire_token_silent(SCOPE, account=accounts[0])
            else:
                result = None
                
            if not result:
                print("🔄 Solicitando autenticación interactiva...")
                result = app.acquire_token_interactive(scopes=SCOPE)
            
        if "access_token" not in result:
            error_msg = f"❌ Error al obtener token: {result.get('error_description', 'Sin descripción del error')}"
            print(error_msg)
            raise Exception(error_msg)
            
        print("✅ Token obtenido exitosamente")
        return result["access_token"]
        
    except Exception as e:
        print(f"❌ Error en get_token: {str(e)}")
        import traceback
        print("📋 Traceback completo:")
        print(traceback.format_exc())
        raise

def get_token_sharepoint():
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    
    # Obtener token
    result = app.acquire_token_for_client(scopes=SCOPES_SHAREPOINT)
    return result["access_token"]

def get_bd_sharepoint(file_path, name_file):
    token = get_token_sharepoint()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    domain = "sunassgobpe.sharepoint.com"
    site_path = "/sites/adp2"
    
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{domain}:{site_path}",
        headers=headers
    )
    
    site = response.json()
    site_id = site["id"]
    
    # Obtener Drive del sitio
    drive_response = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive",
        headers=headers
    )
    
    drive_id = drive_response.json()["id"]
    
    # Descargar el archivo
    download_response = requests.get(
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_path}:/content",
        headers=headers
    )
    
    # Guardar el archivo localmente
    with open(name_file, "wb") as f:
        f.write(download_response.content)

    # Leer el archivo con pandas
    data_ps = pd.read_excel(name_file,sheet_name="CCPP")
    
    return data_ps



# Obtener datos desde Dataverse
def get_data():
    token = get_token()
    print(token)
    headers = {
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    url = f"{RESOURCE}/api/data/v9.2/cr217_prestadors?$select=cr217_codigodeprestador"
    response = requests.get(url, headers=headers)
    data = response.json().get("value", [])
    return data

#LLamada con paginación para obtener todos los prestadores
def fetch_all_prestadores():
    try:
        print("\n=== Iniciando fetch_all_prestadores ===")
        token = get_token()
        print(f"✅ Token obtenido exitosamente")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
        }
        
        url = f"{RESOURCE}/api/data/v9.2/cr217_prestadors?$select=cr217_codigodeprestador,createdon&$orderby=createdon desc"
        print(f"🔍 Consultando URL: {url}")
        
        results = []
        try_count = 0
        max_tries = 3
        
        while url and try_count < max_tries:
            try:
                print(f"\n📡 Intento {try_count + 1} de obtener datos...")
                resp = requests.get(url, headers=headers)
                print(f"📊 Status code: {resp.status_code}")
                
                if resp.status_code == 401:
                    print("❌ Error de autenticación. Obteniendo nuevo token...")
                    token = get_token()
                    headers["Authorization"] = f"Bearer {token}"
                    try_count += 1
                    continue
                    
                if resp.status_code != 200:
                    print(f"❌ Error en la respuesta: {resp.text}")
                    return []
                
                data = resp.json()
                current_batch = data.get("value", [])
                print(f"✅ Registros obtenidos en este lote: {len(current_batch)}")
                
                if not current_batch:
                    print("⚠️ No se encontraron registros en este lote")
                    break
                
                results.extend(current_batch)
                url = data.get("@odata.nextLink")
                if url:
                    print(f"➡️ Siguiente página disponible")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Error en la solicitud HTTP: {str(e)}")
                try_count += 1
                continue
                
        print(f"\n🎉 Total de registros obtenidos: {len(results)}")
        if not results:
            print("⚠️ ADVERTENCIA: No se obtuvieron registros")
            
        return results
        
    except Exception as e:
        print(f"❌ Error en fetch_all_prestadores: {str(e)}")
        import traceback
        print("📋 Traceback completo:")
        print(traceback.format_exc())
        return []

# --- Función para generar informe usando plantilla ---
def generate_report_with_template(prestador_id):
    # Obtener el token de acceso
    token = get_token()
    
    # Parámetros de autenticación
    scopes_sharepoint = ["https://graph.microsoft.com/.default"]

    # Crear la app
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    # Obtener token
    result = app.acquire_token_for_client(scopes=scopes_sharepoint)

    if "access_token" not in result:
        raise Exception(f"No se pudo obtener el token: {result.get('error_description')}")

    access_token = result["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    # Dominio
    domain = "sunassgobpe.sharepoint.com"
    site_path = "/sites/adp2"

    response = requests.get(
        f"https://graph.microsoft.com/v1.0/sites/{domain}:{site_path}",
        headers=headers
    )

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
    else:
        site = response.json()
        site_id = site["id"]
        print(f"Site ID: {site_id}")

    document_library_id = "2d1282da-c17d-4888-9111-d1ee867b9510"

    drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{document_library_id}/drive"
    drive_resp = requests.get(drive_url, headers=headers).json()
    drive_id = drive_resp["id"]
    
    folder_name = find_folder_by_prefix(drive_id, prestador_id, headers)
    
    df_captacion = generar_df_elementos_relacionados(
        codigo_prestador=prestador_id,
        tipo_sistema="agua",
        entidad_relacion="c",
        campos=["cr217_codigodecaptacion", "cr217_nombredelacaptacion", "cr217_anodeconstruccion",
                "cr217_estadooperativodelacaptacion","cr217_justifiquesurespuestacaptacion","cr217_zona","cr217_este",
                "cr217_norte","cr217_altitud"],
        nombres_columnas=["codigodecaptacion","nombredelacaptacion", "anodeconstruccion",
                        "estadooperativodelacaptacion","justifiquesurespuestacaptacion","zona","este",
                        "norte","altitud"],
        token=token
    )
    df_conduccion = generar_df_elementos_relacionados(
        codigo_prestador=prestador_id,
        tipo_sistema="agua",
        entidad_relacion="conduc",
        campos=["cr217_codigodeconduccion", "cr217_anodeconstruccionconduccion","cr217_estadooperativodelconductordeaguacruda",
                "cr217_justifiquesurespuestaconduccion"],
        nombres_columnas=["codigodeconduccion","anodeconstruccionconduccion", "estadooperativodelconductordeaguacruda",
                        "justifiquesurespuestaconduccion"],
        token=token
    )
    df_reservorio = generar_df_elementos_relacionados(
        codigo_prestador=prestador_id,
        tipo_sistema="agua",
        entidad_relacion="reservo",
        campos=["cr217_codigodereservorio", "cr217_anodeconstruccion","cr217_estadooperativodereservorio",
                "cr217_justifiquesurespuestareservorio","cr217_zona","cr217_este",
                "cr217_norte","cr217_altitud","cr217_clororesidualmgl"],
        nombres_columnas=["codigodereservorio","anodeconstruccion", "estadooperativodereservorio",
                        "justifiquesurespuestareservorio","zona","este",
                        "norte","altitud","clororesidualmgl"],
        token=token
    )
    df_ptap = generar_df_elementos_relacionados(
        codigo_prestador=prestador_id,
        tipo_sistema="agua",
        entidad_relacion="ptap",
        campos=["cr217_codigodeptap", "cr217_anodeconstruccion","cr217_tipodeptap","cr217_zona","cr217_este",
                "cr217_norte","cr217_altitud",
                "cr217_tienerejaslenta","cr217_estadooperativorejaslenta","cr217_justifiquesurespuestarejas",
                "cr217_tienedesarenadorlenta","cr217_estadooperativodesarenadorlenta","cr217_justifiquesurespuestadesarenador",
                "cr217_tienepresedimentador","cr217_estadooperativopresedimentador","cr217_justifiquesurespuestapresedimentador",
                "cr217_tienesedimentador","cr217_estadooperativosedimentador","cr217_justifiquesurespuestasedimentador",
                "cr217_tieneprefiltrodegrava","cr217_estadooperativoprefiltrodegrava","cr217_justifiquesurespuestaprefiltrograva",
                "cr217_tienefiltrolento","cr217_estadooperativofiltrolento","cr217_justifiquesurespuestafiltrolento",
                "cr217_tienerejasrapida","cr217_estadooperativorejasrapida","cr217_justifiquesurespuestarejasrapida",
                "cr217_tienedesarenadorrapida","cr217_estadooperativodesarenadorrapida","cr217_justifiquesurespuestadesarenadorrapido",
                "cr217_tienepresedimentadorrapida","cr217_estadooperativopresedimentadorrapida","cr217_justifiquesurespuestapresedimentadorrapido",
                "cr217_tienesedimentadorsincoagulacionprevia","cr217_estadooperativosedimentadorsncoagulacion","cr217_justifiquesurespuestasedimentadorsc",
                "cr217_tienemezcladorrapido","cr217_estadooperativomezcladorrapido","cr217_justifiquesurespuestamezcladorrapido",
                "cr217_tienefloculadorhidraulico","cr217_estadooperativofloculadorhidraulico","cr217_justifiquesurespuestafloculadorh",
                "cr217_tienefloculadormecanico","cr217_estadooperativofloculadormecanico","cr217_justifiquesurespuestafloculadormeca",
                "cr217_tienesedimentacionconcoagulacionprevia","cr217_estadooperativosedimentacionccoagulacion","cr217_justifiquesurespuestasedimentacioncc",
                "cr217_tienedecantador","cr217_estadooperativodecantador","cr217_justifiquesurespuestadecantador",
                "cr217_tienefiltrorapido","cr217_estadooperativofiltrorapido","cr217_justifiquesurespuestafiltrorapido"],
        nombres_columnas=["codigodeptap","anodeconstruccion", "tipodeptap","zona","este",
                        "norte","altitud",
                        "tienerejaslenta","estadooperativorejaslenta","justifiquesurespuestarejas",
                        "tienedesarenadorlenta","estadooperativodesarenadorlenta","justifiquesurespuestadesarenador",
                        "tienepresedimentador","estadooperativopresedimentador","justifiquesurespuestapresedimentador",
                        "tienesedimentador","estadooperativosedimentador","justifiquesurespuestasedimentador",
                        "tieneprefiltrodegrava","estadooperativoprefiltrodegrava","justifiquesurespuestaprefiltrograva",
                        "tienefiltrolento","estadooperativofiltrolento","justifiquesurespuestafiltrolento",
                        "tienerejasrapida","estadooperativorejasrapida","justifiquesurespuestarejasrapida",
                        "tienedesarenadorrapida","estadooperativodesarenadorrapida","justifiquesurespuestadesarenadorrapido",
                        "tienepresedimentadorrapida","estadooperativopresedimentadorrapida","justifiquesurespuestapresedimentadorrapido",
                        "tienesedimentadorsincoagulacionprevia","estadooperativosedimentadorsncoagulacion","justifiquesurespuestasedimentadorsc",
                        "tienemezcladorrapido","estadooperativomezcladorrapido","justifiquesurespuestamezcladorrapido",
                        "tienefloculadorhidraulico","estadooperativofloculadorhidraulico","justifiquesurespuestafloculadorh",
                        "tienefloculadormecanico","estadooperativofloculadormecanico","justifiquesurespuestafloculadormeca",
                        "tienesedimentacionconcoagulacionprevia","estadooperativosedimentacionccoagulacion","justifiquesurespuestasedimentacioncc",
                        "tienedecantador","estadooperativodecantador","justifiquesurespuestadecantador",
                        "tienefiltrorapido","estadooperativofiltrorapido","justifiquesurespuestafiltrorapido"],
        token=token
    )
    df_ptar = generar_df_elementos_relacionados(
        codigo_prestador=prestador_id,
        tipo_sistema="alcantarillado",
        entidad_relacion="ptar",
        campos=["cr217_codigodeptar", "cr217_tienerejas","cr217_eorejas","cr217_justifiquesurespuestarejas",
                "cr217_tienedesarenador","cr217_eodesarenador","cr217_justifiquesurespuestadesarenador",
                "cr217_tienemedidoryrepartidordecaudal","cr217_eomedidoryrepartidorcaudal","cr217_justifiquesurespuestamedidorcaudal",
                "cr217_tieneimhoff","cr217_eoimhoff","cr217_justifiquesurespuestatanqueimhoff",
                "cr217_tienetanqueseptico","cr217_eotanqueseptico","cr217_justifiquesurespuestatanqueseptico",
                "cr217_tienetanquedesedimentacion","cr217_eotanquesedimentacion","cr217_justifiquesurespuestatanquesedimento",
                "cr217_tienetanquedeflotacion","cr217_eotanquedeflotacion","cr217_justifiquesurespuestatanqueflota",
                "cr217_tienerafauasb","cr217_eorafauasb","cr217_justifiquesurespuestarafa",
                "cr217_tienelagunasdeestabilizacion","cr217_eolagunasestabilizacion","cr217_justifiquesurespuestalagunaestabilizacion",
                "cr217_tienelodosactivados","cr217_eolodosactivados","cr217_justifiquesurespuestalodosactivados",
                "cr217_tienefiltrospercoladores","cr217_eofiltrospercoladores","cr217_justifiquesurespuestafiltrospercoladores",
                "cr217_anodeconstruccionptar","cr217_comentarios"],
        nombres_columnas=["codigodeptar","tienerejas", "eorejas","justifiquesurespuestarejas",
                        "tienedesarenador","eodesarenador","justifiquesurespuestadesarenador",
                        "tienemedidoryrepartidordecaudal","eomedidoryrepartidorcaudal","justifiquesurespuestamedidorcaudal",
                        "tieneimhoff","eoimhoff","justifiquesurespuestatanqueimhoff",
                        "tienetanqueseptico","eotanqueseptico","justifiquesurespuestatanqueseptico",
                        "tienetanquedesedimentacion","eotanquesedimentacion","justifiquesurespuestatanquesedimento",
                        "tienetanquedeflotacion","eotanquedeflotacion","justifiquesurespuestatanqueflota",
                        "tienerafauasb","eorafauasb","justifiquesurespuestarafa",
                        "tienelagunasdeestabilizacion","eolagunasestabilizacion","justifiquesurespuestalagunaestabilizacion",
                        "tienelodosactivados","eolodosactivados","justifiquesurespuestalodosactivados",
                        "tienefiltrospercoladores","eofiltrospercoladores","justifiquesurespuestafiltrospercoladores",
                        "anodeconstruccionptar","comentarios"],
        token=token
    )
    df_disposicionfinal = generar_df_elementos_relacionados(
        codigo_prestador=prestador_id,
        tipo_sistema="alcantarillado",
        entidad_relacion="df",
        campos=["cr217_codigodedisposicionfinal","cr217_autorizaciondevertimiento"],
        nombres_columnas=["codigodedisposicionfinal","p029_autorizaciondevertimiento"],
        token=token
    )

    ### ENDPOINTS: 
    # 
    # https://org2fcdeea7.api.crm2.dynamics.com/api/data/v9.2/cr217_prestadors(2fd166eb-dc30-f011-8c4e-002248e0a4e0)?$select=cr217_codigodeprestador,cr217_nombredecentropobladocercano&$expand=cr217_cr217_fuente_Prestador_cr217_prestador($select=cr217_nombredelafuente,cr217_cuentaconlicenciauso),cr217_Prestador_cr217_Prestador_cr217_Pob,cr217_cr217_sistemadeagua_Prestador_cr217_prest($select=cr217_codigodesistemadeagua),cr217_cr217_sistemadealcantarillado_Prestador_c,cr217_Prestador_cr217_Prestador_cr217_Ubs,cr217_Prestador_cr217_Prestador_cr217_Usu,cr217_CentroPoblado($select=cr217_codigodecentropoblado),cr217_Codigoubigeocentropobladocercano($select=cr217_codigodecentropoblado)
    # https://org2fcdeea7.api.crm2.dynamics.com/api/data/v9.2/cr217_sistemadeaguas(fd08c89f-a731-f011-8c4e-002248e0a4e0)?$expand=cr217_Sistemadeagua_cr217_Sistemadeagua_c($select=cr217_codigodecaptacion),cr217_Prestador($select=cr217_codigodeprestador)



    relaciones_config = {
        "__prestador__": {
            "campos": ["cr217_codigodeprestador","cr217_oficinadesconcentrada","cr217_ps1_17_pozos","cr217_ps1_17_acarreo",
                    "cr217_ps1_17_cisterna","cr217_ps1_17_otro","cr217_comoseabasteceotro","cr217_gastomensualpromedioporfamiliaagua",
                    "cr217_fechadecaracterizacion","cr217_existeprestadordessenelccppprincipal","cr217_nombredelprestador",
                    "cr217_nombredelcentropobladoprincipal","cr217_nombreyapellido","cr217_cargo","cr217_ambitodeprestador",
                    "cr217_quetipodeprestadores","cr217_formaasociativadeoc","cr217_brindaagua","cr217_brindaalcantarillado",
                    "cr217_brindatratamientodeaguasresiduales","cr217_brindadisposiciondeexcretas","cr217_comentarios",
                    "cr217_comentariosfuente","cr217_cuentaconordenanzamunicipal","cr217_seencuentradentrodeestructuraorganicayrof",
                    "cr217_anodecreaciondeugmantesde2017","cr217_autorizacionsunassprestacionexcepcional",
                    "cr217_laoccuentaconreconocimientodelamuni","cr217_resolucionmunicipaldereconocimientodelaoc",
                    "cr217_fueconstituidosegunlalgdesociedades","cr217_tienecontratosuscritoconlamunicipalidad",
                    "cr217_recibioasistenciatecnicaenlosultimos3anos","cr217_ps1_32_atm","cr217_ps1_32_muni",
                    "cr217_ps1_32_mvcs","cr217_ps1_32_cac","cr217_ps1_32_pnsr","cr217_ps1_32_pnsu","cr217_ps1_32_drvcs",
                    "cr217_ps1_32_sunass","cr217_ps1_32_otro","cr217_ps1_32_otass","cr217_ps1_33_oym",
                    "cr217_ps1_33_controlcalidad","cr217_ps1_33_controlcalidad","cr217_ps1_33_gestionservicios",
                    "cr217_ps1_33_cuotafamiliar","cr217_ps1_33_otro","cr217_ps1_33_grd","cr217_ps1_33_integracion",
                    "cr217_otroasistenciatecnica","cr217_otrotemaasistencia","cr217_cobracuota","cr217_cobraporcadaservicio",
                    "cr217_elcobroquerealizaes","cr217_elpagoestructuradodependedelamicromedicion",
                    "cr217_acuantoasciendeelcobroquerealiza","cr217_acuantoasciendeelcobroquerealizaagua",
                    "cr217_acuantoasciendeelcobroquerealizaalcantari","cr217_acuantoasciendeelcobroquerealizadisposici",
                    "cr217_acuantoasciendeelcobroquerealizatratamien","cr217_conexionesdomestico","cr217_conexionescomercial",
                    "cr217_conexionesindustrial","cr217_conexionessocial","cr217_cualessonlosrangosdecobrodomestico",
                    "cr217_cualessonlosrangosdecobrocomercial","cr217_cualessonlosrangosdecobroindustrial",
                    "cr217_cualessonlosrangosdecobroestatal","cr217_cualessonlosrangosdecobroalcadomestico",
                    "cr217_cualessonlosrangosdecobroalcacomercial","cr217_cualessonlosrangosdecobroalcaindustrial",
                    "cr217_cualessonlosrangosdecobroalcasocial","cr217_cualessonlosrangosdecobrootrodomestico",
                    "cr217_cualessonlosrangosdecobrootrocomercial","cr217_cualessonlosrangosdecobrootroindustrial",
                    "cr217_cualessonlosrangosdecobrootrosocial","cr217_domesticorango1","cr217_domesticorango1v3de",
                    "cr217_domesticorango1v3a","cr217_domesticorango2solesm3","cr217_domesticorango2volumenenm3de",
                    "cr217_domesticorango2volumenenm3a","cr217_comercialrango1solesm3","cr217_comercialrango1v3de",
                    "cr217_comercialrango1v3a","cr217_comercialrango2solesm3","cr217_comercialrango2volumenenm3de",
                    "cr217_comercialrango2volumenenm3a","cr217_industrialrango1solesm3","cr217_industrialrango1v3de",
                    "cr217_industrialrango1v3a","cr217_industrialrango2solesm3","cr217_industrialrango2volumenenm3de",
                    "cr217_industrialrango2volumenenm3a","cr217_socialrango1solesm3","cr217_socialrango1v3de",
                    "cr217_socialrango1v3a","cr217_socialrango2solesm3","cr217_socialrango2volumenenm3de",
                    "cr217_socialrango2volumenenm3a","cr217_lacuotacubrecostosdeoaym","cr217_frecuenciadecobros",
                    "cr217_frecuenciadecobrootro","cr217_laocaplicalametodologiadecuotafamiliar",
                    "cr217_antiguedaddelatarifacuotaactual","cr217_cobraporcadaservicio","cr217_numerodeusuariosmorosos",
                    "cr217_numerodeusuariosexonerados","cr217_conexionesdeagua","cr217_conexiondedesague",
                    "cr217_instalaciondemicromedidores","cr217_reposiciondelservicio","cr217_registrodeingresosyegresos",
                    "cr217_elprestadorcuentaconcuadernolibrodeinventa","cr217_elprestadortieneunregistrodetodoslosrecib",
                    "cr217_elprestadortieneregistrodetodoslosrecibos","cr217_emitereciboocomprobporelpagodeservicios",
                    "cr217_tienecostosdeoperacion","cr217_tieneenergiaelectrica","cr217_periodoenergiaelectrica",
                    "cr217_periodoenergiaotro","cr217_costototaldeenergiaelectrica","cr217_tienecostosdeinsumosquimicos",
                    "cr217_periodoinsumosquimicos","cr217_periodoinsumosquimicosotro","cr217_costototaldeinsumosquimicos",
                    "cr217_tienecostosdepersonal","cr217_periodopersonal","cr217_periodopersonalotro",
                    "cr217_costototaldepersonal","cr217_tienecostosdemantenimiento","cr217_periodomantenimiento",
                    "cr217_periodomantenimientootro","cr217_costostotalenmantenimientosmensual",
                    "cr217_tienecostosdeadministracion","cr217_periodoadministracion","cr217_periodoadministracionotro",
                    "cr217_costostotalenadministracionsmensual","cr217_tienecostosdereposiciondeequipos",
                    "cr217_periodoreposiciondeequipos","cr217_periodoreposiciondeequiposotro",
                    "cr217_costototaldereposicionsmensual","cr217_tienecostosderehabilitacionesmenores",
                    "cr217_periodorehabilitacionesmenores","cr217_periodorehabilitacionesmenoresotro",
                    "cr217_costototalderehabilitamenoressmensual","cr217_tieneotroscostos","cr217_periodootroscostos",
                    "cr217_periodootrootro","cr217_costototaldeotrosmensual",
                    "cr217_cuentaconplandeemergenciauotroinstrumento","cr217_ps1_65_ninguno",
                    "cr217_cuentaconcuadrillacomitebrigadapararespuest","cr217_p6_agricultura","cr217_p6_industrial",
                    "cr217_p6_prestadores","cr217_p6_mineria","cr217_p6_otros","cr217_otrousodelafuente",
                    "cr217_p9_bofedal","cr217_p9_bosques","cr217_p9_pajonal","cr217_p9_otros","cr217_otrotipodeecosistema",
                    "cr217_ps2_14_ninguno","cr217_ps2_14_disminucion","cr217_ps2_14_aumento","cr217_ps2_14_contaminacion",
                    "cr217_ps2_14_otros","cr217_problemasidentificadosotro","cr217_p15_agricultura","cr217_p15_basura",
                    "cr217_p15_mineria","cr217_p15_deforestacion","cr217_p15_sobrepastoreo","cr217_p15_ninguno","cr217_p15_otros",
                    "cr217_otraactividadambitofuenteagua","cr217_prestadorid"],
            "nombres_columnas": ["codigodeprestador","p001_oficinadesconcentrada", "p009_pozospropios","p009_acarreo",
                                "p009_camioncisterna","p009_otro","p009a_comoseabasteceotro","p010_gastomensualpromedioporfamiliaagua",
                                "p002_fechadecaracterizacion","existeprestadordessenelccppprincipal","p016_nombredelprestador",
                                "p005_nombredelcentropobladoprincipal","p008a_nombreyapellido","p008b_cargo","p019_ambitodeprestador",
                                "p031_quetipodeprestadores","p031B01_formaasociativadeoc","p018_agua","p018_alcantarillado",
                                "p018_tar","p018_disposicionexcretas","comentarios","comentariosfuente",
                                "p031A01b_cuentaconordenanzamunicipal","p031A01c_seencuentradentrodeestructuraorganicayrof",
                                "p031A01d_anodecreaciondeugmantesde2017","p031A01e_autorizacionsunassprestacionexcepcional",
                                "p031B02e_laoccuentaconreconocimientodelamuni","p031B02f_resolucionmunicipaldereconocimientodelaoc",
                                "p031C01_fueconstituidosegunlalgdesociedades","p031C02_tienecontratosuscritoconlamunicipalidad",
                                "p032_recibioasistenciatecnicaenlosultimos3anos","p033_atm","p033_municipalidad","p033_mvcs",
                                "p033_cac","p033_pnsr","p033_pnsu","p033_drvcs","p033_sunass","p033_otro","p033_otass",
                                "p034_oym","p034_controldecalidad","p034_adquisiciondeequiposeinsumos","p034_gestiondelosservicios",
                                "p034_cuotafamiliar","p034_otro","p034_grd","p034_integracion","p033a_otroasistenciatecnica",
                                "p034a_otrotemaasistencia","p035_cobracuota","cobraporcadaservicio","elcobroquerealizaes",
                                "elpagoestructuradodependedelamicromedicion","p040_acuantoasciendeelcobroquerealiza",
                                "acuantoasciendeelcobroquerealizaagua","acuantoasciendeelcobroquerealizaalcantari",
                                "acuantoasciendeelcobroquerealizadisposici","acuantoasciendeelcobroquerealizatratamien",
                                "conexionesdomestico","conexionescomercial","conexionesindustrial","conexionessocial",
                                "montodomesticoagua","montocomercialagua","montoindustrialagua","montosocialagua",
                                "montodomesticoalcantarillado","montocomercialalcantarillado","montoindustrialalcantarillado",
                                "montosocialalcantarillado","montodomesticootro","montocomercialotro","montoindustrialotro",
                                "montosocialotro","domesticorango1solesm3","domesticorango1v3de","domesticorango1v3a",
                                "domesticorango2solesm3","domesticorango2v3de","domesticorango2v3a","comercialrango1solesm3",
                                "comercialrango1v3de","comercialrango1v3a","comercialrango2solesm3","comercialrango2v3de",
                                "comercialrango2v3a","industrialrango1solesm3","industrialrango1v3de","industrialrango1v3a",
                                "industrialrango2solesm3","industrialrango2v3de","industrialrango2v3a","socialrango1solesm3",
                                "socialrango1v3de","socialrango1v3a","socialrango2solesm3","socialrango2v3de","socialrango2v3a",
                                "p059_lacuotacubrecostosdeoaym","p037_frecuenciadecobros","p037a_frecuenciadecobrootro",
                                "p039_laocaplicalametodologiadecuotafamiliar","p036_antiguedaddelatarifacuotaactual",
                                "cobraporcadaservicio","p046_numerodeusuariosmorosos","p047_numerodeusuariosexonerados",
                                "p051a_conexionesdeagua","p051d_conexiondedesague","p051c_instalaciondemicromedidores",
                                "p051b_reposiciondelservicio","p063_elprestadortieneunregistrocontableuotro",
                                "p053_elprestadorcuentaconcuadernolibrodeinventa","p062_elprestadortieneunregistrodetodoslosrecib",
                                "p061_elprestadortieneregistrodetodoslosrecibos","p038_emitereciboocomprobporelpagodeservicios",
                                "p058a_tienecostosdeoperacion","p058a1_tieneenergiaelectrica","p058a1a_periodoenergiaelectrica",
                                "p058a1b_periodoenergiaotro","p058a1c_costototaldeenergiaelectrica",
                                "p058a2_tienecostosdeinsumosquimicos","p058a2a_periodoinsumosquimicos","p058a2b_periodoinsumosquimicosotro",
                                "p058a2c_costototaldeinsumosquimicos","p058a3_tienecostosdepersonal",
                                "p058a3a_periodopersonal","p058a3b_periodopersonalotro","p058a3c_costototaldepersonal",
                                "p058b_tienecostosdemantenimiento","p058b1_periodomantenimiento","p058b2_periodomantenimientootro",
                                "p058b3_costostotalenmantenimientosmensual","p058c_tienecostosdeadministracion",
                                "p058c1_periodoadministracion","p058c2_periodoadministracionotro","p058c3_costostotalenadministracionsmensual",
                                "p058d_tienecostosdereposiciondeequipos","p058d1_periodoreposiciondeequipos",
                                "p058d2_periodoreposiciondeequiposotro","p058d3_costototaldereposicionsmensual",
                                "p058e_tienecostosderehabilitacionesmenores","p058e1_periodorehabilitacionesmenores",
                                "p058e2_periodorehabilitacionesmenoresotro","p058e3_costototalderehabilitamenoressmensual",
                                "p058f_tieneotroscostos","p058f1_periodootroscostos","p058f2_periodootrootro",
                                "p058f3_costototaldeotrosmensual","p064_cuentaconplandeemergenciauotroinstrumento",
                                "p065_ninguno","p067_cuentaconcuadrillacomitebrigadapararespuest","p005_agriculturariego",
                                "p005_industrial","p005_prestadoresdess","p005_mineria","p005_otro","p005a_otrousodelafuente",
                                "p008_bofedal","p008_bosques","p008_pajonal","p008_otro","p008a_otrotipodeecosistema",
                                "p014_ninguno","p014_disminucion","p014_aumento","p014_contaminacion","p014_otros",
                                "p014a_problemasidentificadosotro","p015_agricultura","p015_basuradomestica",
                                "p015_mineria","p015_deforestacion","p015_sobrepastoreo","p015_ninguno","p015_otros",
                                "p015a_otraactividadambitofuenteagua","prestadorid"]  
        },
        "cr217_cr217_fuente_Prestador_cr217_prestador": {
            "campos": ["cr217_nombredelafuente","cr217_tipodefuentedeagua","cr217_subtipodefuentedeaguasubterranea","cr217_subtipodefuentedeaguasuperficial", "cr217_cuentaconlicenciauso"],
            "nombres_columnas": ["nombredelafuente","tipodefuentedeagua","subtipodefuentedeaguasubterranea", "subtipodefuentedeaguasuperficial","cuentaconlicenciauso"]
        },
        "cr217_cr217_sistemadeagua_Prestador_cr217_prest": {
            "campos": ["cr217_codigodesistemadeagua","cr217_cuentaconequipodebombeo","cr217_aniodeconstruccionequipobombeo",
                    "cr217_zonacasetadebombeo","cr217_estecasetedebombeo","cr217_nortecasetadebombeo","cr217_altitudcasetadebombeo",
                    "cr217_tienecasetadebombeo","cr217_estadooperativocasetadebombeo","cr217_justifiquerespuestaocasetabombeo",
                    "cr217_tienecisternadebombeo","cr217_estadooperativocisternadebombeo","cr217_justifiquerespuestaocisternabombeo",
                    "cr217_tieneequipodebombeo","cr217_estadooperativoequipodebombeo","cr217_justifiquerespuestaoequipobombeo",
                    "cr217_tienesistemaenergiaelectrica","cr217_estadooperativosistemaenergia","cr217_justifiquerespuestaoenergiaelectrica",
                    "cr217_aniodeconstrucciondistribucion","cr217_estadooperativoactual","cr217_justificasurespuestadistribucion",
                    "cr217_zona","cr217_este","cr217_norte","cr217_altitud",
                    "cr217_tipodesistemadeagua","cr217_subtipodeaguanoconvencional","cr217_anodeconstruccionaguanoconvencional",
                    "cr217_estadooperativo","cr217_comentarios","cr217_subtipodeaguaconvencional","cr217_comoseconstruyoelsistemadeaguapotable",
                    "cr217_enqueanoseconstruyoelsistemadeagua","cr217_porquenorealizalacloracion",
                    "cr217_realizacloracion","cr217_elsistemadeaguacuentaconequipoclorador","cr217_tipodecloracion",
                    "cr217_clororesidualpuntomaslejano","cr217_mide_turbidez","cr217_turbidezunt","cr217_fecha",
                    "cr217_comentariosdesinfeccion","cr217_comentarios","cr217_observacionessistemadistribucion",
                    "cr217_mantenimientocaptacion","cr217_mantenimientocasetayequipodebombeo",
                    "cr217_mantenimientolineadeconduccion","cr217_mantenimientoptap","cr217_mantenimientoreservorio",
                    "cr217_mantenimientoreddedistribucion"],
            "nombres_columnas": ["codigodesistemadeagua","p016_cuentaconequipodebombeo","aniodeconstruccioncasetabombeo",
                                "zonacasetadebombeo","estecasetedebombeo","nortecasetadebombeo","altitudcasetadebombeo",
                                "tienecasetadebombeo","estadooperativocasetadebombeo","justifiquerespuestaocasetabombeo",
                                "tienecisternadebombeo","estadooperativocisternadebombeo","justifiquerespuestaocisternabombeo",
                                "tieneequipodebombeo","estadooperativoequipodebombeo","justifiquerespuestaoequipobombeo",
                                "tienesistemaenergiaelectrica","estadooperativosistemaenergia","justifiquerespuestaoenergiaelectrica",
                                "aniodeconstrucciondistribucion","estadooperativoactual","justificasurespuestadistribucion",
                                "p004_zona","p004_este","p004_norte","p004_altitud",
                                "tipodesistemadeagua","p003_subtipodeaguanoconvencional","p004_anodecontruccionnoconvencional",
                                "p004_estadooptruccionnoconvencional","p004_comentartruccionnoconvencional","p005_subtipodeaguaconvencional",
                                "p006_comoseconstruyoelsistemadeaguapotable","p007_enqueanoseconstruyoelsistemadeagua","p044_porquenorealizalacloracion",
                                "p030_realizacloracion","p027_elsistemadeaguacuentaconequipoclorador","p028_tipodecloracion",
                                "p043_clororesidualpuntomaslejano","p048_turbidez","turbidezunt","fecha","comentariosdesinfeccion",
                                "p004_comentartruccionnoconvencional","observacionessistemadistribucion","p012_mantenimientocaptacion",
                                "p012_mantenimientocasetayequipodebombeo","p012_mantenimientolineadeconduccion",
                                "p012_mantenimientoptap","p012_mantenimientoreservorio","p012_mantenimientoreddedistribucion"]
        },
        "cr217_cr217_sistemadealcantarillado_Prestador_c": {
            "campos": ["cr217_codigodesistemadealcantarillado","cr217_anodeconstruccion","cr217_tieneebar",
                    "cr217_estadooperativoebar","cr217_justifiquesurespuestaalca","cr217_tipodesistemadealcantarilladosanitario",
                    "cr217_alcantarilladoadministradoporunaeps","cr217_estadooperativodelsistemadealcantarillado",
                    "cr217_comentariossistemaalcantarillado","cr217_realizamantenimientoalareddealcantarillado",
                    "cr217_zona","cr217_este","cr217_norte","cr217_altitud"],
            "nombres_columnas": ["codigodesistemadealcantarillado","anodeconstruccion","tieneebar",
                                "estadooperativoebar","justifiquesurespuestaalca","tipodesistemadealcantarilladosanitario",
                                "alcantarilladoadministradoporunaeps","estadooperativodelsistemadealcantarillado",
                                "comentariossistemaalcantarillado","p008_realizamantenimientoalareddealcantarillado",
                                "zona","este","norte","altitud"]
        },
        "cr217_Prestador_cr217_Prestador_cr217_Ubs": {
            "campos": ["cr217_codigodeubs","cr217_tipoubsodisposicionesinadecuadasdeexcretas","cr217_enqueanoseconstruyolaubs",
                    "cr217_comentarios"],
            "nombres_columnas": ["codigodeubs","tipoubsodisposicionesinadecuadasdeexcretas","enqueanoseconstruyolaubs",
                                "comentarios"]
        },
        "cr217_Prestador_cr217_Prestador_cr217_Usu": {
            "campos": ["cr217_codigodeusuario","cr217_pagaporlosserviciosdesaneamiento","cr217_niveldesatisfaccionconelservicio",
                    "cr217_pagariaunmontoadicionalporelservicio","cr217_p16_riegodehuertas","cr217_p16_lavadodevehiculos",
                    "cr217_p16_riegodecalle","cr217_p16_crianzadeanimales","cr217_p16_otro","cr217_reutilizaelagua",
                    "cr217_elusuariorecibeelserviciodelprestador","cr217_ps1_pozopropio","cr217_ps1_camiones",
                    "cr217_ps1_acarreo","cr217_ps1_otro","cr217_otraformaabastecimiento","cr217_gastomensualsolesenelectricidad",
                    "cr217_gastomensualsolesentelefoniacelular","cr217_gastomensualsolesencable",
                    "cr217_gastomensualsoleseninternet","cr217_gastomensualsolesenstreamingnetflixetc",
                    "cr217_gastomensualsolesengas","cr217_cuantoeselgastomensualenagua","cr217_estariadispuestoqueesteotrolebrindeserv",
                    "cr217_nombreyubicaciondeprestador","cr217_litrosequivalencia","cr217_cuantasvecesalmesseabastece"],
            "nombres_columnas": ["codigodeusuario","p006_pagaporlosserviciosdesaneamiento","p010_niveldesatisfaccionconelservicio",
                                "p012_pagariaunmontoadicionalporelservicio","p016_riegodehuertas","p016_lavadodevehiculos",
                                "p016_riegodecalle","p016_crianzadeanimales","p016_otro","p017_reutilizaelagua",
                                "p005_elusuariorecibeelserviciodelprestador","p001_pozopropio","p001_camiones","p001_acarreo",
                                "p001_otro","p001a_otraformaabastecimiento","p014a_gastomensualsolesenelectricidad",
                                "p014b_gastomensualsolesentelefoniacelular","p014c_gastomensualsolesencable",
                                "p014d_gastomensualsoleseninternet","p014e_gastomensualsolesenstreamingnetflixetc",
                                "p014h_gastomensualsolesengas","p002_cuantoeselgastomensualenagua","p013a_estariadispuestoqueesteotrolebrindeserv",
                                "p013_1_nombreyubicaciondeprestador","p002a_litrosequivalencia","p003_cuantasvecesalmesseabastece"]
        },
        "cr217_CentroPoblado": {
            "campos": ["cr217_codigodecentropoblado"],
            "nombres_columnas": ["codigodecentropoblado"]
        },
        "cr217_Codigoubigeocentropobladocercano": {
            "campos": ["cr217_codigodecentropoblado"],
            "nombres_columnas": ["codigoubigeocentropobladocercano"]
        }
    }


    # Obtener los DataFrames
    dfs = obtener_df_relaciones_prestador(prestador_id, relaciones_config, token)

    # Por ejemplo, ver el df de fuentes
    df_fuente = dfs["cr217_cr217_fuente_Prestador_cr217_prestador"]
    df_sistema_agua = dfs["cr217_cr217_sistemadeagua_Prestador_cr217_prest"]
    df_sistema_alca = dfs["cr217_cr217_sistemadealcantarillado_Prestador_c"]
    df_ubs = dfs["cr217_Prestador_cr217_Prestador_cr217_Ubs"]
    df_usuario = dfs["cr217_Prestador_cr217_Prestador_cr217_Usu"]
    df_prestador = dfs["prestador"]
    df_centropoblado = dfs["cr217_CentroPoblado"]
    df_centropobladoscercano = dfs["cr217_Codigoubigeocentropobladocercano"]


    df_prestador = pd.merge(df_prestador,df_centropoblado, on="codigodeprestador", how="left")
    df_prestador = pd.merge(df_prestador,df_centropobladoscercano, on="codigodeprestador", how="left")
    df_prestador.rename(columns={"codigodecentropoblado": "centropoblado"}, inplace=True)

    print(df_prestador)
    print(df_fuente)
    print(df_captacion)

    # Polacion servida
    campos = ["cr217_conexionesdeaguaactivas", "cr217_conexionesdealcantarilladoactivas",
            "cr217_conexionesdeaguatotales","cr217_conexionesdealcantarilladototales","cr217_cantidaddeubsenelccpp",
            "cr217_continuidadpromedioenepocadelluviahorasdia","cr217_continuidadpromedioenepocadeestiajehorasdia",
            "cr217_viviendascondisposiciondeexcretasnoadecuadas","cr217_tiponoadecuado","cr217_comentarios"]
    nombres_columnas = ["p022_conexionesdeaguaactivas", "p024_conexionesdealcantarilladoactivas",
                        "p021_conexionesdeaguatotales", "p023_conexionesdealcantarilladototales","p027_cantidaddeubsenelccpp",
                        "p029a_continuidadpromedioenepocadelluviahorasdia","p029b_continuidadpromedioenepocadeestiajehorasdia",
                        "viviendascondisposiciondeexcretasnoadecuadas","tiponoadecuado","comentarios"]

    df_ps = obtener_df_prestador_simple(prestador_id, token, campos, nombres_columnas)


    # Conversion fecha
    # 1. Convertimos la columna a tipo datetime
    # 2. Formateamos la fecha al estilo 'yyyy-MM-dd'
    df_prestador['p002_fechadecaracterizacion'] = pd.to_datetime(df_prestador['p002_fechadecaracterizacion'],format='%d/%m/%Y', errors='coerce')

    columnas_a_float_prestador = ['p010_gastomensualpromedioporfamiliaagua','p040_acuantoasciendeelcobroquerealiza',
                                "acuantoasciendeelcobroquerealizaagua","acuantoasciendeelcobroquerealizaalcantari",
                                "acuantoasciendeelcobroquerealizadisposici","acuantoasciendeelcobroquerealizatratamien",
                                "conexionesdomestico","conexionescomercial","conexionesindustrial","conexionessocial",
                                "montodomesticoagua","montocomercialagua","montoindustrialagua","montosocialagua",
                                "montodomesticoalcantarillado","montocomercialalcantarillado","montoindustrialalcantarillado",
                                "montosocialalcantarillado","montodomesticootro","montocomercialotro","montoindustrialotro",
                                "montosocialotro","domesticorango1solesm3","domesticorango1v3de","domesticorango1v3a",
                                "domesticorango2solesm3","domesticorango2v3de","domesticorango2v3a","comercialrango1solesm3",
                                "comercialrango1v3de","comercialrango1v3a","comercialrango2solesm3","comercialrango2v3de",
                                "comercialrango2v3a","industrialrango1solesm3","industrialrango1v3de","industrialrango1v3a",
                                "industrialrango2solesm3","industrialrango2v3de","industrialrango2v3a","socialrango1solesm3",
                                "socialrango1v3de","socialrango1v3a","socialrango2solesm3","socialrango2v3de","socialrango2v3a",
                                "p046_numerodeusuariosmorosos","p047_numerodeusuariosexonerados",
                                "p051a_conexionesdeagua","p051d_conexiondedesague","p051c_instalaciondemicromedidores",
                                "p051b_reposiciondelservicio","p058a1c_costototaldeenergiaelectrica","p058a2c_costototaldeinsumosquimicos",
                                "p058a3c_costototaldepersonal","p058b3_costostotalenmantenimientosmensual",
                                "p058c3_costostotalenadministracionsmensual","p058d3_costototaldereposicionsmensual",
                                "p058e3_costototalderehabilitamenoressmensual","p058f3_costototaldeotrosmensual"]
    columnas_a_float_ps = ["p022_conexionesdeaguaactivas", "p024_conexionesdealcantarilladoactivas",
                        "p021_conexionesdeaguatotales", "p023_conexionesdealcantarilladototales","p027_cantidaddeubsenelccpp",
                        "p029a_continuidadpromedioenepocadelluviahorasdia","p029b_continuidadpromedioenepocadeestiajehorasdia"]
    columnas_a_flota_coords = ["este","norte","altitud"]

    columnas_a_float_usuario = ["p002_cuantoeselgastomensualenagua","p002a_litrosequivalencia","p014a_gastomensualsolesenelectricidad",
                                "p014b_gastomensualsolesentelefoniacelular","p014c_gastomensualsolesencable",
                                "p014d_gastomensualsoleseninternet","p014e_gastomensualsolesenstreamingnetflixetc",
                                "p014h_gastomensualsolesengas"]

    columnas_a_float_res = ['clororesidualmgl']
    columnas_a_float_sis = ['p043_clororesidualpuntomaslejano','turbidezunt',"estecasetedebombeo","nortecasetadebombeo","altitudcasetadebombeo"]
    for col in columnas_a_float_prestador:
        df_prestador[col] = df_prestador[col].apply(limpiar_y_convertir)
    for col in columnas_a_float_ps:
        df_ps[col] = df_ps[col].apply(limpiar_y_convertir)     
    for col in columnas_a_float_usuario:
        df_usuario[col] = df_usuario[col].apply(limpiar_y_convertir)
        

    if not df_sistema_agua.empty:
        df_sistema_agua['fecha'] = pd.to_datetime(df_sistema_agua['fecha'],format='%d/%m/%Y', errors='coerce')
        df_sistema_agua['aniodeconstruccioncasetabombeo'] = pd.to_datetime(df_sistema_agua['aniodeconstruccioncasetabombeo'],format='%d/%m/%Y', errors='coerce')
        df_sistema_agua['aniodeconstruccioncasetabombeo'] = df_sistema_agua['aniodeconstruccioncasetabombeo'].dt.year
        df_sistema_agua['aniodeconstrucciondistribucion'] = pd.to_datetime(df_sistema_agua['aniodeconstrucciondistribucion'],format='%d/%m/%Y', errors='coerce')
        df_sistema_agua['aniodeconstrucciondistribucion'] = df_sistema_agua['aniodeconstrucciondistribucion'].dt.year
        df_sistema_agua['p007_enqueanoseconstruyoelsistemadeagua'] = pd.to_datetime(df_sistema_agua['p007_enqueanoseconstruyoelsistemadeagua'],format='%d/%m/%Y', errors='coerce')
        df_sistema_agua['p007_enqueanoseconstruyoelsistemadeagua'] = df_sistema_agua['p007_enqueanoseconstruyoelsistemadeagua'].dt.year
        for col in columnas_a_float_sis:
            df_sistema_agua[col] = df_sistema_agua[col].apply(limpiar_y_convertir)

    if not df_captacion.empty:
        df_captacion['anodeconstruccion'] = pd.to_datetime(df_captacion['anodeconstruccion'],format='%d/%m/%Y', errors='coerce')
        df_captacion['anodeconstruccion'] = df_captacion['anodeconstruccion'].dt.year
        for col in columnas_a_flota_coords:
            df_captacion[col] = df_captacion[col].apply(limpiar_y_convertir)

    if not df_conduccion.empty:
        df_conduccion['anodeconstruccionconduccion'] = pd.to_datetime(df_conduccion['anodeconstruccionconduccion'],format='%d/%m/%Y', errors='coerce')
        df_conduccion['anodeconstruccionconduccion'] = df_conduccion['anodeconstruccionconduccion'].dt.year

    if not df_reservorio.empty:
        df_reservorio['anodeconstruccion'] = pd.to_datetime(df_reservorio['anodeconstruccion'],format='%d/%m/%Y', errors='coerce')
        df_reservorio['anodeconstruccion'] = df_reservorio['anodeconstruccion'].dt.year
        for col in columnas_a_float_res:
            df_reservorio[col] = df_reservorio[col].apply(limpiar_y_convertir)
        for col in columnas_a_flota_coords:
            df_reservorio[col] = df_reservorio[col].apply(limpiar_y_convertir)

    if not df_ptap.empty:
        df_ptap['anodeconstruccion'] = pd.to_datetime(df_ptap['anodeconstruccion'], format='%d/%m/%Y',errors='coerce')
        df_ptap['anodeconstruccion'] = df_ptap['anodeconstruccion'].dt.year
        for col in columnas_a_flota_coords:
            df_ptap[col] = df_ptap[col].apply(limpiar_y_convertir)


    if not df_ptar.empty:
        df_ptar['anodeconstruccionptar'] = pd.to_datetime(df_ptar['anodeconstruccionptar'],format='%d/%m/%Y', errors='coerce')
        df_ptar['anodeconstruccionptar'] = df_ptar['anodeconstruccionptar'].dt.year



    if not df_sistema_alca.empty:
        df_sistema_alca['anodeconstruccion'] = pd.to_datetime(df_sistema_alca['anodeconstruccion'],format='%d/%m/%Y', errors='coerce')
        df_sistema_alca['anodeconstruccion'] = df_sistema_alca['anodeconstruccion'].dt.year
        for col in columnas_a_flota_coords:
            df_sistema_alca[col] = df_sistema_alca[col].apply(limpiar_y_convertir)

    if not df_ubs.empty:
        df_ubs['enqueanoseconstruyolaubs'] = pd.to_datetime(df_ubs['enqueanoseconstruyolaubs'],format='%d/%m/%Y', errors='coerce')
        df_ubs['enqueanoseconstruyolaubs'] = df_ubs['enqueanoseconstruyolaubs'].dt.year

        


    df_prestador["rutafichas"] = (
        "https://sunassgobpe.sharepoint.com/sites/adp2/cr217_prestador/Forms/AllItems.aspx?id=%2Fsites%2Fadp2%2Fcr217_prestador%2F" +
        df_prestador["codigodeprestador"] + "_" +
        df_prestador["prestadorid"].str.replace("-", "", regex=False) +
        "%2FFICHAS&viewid=589d0427-4c8e-4a99-aa86-36052f289f8d"
    )

    df_prestador['carpetaprestador'] = df_prestador['codigodeprestador'].astype(str) + '_' + df_prestador['prestadorid'].str.replace('-', '', regex=False)

    ############################################# I. Descarga de fotos #############################################
    ################################################################################################################
    
    folder_path = "cr217_prestador"
    os.makedirs(folder_path, exist_ok=True)
    ruta_base = os.path.join(os.getcwd(),folder_path)

    # # Descargar solo la carpeta especificada
    download_from_named_folder(drive_id, folder_name, headers, ruta_base)

    ############################################# I. Ingreso a la base de datos #############################################
    #########################################################################################################################
    # ruta_bd = "/Users/paulmoreno/SUNASS/INFORME_CARACTERIZACION/BD"
    ruta_fotos = ruta_base
    inei_2017 = get_bd_sharepoint("AUTOMATIZACION/BD/PedidoCCPP_validado.xlsx","BD/PedidoCCPP_validado.xlsx")
    print(inei_2017)
    # inei_2017 = pd.read_excel(ruta_bd + "/PedidoCCPP_validado.xlsx", sheet_name="CCPP")

    inei_2017['ubigeo_ccpp'] = pd.to_numeric(inei_2017['ubigeo_ccpp'], errors='coerce') #Conviertiendo el ubigeo a numeric
    #inei_2017['tipo_ref'] = inei_2017['Ubic_APC_EPES'].apply(lambda x: 'tipo1' if x in ['Dentro del Área con población servida de la EPS','A 2.5 Km del Área con población servida de la EPS'] else 'tipo2')
    inei_2017['ambito_ccpp'] = inei_2017['POBTOTAL'].apply(lambda x: 'Rural' if x <= 2000 else 'Pequeña Ciudad' if x > 2000 & x <= 15000 else 'Urbano')
    inei_2017 = inei_2017[['ubigeo_ccpp','NOMDEP','NOMPROV','NOMDIST','NOMCCPP','POBTOTAL','VIVTOTAL','densidad_pob','Ubic_APC_EPES','ambito_ccpp']]

    # Crear una lista de DataFrames con los conteos que quieres fusionar
    dfs_to_merge = [
        df_fuente.groupby('codigodeprestador')['codigodeprestador'].count().reset_index(name='Num_fuentes'),
        df_sistema_agua.groupby('codigodeprestador')['codigodeprestador'].count().reset_index(name='Num_sistemas_agua'),
        df_sistema_alca.groupby('codigodeprestador')['codigodeprestador'].count().reset_index(name='Num_sistemas_alca')
    ]

    df_prestador = reduce(lambda left, right: pd.merge(left, right, on='codigodeprestador', how='left'), 
                        [df_prestador] + dfs_to_merge)
    
    doc_cp = DocxTemplate("Templates/modelo_final2.docx")
    if (df_prestador['p016_nombredelprestador'].values[0] == "ABASTECIMIENTO SIN PRESTADOR"):
        doc_cp = DocxTemplate("Templates/modelo_final2_sin_prestador.docx")


    try:
        cp.generarInforme(prestador_id, df_prestador, inei_2017, df_ps, df_fuente, df_sistema_agua, df_captacion, df_conduccion, df_reservorio, df_ptap, df_sistema_alca, df_ptar, df_disposicionfinal, df_ubs, df_usuario, doc_cp, ruta_fotos)
    except Exception as e:
        # Puedes personalizar este mensaje de error según sea necesario
        print(f"Error al generar informe para el código {prestador_id}: {e}")
    
    # Verificar si la carpeta existe antes de intentar eliminarla
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"🗑️ Carpeta '{folder_path}' eliminada correctamente.")
    else:
        print(f"⚠️ La carpeta '{folder_path}' no existe.")
    
    output_filename = f"INFORME_{prestador_id}.docx"
    filepath = os.path.join("reports", output_filename)
    return filepath
    
@app.route("/")
def index():
    try:
        print("Iniciando obtención de datos...")
        data = fetch_all_prestadores()
        print(f"Datos obtenidos: {len(data)} registros")
        print("Primeros 2 registros de ejemplo:", data[:2] if data else "No hay datos")
        
        return render_template("index.html", data=data)
    except Exception as e:
        print(f"Error en la ruta principal: {str(e)}")
        # Devolver un mensaje de error más descriptivo al usuario
        return f"""
            <html>
                <body>
                    <h1>Error al cargar los datos</h1>
                    <p>Detalles del error: {str(e)}</p>
                    <p>Por favor, verifica:</p>
                    <ul>
                        <li>Las variables de entorno están configuradas correctamente</li>
                        <li>La conexión con el servicio de datos está funcionando</li>
                        <li>Los tokens de autenticación son válidos</li>
                    </ul>
                </body>
            </html>
        """, 500

@app.route("/download/<prestador_id>")
def download(prestador_id):
    try:
        # Asegurar que los directorios existan
        os.makedirs("reports", exist_ok=True)
        os.makedirs("BD", exist_ok=True)
        
        filepath = generate_report_with_template(prestador_id)
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        print(f"❌ Error al generar el informe: {str(e)}")
        return f"Error al generar el informe: {str(e)}", 500


def limpiar_y_convertir(valor):
    if pd.isna(valor):
        return None
    valor = str(valor).strip()
    
    # Eliminar puntos (separador de miles) y convertir coma decimal a punto
    valor = valor.replace(".", "").replace(",", ".")
    
    try:
        return float(valor)
    except ValueError:
        return None


def find_folder_by_prefix(drive_id, prefix, headers):
    """Busca la primera carpeta en el root cuyo nombre comienza con el prefijo dado."""
    print(f"🔍 Buscando carpeta que empieza con: '{prefix}'...")
    all_items = get_all_root_items(drive_id, headers)

    for item in all_items:
        if "folder" in item and item["name"].startswith(prefix):
            print(f"✅ Carpeta encontrada: {item['name']}")
            return item["name"]  # Retorna el nombre completo

    print(f"❌ No se encontró ninguna carpeta que comience con: '{prefix}'")
    return None

def download_drive_folder(drive_id, item_id, local_path, headers):
    """Descarga recursivamente el contenido de una carpeta del drive"""
    os.makedirs(local_path, exist_ok=True)

    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    items = response.json()["value"]

    for item in items:
        item_name = item["name"]
        item_path = os.path.join(local_path, item_name)

        if "folder" in item:
            download_drive_folder(drive_id, item["id"], item_path, headers)
        else:
            download_url = item["@microsoft.graph.downloadUrl"]
            print(f"⬇️ Descargando: {item_path}")
            r = requests.get(download_url)
            with open(item_path, "wb") as f:
                f.write(r.content)


def get_all_root_items(drive_id, headers):
    """Obtiene todos los elementos en el root del drive (maneja paginación)"""
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    all_items = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        all_items.extend(data["value"])
        url = data.get("@odata.nextLink")  # Siguiente página

    return all_items


def download_from_named_folder(drive_id, folder_name, headers, ruta_base):
    """Busca la carpeta por nombre en el root del drive y la descarga"""
    print(f"🔎 Buscando la carpeta '{folder_name}' en el root del drive...")
    root_items = get_all_root_items(drive_id, headers)

    for item in root_items:
        if item["name"] == folder_name and "folder" in item:
            folder_id = item["id"]
            download_drive_folder(drive_id, folder_id, f"{ruta_base}/{folder_name}", headers)
            return

    print(f"❌ Carpeta '{folder_name}' no encontrada (revisado {len(root_items)} elementos del root).")


if __name__ == "__main__":
    try:
        print("\n=== Iniciando aplicación ===")
        # Crear directorios necesarios
        folder_path_report = "reports"
        folder_path_bd = "BD"
        
        print(f"📁 Creando directorio: {folder_path_report}")
        os.makedirs(folder_path_report, exist_ok=True)
        if os.path.exists(folder_path_report):
            print(f"✅ Directorio {folder_path_report} creado correctamente")
        else:
            print(f"❌ Error al crear directorio {folder_path_report}")
            
        print(f"📁 Creando directorio: {folder_path_bd}")
        os.makedirs(folder_path_bd, exist_ok=True)
        if os.path.exists(folder_path_bd):
            print(f"✅ Directorio {folder_path_bd} creado correctamente")
        else:
            print(f"❌ Error al crear directorio {folder_path_bd}")
        
        # Obtener el puerto del entorno (Render lo proporciona) o usar 5001 por defecto
        port = int(os.environ.get("PORT", 5001))
        print(f"🚀 Iniciando servidor en puerto {port}")
        
        # Iniciar la aplicación
        app.run(host='0.0.0.0', port=port, debug=True)
        
    except Exception as e:
        print(f"❌ Error al iniciar la aplicación: {str(e)}")
        raise

    if os.path.exists(folder_path_report):
        shutil.rmtree(folder_path_report)
        print(f"🗑️ Carpeta '{folder_path_report}' eliminada correctamente.")
    else:
        print(f"⚠️ La carpeta '{folder_path_report}' no existe.")
        
    if os.path.exists(folder_path_bd):
        shutil.rmtree(folder_path_bd)
        print(f"🗑️ Carpeta '{folder_path_bd}' eliminada correctamente.")
    else:
        print(f"⚠️ La carpeta '{folder_path_bd}' no existe.")
    
