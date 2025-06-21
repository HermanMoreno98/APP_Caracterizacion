# app.py

from flask import Flask, render_template, send_file, redirect, url_for, flash
import os
import shutil
import traceback # Para imprimir stack traces de errores
import logging # Para un mejor logging

# Importar módulos del proyecto
import config # Tu archivo de configuración (config.py)
from dataverse_api import fetch_all_prestadores_dataverse # Para la lista en index.html
from report_generator import generar_informe_final_desde_api # Para generar el .docx
from sharepoint_api import get_dataverse_token, get_sharepoint_token # Para inicializar/probar tokens al inicio si es necesario

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Crear la aplicación Flask ---
application = Flask(__name__, template_folder='templates')
application.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24)) # Mejor usar variable de entorno para la secret key
app = application

# --- Funciones de Utilidad para Directorios ---
def asegurar_directorios_temporales():
    """Asegura que los directorios temporales base existan."""
    dirs_to_ensure = [
        config.DIR_TEMP_BASE,
        config.DIR_REPORTS,
        config.DIR_GRAPHS,
        config.DIR_PRESTADOR_FILES,
        config.DIR_BD_TEMP
    ]
    for dir_path in dirs_to_ensure:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            logger.error(f"No se pudo crear el directorio {dir_path}: {e}")
            # Podrías decidir terminar la app aquí si estos directorios son cruciales
            # raise OSError(f"No se pudo crear el directorio crítico {dir_path}") from e


def limpiar_directorios_temporales_especificos(prestador_id_codigo):
    """Limpia los directorios temporales específicos de una generación de informe."""
    logger.info(f"Iniciando limpieza de directorios temporales para {prestador_id_codigo}...")
    
    # Ruta a la carpeta específica del prestador (ej: temp_processing/cr217_prestador/PCODIGO_GUID)
    # Necesitamos el nombre completo de la carpeta que se usó.
    # Esto es un poco complicado si el GUID no se pasa directamente.
    # Por ahora, asumiremos que solo limpiamos los directorios generales,
    # la limpieza más profunda de subcarpetas de prestadores puede ser más compleja
    # o se maneja si la carpeta base DIR_PRESTADOR_FILES se borra entera.

    # Limpiar archivos de informe específicos
    informe_path = os.path.join(config.DIR_REPORTS, f"INFORME_{prestador_id_codigo}.docx")
    if os.path.exists(informe_path):
        try:
            os.remove(informe_path)
            logger.info(f"Archivo de informe eliminado: {informe_path}")
        except Exception as e:
            logger.error(f"Error eliminando {informe_path}: {e}")

    # Limpiar gráficos (si tienen un patrón predecible o si se borra toda la carpeta)
    # Si los gráficos son siempre los mismos 5 archivos:
    graficos_a_limpiar = [f"grafico_{i}.png" for i in range(1, 6)]
    for grafico_nombre in graficos_a_limpiar:
        grafico_path = os.path.join(config.DIR_GRAPHS, grafico_nombre)
        if os.path.exists(grafico_path):
            try:
                os.remove(grafico_path)
                logger.info(f"Gráfico eliminado: {grafico_path}")
            except Exception as e:
                logger.error(f"Error eliminando {grafico_path}: {e}")
    
    # Limpiar archivo INEI descargado
    inei_path = os.path.join(config.DIR_BD_TEMP, config.LOCAL_INEI_FILE_NAME)
    if os.path.exists(inei_path):
        try:
            os.remove(inei_path)
            logger.info(f"Archivo INEI eliminado: {inei_path}")
        except Exception as e:
            logger.error(f"Error eliminando {inei_path}: {e}")
            
    # Limpiar carpeta específica de archivos de prestador (FOTOS/ACTAS)
    # Esto requiere conocer el `nombre_carpeta_sharepoint` usado en `report_generator`
    # Si no se pasa ese nombre aquí, es difícil limpiarlo selectivamente.
    # Una opción es que `generar_informe_final_desde_api` devuelva esa ruta.
    # Por ahora, la limpieza de DIR_PRESTADOR_FILES completa se haría al salir de la app.

    logger.info(f"Limpieza parcial para {prestador_id_codigo} completada.")


def limpiar_todos_directorios_temporales_base():
    """Limpia todos los directorios temporales base. Usar con precaución o al salir."""
    if os.path.exists(config.DIR_TEMP_BASE):
        try:
            shutil.rmtree(config.DIR_TEMP_BASE)
            logger.info(f"Directorio temporal base limpiado: {config.DIR_TEMP_BASE}")
        except Exception as e:
            logger.error(f"Error al limpiar el directorio temporal base {config.DIR_TEMP_BASE}: {e}")

# --- Función de Inicialización de la Aplicación ---
def inicializar_aplicacion_una_sola_vez():
    """Tareas a realizar una sola vez cuando la aplicación (o el proceso worker) inicia."""
    logger.info("Función de inicialización de la aplicación ejecutándose...")
    asegurar_directorios_temporales()
    try:
        logger.info("Probando obtención de token de Dataverse...")
        get_dataverse_token() # Llama para asegurar que la config es válida y el token se cachea
        logger.info("Token de Dataverse obtenido/validado.")
        logger.info("Probando obtención de token de SharePoint...")
        get_sharepoint_token()
        logger.info("Token de SharePoint obtenido/validado.")
    except Exception as e:
        logger.error(f"ERROR CRÍTICO durante la inicialización de tokens: {e}. La aplicación podría no funcionar correctamente.", exc_info=True)
        # En un entorno de producción, podrías querer que esto detenga el inicio de la app
        # si los tokens son absolutamente necesarios desde el principio.
        # raise RuntimeError("Fallo al obtener tokens iniciales, la aplicación no puede continuar.") from e
        flash("ADVERTENCIA: Hubo un problema al conectar con los servicios de datos externos. Algunas funcionalidades pueden estar afectadas.", "danger")

# --- LLAMAR A LA FUNCIÓN DE INICIALIZACIÓN UNA VEZ ---
# Esto se ejecutará cuando el módulo app.py se cargue por primera vez.
# En un entorno de producción con múltiples workers (como Gunicorn),
# cada worker ejecutará esto una vez al iniciarse.
if os.environ.get("WERKZEUG_RUN_MAIN") != "true": # Evita doble ejecución con el reloader de Werkzeug en debug
    # Sin embargo, para asegurar que se ejecute al menos una vez ANTES de cualquier request,
    # y para simplificar, podemos llamarlo directamente, pero estar conscientes de la doble ejecución
    # en modo debug si no se maneja el `WERKZEUG_RUN_MAIN`.
    # Una forma más simple es ponerlo sin el if, y aceptar la doble llamada en debug.
    pass 
    # Si es crucial que solo se ejecute una vez incluso en debug con reloader,
    # se pueden usar técnicas más avanzadas o simplemente llamarla y que las funciones internas
    # (como get_token) sean idempotentes o manejen múltiples llamadas.

# Llamada directa para asegurar que se ejecute al menos una vez.
# Las funciones de token ya tienen su propia caché.
inicializar_aplicacion_una_sola_vez()

@app.route("/")
def index():
    logger.info("Acceso a la ruta principal '/'")
    try:
        asegurar_directorios_temporales() # Asegurar que existan por si fueron borrados
        prestadores_data = fetch_all_prestadores_dataverse()
        
        if prestadores_data is None: # fetch_all_prestadores podría devolver None en error grave
            logger.error("fetch_all_prestadores_dataverse devolvió None.")
            flash("Error crítico al cargar la lista de prestadores desde Dataverse. Contacte al administrador.", "danger")
            prestadores_data = []
        elif not prestadores_data:
            logger.info("No se encontraron prestadores o la lista está vacía.")
            flash("No se encontraron prestadores disponibles para generar informes.", "info")
            
        return render_template("index.html", data=prestadores_data)
    except Exception as e:
        logger.error(f"Error en la ruta '/': {e}\n{traceback.format_exc()}")
        flash(f"Ocurrió un error inesperado al cargar la página principal: {str(e)}", "danger")
        return render_template("index.html", data=[])


@app.route("/download/<prestador_id_codigo>")
def download(prestador_id_codigo):
    logger.info(f"Solicitud de descarga para el prestador: {prestador_id_codigo}")
    asegurar_directorios_temporales() # Asegurar que los directorios base existan

    # Directorio base para los archivos de FOTOS/ACTAS de ESTE prestador.
    # `generar_informe_final_desde_api` usará esto para saber dónde buscar/poner los archivos de SP.
    # La subcarpeta específica (ej. PCODIGO_GUID) se crea dentro de `download_prestador_files_sharepoint`
    # y se usa en `report_generator` para acceder a esos archivos.
    ruta_base_archivos_prestador_sp = config.DIR_PRESTADOR_FILES

    try:
        filepath_informe = generar_informe_final_desde_api(
            prestador_id_codigo,
            ruta_base_archivos_prestador_sp # Pasar la ruta donde se manejarán las descargas de SP
        )
        
        if filepath_informe and os.path.exists(filepath_informe):
            logger.info(f"Informe generado: {filepath_informe}. Enviando al cliente...")
            # send_file podría necesitar un nombre de archivo para la descarga
            nombre_descarga = os.path.basename(filepath_informe)
            response = send_file(filepath_informe, as_attachment=True, download_name=nombre_descarga)
            return response
        else:
            logger.error(f"No se pudo generar o encontrar el archivo de informe para {prestador_id_codigo}.")
            flash(f"Error: No se pudo generar el informe para {prestador_id_codigo}. Consulte los logs del servidor.", "danger")
            return redirect(url_for('index'))
            
    except Exception as e:
        logger.error(f"Error crítico durante la generación/descarga para {prestador_id_codigo}: {e}\n{traceback.format_exc()}")
        flash(f"Ocurrió un error grave al generar el informe para {prestador_id_codigo}: {str(e)}", "danger")
        return redirect(url_for('index'))
    finally:
        # Limpieza después de la solicitud (opcional si se confía en la limpieza al salir)
        # Es más robusto limpiar lo que se pueda de esta request específica.
        limpiar_directorios_temporales_especificos(prestador_id_codigo)
        # La carpeta de FOTOS/ACTAS específica del prestador (PCODIGO_GUID) se limpia si
        # la función de limpieza la conoce o si se borra DIR_PRESTADOR_FILES globalmente.


# --- Ejecución de la Aplicación ---
if __name__ == "__main__":
    # Registrar la limpieza de todos los directorios temporales al salir de la aplicación
    # Esto es más útil para desarrollo. En producción, la gestión de temporales puede ser diferente.
    # atexit.register(limpiar_todos_directorios_temporales_base)

    try:
        port = int(os.environ.get("PORT", 5001))
        # Cambiar debug=False para producción
        logger.info(f"Iniciando servidor Flask en el puerto {port}...")
        app.run(host='0.0.0.0', port=port, debug=True) 
        
    except Exception as e:
        logger.critical(f"No se pudo iniciar la aplicación Flask: {str(e)}\n{traceback.format_exc()}")
    finally:
        logger.info("Aplicación Flask terminando.")
        # La limpieza con atexit se ejecutará aquí si la app se cierra limpiamente.
        # Si se usa Ctrl+C, puede que no siempre se ejecute completamente.
        # Para asegurar limpieza, especialmente en desarrollo, puedes llamar explícitamente:
        limpiar_todos_directorios_temporales_base()