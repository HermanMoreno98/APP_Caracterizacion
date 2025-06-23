import pandas as pd
from docxtpl import DocxTemplate, RichText
import os
from functools import reduce 

import config
from utils import limpiar_y_convertir , generar_rutafichas
from data_preparation import *
from dataverse_api import *
from sharepoint_api import *
from image_processing import *
from plot_generator import *

logger = logging.getLogger(__name__)

def _get_value(df, column, default="-"):
    """Función interna para simplificar la obtención de valor de la primera fila."""
    if df.empty or column not in df.columns:
        return default
    val = df[column].iloc[0]
    return val if pd.notna(val) else default


# Verificación de config.RELACIONES_CONFIG_PRESTADOR (se puede hacer una vez al cargar el módulo)
if config.RELACIONES_CONFIG_PRESTADOR is None:
    logger.critical("FATAL: config.RELACIONES_CONFIG_PRESTADOR es None. La aplicación no puede continuar.")
    raise ValueError("config.RELACIONES_CONFIG_PRESTADOR no está definido correctamente.")


def _aplicar_limpieza_tipos_df(df, columnas_float=None, columnas_datetime_format=None, columnas_anio_datetime=None):
    """Aplica limpieza de tipos a un DataFrame."""
    if df.empty:
        return df
    df_copy = df.copy()
    if columnas_float:
        for col in columnas_float:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(limpiar_y_convertir)
    if columnas_datetime_format: # Formato 'dd/mm/yyyy'
        for col in columnas_datetime_format:
            if col in df_copy.columns:
                df_copy[col] = pd.to_datetime(df_copy[col], format='%d/%m/%Y', errors='coerce')
    if columnas_anio_datetime: # Extraer solo el año
        for col in columnas_anio_datetime:
            if col in df_copy.columns:
                df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce').dt.year.astype('Int64') # Int64 para permitir <NA>
    return df_copy


def generar_informe_final_desde_api(prestador_id_codigo, ruta_base_archivos_sp_descargados):
    logger.info(f"Iniciando generación de informe para: {prestador_id_codigo}")
    context_final = {} # El diccionario que se pasará a la plantilla

    # --- 1. OBTENER TODOS LOS DATAFRAMES ---
    logger.info(f"Paso 1: Obteniendo DataFrames de Dataverse para {prestador_id_codigo}...")
    dfs_relaciones = obtener_df_relaciones_prestador_dataverse(prestador_id_codigo, config.RELACIONES_CONFIG_PRESTADOR)
    
    df_prestador = dfs_relaciones.get("prestador", pd.DataFrame())
    if df_prestador.empty:
        logger.error(f"CRÍTICO: No se pudieron obtener datos básicos del prestador {prestador_id_codigo}.")
        return None

    df_fuente = dfs_relaciones.get("cr217_cr217_fuente_prestador_cr217_prestador", pd.DataFrame()) # Clave en minúscula
    df_sistema_agua_raw = dfs_relaciones.get("cr217_cr217_sistemadeagua_prestador_cr217_prest", pd.DataFrame())
    df_sistema_alca_raw = dfs_relaciones.get("cr217_cr217_sistemadealcantarillado_prestador_c", pd.DataFrame())
    df_ubs_raw = dfs_relaciones.get("cr217_prestador_cr217_prestador_cr217_ubs", pd.DataFrame())
    df_usuario_raw = dfs_relaciones.get("cr217_prestador_cr217_prestador_cr217_usu", pd.DataFrame())
    df_centropoblado_principal_raw = dfs_relaciones.get("cr217_centropoblado", pd.DataFrame())
    df_centropoblado_cercano_raw = dfs_relaciones.get("cr217_codigoubigeocentropobladocercano", pd.DataFrame())
    df_centropoblado = pd.merge(
        df_centropoblado_principal_raw,
        df_centropoblado_cercano_raw,
        on="codigodeprestador",
        how="outer"
    )

    df_centropoblado["centropoblado"] = df_centropoblado["codigodecentropoblado"].combine_first(df_centropoblado["codigoubigeocentropobladocercano"])

    # Obtener componentes de sistemas de agua
    df_captacion_raw = generar_df_elementos_relacionados_dataverse(prestador_id_codigo, "agua", "c", config.CAMPOS_CAPTACION_AGUA, config.NOMBRES_COLUMNAS_CAPTACION_AGUA)
    df_conduccion_raw = generar_df_elementos_relacionados_dataverse(prestador_id_codigo, "agua", "conduc", config.CAMPOS_CONDUCCION_AGUA, config.NOMBRES_COLUMNAS_CONDUCCION_AGUA)
    df_reservorio_raw = generar_df_elementos_relacionados_dataverse(prestador_id_codigo, "agua", "reservo", config.CAMPOS_RESERVORIO_AGUA, config.NOMBRES_COLUMNAS_RESERVORIO_AGUA)
    df_ptap_raw = generar_df_elementos_relacionados_dataverse(prestador_id_codigo, "agua", "ptap", config.CAMPOS_PTAP_AGUA, config.NOMBRES_COLUMNAS_PTAP_AGUA)

    # Obtener componentes de sistemas de alcantarillado
    df_ptar_raw = generar_df_elementos_relacionados_dataverse(prestador_id_codigo, "alcantarillado", "ptar", config.CAMPOS_PTAR_ALCA, config.NOMBRES_COLUMNAS_PTAR_ALCA)
    df_disposicionfinal_raw = generar_df_elementos_relacionados_dataverse(prestador_id_codigo, "alcantarillado", "df", config.CAMPOS_DISPOSICION_FINAL_ALCA, config.NOMBRES_COLUMNAS_DISPOSICION_FINAL_ALCA)

    # Población servida
    df_ps_raw = obtener_df_prestador_simple_dataverse(prestador_id_codigo, config.CAMPOS_POBLACION_SERVIDA, config.NOMBRES_POBLACION_SERVIDA)
    logger.info("DataFrames crudos de Dataverse obtenidos.")

    # --- 2. DESCARGAR ARCHIVOS DE SHAREPOINT ---
    logger.info("Paso 2: Descargando archivos de SharePoint...")
    # ruta_inei_local = get_bd_inei_sharepoint(config.DIR_BD_TEMP)
    # inei_2017_df = pd.read_excel(ruta_inei_local, sheet_name="CCPP") # Asegúrate del nombre de la hoja
    
    guid_prestador_dv = _get_value(df_prestador, 'prestadorid', None)
    ruta_fotos_locales_prestador = None
    if guid_prestador_dv:
        nombre_carpeta_sp = f"{prestador_id_codigo}_{guid_prestador_dv.replace('-', '')}"
        logger.info(f"Intentando descargar archivos de SharePoint para la carpeta: {nombre_carpeta_sp}")
        descarga_exitosa = download_prestador_files_sharepoint(nombre_carpeta_sp, ruta_base_archivos_sp_descargados)
        if descarga_exitosa:
            ruta_fotos_locales_prestador = os.path.join(ruta_base_archivos_sp_descargados, nombre_carpeta_sp)
            logger.info(f"Archivos de SharePoint descargados (o intento realizado) en: {ruta_fotos_locales_prestador}")
        else:
            logger.warning(f"No se pudieron descargar archivos para {prestador_id_codigo} desde SharePoint (carpeta: {nombre_carpeta_sp}).")
    else:
        logger.error(f"No se pudo obtener el GUID del prestador {prestador_id_codigo} para descargas de SharePoint.")
    logger.info("Descarga de archivos de SharePoint completada (o intento realizado).")

    # --- 3. LIMPIEZA Y TRANSFORMACIÓN DE TIPOS DE DATOS ---
    logger.info("Paso 3: Limpiando y transformando tipos de datos...")
    df_prestador = _aplicar_limpieza_tipos_df(df_prestador, config.COLUMNAS_FLOAT_PRESTADOR, columnas_datetime_format=['p002_fechadecaracterizacion'])
    df_ps = _aplicar_limpieza_tipos_df(df_ps_raw, config.COLUMNAS_FLOAT_PS)
    df_usuario = _aplicar_limpieza_tipos_df(df_usuario_raw, config.COLUMNAS_FLOAT_USUARIO)
    
    df_sistema_agua = _aplicar_limpieza_tipos_df(df_sistema_agua_raw, config.COLUMNAS_FLOAT_SISTEMA_AGUA, 
                                                columnas_datetime_format=['fecha'], # Ejemplo, ajusta
                                                columnas_anio_datetime=['aniodeconstruccioncasetabombeo', 'aniodeconstrucciondistribucion', 'p007_enqueanoseconstruyoelsistemadeagua', 'p004_anodecontruccionnoconvencional']) # Ejemplo, ajusta
    df_captacion_raw = _aplicar_limpieza_tipos_df(df_captacion_raw, config.COLUMNAS_FLOAT_COORDS, columnas_anio_datetime=['anodeconstruccion'])
    df_conduccion_raw = _aplicar_limpieza_tipos_df(df_conduccion_raw, columnas_anio_datetime=['anodeconstruccionconduccion'])
    df_reservorio_raw = _aplicar_limpieza_tipos_df(df_reservorio_raw, config.COLUMNAS_FLOAT_RESERVORIO + config.COLUMNAS_FLOAT_COORDS, columnas_anio_datetime=['anodeconstruccion'])
    df_ptap_raw = _aplicar_limpieza_tipos_df(df_ptap_raw, config.COLUMNAS_FLOAT_COORDS, columnas_anio_datetime=['anodeconstruccion'])

    df_sistema_alca_raw = _aplicar_limpieza_tipos_df(df_sistema_alca_raw, config.COLUMNAS_FLOAT_COORDS, columnas_anio_datetime=['anodeconstruccion'])
    df_ptar_raw = _aplicar_limpieza_tipos_df(df_ptar_raw, columnas_anio_datetime=['anodeconstruccionptar'])
    df_ubs_raw = _aplicar_limpieza_tipos_df(df_ubs_raw, columnas_anio_datetime=['enqueanoseconstruyolaubs'])
    # df_disposicionfinal_raw no parece necesitar limpieza de tipos según el original

    # Pre-procesar INEI (ya hecho parcialmente antes, pero asegurar consistencia)
    col_ps = ['POBTOTAL','VIVTOTAL','densidad_pob','NOMCCPP','NOMDIST','NOMPROV','NOMDEP']
    inei_2017_df = df_ps.copy()
    df_ps = df_ps.drop(columns=col_ps, errors='ignore')  
    col_ps.append('centropoblado')
    inei_2017_df = inei_2017_df[col_ps].rename(columns={"centropoblado": "ubigeo_ccpp"})
    inei_2017_df['ubigeo_ccpp'] = inei_2017_df['ubigeo_ccpp'].astype(str)
    inei_2017_df['POBTOTAL'] = pd.to_numeric(inei_2017_df['POBTOTAL'], errors='coerce').fillna(0)
    inei_2017_df['VIVTOTAL'] = pd.to_numeric(inei_2017_df['VIVTOTAL'], errors='coerce').fillna(0)
    inei_2017_df['densidad_pob'] = pd.to_numeric(inei_2017_df['densidad_pob'], errors='coerce').fillna(0)
    inei_2017_df['ambito_ccpp'] = inei_2017_df['POBTOTAL'].apply(lambda x: 'Rural' if x <= 2000 else ('Pequeña Ciudad' if x <= 15000 else 'Urbano'))
    # if 'ambito_ccpp' not in inei_2017_df.columns: # Calcular si no viene de la BD INEI
    #     inei_2017_df['ambito_ccpp'] = inei_2017_df['POBTOTAL'].apply(lambda x: 'Rural' if x <= 2000 else ('Pequeña Ciudad' if x <= 15000 else 'Urbano'))
    
    logger.info("Limpieza de tipos de datos completada.")

    # --- 4. MERGES Y CÁLCULOS ADICIONALES ---
    logger.info("Paso 4: Realizando merges y cálculos adicionales...")
    # Merge del prestador con su centro poblado principal
    if not df_centropoblado_principal_raw.empty and 'codigodecentropoblado' in df_centropoblado_principal_raw.columns:
        # Asumir que df_prestador ya tiene 'codigodeprestador' y 'centropoblado' (GUID del CP)
        # Y df_centropoblado_principal_raw tiene 'codigodeprestador' y 'codigodecentropoblado' (el código ubigeo)
        # La lógica original hacía: pd.merge(df_prestador, df_centropoblado, on="codigodeprestador", how="left")
        # Y luego renombraba. Aquí necesitamos asegurar que el merge sea por el campo correcto.
        # Si 'centropoblado' en df_prestador es el ID/GUID del registro de CP, y no el código ubigeo,
        # y 'cr217_CentroPoblado' en RELACIONES_CONFIG_PRESTADOR trae el código, el merge es más complejo.
        # Asumiendo que df_prestador TIENE una columna 'centropoblado' que es el UBIGEO_CCPP para el merge con INEI.
        # Esta columna 'centropoblado' se obtiene de la relación cr217_CentroPoblado.
        if 'centropoblado' in df_centropoblado.columns:
             df_prestador = pd.merge(df_prestador, 
                                     df_centropoblado[['codigodeprestador', 'centropoblado']], 
                                     on='codigodeprestador', how='left')
        else:
            if 'centropoblado' not in df_prestador.columns: # Si no vino de la relación __prestador__
                logger.warning("Columna 'centropoblado' no encontrada en df_prestador para merge con INEI.")
                df_prestador['centropoblado'] = pd.NA # Añadir para evitar error, pero el merge fallará

    # Merge df_prestador con INEI (ya debería tener 'centropoblado' como código ubigeo)
    df_prestador['centropoblado'] = df_prestador['centropoblado'].astype(str)
    df_prestador_merged_inei = pd.merge(df_prestador, inei_2017_df, left_on='centropoblado', right_on='ubigeo_ccpp', how='left')

    # Agregación de conexiones de PS y merge con df_prestador_merged_inei
    if not df_ps.empty and 'p022_conexionesdeaguaactivas' in df_ps.columns and 'p024_conexionesdealcantarilladoactivas' in df_ps.columns:
        df_ps_grouped = df_ps.groupby("codigodeprestador", as_index=False).agg(
            p022_conexionesdeaguaactivas_sum=('p022_conexionesdeaguaactivas', 'sum'),
            p024_conexionesdealcantarilladoactivas_sum=('p024_conexionesdealcantarilladoactivas', 'sum')
        )
        df_prestador_final = pd.merge(df_prestador_merged_inei, df_ps_grouped, on="codigodeprestador", how="left")
        # Renombrar las columnas sumadas a los nombres originales esperados por data_preparation
        df_prestador_final.rename(columns={'p022_conexionesdeaguaactivas_sum': 'p022_conexionesdeaguaactivas',
                                           'p024_conexionesdealcantarilladoactivas_sum': 'p024_conexionesdealcantarilladoactivas'}, inplace=True)
    else:
        df_prestador_final = df_prestador_merged_inei.copy()
        if 'p022_conexionesdeaguaactivas' not in df_prestador_final.columns: df_prestador_final['p022_conexionesdeaguaactivas'] = 0
        if 'p024_conexionesdealcantarilladoactivas' not in df_prestador_final.columns: df_prestador_final['p024_conexionesdealcantarilladoactivas'] = 0
    logger.info("Merges completados.")
    # --- 5. DETERMINAR PLANTILLA DOCX ---
    logger.info("Paso 5: Determinando plantilla DOCX...")
    plantilla_path = config.TEMPLATE_PRINCIPAL
    # nombre_prest_val = _get_value(df_prestador_final, 'p016_nombredelprestador', "")
    # if nombre_prest_val == "ABASTECIMIENTO SIN PRESTADOR":
    #     plantilla_path = config.TEMPLATE_SIN_PRESTADOR
    logger.info(f"Usando plantilla: {plantilla_path}")
    try:
        doc = DocxTemplate(plantilla_path)
    except Exception as e:
        logger.error(f"Error al cargar plantilla {plantilla_path}: {e}", exc_info=True)
        return None

    # --- 6. PREPARAR CONTEXTO LLAMANDO A FUNCIONES DE data_preparation.py ---
    logger.info("Paso 6: Preparando contexto para el informe...")
    
    # Es crucial que df_prestador_final tenga todas las columnas que esperan estas funciones.
    # df_ps ya está filtrado para el prestador_id_codigo
    # df_fuente ya está filtrado para el prestador_id_codigo
    ctx_dg, df_prep_prestador, df_prep_ps, df_prep_fuente = \
        preparar_datos_generales_y_poblacion(df_prestador_final, inei_2017_df, df_ps, df_fuente)
    context_final.update(ctx_dg)

    context_final.update(preparar_constitucion_prestador(df_prep_prestador))
    context_final.update(preparar_capacitacion_asistencia(df_prep_prestador))
    context_final.update(preparar_capacidad_financiera(df_prep_prestador)) # Necesita df_prep_prestador (que tiene las sumas de PS)
    context_final.update(preparar_identificacion_peligros(df_prep_prestador))
    context_final.update(preparar_disponibilidad_recurso_hidrico(df_prep_prestador, df_prep_fuente))

    # Para sistemas de agua, df_ps_actual es df_ps (ya filtrado)
    ctx_agua, coords_agua_list = preparar_sistemas_agua(
        df_prep_prestador, df_sistema_agua, df_captacion_raw, df_conduccion_raw, 
        df_reservorio_raw, df_ptap_raw, df_ps
    )
    context_final.update(ctx_agua)

    # Para saneamiento, df_ps_actual es df_ps (ya filtrado)
    context_final.update(preparar_sistemas_alcantarillado_ptar_ubs(
        df_prep_prestador, df_sistema_alca_raw, df_ptar_raw, df_disposicionfinal_raw, 
        df_ubs_raw, df_ps, coords_agua_list
    ))
    
    es_prestador_render_flag = _get_value(df_prep_prestador, 'existeprestadordessenelccppprincipal', "-")
    ctx_usuarios, df_abast_graf, df_veces_graf, df_gastos_otros_graf = \
        preparar_percepcion_usuarios(df_usuario, es_prestador_render_flag) # Pasar df_usuario (ya filtrado)
    context_final.update(ctx_usuarios)
    
    logger.info("Preparación del contexto de datos completada.")

    # --- 7. MANEJAR IMÁGENES Y GRÁFICOS ---
    logger.info("Paso 7: Preparando imágenes y gráficos...")
    # Enlace a fichas
    rutafichas_val = generar_rutafichas(df_prep_prestador['codigodeprestador'].values[0],
                                        df_prep_prestador['prestadorid'].values[0])
    # rutafichas_val = _get_value(df_prep_prestador, 'rutafichas', None)
    if rutafichas_val and rutafichas_val != '-':
        rt_link = RichText()
        rt_link.add(rutafichas_val, url_id=doc.build_url_id(rutafichas_val))
        context_final['link'] = rt_link
    else:
        context_final['link'] = "-"

    # Recursos fotográficos
    context_final['images_matrix'] = []
    context_final['imageActas'] = []
    if ruta_fotos_locales_prestador and os.path.isdir(ruta_fotos_locales_prestador):
        if guid_prestador_dv: # guid_prestador_dv ya se obtuvo antes
                nombre_carpeta_sharepoint = f"{prestador_id_codigo}_{guid_prestador_dv.replace('-', '')}"
                # ruta_base_archivos_sp_descargados es config.DIR_PRESTADOR_FILES

                fotos_obj_list = cargar_imagenes_para_informe(
                    doc, 
                    ruta_base_archivos_sp_descargados, # ej. "temp_processing/cr217_prestador"
                    nombre_carpeta_sharepoint,         # ej. "P-09723-D2Q3Z_2ce..."
                    'FOTOS',                           # subcarpeta_fotos
                    ancho_pulgadas=3
                )
                context_final['images_matrix'] = organizar_imagenes_matriz(fotos_obj_list, columnas=2)
                
                actas_obj_list = cargar_imagenes_para_informe(
                    doc, 
                    ruta_base_archivos_sp_descargados, 
                    nombre_carpeta_sharepoint,
                    'ACTAS',                           # subcarpeta_fotos
                    ancho_pulgadas=5
                )
                context_final['imageActas'] = actas_obj_list
        else:
            logger.warning(f"No se pudo determinar nombre_carpeta_sharepoint, no se cargarán imágenes para {prestador_id_codigo}")
    else:
        logger.warning(f"No se encontraron fotos/actas locales para {prestador_id_codigo} en {ruta_fotos_locales_prestador}")

    # Gráficos
    # (Asegúrate que plot_generator guarde en config.DIR_GRAPHS)
    # Gráfico 1: Abastecimiento
    path_grafico1 = generar_grafico_abastecimiento_pie(df_abast_graf, "grafico_1.png")
    if path_grafico1 and os.path.exists(path_grafico1):
        context_final['grafico_1'] = InlineImage(doc, path_grafico1, width=Inches(2.5))
    else:
        context_final['grafico_1'] = "Gráfico no disponible"

    # Gráfico 2: Gasto Promedio Abastecimiento
    path_grafico2 = generar_grafico_gasto_promedio_abastecimiento(df_abast_graf, "grafico_2.png")
    if path_grafico2 and os.path.exists(path_grafico2):
        context_final['grafico_2'] = InlineImage(doc, path_grafico2, width=Inches(2.5))
    else:
        context_final['grafico_2'] = "Gráfico no disponible"

    # Gráfico 3: Litros Promedio Abastecimiento
    path_grafico3 = generar_grafico_litros_promedio_abastecimiento(df_abast_graf, "grafico_3.png")
    if path_grafico3 and os.path.exists(path_grafico3):
        context_final['grafico_3'] = InlineImage(doc, path_grafico3, width=Inches(2.5))
    else:
        context_final['grafico_3'] = "Gráfico no disponible"

    # Gráfico 4: Frecuencia de Abastecimiento
    path_grafico4 = generar_grafico_frecuencia_abastecimiento(df_veces_graf, "grafico_4.png")
    if path_grafico4 and os.path.exists(path_grafico4):
        context_final['grafico_4'] = InlineImage(doc, path_grafico4, width=Inches(2.5))
    else:
        context_final['grafico_4'] = "Gráfico no disponible"

    # Gráfico 5: Gasto en Otros Servicios
    path_grafico5 = generar_grafico_gasto_otros_servicios(df_gastos_otros_graf, "grafico_5.png")
    if path_grafico5 and os.path.exists(path_grafico5):
        context_final['grafico_5'] = InlineImage(doc, path_grafico5, width=Inches(2.5))
    else:
        context_final['grafico_5'] = "Gráfico no disponible"


    # --- 8. RENDERIZAR EL DOCUMENTO ---
    logger.info("Paso 8: Renderizando el documento Word...")
    
    # Depuración final del contexto
    debug_context_path = os.path.join(config.DIR_REPORTS, f"DEBUG_CONTEXT_FINAL_{prestador_id_codigo}.json")
    try:
        with open(debug_context_path, 'w', encoding='utf-8') as f_debug:
            def custom_serializer(obj):
                if isinstance(obj, (datetime, pd.Timestamp)): return obj.isoformat()
                if hasattr(obj, '__class__') and 'docxtpl' in str(obj.__class__): return f"<{obj.__class__.__name__} object>"
                try: # Para manejar pd.NA u otros no serializables
                    return str(obj)
                except: return f"<Objeto no serializable: {type(obj)}>"
            json.dump(context_final, f_debug, default=custom_serializer, indent=2, ensure_ascii=False)
        logger.info(f"Contexto final de depuración guardado en: {debug_context_path}")
    except Exception as e_json:
        logger.error(f"No se pudo guardar el contexto final de depuración: {e_json}")

    try:
        doc.render(context_final)
        os.makedirs(config.DIR_REPORTS, exist_ok=True)
        output_filename = f"INFORME_{prestador_id_codigo}.docx"
        filepath = os.path.join(config.DIR_REPORTS, output_filename)
        doc.save(filepath)
        logger.info(f"Informe generado exitosamente: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error al renderizar o guardar informe para {prestador_id_codigo}: {e}", exc_info=True)
        return None