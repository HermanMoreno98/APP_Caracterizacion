import requests
import pandas as pd
from urllib.parse import quote
import logging
import time
import json

import config # Importar desde tu archivo de configuración
from sharepoint_api import get_dataverse_token # Para obtener el token

logger = logging.getLogger(__name__)

def _make_dataverse_request(url, token, method="GET", params=None, json_data=None, retries=1):
    headers = {**config.HEADERS_DATAVERSE_BASE, "Authorization": f"Bearer {token}"}
    current_try = 0
    last_exception = None

    while current_try <= retries:
        try:
            logger.debug(f"Intentando solicitud a Dataverse: {method} {url}")
            response = requests.request(method, url, headers=headers, params=params, json=json_data, timeout=30)
            
            if response.status_code == 401 and current_try < retries:
                logger.warning("Token de Dataverse posiblemente expirado. Obteniendo uno nuevo...")
                token = get_dataverse_token(force_new=True) 
                headers["Authorization"] = f"Bearer {token}"
                current_try += 1
                logger.debug("Reintentando con nuevo token.")
                continue 
                
            response.raise_for_status() # Lanza HTTPError para 4xx/5xx
            
            # Intentar decodificar JSON. Si la respuesta está vacía y es válida, .json() puede fallar.
            if response.content:
                return response.json()
            else:
                logger.warning(f"Respuesta vacía (pero exitosa) de Dataverse para {url}. Devolviendo diccionario vacío.")
                return {} # Respuesta exitosa pero sin contenido JSON

        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP ({e.response.status_code}) en solicitud a Dataverse ({url}): {e.response.text}", exc_info=False) # No necesitamos todo el traceback aquí
            last_exception = e
            if current_try >= retries:
                break # Salir del bucle si se agotaron los reintentos
            current_try += 1
            logger.warning(f"Reintentando solicitud HTTP ({current_try}/{retries})...")
            time.sleep(1 * current_try) # Pequeño delay exponencial

        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON de Dataverse ({url}): {e}. Contenido: {response.text[:500]}...", exc_info=False)
            last_exception = e
            # No reintentar en JSONDecodeError a menos que sea un problema transitorio de la API
            break # Salir del bucle, probablemente no se resolverá reintentando

        except requests.exceptions.RequestException as e: # Otros errores de red/conexión
            logger.error(f"Error de red/conexión en solicitud a Dataverse ({url}): {e}", exc_info=False)
            last_exception = e
            if current_try >= retries:
                break
            current_try += 1
            logger.warning(f"Reintentando solicitud de red ({current_try}/{retries})...")
            time.sleep(1 * current_try)

        except Exception as e: # Captura general para errores inesperados
            logger.error(f"Error inesperado durante solicitud a Dataverse ({url}): {e}", exc_info=True)
            last_exception = e
            break # Salir en error inesperado

    logger.error(f"Todos los reintentos fallaron o error irrecuperable para la solicitud a Dataverse ({url}). Última excepción: {last_exception}")
    return {} # Devolver SIEMPRE un diccionario vacío si todo falla. NUNCA None.

def obtener_prestador_id_dataverse(codigo_prestador):
    """Obtiene el GUID del prestador a partir de su código."""
    token = get_dataverse_token()
    filtro = quote(f"cr217_codigodeprestador eq '{codigo_prestador}'", safe="'= ")
    url = f"{config.RESOURCE_DATAVERSE}/api/data/v9.2/cr217_prestadors?$select=cr217_prestadorid&$filter={filtro}"
    
    try:
        data = _make_dataverse_request(url, token)
        if data and data.get("value"):
            return data["value"][0]["cr217_prestadorid"]
    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP al obtener ID del prestador {codigo_prestador}: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Error inesperado al obtener ID del prestador {codigo_prestador}: {e}")
        
    print(f"Advertencia: No se encontró ID para el código de prestador {codigo_prestador}")
    return None


def obtener_sistemas_dataverse(prestador_guid, tipo_sistema):
    """Obtiene los sistemas (agua/alcantarillado) asociados a un prestador."""
    token = get_dataverse_token()
    entidad_expand = {
        "agua": "cr217_cr217_sistemadeagua_Prestador_cr217_prest",
        "alcantarillado": "cr217_cr217_sistemadealcantarillado_Prestador_c"
    }[tipo_sistema]
    
    # Campos a seleccionar del sistema (ID y código del sistema)
    select_sistema_fields = f"cr217_sistemade{tipo_sistema}id,cr217_codigodesistemade{tipo_sistema}"

    url = (
        f"{config.RESOURCE_DATAVERSE}/api/data/v9.2/cr217_prestadors({prestador_guid})"
        f"?$expand={entidad_expand}($select={select_sistema_fields})"
    )
    try:
        data = _make_dataverse_request(url, token)
        return data.get(entidad_expand, [])
    except Exception as e:
        print(f"Error al obtener sistemas para prestador {prestador_guid}, tipo {tipo_sistema}: {e}")
        return []


def obtener_elementos_por_sistema_dataverse(sistema_id, tipo_sistema, entidad_relacion_sufijo, campos_a_seleccionar):
    """
    Obtiene los elementos (captación, conducción, etc.) de un sistema específico.
    entidad_relacion_sufijo: Parte del nombre de la propiedad de navegación. Ejemplo: "c", "conduc".
    """
    token = get_dataverse_token()
    entidad_padre_map = {
        "agua": "cr217_sistemadeaguas",
        "alcantarillado": "cr217_sistemadealcantarillados"
    }
    entidad_padre = entidad_padre_map[tipo_sistema]

    expand_rel_map = {
        "agua": f"cr217_Sistemadeagua_cr217_Sistemadeagua_{entidad_relacion_sufijo}",
        "alcantarillado": f"cr217_Sistemadealcantarillado_cr217_{entidad_relacion_sufijo}"
    }
    expand_rel = expand_rel_map[tipo_sistema]

    campos_select_str = ",".join(campos_a_seleccionar)
    url = (
        f"{config.RESOURCE_DATAVERSE}/api/data/v9.2/{entidad_padre}({sistema_id})"
        f"?$expand={expand_rel}($select={campos_select_str})"
    )
    
    try:
        data = _make_dataverse_request(url, token)
        elementos = data.get(expand_rel, [])
        # Dataverse puede devolver un objeto en lugar de una lista si solo hay un elemento expandido
        if isinstance(elementos, dict):
            return [elementos]
        return elementos
    except Exception as e:
        print(f"Error al obtener elementos para sistema {sistema_id}, tipo {tipo_sistema}, relación {entidad_relacion_sufijo}: {e}")
        return []


def generar_df_elementos_relacionados_dataverse(codigo_prestador, tipo_sistema, entidad_relacion_sufijo, campos_a_seleccionar, nombres_columnas_df):
    """
    Función de alto nivel para obtener un DataFrame de elementos (captación, etc.)
    relacionados a los sistemas de un prestador.
    """
    token = get_dataverse_token() # El token se pasará implícitamente a través de las llamadas
    prestador_guid = obtener_prestador_id_dataverse(codigo_prestador) # No necesita token como arg explícito
    if not prestador_guid:
        print(f"No se pudo obtener el GUID para el prestador {codigo_prestador}. No se pueden obtener elementos relacionados.")
        return pd.DataFrame(columns=["codigodeprestador", f"codigodesistemade{tipo_sistema}"] + nombres_columnas_df)

    sistemas_info = obtener_sistemas_dataverse(prestador_guid, tipo_sistema) # No necesita token
    registros_totales = []

    for sistema_item in sistemas_info:
        sistema_id = sistema_item.get(f"cr217_sistemade{tipo_sistema}id")
        codigo_sistema_val = sistema_item.get(f"cr217_codigodesistemade{tipo_sistema}", pd.NA)

        if not sistema_id:
            continue

        elementos_del_sistema = obtener_elementos_por_sistema_dataverse(
            sistema_id, tipo_sistema, entidad_relacion_sufijo, campos_a_seleccionar # No necesita token
        )
        
        for elemento in elementos_del_sistema: # elementos_del_sistema ya debería ser una lista
            fila = {
                "codigodeprestador": codigo_prestador,
                f"codigodesistemade{tipo_sistema}": codigo_sistema_val
            }
            for i, campo_original in enumerate(campos_a_seleccionar):
                nombre_col_df = nombres_columnas_df[i]
                # Manejo de valores formateados para OptionSets, Lookups, etc.
                formatted_key = f"{campo_original}@OData.Community.Display.V1.FormattedValue"
                if formatted_key in elemento:
                    fila[nombre_col_df] = elemento.get(formatted_key, pd.NA)
                else:
                    fila[nombre_col_df] = elemento.get(campo_original, pd.NA)
            registros_totales.append(fila)

    if not registros_totales:
        # Devuelve un DataFrame vacío con las columnas esperadas si no hay registros
        return pd.DataFrame(columns=["codigodeprestador", f"codigodesistemade{tipo_sistema}"] + nombres_columnas_df)
        
    return pd.DataFrame(registros_totales)


def obtener_df_relaciones_prestador_dataverse(codigo_prestador, relaciones_config_dict):
    """
    Obtiene un diccionario de DataFrames, uno para el prestador y otros para sus relaciones directas.
    """
    token = get_dataverse_token()
    prestador_guid = obtener_prestador_id_dataverse(codigo_prestador)
    if not prestador_guid:
        print(f"Error: No se encontró GUID para el prestador {codigo_prestador}.")
        # Devolver diccionarios de DataFrames vacíos con las columnas esperadas
        resultados_vacios = {}
        for rel_key, conf in relaciones_config_dict.items():
            if rel_key == "__prestador__":
                cols = ["codigodeprestador"] + conf.get("nombres_columnas", [])
            else:
                cols = ["codigodeprestador"] + conf.get("nombres_columnas", []) # Asumiendo que todos tienen codigodeprestador
            resultados_vacios[rel_key.lower()] = pd.DataFrame(columns=cols) # Claves en minúsculas para consistencia
        return resultados_vacios


    prestador_config_principal = relaciones_config_dict.get("__prestador__", {})
    campos_prestador_select = prestador_config_principal.get("campos", [])
    
    expand_parts = []
    for rel_name, config_item in relaciones_config_dict.items():
        if rel_name == "__prestador__":
            continue
        campos_rel_select = config_item["campos"]
        if campos_rel_select: # Solo añadir expand si hay campos que seleccionar
            campos_select_str = ",".join(campos_rel_select)
            expand_parts.append(f"{rel_name}($select={campos_select_str})")

    url = f"{config.RESOURCE_DATAVERSE}/api/data/v9.2/cr217_prestadors({prestador_guid})"
    query_params_list = []
    if campos_prestador_select:
        query_params_list.append(f"$select={','.join(campos_prestador_select)}")
    if expand_parts:
        query_params_list.append(f"$expand={','.join(expand_parts)}")
    
    if query_params_list:
        url += "?" + "&".join(query_params_list)

    try:
        data_respuesta = _make_dataverse_request(url, token)
    except Exception as e:
        print(f"Error al obtener relaciones para prestador {codigo_prestador}: {e}")
        # Devolver diccionarios de DataFrames vacíos con las columnas esperadas
        resultados_vacios = {}
        for rel_key, conf in relaciones_config_dict.items():
            if rel_key == "__prestador__":
                cols = ["codigodeprestador"] + conf.get("nombres_columnas", [])
            else:
                cols = ["codigodeprestador"] + conf.get("nombres_columnas", [])
            resultados_vacios[rel_key.lower()] = pd.DataFrame(columns=cols)
        return resultados_vacios
        
    resultados_dfs = {}
    
    # Procesar datos del prestador principal
    if campos_prestador_select:
        prestador_fila_dict = {"codigodeprestador": codigo_prestador}
        nombres_cols_prestador = prestador_config_principal.get("nombres_columnas", [])
        for i, campo_orig in enumerate(campos_prestador_select):
            col_nombre_df = nombres_cols_prestador[i] if i < len(nombres_cols_prestador) else campo_orig
            formatted_val_key = f"{campo_orig}@OData.Community.Display.V1.FormattedValue"
            prestador_fila_dict[col_nombre_df] = data_respuesta.get(formatted_val_key, data_respuesta.get(campo_orig, pd.NA))
        resultados_dfs["prestador"] = pd.DataFrame([prestador_fila_dict])
    else: # Si no hay campos para el prestador, al menos devolver el código
        resultados_dfs["prestador"] = pd.DataFrame([{"codigodeprestador": codigo_prestador}])

    # Procesar relaciones expandidas
    for rel_nombre_api, config_rel_item in relaciones_config_dict.items():
        if rel_nombre_api == "__prestador__":
            continue
            
        campos_rel_item_select = config_rel_item["campos"]
        nombres_cols_rel_item_df = config_rel_item["nombres_columnas"]
        registros_rel_list = []
        
        # OBTENER Y VALIDAR DATOS DE RELACIÓN
        datos_de_relacion_raw = data_respuesta.get(rel_nombre_api) # Obtener el valor crudo
        
        if datos_de_relacion_raw is None: # Si la clave existe y es null, o no existe (get devuelve None por defecto si no se especifica otro)
            datos_de_relacion = [] # Tratar como lista vacía
        elif isinstance(datos_de_relacion_raw, dict): 
            datos_de_relacion = [datos_de_relacion_raw] # Convertir a lista si es un solo objeto
        elif isinstance(datos_de_relacion_raw, list):
            datos_de_relacion = datos_de_relacion_raw # Ya es una lista
        else:
            logger.warning(f"Tipo inesperado para datos de relación '{rel_nombre_api}': {type(datos_de_relacion_raw)}. Tratando como vacío.")
            datos_de_relacion = [] # Caso inesperado, tratar como vacío

        # Ahora datos_de_relacion siempre será una lista, incluso si está vacía.
        for item_dataverse in datos_de_relacion: 
            fila_rel_dict = {"codigodeprestador": codigo_prestador}
            for i, campo_orig_rel in enumerate(campos_rel_item_select):
                col_nombre_rel_df = nombres_cols_rel_item_df[i] if i < len(nombres_cols_rel_item_df) else campo_orig_rel
                formatted_val_key_rel = f"{campo_orig_rel}@OData.Community.Display.V1.FormattedValue"
                
                # Asegurarse que item_dataverse sea un diccionario antes de hacer .get()
                if isinstance(item_dataverse, dict):
                    fila_rel_dict[col_nombre_rel_df] = item_dataverse.get(formatted_val_key_rel, item_dataverse.get(campo_orig_rel, pd.NA))
                else:
                    # Esto no debería suceder si la lógica anterior para datos_de_relacion es correcta,
                    # pero es una protección adicional.
                    logger.warning(f"Item inesperado en datos de relación '{rel_nombre_api}': {item_dataverse}. Se omitirá.")
                    fila_rel_dict[col_nombre_rel_df] = pd.NA # O algún valor por defecto

            registros_rel_list.append(fila_rel_dict)
        
        # Crear DataFrame incluso si está vacío, con las columnas correctas
        df_cols = ["codigodeprestador"] + nombres_cols_rel_item_df
        if not registros_rel_list:
            resultados_dfs[rel_nombre_api.lower()] = pd.DataFrame(columns=df_cols)
        else:
            resultados_dfs[rel_nombre_api.lower()] = pd.DataFrame(registros_rel_list)
            
    return resultados_dfs


def obtener_df_prestador_simple_dataverse(codigo_prestador, campos_ps_select, nombres_columnas_ps_df):
    """Obtiene información de Población Servida (PS) para un prestador."""
    token = get_dataverse_token()
    prestador_guid = obtener_prestador_id_dataverse(codigo_prestador)
    nueva_column_ccpp = [
        "cr217_nombredecentropoblado",
        "cr217_poblaciontotaldelcentropoblado",
        "cr217_viviendastotalesdelcentropoblado",
        "cr217_densidadpoblacional",
        "cr217_distrito","cr217_provincia","cr217_departamento"
    ]
    nueva_column_ccpp_formattes = [
        "NOMCCPP","POBTOTAL","VIVTOTAL","densidad_pob","NOMDIST","NOMPROV","NOMDEP"
    ]
    if not prestador_guid:
        print(f"Error: No se encontró GUID para el prestador {codigo_prestador} (Población Servida).")
        return pd.DataFrame(columns=["codigodeprestador", "centropoblado"] + nombres_columnas_ps_df + nueva_column_ccpp_formattes)

    # La propiedad de navegación para Población Servida (PS)
    # y la anidada para Centro Poblado.
    # Revisa tu metadata para los nombres exactos:
    # cr217_Prestador_cr217_Prestador_cr217_Pob
    #   -> cr217_Centropoblado($select=cr217_codigodecentropoblado)
    prop_nav_ps = "cr217_Prestador_cr217_Prestador_cr217_Pob"
    prop_nav_ccpp_en_ps = "cr217_Centropoblado"
    campo_codigo_ccpp = "cr217_codigodecentropoblado"

    nueva_column_ccpp += [campo_codigo_ccpp]
    
    select_ps_str = ",".join(campos_ps_select)
    select_ccpp_str = ",".join(nueva_column_ccpp)
    
    url = (
        f"{config.RESOURCE_DATAVERSE}/api/data/v9.2/cr217_prestadors({prestador_guid})"
        f"?$select=cr217_codigodeprestador"  # Solo necesitamos el código del prestador aquí como referencia
        f"&$expand={prop_nav_ps}($select={select_ps_str};$expand={prop_nav_ccpp_en_ps}($select={select_ccpp_str}))"
    )

    try:
        data_respuesta = _make_dataverse_request(url, token)
    except Exception as e:
        print(f"Error al obtener PS para prestador {codigo_prestador}: {e}")
        return pd.DataFrame(columns=["codigodeprestador", "centropoblado"] + nombres_columnas_ps_df + nueva_column_ccpp_formattes)

    registros_ps_list = []
    datos_ps_list = data_respuesta.get(prop_nav_ps, [])
    if isinstance(datos_ps_list, dict): # Si Dataverse devuelve un solo objeto
        datos_ps_list = [datos_ps_list]

    for item_ps_dataverse in datos_ps_list:
        fila_ps_dict = {"codigodeprestador": codigo_prestador}
        for i, campo_orig_ps in enumerate(campos_ps_select):
            col_nombre_ps_df = nombres_columnas_ps_df[i] if i < len(nombres_columnas_ps_df) else campo_orig_ps
            formatted_val_key_ps = f"{campo_orig_ps}@OData.Community.Display.V1.FormattedValue"
            fila_ps_dict[col_nombre_ps_df] = item_ps_dataverse.get(formatted_val_key_ps, item_ps_dataverse.get(campo_orig_ps, pd.NA))
        
        # Extraer código del centro poblado anidado
        ccpp_info = item_ps_dataverse.get(prop_nav_ccpp_en_ps, {})
        
        for i, campo_orig_ccpp in enumerate(nueva_column_ccpp):
            col_nombre_ps_df = nueva_column_ccpp_formattes[i] if i < len(nueva_column_ccpp_formattes) else campo_orig_ccpp
            formatted_val_key_ps = f"{campo_orig_ccpp}@OData.Community.Display.V1.FormattedValue"
            fila_ps_dict[col_nombre_ps_df] = ccpp_info.get(formatted_val_key_ps, ccpp_info.get(campo_orig_ccpp, pd.NA))

        codigo_ccpp_val = ccpp_info.get(campo_codigo_ccpp, pd.NA)
        # Dataverse puede devolver el valor formateado también para el código del CCPP si es un lookup formateado
        formatted_ccpp_key = f"{campo_codigo_ccpp}@OData.Community.Display.V1.FormattedValue"
        if formatted_ccpp_key in ccpp_info:
            codigo_ccpp_val = ccpp_info.get(formatted_ccpp_key, codigo_ccpp_val)

        fila_ps_dict["centropoblado"] = codigo_ccpp_val
        registros_ps_list.append(fila_ps_dict)

    if not registros_ps_list:
        return pd.DataFrame(columns=["codigodeprestador", "centropoblado"] + nombres_columnas_ps_df + nueva_column_ccpp_formattes)
        
    return pd.DataFrame(registros_ps_list)

# Ejemplo adaptado para fetch_all_prestadores
def fetch_all_prestadores_dataverse():
    token = get_dataverse_token()
    url = f"{config.RESOURCE_DATAVERSE}/api/data/v9.2/cr217_prestadors?$select=cr217_codigodeprestador,createdon&$orderby=createdon desc"
    results = []
    
    while url:
        try:
            data = _make_dataverse_request(url, token) # Usar _make_dataverse_request que maneja re-autenticación
            current_batch = data.get("value", [])
            if not current_batch:
                break
            results.extend(current_batch)
            url = data.get("@odata.nextLink")
        except requests.exceptions.HTTPError as e:
            print(f"Error HTTP al obtener prestadores: {e}. Respuesta: {e.response.text if e.response else 'No response'}")
            # Decidir si reintentar o abortar
            break 
        except Exception as e:
            print(f"Error inesperado al obtener prestadores: {e}")
            break # Abortar en otros errores
            
    return results


