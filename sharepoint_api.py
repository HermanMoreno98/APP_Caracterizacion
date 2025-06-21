import requests
import time
import os
import shutil
from msal import ConfidentialClientApplication
from PIL import Image
import gc # Para garbage collection
import logging

import config # Importar desde tu archivo de configuración

# Variable global para el token de SharePoint para evitar múltiples llamadas innecesarias en una sola ejecución/request
# Esto es una caché simple. Para aplicaciones más robustas, considera una caché con TTL.
_sharepoint_token_cache = None
_sharepoint_token_timestamp = 0
_dataverse_token_cache = None
_dataverse_token_timestamp = 0 
TOKEN_EXPIRATION_SECONDS = 3000 

logger = logging.getLogger(__name__)

def get_auth_token(client_id, client_secret, authority, scope):
    """Función genérica para obtener token de cliente confidencial."""
    app = ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )
    result = app.acquire_token_for_client(scopes=scope)
    if "access_token" not in result:
        error_desc = result.get('error_description', 'No se proporcionó descripción del error.')
        raise Exception(f"No se pudo obtener el token: {result.get('error')}. Detalles: {error_desc}")
    return result["access_token"]

def get_sharepoint_token(force_new=False): # Asegúrate que 'force_new' esté si lo usas en otro lado
    global _sharepoint_token_cache, _sharepoint_token_timestamp
    
    current_time = time.time()
    
    # Usar config.TOKEN_EXPIRATION_SECONDS si lo defines allí
    token_lifetime = getattr(config, 'TOKEN_EXPIRATION_SECONDS', 3000) 

    if not force_new and _sharepoint_token_cache and \
       (current_time - _sharepoint_token_timestamp < token_lifetime):
        # print("Usando token de SharePoint desde caché.") # Para depuración
        return _sharepoint_token_cache
    
    print("Obteniendo un nuevo token de SharePoint...") # Logging
    _sharepoint_token_cache = get_auth_token( # Llama a la función genérica
        config.CLIENT_ID, 
        config.CLIENT_SECRET, 
        config.AUTHORITY, 
        config.SCOPES_SHAREPOINT
    )
    _sharepoint_token_timestamp = current_time
    return _sharepoint_token_cache

def get_dataverse_token(force_new=False):
    global _dataverse_token_cache, _dataverse_token_timestamp
    
    current_time = time.time() # Necesitarás importar time
    
    if not force_new and _dataverse_token_cache and (current_time - _dataverse_token_timestamp < TOKEN_EXPIRATION_SECONDS):
        return _dataverse_token_cache

    print("Obteniendo un nuevo token de Dataverse...")
    _dataverse_token_cache = get_auth_token( # get_auth_token es tu función genérica
        config.CLIENT_ID,
        config.CLIENT_SECRET,
        config.AUTHORITY,
        config.SCOPE_DATAVERSE
    )
    _dataverse_token_timestamp = current_time
    return _dataverse_token_cache

def get_dataverse_token():
    global _dataverse_token_cache
    if _dataverse_token_cache: # Idealmente, verificar expiración
        return _dataverse_token_cache

    _dataverse_token_cache = get_auth_token(
        config.CLIENT_ID,
        config.CLIENT_SECRET,
        config.AUTHORITY,
        config.SCOPE_DATAVERSE
    )
    return _dataverse_token_cache


def _get_site_id(token):
    headers = {**config.HEADERS_GRAPH_BASE, "Authorization": f"Bearer {token}"}
    url = f"{config.RESOURCE_GRAPH}/v1.0/sites/{config.SHAREPOINT_DOMAIN}:{config.SHAREPOINT_SITE_PATH}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["id"]

def _get_drive_id_from_doc_library(token, site_id, library_id):
    headers = {**config.HEADERS_GRAPH_BASE, "Authorization": f"Bearer {token}"}
    url = f"{config.RESOURCE_GRAPH}/v1.0/sites/{site_id}/lists/{library_id}/drive"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["id"]

def _get_drive_id_from_site(token, site_id):
    """Obtiene el ID del Drive principal del sitio."""
    headers = {**config.HEADERS_GRAPH_BASE, "Authorization": f"Bearer {token}"}
    url = f"{config.RESOURCE_GRAPH}/v1.0/sites/{site_id}/drive"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["id"]


def get_bd_inei_sharepoint(local_dir_bd_temp):
    """Descarga el archivo INEI desde SharePoint a una carpeta local temporal."""
    token = get_sharepoint_token()
    headers = {**config.HEADERS_GRAPH_BASE, "Authorization": f"Bearer {token}"}
    
    site_id = _get_site_id(token)
    drive_id = _get_drive_id_from_site(token, site_id) # Asumiendo que está en el drive principal del sitio

    # :/{config.SHAREPOINT_PATH_INEI_FILE}:/ -> Codifica los dos puntos alrededor del path
    encoded_file_path = config.SHAREPOINT_PATH_INEI_FILE.replace(":", "%3A")

    download_url = f"{config.RESOURCE_GRAPH}/v1.0/drives/{drive_id}/root:/{encoded_file_path}:/content"
    
    response = requests.get(download_url, headers=headers, stream=True)
    response.raise_for_status()
    
    os.makedirs(local_dir_bd_temp, exist_ok=True)
    local_file_path = os.path.join(local_dir_bd_temp, config.LOCAL_INEI_FILE_NAME)
    
    with open(local_file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Archivo INEI descargado en: {local_file_path}")
    return local_file_path


def find_folder_by_prefix_sharepoint(drive_id, prefix_to_find, token):
    """
    Busca la primera carpeta en el root del drive cuyo nombre comienza con el prefijo dado,
    ignorando mayúsculas y minúsculas.
    """
    headers = {**config.HEADERS_GRAPH_BASE, "Authorization": f"Bearer {token}"}
    all_items = get_all_root_items_sharepoint(drive_id, token) # Esta función ya debería estar definida

    logger.debug(f"Buscando carpeta con prefijo (insensible a may/min): '{prefix_to_find.lower()}' en drive {drive_id}")
    logger.debug(f"Elementos encontrados en la raíz del drive {drive_id}: {[item.get('name') for item in all_items]}")


    prefix_to_find_lower = prefix_to_find.lower() # Convertir el prefijo a minúsculas una vez

    for item in all_items:
        item_name = item.get("name")
        if item_name and "folder" in item: # Asegurarse que 'name' existe y es una carpeta
            item_name_lower = item_name.lower() # Convertir el nombre del ítem a minúsculas
            if item_name_lower.startswith(prefix_to_find_lower):
                logger.info(f"Carpeta de prestador encontrada en SharePoint (insensible a may/min): '{item_name}' (ID: {item.get('id')})")
                return item_name, item.get("id") # Devolver el nombre original y el ID

    logger.warning(f"Advertencia: No se encontró carpeta con prefijo '{prefix_to_find}' (insensible a may/min) en drive {drive_id}")
    return None, None

def get_all_root_items_sharepoint(drive_id, token):
    """Obtiene todos los elementos en el root del drive (maneja paginación)"""
    headers = {**config.HEADERS_GRAPH_BASE, "Authorization": f"Bearer {token}"}
    url = f"{config.RESOURCE_GRAPH}/v1.0/drives/{drive_id}/root/children"
    all_items = []

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Lanza error si la respuesta no es 2xx
        data = response.json()
        all_items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    return all_items

def download_folder_contents_sharepoint(drive_id, folder_id, local_target_path, token):
    """Descarga el contenido de una carpeta específica de SharePoint (no recursivo por defecto en la lógica original)."""
    headers = {**config.HEADERS_GRAPH_BASE, "Authorization": f"Bearer {token}"}
    
    # Obtener lista de archivos en la carpeta
    url_children = f"{config.RESOURCE_GRAPH}/v1.0/drives/{drive_id}/items/{folder_id}/children"
    response = requests.get(url_children, headers=headers)
    response.raise_for_status()
    items = response.json().get("value", [])
    
    os.makedirs(local_target_path, exist_ok=True)
    
    for item in items:
        try:
            if "folder" in item: # La lógica original parecía descargar subcarpetas como FOTOS/ACTAS
                subfolder_local_path = os.path.join(local_target_path, item["name"])
                # Llamada recursiva si se quieren descargar subcarpetas enteras
                # download_folder_contents_sharepoint(drive_id, item["id"], subfolder_local_path, token) 
                # Por ahora, replicando la lógica de descargar solo archivos de primer nivel de FOTOS/ACTAS
                if item["name"].upper() in ["FOTOS", "ACTAS"]: # Descargar contenido de FOTOS y ACTAS
                     download_folder_contents_sharepoint(drive_id, item["id"], subfolder_local_path, token)
                continue
                
            item_name = item["name"]
            item_local_path = os.path.join(local_target_path, item_name)
            
            # Limitar tamaño y optimizar (como en el original)
            if item.get("size", 0) > 10 * 1024 * 1024:  # Saltar archivos mayores a 10MB
                print(f"Saltando archivo grande: {item_name}")
                continue
                
            download_url = item.get("@microsoft.graph.downloadUrl")
            if not download_url:
                print(f"Advertencia: No se encontró URL de descarga para {item_name}")
                continue
            
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(item_local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            if item_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                try:
                    with Image.open(item_local_path) as img:
                        if img.width > 1600 or img.height > 1600:
                            img.thumbnail((1600, 1600))
                        # Guardar con optimización, formato original o PNG si es necesario
                        save_format = img.format if img.format in ['JPEG', 'PNG'] else 'PNG'
                        img.save(item_local_path, format=save_format, optimize=True, quality=85 if save_format == 'JPEG' else None)
                except Exception as e:
                    print(f"Advertencia: Error al optimizar imagen {item_local_path}: {e}")
                    
        except Exception as e:
            print(f"Error al descargar o procesar {item.get('name', 'elemento desconocido')}: {e}")
            continue
        finally:
            gc.collect() # Forzar liberación de memoria


def download_prestador_files_sharepoint(prestador_codigo_sharepoint, local_base_path_prestador_files):
    """
    Descarga las carpetas FOTOS y ACTAS de un prestador desde SharePoint.
    prestador_codigo_sharepoint es el nombre de la carpeta (ej. P01010101_GUID)
    local_base_path_prestador_files es donde se creará la carpeta del prestador localmente (ej. temp_processing/cr217_prestador)
    """
    token = get_sharepoint_token()
    site_id = _get_site_id(token)
    # Usar el ID de la biblioteca de documentos específica para archivos de prestadores
    drive_id = _get_drive_id_from_doc_library(token, site_id, config.SHAREPOINT_DOC_LIBRARY_ID_PRESTADORES) 

    nombre_carpeta_prestador, id_carpeta_prestador = find_folder_by_prefix_sharepoint(drive_id, prestador_codigo_sharepoint, token)

    if not id_carpeta_prestador:
        print(f"No se encontró la carpeta para el prestador {prestador_codigo_sharepoint} en SharePoint.")
        return False # Indicar que no se descargó nada

    # La ruta local donde se guardarán los archivos de ESTE prestador
    # ej: temp_processing/cr217_prestador/P01010101_GUID
    # Aseguramos que el nombre de la carpeta local sea el mismo que en SharePoint
    local_path_specific_prestador = os.path.join(local_base_path_prestador_files, nombre_carpeta_prestador)
    
    print(f"Descargando archivos de '{nombre_carpeta_prestador}' a '{local_path_specific_prestador}'...")
    download_folder_contents_sharepoint(drive_id, id_carpeta_prestador, local_path_specific_prestador, token)
    return True # Indicar que la descarga (o intento) se realizó