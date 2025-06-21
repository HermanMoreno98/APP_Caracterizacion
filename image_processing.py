import exifread
from PIL import Image, ExifTags
from io import BytesIO
from docxtpl import InlineImage
from docx.shared import Inches
import glob
import os
from natsort import natsorted

def obtener_coordenadas_gps(imagen_path):
    try:
        with open(imagen_path, 'rb') as f:
            tags = exifread.process_file(f, details=False) # details=False para rapidez
            if 'GPS GPSLatitude' not in tags or 'GPS GPSLongitude' not in tags:
                return None

            lat_values = tags['GPS GPSLatitude'].values
            lon_values = tags['GPS GPSLongitude'].values
            
            # Asegurarse que sean listas de 3 elementos numéricos (Ratio)
            if not (isinstance(lat_values, list) and len(lat_values) == 3 and
                    isinstance(lon_values, list) and len(lon_values) == 3):
                return None
            if not all(isinstance(v, exifread.utils.Ratio) for v in lat_values + lon_values):
                 return None
            if not (all(val.den != 0 for val in lat_values) and all(val.den != 0 for val in lon_values)):
                 return None # Evitar división por cero

            lat_deg = float(lat_values[0].num) / lat_values[0].den
            lat_min = float(lat_values[1].num) / lat_values[1].den
            lat_sec = float(lat_values[2].num) / lat_values[2].den
            
            lon_deg = float(lon_values[0].num) / lon_values[0].den
            lon_min = float(lon_values[1].num) / lon_values[1].den
            lon_sec = float(lon_values[2].num) / lon_values[2].den

            latitud_decimal = lat_deg + (lat_min / 60.0) + (lat_sec / 3600.0)
            longitud_decimal = lon_deg + (lon_min / 60.0) + (lon_sec / 3600.0)

            lat_ref = tags.get('GPS GPSLatitudeRef', None)
            lon_ref = tags.get('GPS GPSLongitudeRef', None)

            if lat_ref and lat_ref.values == 'S':
                latitud_decimal = -latitud_decimal
            if lon_ref and lon_ref.values == 'W':
                longitud_decimal = -longitud_decimal
            
            return latitud_decimal, longitud_decimal
    except (IOError, OSError, KeyError, AttributeError, ZeroDivisionError) as e:
        print(f"Error al procesar GPS de la imagen {imagen_path}: {e}")
        return None
    return None


def corregir_orientacion_y_convertir_a_png_memoria(imagen_bytes):
    try:
        imagen = Image.open(BytesIO(imagen_bytes))
        
        # Corregir orientación
        if hasattr(imagen, '_getexif'):
            exif_data = imagen._getexif()
            if exif_data:
                orientation_tag = ExifTags.TAGS.get('Orientation')
                if orientation_tag in exif_data:
                    orientation = exif_data[orientation_tag]
                    if orientation == 3:
                        imagen = imagen.rotate(180, expand=True)
                    elif orientation == 6:
                        imagen = imagen.rotate(270, expand=True)
                    elif orientation == 8:
                        imagen = imagen.rotate(90, expand=True)

        # Convertir a PNG en memoria
        png_buffer = BytesIO()
        imagen.save(png_buffer, format="PNG")
        return png_buffer.getvalue()
    except Exception as e:
        print(f"Error convirtiendo imagen a PNG: {e}")
        return None # O retornar imagen_bytes si falla la conversión y se quiere usar la original

def cargar_imagenes_para_informe(doc, ruta_base_fotos, carpeta_prestador, subcarpeta_fotos, ancho_pulgadas=3):
    """Carga imágenes de una carpeta, las procesa y las prepara para DocxTemplate."""
    image_objects = []
    ruta_completa_fotos = os.path.join(ruta_base_fotos, carpeta_prestador, subcarpeta_fotos)
    formatos_imagen = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]

    if not os.path.isdir(ruta_completa_fotos):
        print(f"Advertencia: La carpeta de fotos no existe: {ruta_completa_fotos}")
        return []

    for fpath in natsorted(glob.glob(os.path.join(ruta_completa_fotos, '*'))):
        if os.path.splitext(fpath)[1].lower() in formatos_imagen:
            try:
                with open(fpath, "rb") as f:
                    original_bytes = f.read()
                
                processed_bytes = corregir_orientacion_y_convertir_a_png_memoria(original_bytes)
                if processed_bytes:
                    img_obj = InlineImage(doc, BytesIO(processed_bytes), width=Inches(ancho_pulgadas))
                    image_objects.append(img_obj)
                else: # Fallback a la imagen original si el procesamiento falla
                    img_obj = InlineImage(doc, BytesIO(original_bytes), width=Inches(ancho_pulgadas))
                    image_objects.append(img_obj)
                    
            except (IOError, OSError) as e:
                print(f"Error abriendo o procesando imagen {fpath}: {e}")
                pass # Ignorar archivos que no se puedan abrir/procesar
    return image_objects

def organizar_imagenes_matriz(image_objects, columnas=2):
    """Organiza una lista de InlineImage en una matriz para la plantilla."""
    if not image_objects:
        return []
    return [image_objects[i:i + columnas] for i in range(0, len(image_objects), columnas)]