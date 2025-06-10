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
import exifread
warnings.filterwarnings("ignore") # Ignorar todos los warnings

# Funcion para extraer coordenadas de la foto
def obtener_coordenadas_gps(imagen_path):
    try:
        with open(imagen_path, 'rb') as f:
            tags = exifread.process_file(f)
            # Verificar si existen datos de GPS en los metadatos
            if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                # Obtener las coordenadas de latitud y longitud
                latitud = tags['GPS GPSLatitude'].values
                longitud = tags['GPS GPSLongitude'].values
                
                # Convertir las coordenadas de formato DMS (grados, minutos, segundos) a decimal
                if all(latitud) and all(longitud):  # Verificar si todos los valores son diferentes de cero
                    latitud_decimal = float(latitud[0].num) / float(latitud[0].den) + \
                                    float(latitud[1].num) / (60 * float(latitud[1].den)) + \
                                    float(latitud[2].num) / (3600 * float(latitud[2].den))
                    longitud_decimal = float(longitud[0].num) / float(longitud[0].den) + \
                                    float(longitud[1].num) / (60 * float(longitud[1].den)) + \
                                    float(longitud[2].num) / (3600 * float(longitud[2].den))
                
                    # Verificar la dirección (Norte, Sur, Este, Oeste)
                    latitud_ref = tags['GPS GPSLatitudeRef'].values
                    longitud_ref = tags['GPS GPSLongitudeRef'].values

                
                    if latitud_ref == 'S':
                        latitud_decimal = -latitud_decimal
                    if longitud_ref == 'W':
                        longitud_decimal = -longitud_decimal
                
                    return latitud_decimal, longitud_decimal
                else:
                    return None
            else:
                return None
    except(IOError, OSError, KeyError) as e:
        print(f"Error al procesar la imagen: {e}")
        return None

# Función para convertir imagen JPEG a PNG en memoria y corregir la rotación
def jpeg_to_png_in_memory(jpeg_bytes):
    # Abrir la imagen JPEG desde memoria
    imagen = Image.open(BytesIO(jpeg_bytes))
    # Obtener la orientación EXIF de la imagen
    exif_orientation = None
    if hasattr(imagen, '_getexif') and imagen._getexif() is not None:
        for tag, value in imagen._getexif().items():
            if ExifTags.TAGS.get(tag) == 'Orientation':
                exif_orientation = value
                break
    # Rotar la imagen según la orientación EXIF (si es necesario)
    if exif_orientation and exif_orientation != 1:
        if exif_orientation == 3:
            imagen = imagen.rotate(180, expand=True)
        elif exif_orientation == 6:
            imagen = imagen.rotate(270, expand=True)
        elif exif_orientation == 8:
            imagen = imagen.rotate(90, expand=True)
    # Crear un buffer de bytes para guardar la imagen PNG
    png_buffer = BytesIO()
    # Convertir y guardar la imagen como PNG en el buffer
    imagen.save(png_buffer, format="PNG")
    # Obtener los bytes de la imagen PNG
    png_bytes = png_buffer.getvalue()
    return png_bytes

# Conversion de costos en distintos periodos a frecuencia anual
def calcular_op_anual(frec, costo):
    """
    Calcula el costo anual basado en la frecuencia y el costo proporcionado.

    Args:
    - frec (str): La frecuencia del costo ('Mensual', 'Trimestral', 'Anual', 'Otro').
    - costo (float): El costo asociado con la frecuencia dada.

    Returns:
    - float or str: El costo anual calculado o "-" si el costo no puede ser calculado.
    """
    if pd.notna(frec) and pd.notna(costo) and frec != "-" and costo != "-":
        if frec == 'Mensual':
            return round((costo * 12), 1)
        elif frec == 'Trimestral':
            return round((costo * 4), 1)
        elif frec == 'Anual' or 'Otro' in frec:
            return round(costo, 1)
    return "-"


# Determinar el mantenimiento del sistema
def determinar_estado_fila(row):
    valores = row[1:]  # Ignoramos la primera columna y tomamos desde la segunda hasta el final
    if all(pd.isnull(value) for value in valores):
        return '-'
    elif all(value == 'Si' for value in valores if pd.notnull(value)):
        return 'Si'
    elif all(value == 'No' for value in valores if pd.notnull(value)):
        return 'No'
    else:
        return 'Parcial'

# Calcular años de antiguedad de los componentes del sistema            
def calcular_anios(x):
    # Verifica si x no es nulo, si es una cadena no vacía o no es un guion, y si es un número (ya sea entero o flotante)
    if pd.notnull(x) and (((isinstance(x, int)) or (isinstance(x, str) and x.strip() != '' and x.strip() != '-')) or isinstance(x, (float))):
        try:
            # Convierte x a entero y calcula la diferencia de años
            year = int(x)
            anio_actual = datetime.now().year
            return str(anio_actual - year) + ' años'
        except ValueError:
            return '-'
    else:
        return '-'       

# Determinar estado operativo del sistema de agua            
def set_eoagua(group):
    if (group['estadooperativo'] == 'Opera normal').all():
        return 'Opera normal'
    elif (group['estadooperativo'] == 'Inoperativo').all():
        return 'Inoperativo'
    else:
        return 'Opera limitado'    

# Determinar estado operativo del sistema de alcantarillado
def evaluar_valores(valores):
    # Excluir los valores "-" y "No cuenta" de la evaluación
    valores_sin_no_cuenta = [valor for valor in valores if valor not in ["-", "No cuenta"]]
    
    if all(pd.isnull(valor) for valor in valores_sin_no_cuenta):
        return "-"
    elif all(valor == "Opera normal" for valor in valores_sin_no_cuenta if pd.notnull(valor)):
        return "Opera normal"
    elif all(valor == "Inoperativo" for valor in valores_sin_no_cuenta if pd.notnull(valor)):
        return "Inoperativo"
    else:
        return "Opera limitado"
        
# Funcion para generar informe            
def generarInforme(codigo,df_prestador,inei_2017,df_ps,df_fuente,df_sistema_agua,df_captacion,df_conduccion,df_reservorio,df_ptap,df_sistema_alca,df_ptar,df_disposicionfinal,df_ubs,df_usuario,doc,ruta_fotos):
    df_prueba = df_prestador.loc[df_prestador['codigodeprestador']==codigo]
    inei_2017['ubigeo_ccpp'] = inei_2017['ubigeo_ccpp'].astype(str)
    df_prueba = pd.merge(df_prueba,inei_2017,left_on='centropoblado',right_on='ubigeo_ccpp',how='inner')
    df_prueba = pd.merge(df_prueba, df_ps.groupby("codigodeprestador").agg({'p022_conexionesdeaguaactivas':'sum',
                                                                            'p024_conexionesdealcantarilladoactivas':'sum'}).reset_index(), on="codigodeprestador", how="left")
    df_ps_prueba = pd.merge(df_prueba[['codigodeprestador']],df_ps,on='codigodeprestador',how='inner')
    df_ps_prueba = pd.merge(df_ps_prueba,inei_2017,left_on='centropoblado',right_on='ubigeo_ccpp',how='inner')

    # Calculando indicadores de cobertura
    df_ps_prueba['cobagua'] = round((df_ps_prueba['p021_conexionesdeaguatotales']*df_ps_prueba['densidad_pob'] / df_ps_prueba['POBTOTAL'])*100,1)
    df_ps_prueba['cobalca'] = round((df_ps_prueba['p023_conexionesdealcantarilladototales']*df_ps_prueba['densidad_pob'] / df_ps_prueba['POBTOTAL'])*100,1)

    df_ps_prueba['cobagua'] = df_ps_prueba['cobagua'].apply(lambda x: min(x,100.0))
    df_ps_prueba['cobalca'] = df_ps_prueba['cobalca'].apply(lambda x: min(x,100.0))

    # Tabla de fuente y prestador
    df_fuente_prueba = pd.merge(df_prueba[['codigodeprestador']],df_fuente,on='codigodeprestador',how='inner')

    ############################## Datos Generales ##############################
    #############################################################################
    oficina_desconcentrada = df_prueba['p001_oficinadesconcentrada'].values[0]
    ods = '-'
    if oficina_desconcentrada == 'SEDE CENTRAL':
        ods = 'DAP-UFDMS'
    elif oficina_desconcentrada == 'ANCASH - HUARAZ':
        ods = 'ODS-HUR'
    elif oficina_desconcentrada == 'ANCASH - CHIMBOTE':
        ods = 'ODS-CHI'
    elif oficina_desconcentrada == 'LA LIBERTAD':
        ods = 'ODS-LLI'
    elif oficina_desconcentrada == 'MADRE DE DIOS':
        ods = 'ODS-MDD'
    elif oficina_desconcentrada == 'HUÁNUCO':
        ods = 'ODS-HUN'
    else:
        ods = 'ODS-' + oficina_desconcentrada[:3]
    ambito_ccpp_p = df_prueba['ambito_ccpp'].values[0]
    ubigeo_ccpp_p = df_prueba['ubigeo_ccpp'].values[0]
    pobtotal_ccpp_p = df_prueba['POBTOTAL'].values[0]
    vivtotal_ccpp_p = df_prueba['VIVTOTAL'].values[0]
    nombres_nuevos_abastecimiento = {
        "p009_pozospropios": "Pozos propios","p009_camioncisterna":"Camión cisterna","p009_acarreo":"Acarreo","p009_otro":"Otro"
    }
    lista_abastecimiento= [f"{nombres_nuevos_abastecimiento[doc]}" for doc in df_prueba[["p009_pozospropios","p009_camioncisterna","p009_acarreo","p009_otro"]] if df_prueba.iloc[0][doc] == "Si"]
    if lista_abastecimiento:    
        if ("Otro" in lista_abastecimiento):
            otra_abastecimiento = df_prueba.iloc[0]["p009a_comoseabasteceotro"]
            abastecimiento_sp  = ", ".join([institucion for institucion in lista_abastecimiento])
            abastecimiento_sp += f" - {otra_abastecimiento}"
        else:
            abastecimiento_sp = ", ".join([institucion for institucion in lista_abastecimiento])
    else:
        abastecimiento_sp='-'
    gasto_sp = "-" if pd.isnull(df_prueba['p010_gastomensualpromedioporfamiliaagua'].values[0]) else df_prueba['p010_gastomensualpromedioporfamiliaagua'].values[0]
    #anio = df_prueba['p002_fechadecaracterizacion'].str[:4].values[0]
    # df_prueba['p002_fechadecaracterizacion'] = pd.to_datetime(df_prueba['p002_fechadecaracterizacion'], origin='1970-01-01',unit='D')
    anio = df_prueba['p002_fechadecaracterizacion'].dt.year.values[0]
    #fecha_caracterizacion = format_date(datetime.strptime(df_prueba['p002_fechadecaracterizacion'].values[0], "%d/%m/%Y"), format="d 'de' MMMM 'del' yyyy", locale='es')
    fecha_caracterizacion = format_date(df_prueba['p002_fechadecaracterizacion'].astype('O')[0], format="d 'de' MMMM 'del' yyyy", locale='es')
    es_prestador = df_prueba['existeprestadordessenelccppprincipal'].values[0]
    nomprest = df_prueba['p016_nombredelprestador'].values[0]
    ccpp_p = df_prueba['p005_nombredelcentropobladoprincipal'].values[0].title()
    dist_p = df_prueba['NOMDIST'].values[0].title()
    prov_p = df_prueba['NOMPROV'].values[0].title()
    dep_p = df_prueba['NOMDEP'].values[0].title()
    nom_representante = '-' if pd.isna(df_prueba['p008a_nombreyapellido'].values[0]) else df_prueba['p008a_nombreyapellido'].values[0].title()
    cargo_representante = '-' if pd.isna(df_prueba['p008b_cargo'].values[0]) else df_prueba['p008b_cargo'].values[0].lower()
    ambito_prestador = df_prueba['p019_ambitodeprestador'].values[0]
    tipo_prestador = df_prueba['p031_quetipodeprestadores'].values[0]
    subtipo_prestador = '-' if pd.isna(df_prueba['p031B01_formaasociativadeoc'].values[0]) else df_prueba['p031B01_formaasociativadeoc'].values[0]
    agua = df_prueba['p018_agua'].values[0]
    alca = df_prueba['p018_alcantarillado'].values[0]
    tar = df_prueba['p018_tar'].values[0]
    excretas = df_prueba['p018_disposicionexcretas'].values[0]
    texto_asunto = f'Informe de caracterización del prestador {nomprest}, del centro poblado de {ccpp_p}, distrito de {dist_p}, provincia de {prov_p}, departamento de {dep_p}.' if es_prestador == 'Si' else f'Informe de caracterización del centro poblado {ccpp_p}, distrito de {dist_p}, provincia de {prov_p}, departamento de {dep_p}.'
    #texto_referencia = 'Caracterización de prestadores dentro del ámbito de respondabilidad y ubicados al entorno de una EPS (zona periurbana).' if df_prueba['tipo_ref'].values[0]=='tipo1' else 'Caracterización de prestadores rurales.'
    comentarios_prestador = df_prueba['comentarios'].values[0]
    comentarios_prestador = '-' if pd.isna(comentarios_prestador) else comentarios_prestador
    comentariosfuente = df_prueba['comentariosfuente'].values[0]
    comentariosfuente = '-' if pd.isna(comentariosfuente) else comentariosfuente
    # Objetivo
    texto_objetivo = f'Mostrar los principales resultados del proceso de caracterización de los servicios de agua potable y saneamiento brindados por el prestador {nomprest}.' if es_prestador=='Si' else f'Mostrar los principales resultados del proceso de caracterización en el centro poblado {ccpp_p} que cuenta con un abastecimiento sin prestador.'

    # Poblacion servida
    poblacionServida = []
    for index,row in df_ps_prueba.iterrows():
        poblacionServida.append({
            "ubigeo" : row["ubigeo_ccpp"],
            "nomccpp": row["NOMCCPP"],
            "viviendas": row["VIVTOTAL"],
            "aguaTot": "{:0.0f}".format(row["p021_conexionesdeaguatotales"]) if not math.isnan(row["p021_conexionesdeaguatotales"]) else "",        
            "aguaAct": "{:0.0f}".format(row["p022_conexionesdeaguaactivas"]) if not math.isnan(row["p022_conexionesdeaguaactivas"]) else "",
            "alcaTot": "{:0.0f}".format(row["p023_conexionesdealcantarilladototales"]) if not math.isnan(row["p023_conexionesdealcantarilladototales"]) else "",
            "alcaAct": "{:0.0f}".format(row["p024_conexionesdealcantarilladoactivas"]) if not math.isnan(row["p024_conexionesdealcantarilladoactivas"]) else "",
            "cobagua": "{:0.1f} %".format(row["cobagua"]) if not math.isnan(row["cobagua"]) else "",
            "cobalca": "{:0.1f} %".format(row["cobalca"]) if not math.isnan(row["cobalca"]) else "",
            "numUbs": "{:0.0f}".format(row["p027_cantidaddeubsenelccpp"]) if pd.notnull(row["p027_cantidaddeubsenelccpp"]) else ""
            #"numUbs": "{:0.0f}".format(row["p027_cantidaddeubsenelccpp"]) if not math.isnan(row["p027_cantidaddeubsenelccpp"]) else ""        
        })
    ############################## Analisis de dimensiones ##############################
    #############################################################################

    ######## A) Constitucion del Prestador ########
    ###############################################
    ugm_rural_1 = df_prueba['p031A01b_cuentaconordenanzamunicipal'].values[0]
    ugm_rural_1 = '-' if pd.isna(ugm_rural_1) else ugm_rural_1
    ugm_rural_2 = df_prueba['p031A01c_seencuentradentrodeestructuraorganicayrof'].values[0]
    ugm_rural_2 = '-' if pd.isna(ugm_rural_2) else ugm_rural_2
    ugm_pc_1 = df_prueba['p031A01d_anodecreaciondeugmantesde2017'].values[0]
    ugm_pc_1 = '-' if pd.isna(ugm_pc_1) else ugm_pc_1
    ugm_pc_2 = df_prueba['p031A01e_autorizacionsunassprestacionexcepcional'].values[0]
    ugm_pc_2 = '-' if pd.isna(ugm_pc_2) else ugm_pc_2
    oc_1 = df_prueba['p031B02e_laoccuentaconreconocimientodelamuni'].values[0]
    oc_1 = '-' if pd.isna(oc_1) else oc_1
    oc_2 = df_prueba['p031B02f_resolucionmunicipaldereconocimientodelaoc'].values[0]
    oc_2 = '-' if pd.isna(oc_2) else oc_2
    oe_1 = df_prueba['p031C01_fueconstituidosegunlalgdesociedades'].values[0]
    oe_1 = '-' if pd.isna(oe_1) else oe_1
    oe_2 = df_prueba['p031C02_tienecontratosuscritoconlamunicipalidad'].values[0]
    oe_2 = '-' if pd.isna(oe_2) else oe_2

    es_formal_lab = '-'
    if (tipo_prestador == 'Prestación Directa del Servicio - UGM' and ambito_prestador == 'Rural'):
        if(ugm_rural_1=='Si' and ugm_rural_2=='Si'):
            es_formal_lab = 'Si'
        if(ugm_rural_1=='No' or ugm_rural_2=='No'):
            es_formal_lab = 'No'
    elif tipo_prestador == 'Prestación Directa del Servicio - UGM' and ambito_prestador == 'Pequeña Ciudad':
        if(ugm_rural_2=='Si' and ugm_pc_1=='Si' and ugm_pc_2=='Si'):
            es_formal_lab = 'Si'
        if(ugm_rural_2=='No' or ugm_pc_1=='No' or ugm_pc_2=='No'):
            es_formal_lab = 'No' 
    elif tipo_prestador == 'Prestación Indirecta del Servicio - Organización Comunal':
        if(oc_1=='Si' and oc_2=='Si'):
            es_formal_lab = 'Si'
        if(oc_1=='No' or oc_2=='No'):
            es_formal_lab = 'No'
    elif tipo_prestador == 'Prestación Indirecta del Servicio - Operador Especializado':
        if(oe_1=='Si' and oe_2=='Si'):
            es_formal_lab = 'Si'
        if(oe_1=='No' or oe_2=='No'):
            es_formal_lab = 'No'
    elif tipo_prestador == 'Prestación Directa del Servicio - Prestador Municipal':
        if(ugm_rural_2 == 'Si'):
            es_formal_lab = 'Si'
        elif(ugm_rural_2 == 'No'):
            es_formal_lab = 'No'



    ######## B) Capacitacion y asistencia técnica ########
    ######################################################
    recibio_asistencia = df_prueba['p032_recibioasistenciatecnicaenlosultimos3anos'].values[0]
    if pd.isna(recibio_asistencia): recibio_asistencia = '-'
    recibio_asistencia_lab = ' '.join([recibio_asistencia,"cuenta"]) if recibio_asistencia!='-' else '-'
    nombres_nuevos_institucion = {
        "p033_atm": "ATM","p033_municipalidad":"Municipalidad","p033_mvcs":"MVCS","p033_cac":"CAC","p033_pnsr":"PNSR","p033_pnsu":"PNSU",
        "p033_drvcs":"DRVCS","p033_sunass":"SUNASS","p033_otro":"Otro","p033_otass":"OTASS"
    }
    nombres_nuevos_temas = {
        "p034_oym":"OyM", "p034_controldecalidad":"Control de calidad","p034_adquisiciondeequiposeinsumos":"Adquisicion de equipos e insumos",
        "p034_gestiondelosservicios":"Gestión de los servicios","p034_cuotafamiliar":"Cuota familiar","p034_otro":"Otro","p034_grd":"Gestión de riesgo de desastre",
        "p034_integracion":"Integración"
    }
    instituciones_asistencia_tecnica = [f"{nombres_nuevos_institucion[doc]}" for doc in df_prueba[["p033_atm","p033_municipalidad","p033_mvcs","p033_cac",
                                                "p033_pnsr","p033_pnsu","p033_drvcs","p033_sunass","p033_otro","p033_otass"]] if df_prueba.iloc[0][doc] == "Si"]
    temas_asistencia_tecnica = [f"{nombres_nuevos_temas[doc]}" for doc in df_prueba[["p034_oym","p034_controldecalidad",
                                                "p034_adquisiciondeequiposeinsumos","p034_gestiondelosservicios",
                                                "p034_cuotafamiliar","p034_otro","p034_grd","p034_integracion"]] if df_prueba.iloc[0][doc] == "Si"]
    if recibio_asistencia == "Si":
        if ("Otro" in instituciones_asistencia_tecnica):
            otra_asistencia = df_prueba.iloc[0]["p033a_otroasistenciatecnica"]
            actor_asistencia  = ", ".join([institucion for institucion in instituciones_asistencia_tecnica])
            actor_asistencia += f" - {otra_asistencia}"
        else:
            actor_asistencia = ", ".join([institucion for institucion in instituciones_asistencia_tecnica])
        if ("Otro" in temas_asistencia_tecnica):
            otro_tema_asistencia = df_prueba.iloc[0]["p034a_otrotemaasistencia"]
            tema_asistencia  =  ", ".join([asistencia for asistencia in temas_asistencia_tecnica])
            tema_asistencia  += f" - {otro_tema_asistencia}"
        else:
            tema_asistencia  =  ", ".join([asistencia for asistencia in temas_asistencia_tecnica])
    else:
        actor_asistencia = "-"
        tema_asistencia = "-"
        
    ######## C) Capacidad financiera, gestión y cobro ########
    ##########################################################
    cobra_cuota = df_prueba['p035_cobracuota'].values[0]
    cobraporcadaservicio = df_prueba['cobraporcadaservicio'].values[0]
    elcobroquerealizaes = df_prueba['elcobroquerealizaes'].values[0]
    elpagoestructuradodependedelamicromedicion = df_prueba['elpagoestructuradodependedelamicromedicion'].values[0]
    conex_act = df_prueba['p022_conexionesdeaguaactivas'].values[0]
    conex_act = "-" if pd.isna(conex_act) else int(round(conex_act,0))
    conex_act_alca = df_prueba['p024_conexionesdealcantarilladoactivas'].values[0]
    conex_act_alca = "-" if pd.isna(conex_act_alca) else int(round(conex_act_alca,0))
    # C.1) Cuota asignada (monto fijo)
    monto_cuota = df_prueba['p040_acuantoasciendeelcobroquerealiza'].values[0]
    # C.1) Cuota asignada (cobro independiente)
    monto_agua = df_prueba['acuantoasciendeelcobroquerealizaagua'].values[0]
    if pd.isna(monto_agua): monto_agua = "-"
    monto_alca = df_prueba['acuantoasciendeelcobroquerealizaalcantari'].values[0]
    if pd.isna(monto_alca): monto_alca = "-"
    monto_de = df_prueba['acuantoasciendeelcobroquerealizadisposici'].values[0]
    if pd.isna(monto_de): monto_de = "-"
    monto_tar = df_prueba['acuantoasciendeelcobroquerealizatratamien'].values[0]
    if pd.isna(monto_tar): monto_tar = "-"
    # C.1) Cuota diferenciada sin micromedicion (cobro unico)
    cx_domestico = df_prueba['conexionesdomestico'].values[0]
    cx_domestico = "-" if pd.isna(cx_domestico) else int(round(cx_domestico,0))
    cx_comercial = df_prueba['conexionescomercial'].values[0]
    cx_comercial = "-" if pd.isna(cx_comercial) else int(round(cx_comercial,0))
    cx_industrial = df_prueba['conexionesindustrial'].values[0]
    cx_industrial = "-" if pd.isna(cx_industrial) else int(round(cx_industrial,0))
    cx_social = df_prueba['conexionessocial'].values[0]
    cx_social = "-" if pd.isna(cx_social) else int(round(cx_social,0))
    agua_dom = df_prueba['montodomesticoagua'].values[0]
    if pd.isna(agua_dom): agua_dom = "-"
    agua_com = df_prueba['montocomercialagua'].values[0]
    if pd.isna(agua_com): agua_com = "-"
    agua_indus = df_prueba['montoindustrialagua'].values[0]
    if pd.isna(agua_indus): agua_indus = "-"
    agua_social = df_prueba['montosocialagua'].values[0]
    if pd.isna(agua_social): agua_social = "-"
    # C.1) Cuota diferenciada sin micromedicion (cobro independiente)
    alca_dom = df_prueba['montodomesticoalcantarillado'].values[0]
    if pd.isna(alca_dom): alca_dom = "-"
    alca_com = df_prueba['montocomercialalcantarillado'].values[0]
    if pd.isna(alca_com): alca_com = "-"
    alca_indus = df_prueba['montoindustrialalcantarillado'].values[0]
    if pd.isna(alca_indus): alca_indus = "-"
    alca_social = df_prueba['montosocialalcantarillado'].values[0]
    if pd.isna(alca_social): alca_social = "-"
    otro_dom = df_prueba['montodomesticootro'].values[0]
    if pd.isna(otro_dom): otro_dom = "-"
    otro_com = df_prueba['montocomercialotro'].values[0]
    if pd.isna(otro_com): otro_com = "-"
    otro_indus = df_prueba['montoindustrialotro'].values[0]
    if pd.isna(otro_indus): otro_indus = "-"
    otro_social = df_prueba['montosocialotro'].values[0]
    if pd.isna(otro_social): otro_social = "-"
    # C.1) Cuota diferenciada con micromedicion 
    #Domestico
    d_sol1 = df_prueba['domesticorango1solesm3'].values[0]
    if pd.isna(d_sol1): d_sol1 = "-"
    d_de1 = df_prueba['domesticorango1v3de'].values[0]
    if pd.isna(d_de1): d_de1 = "-"
    d_hasta1 = df_prueba['domesticorango1v3a'].values[0]
    if pd.isna(d_hasta1): d_hasta1 = "-"
    d_sol2 = df_prueba['domesticorango2solesm3'].values[0]
    if pd.isna(d_sol2): d_sol2 = "-"
    d_de2 = df_prueba['domesticorango2v3de'].values[0]
    if pd.isna(d_de2): d_de2 = "-"
    d_hasta2 = df_prueba['domesticorango2v3a'].values[0]
    if pd.isna(d_hasta2): d_hasta2 = "-"
    #Comercial
    c_sol1 = df_prueba['comercialrango1solesm3'].values[0]
    if pd.isna(c_sol1): c_sol1 = "-"
    c_de1 = df_prueba['comercialrango1v3de'].values[0]
    if pd.isna(c_de1): c_de1 = "-"
    c_hasta1 = df_prueba['comercialrango1v3a'].values[0]
    if pd.isna(c_hasta1): c_hasta1 = "-"
    c_sol2 = df_prueba['comercialrango2solesm3'].values[0]
    if pd.isna(c_sol2): c_sol2 = "-"
    c_de2 = df_prueba['comercialrango2v3de'].values[0]
    if pd.isna(c_de2): c_de2 = "-"
    c_hasta2 = df_prueba['comercialrango2v3a'].values[0]
    if pd.isna(c_hasta2): c_hasta2 = "-"
    #Industrial
    i_sol1 = df_prueba['industrialrango1solesm3'].values[0]
    if pd.isna(i_sol1): i_sol1 = "-"
    i_de1 = df_prueba['industrialrango1v3de'].values[0]
    if pd.isna(i_de1): i_de1 = "-"
    i_hasta1 = df_prueba['industrialrango1v3a'].values[0]
    if pd.isna(i_hasta1): i_hasta1 = "-"
    i_sol2 = df_prueba['industrialrango2solesm3'].values[0]
    if pd.isna(i_sol2): i_sol2 = "-"
    i_de2 = df_prueba['industrialrango2v3de'].values[0]
    if pd.isna(i_de2): i_de2 = "-"
    i_hasta2 = df_prueba['industrialrango2v3a'].values[0]
    if pd.isna(i_hasta2): i_hasta2 = "-"
    #Social
    s_sol1 = df_prueba['socialrango1solesm3'].values[0]
    if pd.isna(s_sol1): s_sol1 = "-"
    s_de1 = df_prueba['socialrango1v3de'].values[0]
    if pd.isna(s_de1): s_de1 = "-"
    s_hasta1 = df_prueba['socialrango1v3a'].values[0]
    if pd.isna(s_hasta1): s_hasta1 = "-"
    s_sol2 = df_prueba['socialrango2solesm3'].values[0]
    if pd.isna(s_sol2): s_sol2 = "-"
    s_de2 = df_prueba['socialrango2v3de'].values[0]
    if pd.isna(s_de2): s_de2 = "-"
    s_hasta2 = df_prueba['socialrango2v3a'].values[0]
    if pd.isna(s_hasta2): s_hasta2 = "-"

    # ¿La cuota cubre los costos?
    cuota_cubre = df_prueba['p059_lacuotacubrecostosdeoaym'].values[0]
    cuota_cubre_lab = 'Superávit' if cuota_cubre == 'Si' else 'Déficit' if cuota_cubre == 'No' else '-'

    frecuencia_cobro = metodologia_oc = antiguedad_cuota = flujo_cuota = conex_morosidad = conex_exoner = "-"
    if cobra_cuota == "Si":
        frecuencia_cobro = df_prueba['p037_frecuenciadecobros'].values[0]
        if frecuencia_cobro == "Otro":
            frecuencia_cobro = df_prueba['p037a_frecuenciadecobrootro'].values[0]
        if tipo_prestador == "Prestación Indirecta del Servicio - Organización Comunal":
            metodologia_oc = '-' if pd.isna(df_prueba['p039_laocaplicalametodologiadecuotafamiliar'].values[0]) else df_prueba['p039_laocaplicalametodologiadecuotafamiliar'].values[0]
        antiguedad_cuota = df_prueba['p036_antiguedaddelatarifacuotaactual'].values[0]
        if pd.notna(df_prueba['cobraporcadaservicio'].values[0]):
             flujo_cuota = df_prueba['cobraporcadaservicio'].values[0]
        else:
            flujo_cuota = "-"
        #if pd.isna(df_prueba['elpagoestructuradodependedelamicromedicion'].values[0]):
        #    if pd.notna(df_prueba['cobraporcadaservicio'].values[0]) and pd.notna(df_prueba['elcobroquerealizaes'].values[0]):
        #        flujo_cuota = "-" + df_prueba['cobraporcadaservicio'].values[0] + "\n" + "-" + df_prueba['elcobroquerealizaes'].values[0]
        #    else:
        #        flujo_cuota = "-"
        #else:
        #    if pd.notna(df_prueba['cobraporcadaservicio'].values[0]) and pd.notna(df_prueba['elcobroquerealizaes'].values[0]) and pd.notna(df_prueba['elpagoestructuradodependedelamicromedicion'].values[0]):
        #        flujo_cuota = df_prueba['cobraporcadaservicio'].values[0] + ", " + df_prueba['elcobroquerealizaes'].values[0] + ", " + df_prueba['elpagoestructuradodependedelamicromedicion'].values[0]
        #    else:
        #        flujo_cuota = "-"
    # C3) Morosidad
        conex_morosidad = df_prueba['p046_numerodeusuariosmorosos'].values[0]
        conex_morosidad = "-" if pd.isna(conex_morosidad) else int(round(conex_morosidad,0))
        conex_exoner = df_prueba['p047_numerodeusuariosexonerados'].values[0]
        conex_exoner = "-" if pd.isna(conex_exoner) else int(round(conex_exoner,0))

    # C2) Cobro de servicios colaterales
    colateral_agua = colateral_alca = colateral_micro = colateral_repo = "-"
    if pd.notna(df_prueba['p051a_conexionesdeagua'].values[0]):
        colateral_agua = int(round(df_prueba['p051a_conexionesdeagua'].values[0],0))
    if pd.notna(df_prueba['p051d_conexiondedesague'].values[0]):
        colateral_alca = int(round(df_prueba['p051d_conexiondedesague'].values[0],0))
    if pd.notna(df_prueba['p051c_instalaciondemicromedidores'].values[0]):
        colateral_micro = int(round(df_prueba['p051c_instalaciondemicromedidores'].values[0],0))
    if pd.notna(df_prueba['p051b_reposiciondelservicio'].values[0]):
        colateral_repo = int(round(df_prueba['p051b_reposiciondelservicio'].values[0],0))
    # C4) Documentos de gestión financiera e inventarios
    g1_si = g1_no = g2_si = g2_no = g3_si = g3_no = g4_si = g4_no = g5_si = g5_no = "-"
    if (pd.notna(df_prueba['p063_elprestadortieneunregistrocontableuotro'].values[0]) and df_prueba['p063_elprestadortieneunregistrocontableuotro'].values[0]=="Si"):
        g1_si = "X"
        g1_no = ""
    if (pd.notna(df_prueba['p063_elprestadortieneunregistrocontableuotro'].values[0]) and df_prueba['p063_elprestadortieneunregistrocontableuotro'].values[0]=="No"):
        g1_si = ""
        g1_no = "X"
    if (pd.notna(df_prueba['p053_elprestadorcuentaconcuadernolibrodeinventa'].values[0]) and df_prueba['p053_elprestadorcuentaconcuadernolibrodeinventa'].values[0]=="Si"):
        g2_si = "X"
        g2_no = ""
    if (pd.notna(df_prueba['p053_elprestadorcuentaconcuadernolibrodeinventa'].values[0]) and df_prueba['p053_elprestadorcuentaconcuadernolibrodeinventa'].values[0]=="No"):
        g2_si = ""
        g2_no = "X"
    if (pd.notna(df_prueba['p062_elprestadortieneunregistrodetodoslosrecib'].values[0]) and df_prueba['p062_elprestadortieneunregistrodetodoslosrecib'].values[0]=="Si"):
        g3_si = "X"
        g3_no = ""
    if (pd.notna(df_prueba['p062_elprestadortieneunregistrodetodoslosrecib'].values[0]) and df_prueba['p062_elprestadortieneunregistrodetodoslosrecib'].values[0]=="No"):
        g3_si = ""
        g3_no = "X"
    if (pd.notna(df_prueba['p061_elprestadortieneregistrodetodoslosrecibos'].values[0]) and df_prueba['p061_elprestadortieneregistrodetodoslosrecibos'].values[0]=="Si"):
        g4_si = "X"
        g4_no = ""
    if (pd.notna(df_prueba['p061_elprestadortieneregistrodetodoslosrecibos'].values[0]) and df_prueba['p061_elprestadortieneregistrodetodoslosrecibos'].values[0]=="No"):
        g4_si = ""
        g4_no = "X"
    if (pd.notna(df_prueba['p038_emitereciboocomprobporelpagodeservicios'].values[0]) and df_prueba['p038_emitereciboocomprobporelpagodeservicios'].values[0]=="Si"):
        g5_si = "X"
        g5_no = ""
    if (pd.notna(df_prueba['p038_emitereciboocomprobporelpagodeservicios'].values[0]) and df_prueba['p038_emitereciboocomprobporelpagodeservicios'].values[0]=="No"):
        g5_si = ""
        g5_no = "X"
    # C5) Costos para la prestación del servicio
    op = op1 = op2 = op3 = m = adm = re = rm = op1_frec = op2_frec = op3_frec = m_frec = adm_frec = re_frec = rm_frec = op1_costo = op2_costo = op3_costo = m_costo = adm_costo = re_costo = rm_costo = "-"
    op1_anual = op2_anual = op3_anual = m_anual = adm_anual = re_anual = rm_anual = "-"
    #Operacion
    op = df_prueba['p058a_tienecostosdeoperacion'].values[0]
    op = "-" if pd.isna(op) else op
    #Energia electrica
    op1 = df_prueba['p058a1_tieneenergiaelectrica'].values[0]
    if (df_prueba['p058a1a_periodoenergiaelectrica'].values[0]=='Otro' and pd.notna(df_prueba['p058a1b_periodoenergiaotro'].values[0])):
        op1_frec = ', '.join([df_prueba['p058a1a_periodoenergiaelectrica'].values[0],df_prueba['p058a1b_periodoenergiaotro'].values[0]])
    else:
        op1_frec = df_prueba['p058a1a_periodoenergiaelectrica'].values[0]
    op1_costo = df_prueba['p058a1c_costototaldeenergiaelectrica'].values[0]
    op1 = "-" if pd.isna(op1) else op1
    op1_frec = "-" if pd.isna(op1_frec) else op1_frec
    op1_costo = "-" if pd.isna(op1_costo) else round(op1_costo,1)
    #Insumos quimicos
    op2 = df_prueba['p058a2_tienecostosdeinsumosquimicos'].values[0]
    if (df_prueba['p058a2a_periodoinsumosquimicos'].values[0]=='Otro' and pd.notna(df_prueba['p058a2b_periodoinsumosquimicosotro'].values[0])):
        op2_frec = ', '.join([df_prueba['p058a2a_periodoinsumosquimicos'].values[0],df_prueba['p058a2b_periodoinsumosquimicosotro'].values[0]])
    else:
        op2_frec = df_prueba['p058a2a_periodoinsumosquimicos'].values[0]
    op2_costo = df_prueba['p058a2c_costototaldeinsumosquimicos'].values[0]
    op2 = "-" if pd.isna(op2) else op2
    op2_frec = "-" if pd.isna(op2_frec) else op2_frec
    op2_costo = "-" if pd.isna(op2_costo) else round(op2_costo,1)
    #Personal
    op3 = df_prueba['p058a3_tienecostosdepersonal'].values[0]
    if (df_prueba['p058a3a_periodopersonal'].values[0]=='Otro' and pd.notna(df_prueba['p058a3b_periodopersonalotro'].values[0])):
        op3_frec = ', '.join([df_prueba['p058a3a_periodopersonal'].values[0],df_prueba['p058a3b_periodopersonalotro'].values[0]])
    else:
        op3_frec = df_prueba['p058a3a_periodopersonal'].values[0]
    op3_costo = df_prueba['p058a3c_costototaldepersonal'].values[0]
    op3 = "-" if pd.isna(op3) else op3
    op3_frec = "-" if pd.isna(op3_frec) else op3_frec
    op3_costo = "-" if pd.isna(op3_costo) else round(op3_costo,1)
    #Mantenimiento
    m = df_prueba['p058b_tienecostosdemantenimiento'].values[0]
    if (df_prueba['p058b1_periodomantenimiento'].values[0]=='Otro' and pd.notna(df_prueba['p058b2_periodomantenimientootro'].values[0])):
        m_frec = ', '.join([df_prueba['p058b1_periodomantenimiento'].values[0],df_prueba['p058b2_periodomantenimientootro'].values[0]])
    else:
        m_frec = df_prueba['p058b1_periodomantenimiento'].values[0]
    m_costo = df_prueba['p058b3_costostotalenmantenimientosmensual'].values[0]
    m = "-" if pd.isna(m) else m
    m_frec = "-" if pd.isna(m_frec) else m_frec
    m_costo = "-" if pd.isna(m_costo) else round(m_costo,1)
    #Administracion
    adm = df_prueba['p058c_tienecostosdeadministracion'].values[0]
    if (df_prueba['p058c1_periodoadministracion'].values[0]=='Otro' and pd.notna(df_prueba['p058c2_periodoadministracionotro'].values[0])):
        adm_frec = ', '.join([df_prueba['p058c1_periodoadministracion'].values[0],df_prueba['p058c2_periodoadministracionotro'].values[0]])
    else:
        adm_frec = df_prueba['p058c1_periodoadministracion'].values[0]
    adm_costo = df_prueba['p058c3_costostotalenadministracionsmensual'].values[0]
    adm = "-" if pd.isna(adm) else adm
    adm_frec = "-" if pd.isna(adm_frec) else adm_frec
    adm_costo = "-" if pd.isna(adm_costo) else round(adm_costo,1)
    #Reposicion de equipos
    re = df_prueba['p058d_tienecostosdereposiciondeequipos'].values[0]
    if (df_prueba['p058d1_periodoreposiciondeequipos'].values[0]=='Otro' and pd.notna(df_prueba['p058d2_periodoreposiciondeequiposotro'].values[0])):
        re_frec = ', '.join([df_prueba['p058d1_periodoreposiciondeequipos'].values[0],df_prueba['p058d2_periodoreposiciondeequiposotro'].values[0]])
    else:
        re_frec = df_prueba['p058d1_periodoreposiciondeequipos'].values[0]
    re_costo = df_prueba['p058d3_costototaldereposicionsmensual'].values[0]
    re = "-" if pd.isna(re) else re
    re_frec = "-" if pd.isna(re_frec) else re_frec
    re_costo = "-" if pd.isna(re_costo) else round(re_costo,1)
    #Rehabilitaciones menores
    rm = df_prueba['p058e_tienecostosderehabilitacionesmenores'].values[0]
    if (df_prueba['p058e1_periodorehabilitacionesmenores'].values[0]=='Otro' and pd.notna(df_prueba['p058e2_periodorehabilitacionesmenoresotro'].values[0])):
        rm_frec = ', '.join([df_prueba['p058e1_periodorehabilitacionesmenores'].values[0],df_prueba['p058e2_periodorehabilitacionesmenoresotro'].values[0]])
    else:
        rm_frec = df_prueba['p058e1_periodorehabilitacionesmenores'].values[0]
    rm_costo = df_prueba['p058e3_costototalderehabilitamenoressmensual'].values[0]
    rm = "-" if pd.isna(rm) else rm
    rm_frec = "-" if pd.isna(rm_frec) else rm_frec
    rm_costo = "-" if pd.isna(rm_costo) else round(rm_costo,1)
    #Otros costos
    otro = df_prueba['p058f_tieneotroscostos'].values[0]
    if (df_prueba['p058f1_periodootroscostos'].values[0]=='Otro' and pd.notna(df_prueba['p058f2_periodootrootro'].values[0])):
        otros_frec = ' - '.join([df_prueba['p058f1_periodootroscostos'].values[0],df_prueba['p058f2_periodootrootro'].values[0]])
    else:
        otros_frec = df_prueba['p058f1_periodootroscostos'].values[0]
    otros_costo = df_prueba['p058f3_costototaldeotrosmensual'].values[0]
    otro = "-" if pd.isna(otro) else otro
    otros_frec = "-" if pd.isna(otros_frec) else otros_frec
    otros_costo = "-" if pd.isna(otros_costo) else round(otros_costo,1)
    
    #Costos anuales
    
    op1_anual = calcular_op_anual(op1_frec, op1_costo)
    op2_anual = calcular_op_anual(op2_frec, op2_costo)
    op3_anual = calcular_op_anual(op3_frec, op3_costo)
    m_anual = calcular_op_anual(m_frec, m_costo)
    adm_anual = calcular_op_anual(adm_frec, adm_costo)
    re_anual = calcular_op_anual(re_frec, re_costo)
    rm_anual = calcular_op_anual(rm_frec, rm_costo)
    otros_anual = calcular_op_anual(otros_frec, otros_costo)
    valores_anuales = [op1_anual,op2_anual,op3_anual,m_anual,adm_anual,re_anual,rm_anual,otros_anual]
    #costoAnual = sum(float(valor) for valor in valores_anuales if valor != "-") if any(valor != "-" for valor in valores_anuales) else "-"
    valores_numericos_costo_total = [float(valor) for valor in valores_anuales if valor != "-"]
    if valores_numericos_costo_total:
    # Calcular la suma de los valores numéricos y redondear
        costoAnual = round(sum(valores_numericos_costo_total), 1)
    else:
        # Si no hay valores numéricos, asignar "-"
        costoAnual = "-"
    #costoAnual = round(sum(float(valor) for valor in valores_anuales if valor != "-") if any(valor != "-" for valor in valores_anuales) else "-", 1)
    costoAnual_lab = "No cuenta" if costoAnual == "-" else f"S/. {costoAnual:,.0f} anual*".replace(",", " ")
    valor_ref = "" if costoAnual == "-" else f"(*) Valor referencial. Declarado por el {cargo_representante}."
    costoAnual = str(costoAnual) + "(*)" if costoAnual != "-" else costoAnual
    
    ######## D) Identificacion de peligros y amenazas ########
    ###########################################################
    peligro1_si = peligro1_no = peligro2_si = peligro2_no = peligro3_si = peligro3_no = '-'
    if (pd.notna(df_prueba['p064_cuentaconplandeemergenciauotroinstrumento'].values[0]) and df_prueba['p064_cuentaconplandeemergenciauotroinstrumento'].values[0]=="Si"):
        peligro1_si = "X"
        peligro1_no = ""
    if (pd.notna(df_prueba['p064_cuentaconplandeemergenciauotroinstrumento'].values[0]) and df_prueba['p064_cuentaconplandeemergenciauotroinstrumento'].values[0]=="No"):
        peligro1_si = ""
        peligro1_no = "X"
    if (df_prueba['p065_ninguno'].values[0]=="Si"):
        peligro2_si = ""
        peligro2_no = "X"
    else:
        peligro2_si = "X"
        peligro2_no = "" 
    if (pd.notna(df_prueba['p067_cuentaconcuadrillacomitebrigadapararespuest'].values[0]) and df_prueba['p067_cuentaconcuadrillacomitebrigadapararespuest'].values[0]=="Si"):
        peligro3_si = "X"
        peligro3_no = ""
    if (pd.notna(df_prueba['p067_cuentaconcuadrillacomitebrigadapararespuest'].values[0]) and df_prueba['p067_cuentaconcuadrillacomitebrigadapararespuest'].values[0]=="No"):
        peligro3_si = ""
        peligro3_no = "X"


    ######## 5.2) Disponibilidad del recurso hídrico ########
    ########################################################
    fuentes = []
    for index,row in df_fuente_prueba.iterrows():
        fuentes.append({
            "nomfuente" : row["nombredelafuente"],
            "tipofuente": row["tipodefuentedeagua"],
            'subtipofuente': row['subtipodefuentedeaguasubterranea'] if row['tipodefuentedeagua'] == 'Subterránea' else row['subtipodefuentedeaguasuperficial'] if row['tipodefuentedeagua'] == 'Superficial' else 'Pluvial' if row['tipodefuentedeagua'] == 'Pluvial' else '-',
            'licenciauso': row['cuentaconlicenciauso']  
        })

    contador_licencias = {"Si": 0, "No": 0}

    # Itera sobre cada fuente para contar las respuestas de licencia de uso
    for fuente in fuentes:
        licencia = fuente['licenciauso']
        if licencia in contador_licencias:
            contador_licencias[licencia] += 1

    # Determina el valor final basado en los contadores
    if len(fuentes) == 1:
        if contador_licencias["Si"] == 1:
            licenciauso_lab = "Si tiene"
        elif contador_licencias["Si"] == 0:
            licenciauso_lab = "No tiene"
    elif len(fuentes) > 1:
        if contador_licencias["Si"] > 0 and contador_licencias["No"] == 0:
            licenciauso_lab = "Si"
        elif contador_licencias["No"] > 0 and contador_licencias["Si"] == 0:
            licenciauso_lab = "No"
        elif contador_licencias["No"] > 0 and contador_licencias["Si"] > 0:
            licenciauso_lab = "Sólo algunas tienen"
        else:
            licenciauso_lab = "-"
    else:
        licenciauso_lab = "-"


    # Otros usos que se le da a la fuente
    nombres_nuevos_infra1 = {
        "p005_agriculturariego": "Agricultura (Riego)","p005_industrial":"Industrial","p005_prestadoresdess":"Prestadores de servicios","p005_mineria":"Minería","p005_otro":"Otro"
    }
    lista_infra1= [f"{nombres_nuevos_infra1[doc]}" for doc in df_prueba[["p005_agriculturariego","p005_industrial","p005_prestadoresdess","p005_mineria",
                                                "p005_otro"]] if df_prueba.iloc[0][doc] == "Si"]

    if lista_infra1:
        # Si la lista contiene datos, se establece la variable como "Si cuenta"
        texto_infra1_lab = "Si cuenta"
        # Verificar si "Otros" está en la lista
        if "Otro" in lista_infra1:
            # Si "Otros" está en la lista, se obtiene el valor de otra_infra4 y se agrega a texto_infra4
            otra_infra1 = df_prueba.iloc[0]["p005a_otrousodelafuente"]
            texto_infra1  = ", ".join([institucion for institucion in lista_infra1])
            texto_infra1 += f" - {otra_infra1}"
        else:
            # Si "Otros" no está en la lista, se utiliza texto_infra4 sin modificaciones
            texto_infra1 = ", ".join([institucion for institucion in lista_infra1])
    else:
        # Si la lista está vacía, tanto si_cuenta como texto_infra4 se establecen como "No cuenta"
        texto_infra1_lab = "No cuenta"
        texto_infra1 = "No cuenta"

    # Ecosistema que predomina en la fuente
    nombres_nuevos_infra2 = {
        "p008_bofedal": "Bofedal","p008_bosques":"Bosques","p008_pajonal":"Pajonal","p008_otro":"Otro"
    }
    lista_infra2= [f"{nombres_nuevos_infra2[doc]}" for doc in df_prueba[["p008_bofedal","p008_bosques","p008_pajonal","p008_otro"]] if df_prueba.iloc[0][doc] == "Si"]
    # if ("Otro" in lista_infra2):
    #     otra_infra2 = df_prueba.iloc[0]["p008a_otrotipodeecosistema"]
    #     texto_infra2  = ", ".join([institucion for institucion in lista_infra2])
    #     texto_infra2 += f" - {otra_infra2}"
    # else:
    #     texto_infra2 = ", ".join([institucion for institucion in lista_infra2])

    if lista_infra2:
        texto_infra2_lab = "Si cuenta"
        # Verificar si "Otros" está en la lista
        if "Otro" in lista_infra2:
            # Si "Otros" está en la lista, se obtiene el valor de otra_infra4 y se agrega a texto_infra4
            otra_infra2 = df_prueba.iloc[0]["p008a_otrotipodeecosistema"]
            texto_infra2  = ", ".join([institucion for institucion in lista_infra2])
            texto_infra2 += f" - {otra_infra2}"
        else:
            # Si "Otros" no está en la lista, se utiliza texto_infra4 sin modificaciones
            texto_infra2 = ", ".join([institucion for institucion in lista_infra2])
    else:
        # Si la lista está vacía, tanto si_cuenta como texto_infra4 se establecen como "No cuenta"
        texto_infra2_lab = "No cuenta"
        texto_infra2 = "No cuenta"

    # Problemas que afectan a la fuente de agua
    nombres_nuevos_infra3 = {
        "p014_ninguno": "Ninguno","p014_disminucion":"Disminución de agua (caudal) en época de estiaje","p014_aumento":"Aumento de turbidez (sedimentos)","p014_contaminacion":"Presencia de contaminantes en el agua",
        "p014_otros":"Otros"
    }
    
    lista_infra3= [f"{nombres_nuevos_infra3[doc]}" for doc in df_prueba[["p014_ninguno","p014_disminucion","p014_aumento","p014_contaminacion","p014_otros"]] if df_prueba.iloc[0][doc] == "Si"]
    if lista_infra3:
        # Si la lista contiene datos, se establece la variable como "Si cuenta"
        texto_infra3_lab = "Si cuenta"
        # Verificar si "Otros" está en la lista
        if "Otros" in lista_infra3:
            # Si "Otros" está en la lista, se obtiene el valor de otra_infra4 y se agrega a texto_infra4
            otra_infra3 = df_prueba.iloc[0]["p014a_problemasidentificadosotro"]
            texto_infra3  = ", ".join([institucion for institucion in lista_infra3])
            texto_infra3 += f" - {otra_infra3}"
        else:
            # Si "Otros" no está en la lista, se utiliza texto_infra4 sin modificaciones
            texto_infra3 = ", ".join([institucion for institucion in lista_infra3])
    else:
        # Si la lista está vacía, tanto si_cuenta como texto_infra4 se establecen como "No cuenta"
        texto_infra3_lab = "No cuenta"
        texto_infra3 = "No cuenta"

    # Actividades que pueden afectar a la fuente
    nombres_nuevos_infra4 = {
        "p015_agricultura": "Agricultura","p015_basuradomestica":"Basura doméstica","p015_mineria":"Minería","p015_deforestacion":"Deforestación",
        "p015_sobrepastoreo":"Sobrepastoreo","p015_ninguno":"Ninguno", 'p015_otros':"Otros"
    }
    lista_infra4= [f"{nombres_nuevos_infra4[doc]}" for doc in df_prueba[["p015_agricultura","p015_basuradomestica","p015_mineria","p015_deforestacion","p015_sobrepastoreo","p015_ninguno","p015_otros"]] if df_prueba.iloc[0][doc] == "Si"]
    # if ("Otros" in lista_infra4):
    #     otra_infra4 = df_prueba.iloc[0]["p015a_otraactividadambitofuenteagua"]
    #     texto_infra4  = ", ".join([institucion for institucion in lista_infra4])
    #     texto_infra4 += f" - {otra_infra4}"
    # else:
    #     texto_infra4 = ", ".join([institucion for institucion in lista_infra4])
    
    if lista_infra4:
        # Si la lista contiene datos, se establece la variable como "Si cuenta"
        texto_infra4_lab = "Si cuenta"
        # Verificar si "Otros" está en la lista
        if "Otros" in lista_infra4:
            # Si "Otros" está en la lista, se obtiene el valor de otra_infra4 y se agrega a texto_infra4
            otra_infra4 = df_prueba.iloc[0]["p015a_otraactividadambitofuenteagua"]
            texto_infra4  = ", ".join([institucion for institucion in lista_infra4])
            texto_infra4 += f" - {otra_infra4}"
        else:
            # Si "Otros" no está en la lista, se utiliza texto_infra4 sin modificaciones
            texto_infra4 = ", ".join([institucion for institucion in lista_infra4])
    else:
        # Si la lista está vacía, tanto si_cuenta como texto_infra4 se establecen como "No cuenta"
        texto_infra4_lab = "No cuenta"
        texto_infra4 = "No cuenta"

    ######## 5.3) Agua y Saneamiento ########
    ########################################################

    df_sistema_agua_prueba = df_sistema_agua.loc[df_sistema_agua['codigodeprestador']==df_prueba['codigodeprestador'].values[0]]

    # Captacion
    df_captacion['nombredelacaptacion'] = df_captacion['nombredelacaptacion'].apply(lambda x: 'Captación ' + str(x) if not str(x).lower().count('capta') else str(x))
    df_captacion_prueba = pd.merge(df_sistema_agua_prueba[['codigodesistemadeagua']],df_captacion[[
    'codigodesistemadeagua','nombredelacaptacion','anodeconstruccion','estadooperativodelacaptacion','justifiquesurespuestacaptacion','zona','este','norte','altitud'
    ]],on='codigodesistemadeagua',how='inner').rename(columns={'nombredelacaptacion':'nombre','anodeconstruccion':'aniodeconstruccion','estadooperativodelacaptacion':'estadooperativo','justifiquesurespuestacaptacion':'descripcion'})
    df_captacion_prueba.insert(2,'cuenta',np.nan)
    if not df_captacion_prueba.empty:
        df_captacion_prueba['cuenta'] = df_captacion_prueba['cuenta'].fillna('Si')


    # Caseta y equipo de bombeo
    df_equipo_bombeo = df_sistema_agua_prueba[['codigodesistemadeagua','p016_cuentaconequipodebombeo','aniodeconstruccioncasetabombeo',
                                            'zonacasetadebombeo','estecasetedebombeo','nortecasetadebombeo','altitudcasetadebombeo']].rename(columns={'p016_cuentaconequipodebombeo':'cuenta','aniodeconstruccioncasetabombeo':'aniodeconstruccion',
                                                                                                                                                        'zonacasetadebombeo':'zona','estecasetedebombeo':'este','nortecasetadebombeo':'norte',
                                                                                                                                                        'altitudcasetadebombeo':'altitud'})
    posicion = 1
    nombre_columna = 'nombre'
    df_equipo_bombeo.insert(posicion,nombre_columna,'Caseta y equipo de bombeo')
    df_equipo_bombeo['estadooperativo'] = ''
    df_equipo_bombeo['descripcion'] = ''

    df_caseta_bombeo = df_sistema_agua_prueba[['codigodesistemadeagua','tienecasetadebombeo','estadooperativocasetadebombeo','justifiquerespuestaocasetabombeo']].rename(columns={'tienecasetadebombeo':'cuenta','estadooperativocasetadebombeo':'estadooperativo','justifiquerespuestaocasetabombeo':'descripcion'})
    posicion = 1
    nombre_columna = 'nombre'
    df_caseta_bombeo.insert(posicion,nombre_columna,'   Caseta de bombeo')
    posicion = 3
    nombre_columna = 'aniodeconstruccion'
    df_caseta_bombeo.insert(posicion,nombre_columna,'')

    df_cisterna_bombeo = df_sistema_agua_prueba[['codigodesistemadeagua','tienecisternadebombeo','estadooperativocisternadebombeo','justifiquerespuestaocisternabombeo']].rename(columns={'tienecisternadebombeo':'cuenta','estadooperativocisternadebombeo':'estadooperativo','justifiquerespuestaocisternabombeo':'descripcion'})
    posicion = 1
    nombre_columna = 'nombre'
    df_cisterna_bombeo.insert(posicion,nombre_columna,'   Cisterna de bombeo')
    posicion = 3
    nombre_columna = 'aniodeconstruccion'
    df_cisterna_bombeo.insert(posicion,nombre_columna,'')

    df_solo_equipo_bombeo = df_sistema_agua_prueba[['codigodesistemadeagua','tieneequipodebombeo','estadooperativoequipodebombeo','justifiquerespuestaoequipobombeo']].rename(columns={'tieneequipodebombeo':'cuenta','estadooperativoequipodebombeo':'estadooperativo','justifiquerespuestaoequipobombeo':'descripcion'})
    posicion = 1
    nombre_columna = 'nombre'
    df_solo_equipo_bombeo.insert(posicion,nombre_columna,'   Equipo de bombeo')
    posicion = 3
    nombre_columna = 'aniodeconstruccion'
    df_solo_equipo_bombeo.insert(posicion,nombre_columna,'')

    df_energia = df_sistema_agua_prueba[['codigodesistemadeagua','tienesistemaenergiaelectrica','estadooperativosistemaenergia','justifiquerespuestaoenergiaelectrica']].rename(columns={'tienesistemaenergiaelectrica':'cuenta','estadooperativosistemaenergia':'estadooperativo','justifiquerespuestaoenergiaelectrica':'descripcion'})
    posicion = 1
    nombre_columna = 'nombre'
    df_energia.insert(posicion,nombre_columna,'   Sistema de energía electrica')
    posicion = 3
    nombre_columna = 'aniodeconstruccion'
    df_energia.insert(posicion,nombre_columna,'')

    df_equipo_casete_bombeo = pd.concat([df_equipo_bombeo,df_caseta_bombeo,df_cisterna_bombeo,df_solo_equipo_bombeo,df_energia], ignore_index=True)
    df_equipo_casete_bombeo['zona'] = np.nan
    df_equipo_casete_bombeo['este'] = np.nan
    df_equipo_casete_bombeo['norte'] = np.nan
    df_equipo_casete_bombeo['altitud'] = np.nan

    # Linea de conduccion
    df_conduccion = df_conduccion.rename(columns={'codigodesistemaagua':'codigodesistemadeagua'})
    df_conduccion_prueba = pd.merge(df_sistema_agua_prueba[['codigodesistemadeagua']],df_conduccion[[
    'codigodesistemadeagua','anodeconstruccionconduccion','estadooperativodelconductordeaguacruda','justifiquesurespuestaconduccion'
    ]],on='codigodesistemadeagua',how='inner').rename(columns={'anodeconstruccionconduccion':'aniodeconstruccion','estadooperativodelconductordeaguacruda':'estadooperativo','justifiquesurespuestaconduccion':'descripcion'})
    df_conduccion_prueba = df_conduccion_prueba[['codigodesistemadeagua', 'aniodeconstruccion',
        'estadooperativo', 'descripcion']]

    df_conduccion_prueba.insert(1,'nombre',np.nan)
    df_conduccion_prueba.insert(2,'cuenta',np.nan)
    
    df_conduccion_prueba['zona'] = np.nan
    df_conduccion_prueba['este'] = np.nan
    df_conduccion_prueba['norte'] = np.nan
    df_conduccion_prueba['altitud'] = np.nan  
    
    if not df_conduccion_prueba.empty:
        df_conduccion_prueba['nombre'] = df_conduccion_prueba['nombre'].fillna('Línea de conducción / Impulsión')
        df_conduccion_prueba['cuenta'] = df_conduccion_prueba['cuenta'].fillna('Si')


    # PTAP
    #df_ptap = df_ptap.rename(columns={'codigodesistemaagua':'codigodesistemadeagua'})
    df_ptap_prueba_general = pd.DataFrame()
    df_ptap_prueba = pd.DataFrame()
    if not df_ptap.empty:
        df_ptap_prueba = pd.merge(df_sistema_agua_prueba[['codigodesistemadeagua']],df_ptap,on='codigodesistemadeagua',how='inner') #.head(1)
        df_ptap_prueba_general = df_ptap_prueba[['codigodesistemadeagua','anodeconstruccion','tipodeptap','zona','este','norte','altitud']].rename(columns={'anodeconstruccion':'aniodeconstruccion'})
        df_ptap_prueba_general.insert(1,'nombre',np.nan)
        df_ptap_prueba_general.insert(2,'cuenta',np.nan)
        df_ptap_prueba_general.insert(4,'estadooperativo',np.nan)
        df_ptap_prueba_general.insert(5,'descripcion',np.nan)

    if not df_ptap_prueba_general.empty:
        df_ptap_prueba_general['nombre'] = df_ptap_prueba_general['nombre'].fillna('PTAP')
        df_ptap_prueba_general['nombre'] = df_ptap_prueba_general.apply(
            lambda row: row['nombre'] + ' (' + str(row['tipodeptap']) + ')' if pd.notna(row['tipodeptap']) else row['nombre'] + ' ()',
            axis=1
        )
        #df_ptap_prueba_general['nombre'] = df_ptap_prueba_general.apply(lambda row: row['nombre'] + ' (' + row['tipodeptap'] + ')', axis=1)
        df_ptap_prueba_general['cuenta'] = df_ptap_prueba_general['cuenta'].fillna('Si')

        df_ptap_prueba_general = df_ptap_prueba_general[['codigodesistemadeagua', 'nombre', 'cuenta', 'aniodeconstruccion','estadooperativo', 'descripcion','zona','este','norte','altitud']]

    df_ptap_componentes = pd.DataFrame()
    if not df_ptap_prueba.empty:
        # Rejas lenta
        df_rejaslenta = df_ptap_prueba[['codigodesistemadeagua','tienerejaslenta','estadooperativorejaslenta','justifiquesurespuestarejas']].rename(columns={'tienerejaslenta':'cuenta','estadooperativorejaslenta':'estadooperativo','justifiquesurespuestarejas':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_rejaslenta.insert(posicion,nombre_columna,'     Rejas (Filtración lenta)')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_rejaslenta.insert(posicion,nombre_columna,'')

        # Desarenador
        df_desarenadorlenta = df_ptap_prueba[['codigodesistemadeagua','tienedesarenadorlenta','estadooperativodesarenadorlenta','justifiquesurespuestadesarenador']].rename(columns={'tienedesarenadorlenta':'cuenta','estadooperativodesarenadorlenta':'estadooperativo','justifiquesurespuestadesarenador':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_desarenadorlenta.insert(posicion,nombre_columna,'     Desarenador (Filtración lenta)')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_desarenadorlenta.insert(posicion,nombre_columna,'')

        # Presedimentador
        df_presedimentador = df_ptap_prueba[['codigodesistemadeagua','tienepresedimentador','estadooperativopresedimentador','justifiquesurespuestapresedimentador']].rename(columns={'tienepresedimentador':'cuenta','estadooperativopresedimentador':'estadooperativo','justifiquesurespuestapresedimentador':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_presedimentador.insert(posicion,nombre_columna,'     Pre sedimentador')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_presedimentador.insert(posicion,nombre_columna,'')

        # Sedimentador
        df_sedimentador = df_ptap_prueba[['codigodesistemadeagua','tienesedimentador','estadooperativosedimentador','justifiquesurespuestasedimentador']].rename(columns={'tienesedimentador':'cuenta','estadooperativosedimentador':'estadooperativo','justifiquesurespuestasedimentador':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_sedimentador.insert(posicion,nombre_columna,'     Sedimentador')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_sedimentador.insert(posicion,nombre_columna,'')

        # Pre filtro de grava
        df_prefiltrograva = df_ptap_prueba[['codigodesistemadeagua','tieneprefiltrodegrava','estadooperativoprefiltrodegrava','justifiquesurespuestaprefiltrograva']].rename(columns={'tieneprefiltrodegrava':'cuenta','estadooperativoprefiltrodegrava':'estadooperativo','justifiquesurespuestaprefiltrograva':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_prefiltrograva.insert(posicion,nombre_columna,'     Pre filtro de grava')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_prefiltrograva.insert(posicion,nombre_columna,'')

        # Filtro lento
        df_filtrolento = df_ptap_prueba[['codigodesistemadeagua','tienefiltrolento','estadooperativofiltrolento','justifiquesurespuestafiltrolento']].rename(columns={'tienefiltrolento':'cuenta','estadooperativofiltrolento':'estadooperativo','justifiquesurespuestafiltrolento':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_filtrolento.insert(posicion,nombre_columna,'     Filtro lento')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_filtrolento.insert(posicion,nombre_columna,'')

        # Rejas rapido
        df_rejasrapida = df_ptap_prueba[['codigodesistemadeagua','tienerejasrapida','estadooperativorejasrapida','justifiquesurespuestarejasrapida']].rename(columns={'tienerejasrapida':'cuenta','estadooperativorejasrapida':'estadooperativo','justifiquesurespuestarejasrapida':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_rejasrapida.insert(posicion,nombre_columna,'     Rejas (Filtración rápida)')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_rejasrapida.insert(posicion,nombre_columna,'')

        # Desarenador rapida
        df_desarenadorrapida = df_ptap_prueba[['codigodesistemadeagua','tienedesarenadorrapida','estadooperativodesarenadorrapida','justifiquesurespuestadesarenadorrapido']].rename(columns={'tienedesarenadorrapida':'cuenta','estadooperativodesarenadorrapida':'estadooperativo','justifiquesurespuestadesarenadorrapido':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_desarenadorrapida.insert(posicion,nombre_columna,'     Desarenador (Filtración rápida)')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_desarenadorrapida.insert(posicion,nombre_columna,'')

        # Presedimentador rapida
        df_presedimentadorrapida = df_ptap_prueba[['codigodesistemadeagua','tienepresedimentadorrapida','estadooperativopresedimentadorrapida','justifiquesurespuestapresedimentadorrapido']].rename(columns={'tienepresedimentadorrapida':'cuenta','estadooperativopresedimentadorrapida':'estadooperativo','justifiquesurespuestapresedimentadorrapido':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_presedimentadorrapida.insert(posicion,nombre_columna,'     Pre sedimentador (Filtración rápida)')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_presedimentadorrapida.insert(posicion,nombre_columna,'')

        # Sedimentador sin coagulación previa
        df_sedimentadorsincoag = df_ptap_prueba[['codigodesistemadeagua','tienesedimentadorsincoagulacionprevia','estadooperativosedimentadorsncoagulacion','justifiquesurespuestasedimentadorsc']].rename(columns={'tienesedimentadorsincoagulacionprevia':'cuenta','estadooperativosedimentadorsncoagulacion':'estadooperativo','justifiquesurespuestasedimentadorsc':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_sedimentadorsincoag.insert(posicion,nombre_columna,'     Sedimentador sin coagulación previa')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_sedimentadorsincoag.insert(posicion,nombre_columna,'')

        # Mezclador rapido
        df_mezcladorrapido = df_ptap_prueba[['codigodesistemadeagua','tienemezcladorrapido','estadooperativomezcladorrapido','justifiquesurespuestamezcladorrapido']].rename(columns={'tienemezcladorrapido':'cuenta','estadooperativomezcladorrapido':'estadooperativo','justifiquesurespuestamezcladorrapido':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_mezcladorrapido.insert(posicion,nombre_columna,'     Mezclador rápido')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_mezcladorrapido.insert(posicion,nombre_columna,'')

        # Floculador hidraulico
        df_floculadorh = df_ptap_prueba[['codigodesistemadeagua','tienefloculadorhidraulico','estadooperativofloculadorhidraulico','justifiquesurespuestafloculadorh']].rename(columns={'tienefloculadorhidraulico':'cuenta','estadooperativofloculadorhidraulico':'estadooperativo','justifiquesurespuestafloculadorh':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_floculadorh.insert(posicion,nombre_columna,'     Floculador hidráulico')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_floculadorh.insert(posicion,nombre_columna,'')

        # Floculador mecánico
        df_floculadorm = df_ptap_prueba[['codigodesistemadeagua','tienefloculadormecanico','estadooperativofloculadormecanico','justifiquesurespuestafloculadormeca']].rename(columns={'tienefloculadormecanico':'cuenta','estadooperativofloculadormecanico':'estadooperativo','justifiquesurespuestafloculadormeca':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_floculadorm.insert(posicion,nombre_columna,'     Floculador mecánico')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_floculadorm.insert(posicion,nombre_columna,'')

        # Sedimentador con coagulación previa
        df_sedimentadorconcoag = df_ptap_prueba[['codigodesistemadeagua','tienesedimentacionconcoagulacionprevia','estadooperativosedimentacionccoagulacion','justifiquesurespuestasedimentacioncc']].rename(columns={'tienesedimentacionconcoagulacionprevia':'cuenta','estadooperativosedimentacionccoagulacion':'estadooperativo','justifiquesurespuestasedimentacioncc':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_sedimentadorconcoag.insert(posicion,nombre_columna,'     Sedimentador con coagulación previa')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_sedimentadorconcoag.insert(posicion,nombre_columna,'')

        # Decantador
        df_decantador = df_ptap_prueba[['codigodesistemadeagua','tienedecantador','estadooperativodecantador','justifiquesurespuestadecantador']].rename(columns={'tienedecantador':'cuenta','estadooperativodecantador':'estadooperativo','justifiquesurespuestadecantador':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_decantador.insert(posicion,nombre_columna,'     Decantador')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_decantador.insert(posicion,nombre_columna,'')

        # Fitlro rapido
        df_filtrorapido = df_ptap_prueba[['codigodesistemadeagua','tienefiltrorapido','estadooperativofiltrorapido','justifiquesurespuestafiltrorapido']].rename(columns={'tienefiltrorapido':'cuenta','estadooperativofiltrorapido':'estadooperativo','justifiquesurespuestafiltrorapido':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_filtrorapido.insert(posicion,nombre_columna,'     Filtro rápido')
        posicion = 3
        nombre_columna = 'aniodeconstruccion'
        df_filtrorapido.insert(posicion,nombre_columna,'')


        df_ptap_componentes = pd.concat([
        df_ptap_prueba_general,df_rejaslenta,df_desarenadorlenta,df_presedimentador,df_sedimentador,df_prefiltrograva,df_filtrolento,df_rejasrapida,
        df_desarenadorrapida,df_presedimentadorrapida,df_sedimentadorsincoag,df_mezcladorrapido,df_floculadorh,df_floculadorm,
        df_sedimentadorconcoag,df_decantador,df_filtrorapido
        ], ignore_index=True)

        df_ptap_componentes['zona'] = np.nan
        df_ptap_componentes['este'] = np.nan
        df_ptap_componentes['norte'] = np.nan
        df_ptap_componentes['altitud'] = np.nan  

    # Reservorio
    df_reservorio = df_reservorio.rename(columns={'codigodesistemaagua':'codigodesistemadeagua'})
    df_reservorio_prueba = pd.merge(df_sistema_agua_prueba[['codigodesistemadeagua']],df_reservorio[[
    'codigodesistemadeagua','anodeconstruccion','estadooperativodereservorio','justifiquesurespuestareservorio','zona','este','norte','altitud'
    ]],on='codigodesistemadeagua',how='inner').rename(columns={'anodeconstruccion':'aniodeconstruccion','estadooperativodereservorio':'estadooperativo','justifiquesurespuestareservorio':'descripcion'})
    df_reservorio_prueba.insert(1,'nombre',np.nan)
    df_reservorio_prueba.insert(2,'cuenta',np.nan)

    if not df_reservorio_prueba.empty:
        df_reservorio_prueba['nombre'] = df_reservorio_prueba['nombre'].fillna('Reservorio')
        df_reservorio_prueba['cuenta'] = df_reservorio_prueba['cuenta'].fillna('Si')


    # Sistema de distribucion
    df_distribucion = df_sistema_agua_prueba[['codigodesistemadeagua','aniodeconstrucciondistribucion','estadooperativoactual','justificasurespuestadistribucion']].rename(columns={'aniodeconstrucciondistribucion':'aniodeconstruccion','estadooperativoactual':'estadooperativo','justificasurespuestadistribucion':'descripcion'})
    df_distribucion.insert(1,'nombre',np.nan)
    df_distribucion.insert(2,'cuenta',np.nan)

    df_distribucion['zona'] = np.nan
    df_distribucion['este'] = np.nan
    df_distribucion['norte'] = np.nan
    df_distribucion['altitud'] = np.nan  

    if not df_distribucion.empty:
        df_distribucion['nombre'] = df_distribucion['nombre'].fillna('Red de distribución de agua')
        df_distribucion['cuenta'] = df_distribucion['cuenta'].fillna('Si')

    coordenadas_agua = pd.DataFrame()   
    df_noconvencional = pd.DataFrame()  
    df_sistema_agua_resumen_convencional = pd.DataFrame()  
    df_sistema_agua_resumen_noconvencional = pd.DataFrame() 
    convencional = noconvencional = '-'

    if es_prestador == "Si" or es_prestador == "No":
        df_sistema_general = pd.concat([df_captacion_prueba,df_equipo_casete_bombeo,df_conduccion_prueba,df_ptap_componentes,df_reservorio_prueba,df_distribucion],ignore_index=True)
        df_sistema_general['N_aux'] = df_sistema_general.groupby(['codigodesistemadeagua','nombre']).cumcount() + 1
        if not df_sistema_general.empty:
            df_sistema_general['Nombre_aux'] = df_sistema_general.apply(lambda row: row['nombre'] + str(row['N_aux']), axis=1)
        else:
            df_sistema_general['Nombre_aux'] = np.nan

        df_sistema_nombre = pd.concat([df_captacion_prueba,df_equipo_bombeo,df_conduccion_prueba,df_ptap_prueba_general,df_reservorio_prueba,df_distribucion],ignore_index=True)
        df_sistema_nombre['N_aux'] = df_sistema_nombre.groupby(['codigodesistemadeagua','nombre']).cumcount() + 1
        if not df_sistema_nombre.empty:
            df_sistema_nombre['Nombre_aux'] = df_sistema_nombre.apply(lambda row: row['nombre'] + str(row['N_aux']), axis=1)
        else:
            df_sistema_nombre['Nombre_aux'] = np.nan
        
        df_sistema_nombre = df_sistema_nombre.loc[df_sistema_nombre['cuenta']=='Si']
        df_sistema_nombre['N'] = df_sistema_nombre.groupby('codigodesistemadeagua').cumcount() + 1

        if not df_sistema_nombre.empty:
            df_sistema_nombre['nombre_fin'] = df_sistema_nombre.apply(lambda row: str(row['N']) + ". " + row['nombre'], axis=1)
        else:
            df_sistema_nombre['nombre_fin'] = np.nan

        df_sistema_nombre_general_2 = pd.merge(df_sistema_general,df_sistema_nombre[['codigodesistemadeagua','nombre_fin','Nombre_aux','zona','este','norte','altitud']],on=['codigodesistemadeagua', 'Nombre_aux'], how='left')
        df_sistema_nombre_general_2['zona'] = df_sistema_nombre_general_2['zona_x'].combine_first(df_sistema_nombre_general_2['zona_y'])
        df_sistema_nombre_general_2['este'] = df_sistema_nombre_general_2['este_x'].combine_first(df_sistema_nombre_general_2['este_y'])
        df_sistema_nombre_general_2['norte'] = df_sistema_nombre_general_2['norte_x'].combine_first(df_sistema_nombre_general_2['norte_y'])
        df_sistema_nombre_general_2['altitud'] = df_sistema_nombre_general_2['altitud_x'].combine_first(df_sistema_nombre_general_2['altitud_y'])
        df_sistema_nombre_general_2['nombre'] = df_sistema_nombre_general_2['nombre_fin'].fillna(df_sistema_nombre_general_2['nombre'])
        df_sistema_nombre_general_2 = df_sistema_nombre_general_2.loc[df_sistema_nombre_general_2['cuenta']=='Si']

        # Aplicando funcion para calcular años de antiguedad
        df_sistema_nombre_general_2['antiguedad'] = df_sistema_nombre_general_2['aniodeconstruccion'].apply(calcular_anios)

        df_sistema_nombre_general_2 = df_sistema_nombre_general_2[['codigodesistemadeagua', 'nombre','antiguedad','estadooperativo', 'descripcion','zona','este','norte','altitud']]
        # Filtrar el DataFrame para incluir solo los registros que contienen "Línea de conducción / Impulsión" y "Reservorio"
        if not df_sistema_nombre_general_2.empty:
            filtro = df_sistema_nombre_general_2['nombre'].str.contains('Línea de conducción / Impulsión|Reservorio')

            # Aplicar la operación de reemplazo solo a los registros que cumplen con el filtro
            df_sistema_nombre_general_2.loc[filtro, 'nombre_sin_numero'] = df_sistema_nombre_general_2.loc[filtro, 'nombre'].str.replace(r'^\d+\.\s*', '', regex=True)
                
            filtro = df_sistema_nombre_general_2['nombre_sin_numero'].notnull()
            df_sistema_nombre_general_2.loc[filtro, 'auxiliar'] = df_sistema_nombre_general_2[filtro].groupby(['codigodesistemadeagua', 'nombre_sin_numero']).cumcount() + 1
            df_sistema_nombre_general_2['auxiliar'] = pd.to_numeric(df_sistema_nombre_general_2['auxiliar'], errors='coerce').astype('Int64')
            df_sistema_nombre_general_2['nombre'] = df_sistema_nombre_general_2.apply(lambda row: str(row['nombre'] + ' (N°0' + str(row['auxiliar']) + ')' if not pd.isnull(row['nombre_sin_numero']) else row['nombre']), axis=1)

            df_sistema_nombre_general_2.loc[:, 'nombre_sin_numero'] = df_sistema_nombre_general_2.loc[:, 'nombre'].str.replace(r'^\d+\.\s*', '', regex=True)
            
        else:
            df_sistema_nombre_general_2['nombre_sin_numero'] = np.nan

        coordenadas_agua = df_sistema_nombre_general_2.loc[df_sistema_nombre_general_2['zona'].notnull(),['nombre_sin_numero','zona','este','norte','altitud']].rename(columns={'nombre_sin_numero':'nombre'})
        df_noconvencional = df_sistema_agua_prueba[['p004_zona','p004_este','p004_norte','p004_altitud']].rename(columns={
            'p004_zona':'zona','p004_este':'este','p004_norte':'norte','p004_altitud':'altitud'
        })
        df_noconvencional.insert(0,'nombre','Sistema no convencional')

        df_sistema_nombre_general_2 = df_sistema_nombre_general_2[['codigodesistemadeagua', 'nombre','antiguedad','estadooperativo', 'descripcion']]

        df_sistema_agua_resumen = df_sistema_agua_prueba[['codigodesistemadeagua', 'codigodeprestador', 'tipodesistemadeagua', 'p003_subtipodeaguanoconvencional','p004_anodecontruccionnoconvencional','p004_estadooptruccionnoconvencional',
        'p004_comentartruccionnoconvencional','p005_subtipodeaguaconvencional','p006_comoseconstruyoelsistemadeaguapotable','p007_enqueanoseconstruyoelsistemadeagua','p044_porquenorealizalacloracion',
        'p030_realizacloracion','p027_elsistemadeaguacuentaconequipoclorador','p028_tipodecloracion','p043_clororesidualpuntomaslejano','p048_turbidez','turbidezunt','fecha','comentariosdesinfeccion',
        'p004_comentartruccionnoconvencional','observacionessistemadistribucion','p012_mantenimientocaptacion','p012_mantenimientocasetayequipodebombeo','p012_mantenimientolineadeconduccion','p012_mantenimientoptap','p012_mantenimientoreservorio','p012_mantenimientoreddedistribucion']]
        df_sistema_agua_resumen['N'] = df_sistema_agua_resumen.groupby('tipodesistemadeagua').cumcount() + 1
        df_sistema_agua_resumen['num'] = df_sistema_agua_resumen.apply(lambda row: "S" + str(row['N']), axis=1)

        # Cloro residual en el reservorio
        df_reservorio_cloro = pd.merge(df_sistema_agua_resumen[['codigodesistemadeagua']],df_reservorio[[
        'codigodesistemadeagua','clororesidualmgl']],on='codigodesistemadeagua',how='inner')
        df_reservorio_cloro = df_reservorio_cloro.dropna(subset=['clororesidualmgl'])
        df_reservorio_cloro = df_reservorio_cloro.groupby('codigodesistemadeagua').agg({'clororesidualmgl':'mean'}).reset_index()
        df_reservorio_cloro['clororesidualmgl'] = df_reservorio_cloro['clororesidualmgl'].apply(lambda x: "{:0.1f}".format(x))
        df_sistema_agua_resumen = pd.merge(df_sistema_agua_resumen,df_reservorio_cloro,on=['codigodesistemadeagua'],how='left')

        # Continuidad del servicio
        df_ps_continuidad = df_ps[['codigodeprestador','p029a_continuidadpromedioenepocadelluviahorasdia', 'p029b_continuidadpromedioenepocadeestiajehorasdia']]
        df_ps_continuidad = pd.merge(df_sistema_agua_prueba[['codigodesistemadeagua', 'codigodeprestador']],df_ps_continuidad, on='codigodeprestador', how='inner')
        df_ps_continuidad = df_ps_continuidad.groupby('codigodeprestador').agg({'p029a_continuidadpromedioenepocadelluviahorasdia':'mean','p029b_continuidadpromedioenepocadeestiajehorasdia':'mean'}).reset_index()
        df_ps_continuidad = pd.merge(df_sistema_agua_prueba[['codigodesistemadeagua', 'codigodeprestador']],df_ps_continuidad, on='codigodeprestador', how='inner')
        df_ps_continuidad['p029a_continuidadpromedioenepocadelluviahorasdia'] = df_ps_continuidad['p029a_continuidadpromedioenepocadelluviahorasdia'].apply(lambda x: "{:0.1f}".format(x))
        df_ps_continuidad['p029b_continuidadpromedioenepocadeestiajehorasdia'] = df_ps_continuidad['p029b_continuidadpromedioenepocadeestiajehorasdia'].apply(lambda x: "{:0.1f}".format(x))

        # Renombrando columnas
        df_sistema_agua_resumen = pd.merge(df_sistema_agua_resumen,df_ps_continuidad,on=['codigodesistemadeagua'],how='left')
        df_sistema_agua_resumen.rename(columns={'p029a_continuidadpromedioenepocadelluviahorasdia':'contia','p029b_continuidadpromedioenepocadeestiajehorasdia':'contie',
                                                'p027_elsistemadeaguacuentaconequipoclorador':'tieneequipoclorador'}, inplace=True)
        
        df_sistema_agua_resumen['p007_enqueanoseconstruyoelsistemadeagua'] = df_sistema_agua_resumen['p007_enqueanoseconstruyoelsistemadeagua'].apply(lambda x: int(x) if pd.notnull(x) and isinstance(x, float) else x)
        df_sistema_agua_resumen['p004_anodecontruccionnoconvencional'] = df_sistema_agua_resumen['p004_anodecontruccionnoconvencional'].apply(lambda x: int(x) if pd.notnull(x) and isinstance(x, float) else x)

        df_sistema_agua_resumen = df_sistema_agua_resumen.fillna('-')
        df_sistema_nombre_general_2 = df_sistema_nombre_general_2.fillna('-')

        df_sistema_nombre_general_2_aux = f_sistema_agua_resumen = df_sistema_agua_resumen_convencional = df_sistema_agua_resumen_noconvencional = pd.DataFrame()
        if not df_sistema_nombre_general_2.empty:
            df_sistema_nombre_general_2_aux = df_sistema_nombre_general_2.groupby('codigodesistemadeagua').apply(set_eoagua).reset_index(level=0).rename(columns={0:'EO'})
            df_sistema_agua_resumen['antiguedadnoconven'] = df_sistema_agua_resumen['p004_anodecontruccionnoconvencional'].apply(calcular_anios)
            df_sistema_agua_resumen['antiguedadconven'] = df_sistema_agua_resumen['p007_enqueanoseconstruyoelsistemadeagua'].apply(calcular_anios)
            df_sistema_agua_resumen = pd.merge(df_sistema_agua_resumen,df_sistema_nombre_general_2_aux,on='codigodesistemadeagua',how='left')

            # Aplicar la función a cada fila del DataFrame
            df_sistema_agua_resumen['mantenimiento'] = df_sistema_agua_resumen[['codigodesistemadeagua','p012_mantenimientocaptacion','p012_mantenimientocasetayequipodebombeo','p012_mantenimientolineadeconduccion','p012_mantenimientoptap','p012_mantenimientoreservorio','p012_mantenimientoreddedistribucion']].apply(determinar_estado_fila, axis=1)
            
            df_sistema_agua_resumen_convencional = df_sistema_agua_resumen.loc[df_sistema_agua_resumen['tipodesistemadeagua']=='Sistema de agua convencional']
            df_sistema_agua_resumen_noconvencional = df_sistema_agua_resumen.loc[df_sistema_agua_resumen['tipodesistemadeagua']=='Sistema de agua no convencional']
        
        if not df_sistema_agua_resumen_convencional.empty:
            convencional = "Si"
        if not df_sistema_agua_resumen_noconvencional.empty:
            noconvencional = "Si"
        
    sistemas_de_agua = []

    if es_prestador == "Si" or es_prestador == "No":
        for _, sistema in df_sistema_agua_resumen.iterrows():
            sistema_dict = sistema.to_dict()  # Convertir la fila a un diccionario
            sistema_dict['componentes'] = []  # Inicializar la lista de captaciones para este sistema
            
            # Filtrar las captaciones correspondientes a este sistema
            componentes_sistema = df_sistema_nombre_general_2[df_sistema_nombre_general_2['codigodesistemadeagua'] == sistema['codigodesistemadeagua']]
            # Iterar sobre las filas del DataFrame de captaciones del sistema actual
            for _, componente in componentes_sistema.iterrows():
                sistema_dict['componentes'].append(componente.to_dict())  # Agregar la captación al sistema
            
            # Agregar el sistema completo a la lista de sistemas de agua
            sistemas_de_agua.append(sistema_dict)
    
    sistemas_de_agua_convecional = []

    if es_prestador == "Si" or es_prestador == "No":
        for _, sistema in df_sistema_agua_resumen_convencional.iterrows():
            sistema_dict = sistema.to_dict()  # Convertir la fila a un diccionario
            sistema_dict['componentes'] = []  # Inicializar la lista de captaciones para este sistema
            
            # Filtrar las captaciones correspondientes a este sistema
            componentes_sistema = df_sistema_nombre_general_2[df_sistema_nombre_general_2['codigodesistemadeagua'] == sistema['codigodesistemadeagua']]
            
            # Iterar sobre las filas del DataFrame de captaciones del sistema actual
            for _, componente in componentes_sistema.iterrows():                
                sistema_dict['componentes'].append(componente.to_dict())  # Agregar la captación al sistema
            
            # Agregar el sistema completo a la lista de sistemas de agua
            sistemas_de_agua_convecional.append(sistema_dict)

    sistemas_de_agua_noconvencional = []

    if es_prestador == "Si" or es_prestador == "No":
        for _, sistema in df_sistema_agua_resumen_noconvencional.iterrows():
            sistema_dict = sistema.to_dict()  # Convertir la fila a un diccionario
            sistema_dict['componentes'] = []  # Inicializar la lista de captaciones para este sistema
            
            # Filtrar las captaciones correspondientes a este sistema
            componentes_sistema = df_sistema_nombre_general_2[df_sistema_nombre_general_2['codigodesistemadeagua'] == sistema['codigodesistemadeagua']]
            
            # Iterar sobre las filas del DataFrame de captaciones del sistema actual
            for _, componente in componentes_sistema.iterrows():
                sistema_dict['componentes'].append(componente.to_dict())  # Agregar la captación al sistema
            
            # Agregar el sistema completo a la lista de sistemas de agua
            sistemas_de_agua_noconvencional.append(sistema_dict)
   
    ########## Sistema de alcantarillado ##########
    df_sistema_alca_prueba = pd.DataFrame()
    if not df_sistema_alca_prueba.empty:
        df_sistema_alca_prueba = df_sistema_alca.loc[df_sistema_alca['codigodeprestador']==df_prueba['codigodeprestador'].values[0]].head(1)
        df_sistema_alca_prueba['antiguedadalca'] = df_sistema_alca_prueba['anodeconstruccion'].apply(calcular_anios)
        df_sistema_alca_prueba['anodeconstruccionalca'] = df_sistema_alca_prueba['anodeconstruccion'].apply(lambda x: int(x) if pd.notnull(x) and isinstance(x, float) else x)
        df_sistema_alca_prueba['eoebar'] = df_sistema_alca_prueba.apply(lambda row: 'No cuenta' if row['tieneebar']=='No' else row['estadooperativoebar'], axis=1)
        df_sistema_alca_prueba['descripcionebar'] = df_sistema_alca_prueba.apply(lambda row: 'No cuenta' if row['tieneebar']=='No' else row['justifiquesurespuestaalca'], axis=1)

    df_disposicionfinal_prueba = pd.DataFrame()
    if not df_disposicionfinal.empty:
        df_disposicionfinal_prueba = df_disposicionfinal.loc[df_disposicionfinal['codigodeprestador']==df_prueba['codigodeprestador'].values[0]]
        df_disposicionfinal_prueba = df_disposicionfinal_prueba.loc[df_disposicionfinal_prueba['p029_autorizaciondevertimiento'].notnull()].head(1)
       
    df_ptar_prueba = pd.DataFrame() 
    if not df_ptar.empty:
        df_ptar_prueba = df_ptar.loc[df_ptar['codigodeprestador']==df_prueba['codigodeprestador'].values[0]].head(1)
        df_ptar_prueba['anodeconstruccionptar'] = df_ptar_prueba['anodeconstruccionptar'].apply(lambda x: int(x) if pd.notnull(x) and isinstance(x, float) else x)

    tiene_alca = tiene_ptar = 'No'
    tipodesistemadealcantarilladosanitario = anodeconstruccionalca = eoalca = descripcionalca = eoebar = descripcionebar = comentariossistemaalcantarillado = antiguedadalca = p008_realizamantenimientoalareddealcantarillado = p029_autorizaciondevertimiento = anodeconstruccionptar = alcantarilladoadministradoporunaeps = comentariosptar = '-'
    if not df_sistema_alca_prueba.empty:
        tiene_alca = 'Si'
        df_sistema_alca_prueba_2 = df_sistema_alca_prueba.fillna('-')
        tipodesistemadealcantarilladosanitario = df_sistema_alca_prueba_2['tipodesistemadealcantarilladosanitario'].values[0] 
        alcantarilladoadministradoporunaeps = df_sistema_alca_prueba_2['alcantarilladoadministradoporunaeps'].values[0] 
        anodeconstruccionalca = df_sistema_alca_prueba_2['anodeconstruccionalca'].values[0]
        eoalca = df_sistema_alca_prueba_2['estadooperativodelsistemadealcantarillado'].values[0]
        descripcionalca = df_sistema_alca_prueba_2['justifiquesurespuestaalca'].values[0]
        eoebar = df_sistema_alca_prueba_2['eoebar'].values[0]
        descripcionebar = df_sistema_alca_prueba_2['descripcionebar'].values[0]
        comentariossistemaalcantarillado = df_sistema_alca_prueba_2['comentariossistemaalcantarillado'].values[0]
        antiguedadalca = df_sistema_alca_prueba_2['antiguedadalca'].values[0]
        p008_realizamantenimientoalareddealcantarillado = df_sistema_alca_prueba_2['p008_realizamantenimientoalareddealcantarillado'].values[0]

    if not df_ptar_prueba.empty:
        tiene_ptar = 'Si'
        df_ptar_prueba = df_ptar_prueba.fillna('-')
        anodeconstruccionptar = df_ptar_prueba['anodeconstruccionptar'].values[0]
        comentariosptar = df_ptar_prueba['comentarios'].values[0]
        

    if not df_disposicionfinal_prueba.empty:
        p029_autorizaciondevertimiento = df_disposicionfinal_prueba['p029_autorizaciondevertimiento'].values[0]
        df_disposicionfinal_prueba = df_disposicionfinal_prueba.fillna('-')


    ###### PTAR ######

    # Rejas
    eotar = '-'
    df_preliminar = pd.DataFrame(columns=['tipo','codigosistemaalcantarillado'])
    df_primario = pd.DataFrame(columns=['tipo','codigosistemaalcantarillado'])
    df_secundario = pd.DataFrame(columns=['tipo','codigosistemaalcantarillado'])
    if not df_ptar_prueba.empty:
        df_rejas_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienerejas','eorejas','justifiquesurespuestarejas']].rename(columns={'tienerejas':'cuenta','eorejas':'estadooperativo','justifiquesurespuestarejas':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_rejas_ptar.insert(posicion,nombre_columna,'Rejas')

        # Desarenador
        df_desarenador_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienedesarenador','eodesarenador','justifiquesurespuestadesarenador']].rename(columns={'tienedesarenador':'cuenta','eodesarenador':'estadooperativo','justifiquesurespuestadesarenador':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_desarenador_ptar.insert(posicion,nombre_columna,'Desarenador')

        # Medidor de caudal
        df_medidorcaudal_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienemedidoryrepartidordecaudal','eomedidoryrepartidorcaudal','justifiquesurespuestamedidorcaudal']].rename(columns={'tienemedidoryrepartidordecaudal':'cuenta','eomedidoryrepartidorcaudal':'estadooperativo','justifiquesurespuestamedidorcaudal':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_medidorcaudal_ptar.insert(posicion,nombre_columna,'Medidor y repartidor de caudal')

        df_tratamiento_preliminar = pd.concat([df_rejas_ptar,df_desarenador_ptar,df_medidorcaudal_ptar], ignore_index=True)
        df_tratamiento_preliminar['tipo'] = 'TRATAMIENTO PRELIMINAR'
        df_tratamiento_preliminar = df_tratamiento_preliminar.loc[df_tratamiento_preliminar['cuenta']=='Si']

        # imhoff
        df_imhoff_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tieneimhoff','eoimhoff','justifiquesurespuestatanqueimhoff']].rename(columns={'tieneimhoff':'cuenta','eoimhoff':'estadooperativo','justifiquesurespuestatanqueimhoff':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_imhoff_ptar.insert(posicion,nombre_columna,'Tanque Imhoff')

        # Tanque séptico
        df_septico_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienetanqueseptico','eotanqueseptico','justifiquesurespuestatanqueseptico']].rename(columns={'tienetanqueseptico':'cuenta','eotanqueseptico':'estadooperativo','justifiquesurespuestatanqueseptico':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_septico_ptar.insert(posicion,nombre_columna,'Tanque séptico')

        # Tanque de sedimentación
        df_sedimentacion_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienetanquedesedimentacion','eotanquesedimentacion','justifiquesurespuestatanquesedimento']].rename(columns={'tienetanquedesedimentacion':'cuenta','eotanquesedimentacion':'estadooperativo','justifiquesurespuestatanquesedimento':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_sedimentacion_ptar.insert(posicion,nombre_columna,'Tanque de sedimentación')

        # Tanque de flotación
        df_flotacion_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienetanquedeflotacion','eotanquedeflotacion','justifiquesurespuestatanqueflota']].rename(columns={'tienetanquedeflotacion':'cuenta','eotanquedeflotacion':'estadooperativo','justifiquesurespuestatanqueflota':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_flotacion_ptar.insert(posicion,nombre_columna,'Tanque de flotación')

        # RAFA/UASB
        df_rafa_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienerafauasb','eorafauasb','justifiquesurespuestarafa']].rename(columns={'tienerafauasb':'cuenta','eorafauasb':'estadooperativo','justifiquesurespuestarafa':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_rafa_ptar.insert(posicion,nombre_columna,'RAFA/UASB')

        df_tratamiento_primario = pd.concat([df_imhoff_ptar,df_septico_ptar,df_sedimentacion_ptar,df_flotacion_ptar,df_rafa_ptar], ignore_index=True)
        df_tratamiento_primario['tipo'] = 'TRATAMIENTO PRIMARIO'
        df_tratamiento_primario = df_tratamiento_primario.loc[df_tratamiento_primario['cuenta']=='Si']

        # Lagunas de estabilizacion
        df_estabilizacion_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienelagunasdeestabilizacion','eolagunasestabilizacion','justifiquesurespuestalagunaestabilizacion']].rename(columns={'tienelagunasdeestabilizacion':'cuenta','eolagunasestabilizacion':'estadooperativo','justifiquesurespuestalagunaestabilizacion':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_estabilizacion_ptar.insert(posicion,nombre_columna,'Lagunas de estabilizacion')

        # Lodos activados
        df_lodos_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienelodosactivados','eolodosactivados','justifiquesurespuestalodosactivados']].rename(columns={'tienelodosactivados':'cuenta','eolodosactivados':'estadooperativo','justifiquesurespuestalodosactivados':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_lodos_ptar.insert(posicion,nombre_columna,'Lodos activados')

        # Filtros percoladores
        df_percoladores_ptar = df_ptar_prueba[['codigosistemaalcantarillado','tienefiltrospercoladores','eofiltrospercoladores','justifiquesurespuestafiltrospercoladores']].rename(columns={'tienefiltrospercoladores':'cuenta','eofiltrospercoladores':'estadooperativo','justifiquesurespuestafiltrospercoladores':'descripcion'})
        posicion = 1
        nombre_columna = 'nombre'
        df_percoladores_ptar.insert(posicion,nombre_columna,'Filtros percoladores')


        df_tratamiento_secundario = pd.concat([df_estabilizacion_ptar,df_lodos_ptar,df_percoladores_ptar], ignore_index=True)
        df_tratamiento_secundario['tipo'] = 'TRATAMIENTO SECUNDARIO'
        df_tratamiento_secundario = df_tratamiento_secundario.loc[df_tratamiento_secundario['cuenta']=='Si']



        
        if not df_tratamiento_preliminar.empty:
            df_preliminar.loc[len(df_preliminar)] = ['TRATAMIENTO PRELIMINAR',df_ptar_prueba['codigosistemaalcantarillado'].values[0]]

        
        if not df_tratamiento_primario.empty:
            df_primario.loc[len(df_primario)] = ['TRATAMIENTO PRIMARIO',df_ptar_prueba['codigosistemaalcantarillado'].values[0]]
        
        
        if not df_tratamiento_secundario.empty:
            df_secundario.loc[len(df_secundario)] = ['TRATAMIENTO SECUNDARIO',df_ptar_prueba['codigosistemaalcantarillado'].values[0]]

    
        if not pd.concat([df_tratamiento_preliminar,df_tratamiento_primario,df_tratamiento_secundario], ignore_index=True).groupby('codigosistemaalcantarillado').apply(set_eoagua).empty:
            eotar = pd.concat([df_tratamiento_preliminar,df_tratamiento_primario,df_tratamiento_secundario], ignore_index=True).groupby('codigosistemaalcantarillado').apply(set_eoagua).reset_index(level=0).rename(columns={0:'EOptar'})['EOptar'].values[0]

    valores = [eoalca, eoebar, eotar]

    # Aplicamos la función a los valores
    eofinalca = evaluar_valores(valores)

    listadopreliminar = []

    if not df_preliminar.empty:
        # Iterar sobre las filas del DataFrame de sistemas de agua
        for _, preliminar in df_preliminar.iterrows():
            preliminar_dict = preliminar.to_dict()  # Convertir la fila a un diccionario
            preliminar_dict['componentes'] = []  # Inicializar la lista de captaciones para este sistema
            
            # Filtrar las captaciones correspondientes a este sistema
            componentes_preliminar = df_tratamiento_preliminar[df_tratamiento_preliminar['codigosistemaalcantarillado'] == preliminar['codigosistemaalcantarillado']]
            
            # Iterar sobre las filas del DataFrame de captaciones del sistema actual
            for _, componente in componentes_preliminar.iterrows():
                preliminar_dict['componentes'].append(componente.to_dict())  # Agregar la captación al sistema
            
            # Agregar el sistema completo a la lista de sistemas de agua
            listadopreliminar.append(preliminar_dict)


    listadoprimario = []

    if not df_primario.empty:
        # Iterar sobre las filas del DataFrame de sistemas de agua
        for _, preliminar in df_primario.iterrows():
            preliminar_dict = preliminar.to_dict()  # Convertir la fila a un diccionario
            preliminar_dict['componentes'] = []  # Inicializar la lista de captaciones para este sistema
            
            # Filtrar las captaciones correspondientes a este sistema
            componentes_primario = df_tratamiento_primario[df_tratamiento_primario['codigosistemaalcantarillado'] == preliminar['codigosistemaalcantarillado']]
            
            # Iterar sobre las filas del DataFrame de captaciones del sistema actual
            
            for _, componente in componentes_primario.iterrows():
                preliminar_dict['componentes'].append(componente.to_dict())  # Agregar la captación al sistema
            
            # Agregar el sistema completo a la lista de sistemas de agua
            listadoprimario.append(preliminar_dict)


    listadosecundario = []

    if not df_secundario.empty:
    # Iterar sobre las filas del DataFrame de sistemas de agua
        for _, preliminar in df_secundario.iterrows():
            preliminar_dict = preliminar.to_dict()  # Convertir la fila a un diccionario
            preliminar_dict['componentes'] = []  # Inicializar la lista de captaciones para este sistema
            
            # Filtrar las captaciones correspondientes a este sistema
            componentes_secundario = df_tratamiento_secundario[df_tratamiento_secundario['codigosistemaalcantarillado'] == preliminar['codigosistemaalcantarillado']]
            
            # Iterar sobre las filas del DataFrame de captaciones del sistema actual
            
            for _, componente in componentes_secundario.iterrows():
                preliminar_dict['componentes'].append(componente.to_dict())  # Agregar la captación al sistema
            
            # Agregar el sistema completo a la lista de sistemas de agua
            listadosecundario.append(preliminar_dict)



    lista_total = listadopreliminar + listadoprimario + listadosecundario
    df_ebar = pd.DataFrame()
    if not df_sistema_alca_prueba.empty:
        df_ebar = df_sistema_alca_prueba[['zona','este','norte','altitud']]
        df_ebar.insert(0,'nombre','EBAR')
    df_tar = pd.DataFrame()
    if not df_ptar_prueba.empty:
        df_tar = df_ptar_prueba[['zona','este','norte','altitud']]
        df_tar.insert(0,'nombre','PTAR')

    componentes_final = pd.concat([coordenadas_agua,df_noconvencional,df_ebar,df_tar])

    componentes_final = componentes_final.loc[(componentes_final['este'].notnull()) & (componentes_final['este'] != '-')]

    componentes_final['este'] = componentes_final['este'].apply(lambda x: int(x) if pd.notnull(x) else "-")
    componentes_final['norte'] = componentes_final['norte'].apply(lambda x: int(x) if pd.notnull(x) else "-")
    componentes_final['altitud'] = componentes_final['altitud'].apply(lambda x: int(x) if pd.notnull(x) else "-")

    
    coordenadas = []
    for index,row in componentes_final.iterrows():
        coordenadas.append({
            "nombre" : row["nombre"],
            "zona": row["zona"],
            "este": row["este"],
            "norte": row["norte"],
            "altitud": row["altitud"],      
        })
    
    tiene_ubs = 'No'
    tipoubs = tipo_ubs_aux = anioubs = comentariosubs = '-'
    df_ubs = pd.DataFrame()
    if not df_ubs.empty:
        df_ubs['tipo_aux'] = df_ubs['tipoubsodisposicionesinadecuadasdeexcretas'].apply(lambda x: 'UBS - AH' if x=='Arrastre hidráulico' else
                                                                                        'UBS - C' if x=='Compostera' else 'UBS - HSV' if x=='Hoyo seco ventilado' else x)
        df_ubs['enqueanoseconstruyolaubs'] = df_ubs['enqueanoseconstruyolaubs'].fillna(-1).astype(int).replace(-1,pd.NA)
        
        df_ubs_prueba = df_ubs.loc[df_ubs['codigodeprestador']==df_prueba['codigodeprestador'].values[0]].head(1)

        
        if not df_ubs_prueba.empty:
            tiene_ubs = 'Si'
            df_ubs_prueba = df_ubs_prueba.fillna('-')
            tipoubs = df_ubs_prueba['tipoubsodisposicionesinadecuadasdeexcretas'].values[0]
            tipo_ubs_aux = df_ubs_prueba['tipo_aux'].values[0]
            anioubs = df_ubs_prueba['enqueanoseconstruyolaubs'].values[0]
            comentariosubs = df_ubs_prueba['comentarios'].values[0]
            
        
    # Disposicion no adecuada
    df_ps_prueba_alca = df_ps.loc[df_ps['codigodeprestador']==df_prueba['codigodeprestador'].values[0]]
    df_ps_prueba_alca = df_ps_prueba_alca.dropna(subset=['viviendascondisposiciondeexcretasnoadecuadas'])
    df_ps_prueba_alca = df_ps_prueba_alca.loc[df_ps_prueba_alca['viviendascondisposiciondeexcretasnoadecuadas']=='Si'].head(1)
    tiene_noadecuado=tiponoadecuado =comentarionoadecuado='-'
    if not df_ps_prueba_alca.empty:
        tiene_noadecuado = 'Si'
        df_ps_prueba_alca = df_ps_prueba_alca.fillna('-')
        tiponoadecuado = df_ps_prueba_alca['tiponoadecuado'].values[0]
        comentarionoadecuado = df_ps_prueba_alca['comentarios'].values[0]


    ######## 5.4) Percepción de los servicios por los usuarios ########
    ###################################################################
    df_usuario_prueba = df_usuario.loc[df_usuario['codigodeprestador'] == df_prueba.at[0, 'codigodeprestador']]

    #### Caso: Con prestador
    # Cobro del servicio
    cantidad_cobro = df_usuario_prueba['p006_pagaporlosserviciosdesaneamiento'].value_counts()
    porcentaje_cobro = df_usuario_prueba['p006_pagaporlosserviciosdesaneamiento'].value_counts(normalize=True)*100
    porcentaje_cobro_si = "{:0.1f} %".format(porcentaje_cobro.get('Si',0))
    cantidad_cobro_si = cantidad_cobro.get('Si',0)
    cantidad_cobro_total = cantidad_cobro.get('Si',0) + cantidad_cobro.get('No',0)
    texto_cobro = f'El {porcentaje_cobro_si} ({cantidad_cobro_si} de {cantidad_cobro_total}) de usuarios entrevistados pagan por los servicios de saneamiento.'
    # Nivel de satisfaccion
    cantidad_satisfaccion = df_usuario_prueba['p010_niveldesatisfaccionconelservicio'].value_counts()
    satisfaccion_si = cantidad_satisfaccion.get('Satisfecho',0) + cantidad_satisfaccion.get('Muy satisfecho',0)
    #satisfaccion_total = cantidad_satisfaccion.get('Satisfecho',0) + cantidad_satisfaccion.get('Muy satisfecho',0) + cantidad_satisfaccion.get('Indiferente',0) + cantidad_satisfaccion.get('Poco satisfecho',0) + cantidad_satisfaccion.get('Nada satisfecho',0)
    satisfaccion_total = df_usuario_prueba['p010_niveldesatisfaccionconelservicio'].count()
    try:
        porcentaje_satisfaccion_si = "{:0.1f} %".format((satisfaccion_si/satisfaccion_total)*100)
    except ZeroDivisionError:
        print("Error: división por cero")
    texto_satisfaccion = f'El {porcentaje_satisfaccion_si} ({satisfaccion_si} de {satisfaccion_total}) de usuarios entrevistados refieren estar satisfechos con el servicio brindado por el prestador'
    # Disposicion a pagar
    cantidad_disposicion = df_usuario_prueba['p012_pagariaunmontoadicionalporelservicio'].value_counts()
    porcentaje_disposicion  = df_usuario_prueba['p012_pagariaunmontoadicionalporelservicio'].value_counts(normalize=True)*100
    porcentaje_disposicion_si = "{:0.1f} %".format(porcentaje_disposicion.get('Si',0))
    porcentaje_disposicion_no = "{:0.1f} %".format(porcentaje_disposicion.get('No',0))
    cantidad_disposicion_si = cantidad_disposicion.get('Si',0)
    cantidad_disposicion_no = cantidad_disposicion.get('No',0)
    cantidad_disposicion_total = cantidad_disposicion.get('Si',0) + cantidad_disposicion.get('No',0)
    texto_disposicion = f'El {porcentaje_disposicion_si} ({cantidad_disposicion_si} de {cantidad_disposicion_total}) de usuarios refieren que están de acuerdo en pagar un monto adicional por una mejora en el servicio. En tanto, el otro {porcentaje_disposicion_no} ({cantidad_disposicion_no} de {cantidad_disposicion_total}) no están de acuerdo con pagar un monto adicional.'
    # Uso del servicio
    df_usuario_prueba['uso'] = df_usuario_prueba.apply(lambda row: 'Si' if 'Si' in [row['p016_riegodehuertas'], row['p016_lavadodevehiculos'], row['p016_riegodecalle'], row['p016_crianzadeanimales'], row['p016_otro']] else 'No', axis=1)
    cantidad_uso = df_usuario_prueba['uso'].value_counts()
    porcentaje_uso = df_usuario_prueba['uso'].value_counts(normalize=True)*100
    porcentaje_uso_si = "{:0.1f} %".format(porcentaje_uso.get('Si',0))
    porcentaje_uso_no = "{:0.1f} %".format(porcentaje_uso.get('No',0))
    cantidad_uso_si = cantidad_uso.get('Si',0)
    cantidad_uso_total = df_usuario_prueba['uso'].count()

    # Lista de columnas a verificar
    columnas_verificar = ['p016_riegodehuertas', 'p016_lavadodevehiculos', 'p016_riegodecalle', 'p016_crianzadeanimales', 'p016_otro']

    columnas_con_si = []

    for columna in columnas_verificar:
        if (df_usuario_prueba[columna] == 'Si').any():
            columnas_con_si.append(columna)

    nombres_nuevos = {
        'p016_riegodehuertas': 'riego de huertas',
        'p016_lavadodevehiculos': 'lavado de vehículos',
        'p016_riegodecalle': 'riego de calle',
        'p016_crianzadeanimales': 'crianza de animales',
        'p016_otro': 'otro'
    }

    # Cambiar nombres de las columnas en columnas_con_si
    columnas_con_si = [nombres_nuevos.get(col, col) for col in columnas_con_si]
    columnas_con_si_concatenadas = ', '.join(columnas_con_si)

    if porcentaje_uso_no=='100.0 %':
        texto_uso = 'Ninguno de los usuarios entrevistados refieren que le dan otros usos al agua potable.'
    else:
        texto_uso = f'El {porcentaje_uso_si} ({cantidad_uso_si} de {cantidad_uso_total}) de los entrevistados refieren que otros usos le dan al agua: {columnas_con_si_concatenadas}.'

    # Reutilizan el agua
    cantidad_reutiliza = df_usuario_prueba['p017_reutilizaelagua'].value_counts()
    porcentaje_reutiliza  = df_usuario_prueba['p017_reutilizaelagua'].value_counts(normalize=True)*100
    porcentaje_reutiliza_si = "{:0.1f} %".format(porcentaje_reutiliza.get('Si',0))
    porcentaje_reutiliza_no = "{:0.1f} %".format(porcentaje_reutiliza.get('No',0))
    cantidad_reutiliza_si = cantidad_reutiliza.get('Si',0)
    cantidad_reutiliza_no = cantidad_reutiliza.get('No',0)
    cantidad_reutiliza_total = cantidad_reutiliza.get('Si',0) + cantidad_reutiliza.get('No',0)
    texto_reutiliza = f'El {porcentaje_reutiliza_si} ({cantidad_reutiliza_si} de {cantidad_reutiliza_total}) de entrevistados manifiestan que reutilizan el agua.'

    
    ##### Caso: Sin prestador
    es_abastecido_todos = '-'
    es_abastecido_algunos = '-'
    if (df_usuario_prueba['p005_elusuariorecibeelserviciodelprestador'] == 'Si').any():
        es_abastecido_todos = 'Si'
    if (df_usuario_prueba['p005_elusuariorecibeelserviciodelprestador'] == 'No').any():
        es_abastecido_algunos = 'Si'
        
    df_usuario_prueba_no = df_usuario_prueba.loc[df_usuario_prueba['p005_elusuariorecibeelserviciodelprestador'] == 'No']
    # Abastecimiento
    def count_si(column):
        return (df_usuario_prueba_no[column] == 'Si').sum()
    def gasto_promedio(column):
        promedio =  df_usuario_prueba_no.loc[df_usuario_prueba_no[column] == 'Si', 'p002_cuantoeselgastomensualenagua'].mean()
        return round(promedio, 1)
    def litros_promedio(column):
        promedio = df_usuario_prueba_no.loc[df_usuario_prueba_no[column] == 'Si', 'p002a_litrosequivalencia'].mean()
        return round(promedio, 1)
    resumen = {
        'tipo': ['Pozos propios', 'Camiones cisterna', 'Acarreo','Otros'],
        'Cantidad': [count_si('p001_pozopropio'), count_si('p001_camiones'), count_si('p001_acarreo'), count_si('p001_otro')],
        'Gasto Promedio': [gasto_promedio('p001_pozopropio'), gasto_promedio('p001_camiones'), gasto_promedio('p001_acarreo'), gasto_promedio('p001_otro')],
        'Litros Promedio': [litros_promedio('p001_pozopropio'), litros_promedio('p001_camiones'), litros_promedio('p001_acarreo'), litros_promedio('p001_otro')]
    }

    otros_tipos = df_usuario_prueba_no[df_usuario_prueba_no['p001_otro'] == 'Si']['p001a_otraformaabastecimiento'].str.lower().unique()
    otros_tipos = [x for x in otros_tipos if not (isinstance(x, float) and np.isnan(x))] 
  

    resumen_abastecimiento = pd.DataFrame(resumen)
    resumen_abastecimiento['Descripción'] = None 
    resumen_abastecimiento['Descripción'] = resumen_abastecimiento.apply(lambda x: 'otra forma de abastecimiento (' + ', '.join(otros_tipos) + ')' if x['tipo']=='Otros' else x['tipo'].lower(), axis=1)
    resumen_abastecimiento = resumen_abastecimiento.loc[resumen_abastecimiento['Cantidad']!=0]
    total_observaciones = resumen_abastecimiento['Cantidad'].sum()
    try:
        resumen_abastecimiento['Porcentaje'] = ((resumen_abastecimiento['Cantidad'] / total_observaciones) * 100).round(1)
    except ZeroDivisionError:
        print("Error: división por cero")
    # Graficos automaticos abastecimiento
    num_items = len(resumen_abastecimiento)
    if num_items == 0:
        pass
    else:
        plt.figure() 
        colormap = plt.get_cmap('Blues')
        colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
        plt.pie(resumen_abastecimiento['Porcentaje'], labels=resumen_abastecimiento['tipo'], autopct='%1.1f%%', startangle=90, colors=colors, textprops={'fontsize': 20})
        plt.savefig("graphs/grafico_1.png")

    def func(allvalues):
        total = allvalues.sum() 
        #absolute = int(pct / 100. * np.sum(allvalues))
        return "{:.1f}".format(total)
    # Graficos automaticos gasto promedio
    num_items = len(resumen_abastecimiento)
    if num_items == 0:
        pass
    else:
        if num_items == 1:
            if resumen_abastecimiento['Gasto Promedio'].notnull().all():
                plt.figure() 
                colormap = plt.get_cmap('Blues')
                colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
                plt.pie(resumen_abastecimiento['Gasto Promedio'], labels=resumen_abastecimiento['tipo'], startangle=90, colors=colors, autopct=lambda _: func(resumen_abastecimiento['Gasto Promedio']), textprops={'fontsize': 20})
                plt.savefig("graphs/grafico_2.png")
            else:
                plt.figure()
                plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
                plt.axis('off')  # Elimina los ejes
                plt.savefig("graphs/grafico_2.png")
        else:
            if resumen_abastecimiento['Gasto Promedio'].notnull().all():
                plt.figure() 
                colormap = plt.get_cmap('Blues')
                color = colormap(0.5) 
                # Número de categorías
                # Crear una lista de colores usando el mapa de colores
                colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
                # Crear la figura y los ejes
                fig, ax = plt.subplots()
                # Ancho de cada barra
                bar_width = 0.4
                # Crear las barras
                bar_positions = range(len(resumen_abastecimiento))
                bars = ax.bar(bar_positions, resumen_abastecimiento['Gasto Promedio'], color=color, width=bar_width)
                # Establecer las etiquetas de las categorías en el eje x
                plt.xticks(rotation=90)
                ax.set_xticks(bar_positions)
                ax.set_xticklabels(resumen_abastecimiento['tipo'], fontsize=20)
                # Añadir etiquetas de valor en la parte superior de cada barra
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate('{}'.format(height),
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),  # offset vertical
                                textcoords="offset points",
                                ha='center', va='bottom',
                                fontsize=20)
                # Añadir título y etiquetas de los ejes
                #ax.set_title("Cantidad de abastecimiento por frecuencia")
                #ax.set_xlabel("Forma de abastecimiento")
                #ax.set_ylabel("Gasto mensual promedio (S/.)", fontsize=20)
                ax.tick_params(axis='y', labelsize=20)
                # Mostrar el gráfico
                ax.margins(y=0.2) 
                plt.tight_layout()  # Ajustar automáticamente el diseño
                plt.savefig("graphs/grafico_2.png")
            else:
                plt.figure()
                plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
                plt.axis('off')  # Elimina los ejes
                plt.savefig("graphs/grafico_2.png")

    # Graficos automaticos listros promedio
    num_items = len(resumen_abastecimiento)
    if num_items == 0:
        pass
    else:
        if num_items == 1:
            if resumen_abastecimiento['Litros Promedio'].notnull().all():
                plt.figure() 
                colormap = plt.get_cmap('Blues')
                colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
                plt.pie(resumen_abastecimiento['Litros Promedio'], labels=resumen_abastecimiento['tipo'], startangle=90, colors=colors, autopct=lambda _: func(resumen_abastecimiento['Litros Promedio']), textprops={'fontsize': 20})
                plt.savefig("graphs/grafico_3.png")
            else:
                plt.figure()
                plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
                plt.axis('off')  # Elimina los ejes
                plt.savefig("graphs/grafico_3.png")
        else:
            if resumen_abastecimiento['Litros Promedio'].notnull().all():
                plt.figure() 
                colormap = plt.get_cmap('Blues')
                color = colormap(0.5) 
                # Crear una lista de colores usando el mapa de colores
                colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
                # Crear la figura y los ejes
                fig, ax = plt.subplots()
                # Ancho de cada barra
                bar_width = 0.4
                # Crear las barras
                bar_positions = range(len(resumen_abastecimiento))
                bars = ax.bar(bar_positions, resumen_abastecimiento['Litros Promedio'], color=color, width=bar_width)
                # Establecer las etiquetas de las categorías en el eje x
                plt.xticks(rotation=90)
                ax.set_xticks(bar_positions)
                ax.set_xticklabels(resumen_abastecimiento['tipo'], fontsize=20)
                # Añadir etiquetas de valor en la parte superior de cada barra
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate('{}'.format(height),
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),  # offset vertical
                                textcoords="offset points",
                                ha='center', va='bottom',
                                fontsize=20)
                # Añadir título y etiquetas de los ejes
                #ax.set_title("Cantidad de abastecimiento por frecuencia")
                #ax.set_xlabel("Forma de abastecimiento")
                #ax.set_ylabel("Consumo promedio al mes (litros)", fontsize=20)
                ax.tick_params(axis='y', labelsize=20)
                # Mostrar el gráfico
                ax.margins(y=0.2) 
                plt.tight_layout()  # Ajustar automáticamente el diseño
                plt.savefig("graphs/grafico_3.png")
            else:
                plt.figure()
                plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
                plt.axis('off')  # Elimina los ejes
                plt.savefig("graphs/grafico_3.png")

    resumen_abastecimiento = resumen_abastecimiento.fillna('-')
    abastecimiento = []
    for index, row in resumen_abastecimiento.iterrows():
        texto_abastecimiento = f"El {row['Porcentaje']}% de los entrevistados mencionan que se abastecen mediante {row['Descripción']}."
        abastecimiento.append(texto_abastecimiento)
    gastomensual = []
    for index, row in resumen_abastecimiento.iterrows():
        texto_gastoagua = f"En promedio, los usuarios que se abastecen mediante {row['Descripción']} gastan mensualmente S/. {row['Gasto Promedio']} soles para obtener el agua."
        gastomensual.append(texto_gastoagua)
    litrosagua = []
    for index, row in resumen_abastecimiento.iterrows():
        texto_listrosagua = f"En promedio, los usuarios que se abastecen mediante {row['Descripción']} consumen mensualmente {row['Litros Promedio']} litros de agua al mes."
        litrosagua.append(texto_listrosagua)

    cant_vecesabast = df_usuario_prueba_no['p003_cuantasvecesalmesseabastece'].value_counts().reset_index().rename(columns={'p003_cuantasvecesalmesseabastece':'frecuencia','count':'Cantidad'})
    porc_vecesabast = df_usuario_prueba_no['p003_cuantasvecesalmesseabastece'].value_counts(normalize=True).reset_index().rename(columns={'p003_cuantasvecesalmesseabastece':'frecuencia','proportion':'Porcentaje'})
    porc_vecesabast['Porcentaje'] *= 100
    vecesabast = pd.merge(cant_vecesabast,porc_vecesabast,on='frecuencia',how='inner')

    # Graficos automaticos frecuencia de pago
    num_items = len(vecesabast)
    if num_items == 1:
        if vecesabast['Cantidad'].notnull().all():
            plt.figure() 
            colormap = plt.get_cmap('Blues')
            colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
            plt.pie(vecesabast['Cantidad'], labels=vecesabast['frecuencia'], startangle=90, colors=colors, autopct=lambda _: func(vecesabast['Cantidad']), textprops={'fontsize': 20})
            plt.savefig("graphs/grafico_4.png")
        else:
            plt.figure()
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')  # Elimina los ejes
            plt.savefig("graphs/grafico_4.png")
    else:
        if vecesabast['Cantidad'].notnull().all():
            plt.figure() 
            colormap = plt.get_cmap('Blues')
            color = colormap(0.5) 
            
            # Crear una lista de colores usando el mapa de colores
            colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]

            # Crear la figura y los ejes
            fig, ax = plt.subplots()

            # Ancho de cada barra
            bar_width = 0.4

            # Crear las barras
            bar_positions = range(len(vecesabast))
            bars = ax.bar(bar_positions, vecesabast['Cantidad'], color=color, width=bar_width)

            # Establecer las etiquetas de las categorías en el eje x
            plt.xticks(rotation=90)
            ax.set_xticks(bar_positions)
            ax.set_xticklabels(vecesabast['frecuencia'], fontsize=20)

            # Añadir etiquetas de valor en la parte superior de cada barra
            for bar in bars:
                height = bar.get_height()
                ax.annotate('{}'.format(height),
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),  # offset vertical
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=20)

            # Añadir título y etiquetas de los ejes
            #ax.set_title("Cantidad de abastecimiento por frecuencia")
            #ax.set_xlabel("Frecuencia de abastecimiento")
            #ax.set_ylabel("Consumo promedio al mes (litros)", fontsize=20)
            ax.tick_params(axis='y', labelsize=20)
            #plt.subplots_adjust(bottom=0.2) 
            # Mostrar el gráfico
            ax.margins(y=0.2) 
            plt.tight_layout()  # Ajustar automáticamente el diseño
            plt.savefig("graphs/grafico_4.png")
        else:
            plt.figure()
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')  # Elimina los ejes
            plt.savefig("graphs/grafico_4.png")

    frecuencias = []
    for index, row in vecesabast.iterrows():
        texto_frecuencia = f"El {'{:0.1f} %'.format(row['Porcentaje'])} de los entrevistados mencionan que su abastecimiendo tiene periodicidad {row['frecuencia']}."
        frecuencias.append(texto_frecuencia)

    df_gastos = pd.DataFrame({
        'Categoria': ['Electricidad', 'Telefonía', 'Cable', 'Internet', 'Netflix', 'Gas'],
        'Promedio de Gasto': [
            df_usuario_prueba_no['p014a_gastomensualsolesenelectricidad'].mean(),
            df_usuario_prueba_no['p014b_gastomensualsolesentelefoniacelular'].mean(),
            df_usuario_prueba_no['p014c_gastomensualsolesencable'].mean(),
            df_usuario_prueba_no['p014d_gastomensualsoleseninternet'].mean(),
            df_usuario_prueba_no['p014e_gastomensualsolesenstreamingnetflixetc'].mean(),
            df_usuario_prueba_no['p014h_gastomensualsolesengas'].mean()
        ]
    })

    df_gastos = df_gastos.dropna(subset=['Promedio de Gasto'])
    df_gastos['Promedio de Gasto'] = df_gastos['Promedio de Gasto'].round(1)
    gastos = []
    for index, row in df_gastos.iterrows():
        texto_gasto = f"En promedio, los usuarios gastan S/. {row['Promedio de Gasto']} soles para el servicio de {row['Categoria']} al mes."
        gastos.append(texto_gasto)


    # Graficos automaticos gasto de otros servicios
    num_items = len(df_gastos)
    if num_items == 0:
        pass
    else:
        if num_items == 1:
            if df_gastos['Promedio de Gasto'].notnull().all():
                plt.figure() 
                colormap = plt.get_cmap('Blues')
                colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
                plt.pie(df_gastos['Promedio de Gasto'], labels=df_gastos['Categoria'], startangle=90, colors=colors, autopct=lambda _: func(df_gastos['Promedio de Gasto']), textprops={'fontsize': 20})
                plt.savefig("graphs/grafico_5.png")
            else:
                plt.figure()
                plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
                plt.axis('off')  # Elimina los ejes
                plt.savefig("graphs/grafico_5.png")
        else:
            if df_gastos['Promedio de Gasto'].notnull().all():
                plt.figure() 
                colormap = plt.get_cmap('Blues')
                color = colormap(0.5) 

                # Crear una lista de colores usando el mapa de colores
                colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]

                # Crear la figura y los ejes
                fig, ax = plt.subplots()

                # Ancho de cada barra
                bar_width = 0.4

                # Crear las barras
                bar_positions = range(len(df_gastos))
                bars = ax.bar(bar_positions, df_gastos['Promedio de Gasto'], color=color, width=bar_width)

                # Establecer las etiquetas de las categorías en el eje x
                plt.xticks(rotation=90)
                ax.set_xticks(bar_positions)
                ax.set_xticklabels(df_gastos['Categoria'], fontsize=20)
                

                # Añadir etiquetas de valor en la parte superior de cada barra
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate('{}'.format(height),
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),  # offset vertical
                                textcoords="offset points",
                                ha='center', va='bottom',
                                fontsize=20)

                # Añadir título y etiquetas de los ejes
                #ax.set_title("Cantidad de abastecimiento por frecuencia")
                #ax.set_xlabel("Frecuencia de abastecimiento")
                #ax.set_ylabel("Gasto promedio (S/.)", fontsize=20)
                ax.tick_params(axis='y', labelsize=20)
                # Mostrar el gráfico
                ax.margins(y=0.2) 
                plt.tight_layout()  # Ajustar automáticamente el diseño
                plt.savefig("graphs/grafico_5.png")
            else:
                plt.figure()
                plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
                plt.axis('off')  # Elimina los ejes
                plt.savefig("graphs/grafico_5.png")

    df_usuario_prueba_no['abastecimiento'] = df_usuario_prueba_no.apply(lambda row: 'Si' if 'Si' in [row['p001_acarreo'], row['p001_camiones'], row['p001_pozopropio'], row['p001_otro']] else 'No', axis=1)

    df_usuario_prueba_no['otroabastecimiento'] = df_usuario_prueba_no.apply(lambda x: x['p001_otro'] if pd.isna(x['p001a_otraformaabastecimiento']) or x['p001a_otraformaabastecimiento'] == '' else x['p001_otro'] + x['p001a_otraformaabastecimiento'], axis=1)


    cantidad_abastecimiento = df_usuario_prueba_no['abastecimiento'].value_counts()

    porcentaje_abastecimiento = df_usuario_prueba_no['abastecimiento'].value_counts(normalize=True)*100
    porcentaje_abastecimiento_si = "{:0.1f} %".format(porcentaje_abastecimiento.get('Si',0))
    porcentaje_abastecimiento_no = "{:0.1f} %".format(porcentaje_abastecimiento.get('No',0))
    cantidad_abastecimiento_si = cantidad_abastecimiento.get('Si',0)
    cantidad_abastecimiento_total = df_usuario_prueba_no['abastecimiento'].count()

    columnas_verificar = ['p001_acarreo', 'p001_camiones', 'p001_pozopropio', 'p001_otro']
    columnas_con_si = []
    for columna in columnas_verificar:
        if (df_usuario_prueba[columna] == 'Si').any():
            columnas_con_si.append(columna)
    nombres_nuevos = {
        'p001_acarreo': 'acarreo',
        'p001_camiones': 'camiones cisterna',
        'p001_pozopropio': 'pozos propios',
        'p001_otro': 'otro'
    }
    columnas_con_si = [nombres_nuevos.get(col, col) for col in columnas_con_si]
    columnas_con_si_concatenadas = ', '.join(columnas_con_si)

    if porcentaje_abastecimiento_no=='100.0 %':
        texto_abastecimiento = 'Ninguno de los usuarios entrevistados ha mencionado información sobre abastecimiento alternativo de agua potable.'
    else:
        texto_abastecimiento = f'El {porcentaje_abastecimiento_si} ({cantidad_abastecimiento_si} de {cantidad_abastecimiento_total}) de los entrevistados menciona que el abastecimiento es a través de {columnas_con_si_concatenadas}.'


    # Gasto mensual

    gasto_agua = df_usuario_prueba_no['p002_cuantoeselgastomensualenagua'].mean()
    gasto_agua = "-" if pd.isna(gasto_agua) else round(gasto_agua,1)
    cantidad_no_nulos = df_usuario_prueba_no['p002_cuantoeselgastomensualenagua'].notnull().sum()
    try:
        porcentaje_no_nulos = (cantidad_no_nulos / len(df_usuario_prueba_no)) * 100 
    except ZeroDivisionError:
        print("Error: división por cero")
    porcentaje_no_nulos = "{:0.1f} %".format(porcentaje_no_nulos)

    texto_gasto_agua = f'El {porcentaje_no_nulos} de usuarios entrevistados refieren que para abastecerse de agua gastan en promedio {gasto_agua} soles mensuales.'
    if (cantidad_no_nulos == 0):
        texto_gasto_agua = 'Ninguno de los usuarios entrevistados refieren gasto promedio en abastecimiento de agua.'

    # Disposicion a recibir servicio
    cantidad_disposicion_recibir = df_usuario_prueba_no['p013a_estariadispuestoqueesteotrolebrindeserv'].value_counts()
    porcentaje_disposicion_recibir = df_usuario_prueba_no['p013a_estariadispuestoqueesteotrolebrindeserv'].value_counts(normalize=True)*100
    porcentaje_porcentaje_disposicion_recibir_si = "{:0.1f} %".format(porcentaje_disposicion_recibir.get('Si',0))
    porcentaje_porcentaje_disposicion_recibir_no = "{:0.1f} %".format(porcentaje_disposicion_recibir.get('No',0))
    cantidad_porcentaje_disposicion_recibir_si = cantidad_disposicion_recibir.get('Si',0)
    cantidad_porcentaje_disposicion_recibir_total = df_usuario_prueba_no['p013a_estariadispuestoqueesteotrolebrindeserv'].count()
    nombre_prestador = df_usuario_prueba_no['p013_1_nombreyubicaciondeprestador'].dropna()


    texto_disposicion_recibir = f'El {porcentaje_porcentaje_disposicion_recibir_si} ({cantidad_porcentaje_disposicion_recibir_si} de {cantidad_porcentaje_disposicion_recibir_total}) de usuarios refieren que estarían de acuerdo con que el prestador {nombre_prestador}, les provea del servicio.'


    # Gasto mensual en otros servicios
    gasto_electricidad = df_usuario_prueba['p014a_gastomensualsolesenelectricidad'].mean()
    gasto_electricidad = '-' if pd.isna(gasto_electricidad) else round(gasto_electricidad,1)
    gasto_telefonia = df_usuario_prueba['p014b_gastomensualsolesentelefoniacelular'].mean()
    gasto_telefonia = '-' if pd.isna(gasto_telefonia) else round(gasto_telefonia,1)
    texto_gasto_otroservicio = f'En promedio, el gasto en servicio de electricidad es de S/. {gasto_electricidad} y en telefonía celular es de S/. {gasto_telefonia}.'



    ###############

    #Enlace de informe
    #type_tiny = pyshorteners.Shortener()
    #link_fichas = type_tiny.tinyurl.short(df_prueba['rutafichas'].values[0], timeout=5)
    link_fichas = df_prueba['rutafichas'].values[0]
    # link = RichText('You can add here ')
    # link.add('prueba', url_id = doc.build_url_id(link_fichas))
    link = RichText()
    link.add(link_fichas,url_id = doc.build_url_id(link_fichas))


    # Recursos fotograficos
    carpetaprestador = df_prueba['carpetaprestador'].values[0]
    ruta_carpeta_fotos = ruta_fotos + "\\" + carpetaprestador
    
    #Formatos de imagen
    formatos_imagen = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]
    imageObjs = []
    for fPath in natsorted(glob.glob(os.path.join(ruta_fotos, carpetaprestador, 'FOTOS', '*'))):
        # Verificar si la extensión del archivo está en la lista de formatos de imagen
        if os.path.splitext(fPath)[1].lower() in formatos_imagen:
            # Verificar si la imagen es un archivo JPEG y tiene coordenadas GPS
            #if os.path.splitext(fPath)[1].lower() == '.jpg' and obtener_coordenadas_gps(fPath):
            if obtener_coordenadas_gps(fPath):
                    # Convertir la imagen JPEG a PNG en memoria y corregir la rotación
                with open(fPath, "rb") as f:
                    jpeg_bytes = f.read()
                png_bytes = jpeg_to_png_in_memory(jpeg_bytes)
                    # Agregar la imagen PNG a la lista imageObjs
                imgObj = InlineImage(doc, BytesIO(png_bytes), width=Inches(3))
                imageObjs.append(imgObj)
            else:
                # Agregar la imagen tal como está a la lista imageObjs
                try:
                    # Agregando la funcion jpeg_to_png_in_memory (para evaluar)
                    with open(fPath, "rb") as f:
                        jpeg_bytes = f.read()
                    png_bytes = jpeg_to_png_in_memory(jpeg_bytes)
                    # imgObj = InlineImage(doc, fPath, width=Inches(3))
                    imgObj = InlineImage(doc, BytesIO(png_bytes), width=Inches(3))
                    imageObjs.append(imgObj)
                except (IOError, OSError):
                    # Ignorar archivos que no se puedan abrir como imágenes
                    pass
 

    # num_rows = (len(imageObjs) + 1) // 2
    # Crear una lista de listas para organizar las imágenes en filas y columnas
    images_matrix = [imageObjs[i:i+2] for i in range(0, len(imageObjs), 2)]
 
    # Procesando imagenes de las actas
    imageActas = []
    # for fPath in natsorted(glob.glob(ruta_fotos + '/' + carpetaprestador+'/ACTAS/*')):
    #     imgActa = InlineImage(doc, fPath, width=Inches(5))
    #     imageActas.append(imgActa)
    
    for fPath in natsorted(glob.glob(os.path.join(ruta_fotos, carpetaprestador, 'ACTAS', '*'))):
        # Verifica si la extensión del archivo está en la lista de formatos de imagen
        if os.path.splitext(fPath)[1].lower() in formatos_imagen:
            # Abre la imagen para verificar si es una imagen válida
            try:
                #Image.open(fPath)
                # Si no hay excepciones al abrir la imagen, entonces la agregamos
                imgActa = InlineImage(doc, fPath, width=Inches(5))
                imageActas.append(imgActa)
            except (IOError, OSError):
                # Ignorar archivos que no se puedan abrir como imágenes
                pass
    ########################################## Renderizando

    context = {
        "anio": anio,"texto_asunto":texto_asunto,"ods":ods,"ambito_ccpp_p":ambito_ccpp_p,"ubigeo_ccpp_p":ubigeo_ccpp_p,"pobtotal_ccpp_p":pobtotal_ccpp_p,
        "vivtotal_ccpp_p":vivtotal_ccpp_p,"fecha_caracterizacion": fecha_caracterizacion, "es_prestador":es_prestador,"abastecimiento_sp":abastecimiento_sp,"gasto_sp":gasto_sp,
        "nomprest": nomprest,"texto_objetivo":texto_objetivo,
        "ccpp_p": ccpp_p,
        "dist_p": dist_p, "prov_p": prov_p, "dep_p": dep_p, "nom_representante":nom_representante, "cargo_representante": cargo_representante,
        "ambito_prestador": ambito_prestador, "tipo_prestador": tipo_prestador, "subtipo_prestador": subtipo_prestador, "agua": agua,
        "alca": alca, "tar": tar, "excretas":excretas, "poblacionServida": poblacionServida,'ugm_rural_1':ugm_rural_1,'ugm_rural_2':ugm_rural_2,
        'ugm_pc_1':ugm_pc_1,'ugm_pc_2':ugm_pc_2,'oc_1':oc_1,'oc_2':oc_2,'oe_1':oe_1,'oe_2':oe_2,'recibio_asistencia':recibio_asistencia,
        'actor_asistencia':actor_asistencia,'tema_asistencia':tema_asistencia,'cobra_cuota':cobra_cuota,'frecuencia_cobro':frecuencia_cobro,'flujo_cuota':flujo_cuota,'cobraporcadaservicio':cobraporcadaservicio,
        'metodologia_oc':metodologia_oc,'antiguedad_cuota':antiguedad_cuota,
        'elcobroquerealizaes':elcobroquerealizaes,'elpagoestructuradodependedelamicromedicion':elpagoestructuradodependedelamicromedicion,'tipo_tarifa':elcobroquerealizaes,
        'conex_act':conex_act,'conex_act_alca':conex_act_alca,'monto_cuota':monto_cuota,'monto_agua':monto_agua,'monto_alca':monto_alca,'monto_de':monto_de,'monto_tar':monto_tar,'cx_domestico':cx_domestico,'cx_comercial':cx_comercial,
        'cx_industrial':cx_industrial,'cx_social':cx_social,'agua_dom':agua_dom,'agua_com':agua_com,'agua_indus':agua_indus,'agua_social':agua_social,'alca_dom':alca_dom,'alca_com':alca_com,'alca_indus':alca_indus,
        'alca_social':alca_social,'otro_dom':otro_dom,'otro_com':otro_com,'otro_indus':otro_indus,'otro_social':otro_social, 'd_sol1':d_sol1, 'd_de1':d_de1, 'd_hasta1':d_hasta1, 'd_sol2':d_sol2, 'd_de2':d_de2,'d_hasta2':d_hasta2,
        'c_sol1':c_sol1, 'c_de1':c_de1, 'c_hasta1':c_hasta1, 'c_sol2':c_sol2, 'c_de2':c_de2, 'c_hasta2':c_hasta2, 'i_sol1':i_sol1, 'i_de1':i_de1, 'i_hasta1':i_hasta1, 'i_sol2':i_sol2, 'i_de2':i_de2, 'i_hasta2':i_hasta2,
        's_sol1':s_sol1, 's_de1':s_de1, 's_hasta1':s_hasta1, 's_sol2':s_sol2, 's_de2':s_de2, 's_hasta2':s_hasta2,
        'conex_morosidad':conex_morosidad,'conex_exoner':conex_exoner,
        'colateral_agua':colateral_agua,'colateral_alca':colateral_alca,'colateral_micro':colateral_micro,'colateral_repo':colateral_repo,
        'g1_si':g1_si,'g1_no':g1_no,'g2_si':g2_si,'g2_no':g2_no,'g3_si':g3_si,'g3_no':g3_no,'g4_si':g4_si,'g4_no':g4_no,'g5_si':g5_si,'g5_no':g5_no,
        'op':op,'op1':op1,'op1_frec':op1_frec,'op1_costo':op1_costo,'op1_anual':op1_anual,'op2':op2,'op2_frec':op2_frec,'op2_costo':op2_costo,'op2_anual':op2_anual,
        'op3':op3,'op3_frec':op3_frec,'op3_costo':op3_costo,'op3_anual':op3_anual,'m':m,'m_frec':m_frec,'m_costo':m_costo,'m_anual':m_anual,'adm':adm,'adm_frec':adm_frec,'adm_costo':adm_costo,'adm_anual':adm_anual,
        're':re,'re_frec':re_frec,'re_costo':re_costo,'re_anual':re_anual,'rm':rm,'rm_frec':rm_frec,'rm_costo':rm_costo,'rm_anual':rm_anual,'otro':otro,'otros_frec':otros_frec,'otros_costo':otros_costo,'otros_anual':otros_anual,"valor_ref":valor_ref,
        'costoAnual':costoAnual,'peligro1_si':peligro1_si,'peligro1_no':peligro1_no,'peligro2_si':peligro2_si,'peligro2_no':peligro2_no,'peligro3_si':peligro3_si,'peligro3_no':peligro3_no,
        'recibio_asistencia_lab':recibio_asistencia_lab,'es_formal_lab':es_formal_lab, 'costoAnual_lab':costoAnual_lab, 'cuota_cubre_lab':cuota_cubre_lab,
        'fuentes':fuentes, 'in_1':texto_infra1, 'in_2':texto_infra2, 'in_3':texto_infra3, 'in_4':texto_infra4, 'licenciauso_lab':licenciauso_lab,'in_4lab':texto_infra4_lab,
        #Usuarios
        'texto_cobro':texto_cobro,'porcentaje_cobro_si':porcentaje_cobro_si, 'texto_satisfaccion':texto_satisfaccion, 'porcentaje_satisfaccion_si':porcentaje_satisfaccion_si,'texto_disposicion':texto_disposicion,
        'porcentaje_disposicion_si':porcentaje_disposicion_si, 'texto_uso':texto_uso, 'texto_reutiliza':texto_reutiliza, 'porcentaje_reutiliza_si':porcentaje_reutiliza_si, 'es_abastecido_todos':es_abastecido_todos,
        'es_abastecido_algunos':es_abastecido_algunos,'texto_abastecimiento':texto_abastecimiento, 'texto_gasto_agua':texto_gasto_agua, 'texto_disposicion_recibir':texto_disposicion_recibir, 'texto_gasto_otroservicio':texto_gasto_otroservicio,
        "sistemasdeagua": sistemas_de_agua,'sistemas_de_agua_convecional':sistemas_de_agua_convecional,'sistemas_de_agua_noconvencional':sistemas_de_agua_noconvencional,'tipodesistemadealcantarilladosanitario':tipodesistemadealcantarilladosanitario,
        'anodeconstruccionalca':anodeconstruccionalca,'eoalca':eoalca,'descripcionalca':descripcionalca,'eoebar':eoebar,'descripcionebar':descripcionebar,
        'comentariossistemaalcantarillado':comentariossistemaalcantarillado,'anodeconstruccionptar':anodeconstruccionptar,'antiguedadalca':antiguedadalca,
        'p008_realizamantenimientoalareddealcantarillado':p008_realizamantenimientoalareddealcantarillado,'p029_autorizaciondevertimiento':p029_autorizaciondevertimiento,
        'tiene_alca':tiene_alca,'tiene_ptar':tiene_ptar,'alcantarilladoadministradoporunaeps':alcantarilladoadministradoporunaeps,'comentariosptar':comentariosptar,
        'listadopreliminar':lista_total,'coordenadas':coordenadas,'tiene_ubs':tiene_ubs,'tipoubs':tipoubs,'tipo_ubs_aux':tipo_ubs_aux,'anioubs':anioubs,'comentariosubs':comentariosubs,
        'tiene_noadecuado':tiene_noadecuado,'tiponoadecuado':tiponoadecuado,'comentarionoadecuado':comentarionoadecuado, 'eofinalca':eofinalca, 'noconvencional':noconvencional,
        'convencional':convencional, 'link':link, 'comentarios_prestador':comentarios_prestador,'images_matrix': images_matrix,'imageActas':imageActas,
        'comentariosfuente':comentariosfuente, 'abastecimiento':abastecimiento,'gastomensual':gastomensual,'litrosagua':litrosagua,'frecuencias':frecuencias,'gastos':gastos,
        "grafico_1":InlineImage(doc, "graphs/grafico_1.png", width = Inches(2)), "grafico_2":InlineImage(doc, "graphs/grafico_2.png", width = Inches(2)), "grafico_3":InlineImage(doc, "graphs/grafico_3.png", width = Inches(2)), 
        "grafico_4":InlineImage(doc, "graphs/grafico_4.png", width = Inches(2)), "grafico_5":InlineImage(doc, "graphs/grafico_5.png", width = Inches(2))
            

    }

    doc.render(context)
    print(df_prueba['codigodeprestador'].values[0])
    # doc.save(f"{ruta_carpeta_fotos}\\INFORME_{df_prueba['codigodeprestador'].values[0]}.docx")
    doc.save(f"./reports/INFORME_{df_prueba['codigodeprestador'].values[0]}.docx")
