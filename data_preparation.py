# data_preparation.py
import pandas as pd
import numpy as np
from babel.dates import format_date
from datetime import datetime
import math
import logging

# Asumiendo que tienes estas funciones en utils.py (como se definió antes)
from utils import (
    calcular_costo_anual,
    determinar_estado_mantenimiento_fila,
    calcular_anios_antiguedad,
    determinar_estado_operativo_grupo,
    evaluar_estado_operativo_alcantarillado,
    formatear_valor,
    obtener_valor_o_defecto # Asegúrate que esta función maneje series o df y columna
)

logger = logging.getLogger(__name__)

def _get_value(df, column, default="-"):
    """Función interna para simplificar la obtención de valor de la primera fila."""
    if df.empty or column not in df.columns:
        return default
    val = df[column].iloc[0]
    return val if pd.notna(val) else default


def preparar_datos_generales_y_poblacion(df_prestador_actual, inei_2017_df, df_ps_actual, df_fuente_actual):
    context_dg = {}
    df_merged_prestador = df_prestador_actual.copy()

    if df_merged_prestador.empty:
        # Devuelve un diccionario de contexto con valores por defecto
        default_context_keys = [
            "anio", "texto_asunto", "ods", "ambito_ccpp_p", "ubigeo_ccpp_p", "pobtotal_ccpp_p",
            "vivtotal_ccpp_p", "fecha_caracterizacion", "es_prestador", "abastecimiento_sp",
            "gasto_sp", "nomprest", "texto_objetivo", "ccpp_p", "dist_p", "prov_p", "dep_p",
            "nom_representante", "cargo_representante", "ambito_prestador", "tipo_prestador",
            "subtipo_prestador", "agua", "alca", "tar", "excretas", "comentarios_prestador",
            "comentariosfuente"
        ]
        for key in default_context_keys: context_dg[key] = "-"
        context_dg["anio"] = datetime.now().year
        context_dg["pobtotal_ccpp_p"] = "0"
        context_dg["vivtotal_ccpp_p"] = "0"
        context_dg["poblacionServida"] = []
        return context_dg, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- Datos Generales ---
    oficina_val = _get_value(df_merged_prestador, 'p001_oficinadesconcentrada')
    ods_map = {
        'SEDE CENTRAL': 'DAP-UFDMS', 'ANCASH - HUARAZ': 'ODS-HUR', 'ANCASH - CHIMBOTE': 'ODS-CHI',
        'LA LIBERTAD': 'ODS-LLI', 'MADRE DE DIOS': 'ODS-MDD', 'HUÁNUCO': 'ODS-HUN'
    }
    context_dg['ods'] = ods_map.get(oficina_val, f'ODS-{oficina_val[:3].upper()}' if oficina_val and oficina_val != '-' else '-')
    
    context_dg['ambito_ccpp_p'] = _get_value(df_merged_prestador, 'ambito_ccpp')
    context_dg['ubigeo_ccpp_p'] = _get_value(df_merged_prestador, 'ubigeo_ccpp')
    context_dg['pobtotal_ccpp_p'] = _get_value(df_merged_prestador, 'POBTOTAL', 0)
    context_dg['vivtotal_ccpp_p'] = _get_value(df_merged_prestador, 'VIVTOTAL', 0)

    nombres_abast = {
        "p009_pozospropios": "Pozos propios", "p009_camioncisterna": "Camión cisterna",
        "p009_acarreo": "Acarreo", "p009_otro": "Otro"
    }
    lista_abast = [nombres_abast[col] for col in nombres_abast if _get_value(df_merged_prestador, col) == "Si"]
    abast_sp_val = "-"
    if lista_abast:
        abast_sp_val = ", ".join(lista_abast)
        if "Otro" in lista_abast:
            otro_detalle = _get_value(df_merged_prestador, "p009a_comoseabasteceotro")
            if otro_detalle != "-":
                abast_sp_val += f" - {otro_detalle}"
    context_dg['abastecimiento_sp'] = abast_sp_val
    context_dg['gasto_sp'] = formatear_valor(_get_value(df_merged_prestador, 'p010_gastomensualpromedioporfamiliaagua'))

    fecha_car_dt_val = _get_value(df_merged_prestador, 'p002_fechadecaracterizacion', None)
    if pd.notna(fecha_car_dt_val) and isinstance(fecha_car_dt_val, (datetime, pd.Timestamp)):
        context_dg['anio'] = fecha_car_dt_val.year
        context_dg['fecha_caracterizacion'] = format_date(fecha_car_dt_val, "d 'de' MMMM 'del' yyyy", locale='es')
    else:
        context_dg['anio'] = datetime.now().year
        context_dg['fecha_caracterizacion'] = "-"

    context_dg['es_prestador'] = _get_value(df_merged_prestador, 'existeprestadordessenelccppprincipal')
    context_dg['nomprest'] = _get_value(df_merged_prestador, 'p016_nombredelprestador')
    context_dg['ccpp_p'] = str(_get_value(df_merged_prestador, 'p005_nombredelcentropobladoprincipal')).title()
    context_dg['dist_p'] = str(_get_value(df_merged_prestador, 'NOMDIST')).title()
    context_dg['prov_p'] = str(_get_value(df_merged_prestador, 'NOMPROV')).title()
    context_dg['dep_p'] = str(_get_value(df_merged_prestador, 'NOMDEP')).title()
    context_dg['nom_representante'] = str(_get_value(df_merged_prestador, 'p008a_nombreyapellido')).title()
    context_dg['cargo_representante'] = str(_get_value(df_merged_prestador, 'p008b_cargo')).lower()
    context_dg['ambito_prestador'] = _get_value(df_merged_prestador, 'p019_ambitodeprestador')
    context_dg['tipo_prestador'] = _get_value(df_merged_prestador, 'p031_quetipodeprestadores')
    context_dg['subtipo_prestador'] = _get_value(df_merged_prestador, 'p031B01_formaasociativadeoc')
    context_dg['agua'] = _get_value(df_merged_prestador, 'p018_agua')
    context_dg['alca'] = _get_value(df_merged_prestador, 'p018_alcantarillado')
    context_dg['tar'] = _get_value(df_merged_prestador, 'p018_tar')
    context_dg['excretas'] = _get_value(df_merged_prestador, 'p018_disposicionexcretas')

    if context_dg['es_prestador'] == 'Si':
        context_dg['texto_asunto'] = f"Informe de caracterización del prestador {context_dg['nomprest']}, del centro poblado de {context_dg['ccpp_p']}, distrito de {context_dg['dist_p']}, provincia de {context_dg['prov_p']}, departamento de {context_dg['dep_p']}."
        context_dg['texto_objetivo'] = f"Mostrar los principales resultados del proceso de caracterización de los servicios de agua potable y saneamiento brindados por el prestador {context_dg['nomprest']}."
    else:
        context_dg['texto_asunto'] = f"Informe de caracterización del centro poblado {context_dg['ccpp_p']}, distrito de {context_dg['dist_p']}, provincia de {context_dg['prov_p']}, departamento de {context_dg['dep_p']}."
        context_dg['texto_objetivo'] = f"Mostrar los principales resultados del proceso de caracterización en el centro poblado {context_dg['ccpp_p']} que cuenta con un abastecimiento sin prestador."

    context_dg['comentarios_prestador'] = _get_value(df_merged_prestador, 'comentarios')
    context_dg['comentariosfuente'] = _get_value(df_merged_prestador, 'comentariosfuente')

    # --- Población Servida ---
    df_ps_procesado = pd.DataFrame()
    poblacion_servida_list = []
    if not df_ps_actual.empty and not inei_2017_df.empty:
        # Asumimos que df_ps_actual ya tiene 'centropoblado' y los campos de conexiones
        # y que inei_2017_df tiene 'ubigeo_ccpp'
        # Asegurar que las columnas de merge sean del mismo tipo
        df_ps_actual_copy = df_ps_actual.copy()
        inei_2017_df_copy = inei_2017_df.copy()
        df_ps_actual_copy['centropoblado_str'] = df_ps_actual_copy['centropoblado'].astype(str)
        inei_2017_df_copy['ubigeo_ccpp_str'] = inei_2017_df_copy['ubigeo_ccpp'].astype(str)
        df_ps_procesado = pd.merge(df_ps_actual_copy, inei_2017_df_copy, left_on='centropoblado_str', right_on='ubigeo_ccpp_str', how='inner')
        
        if not df_ps_procesado.empty:
            df_ps_procesado['POBTOTAL_corr'] = np.where(df_ps_procesado['POBTOTAL'].fillna(0) == 0, np.nan, df_ps_procesado['POBTOTAL'])
            df_ps_procesado['densidad_pob_corr'] = df_ps_procesado['densidad_pob'].fillna(0)


            df_ps_procesado['cobagua'] = (df_ps_procesado['p021_conexionesdeaguatotales'].fillna(0) * df_ps_procesado['densidad_pob_corr'] / df_ps_procesado['POBTOTAL_corr']) * 100
            df_ps_procesado['cobalca'] = (df_ps_procesado['p023_conexionesdealcantarilladototales'].fillna(0) * df_ps_procesado['densidad_pob_corr'] / df_ps_procesado['POBTOTAL_corr']) * 100
            
            df_ps_procesado['cobagua'] = df_ps_procesado['cobagua'].apply(lambda x: min(x, 100.0) if pd.notna(x) else np.nan).round(1)
            df_ps_procesado['cobalca'] = df_ps_procesado['cobalca'].apply(lambda x: min(x, 100.0) if pd.notna(x) else np.nan).round(1)

            for _, row in df_ps_procesado.iterrows():
                poblacion_servida_list.append({
                    "ubigeo": _get_value(row.to_frame().T, 'ubigeo_ccpp_str'), #_x si hay conflicto
                    "nomccpp": _get_value(row.to_frame().T, 'NOMCCPP'),
                    "viviendas": formatear_valor(_get_value(row.to_frame().T, 'VIVTOTAL')),
                    "aguaTot": formatear_valor(_get_value(row.to_frame().T, "p021_conexionesdeaguatotales")),
                    "aguaAct": formatear_valor(_get_value(row.to_frame().T, "p022_conexionesdeaguaactivas")),
                    "alcaTot": formatear_valor(_get_value(row.to_frame().T, "p023_conexionesdealcantarilladototales")),
                    "alcaAct": formatear_valor(_get_value(row.to_frame().T, "p024_conexionesdealcantarilladoactivas")),
                    "cobagua": formatear_valor(_get_value(row.to_frame().T, "cobagua"), defecto="- %"),
                    "cobalca": formatear_valor(_get_value(row.to_frame().T, "cobalca"), defecto="- %"),
                    "numUbs": formatear_valor(_get_value(row.to_frame().T, "p027_cantidaddeubsenelccpp"))
                })
    context_dg['poblacionServida'] = poblacion_servida_list
    
    return context_dg, df_merged_prestador, df_ps_procesado, df_fuente_actual


def preparar_constitucion_prestador(df_prestador_actual):
    context_const = {}
    if df_prestador_actual.empty: return context_const

    tipo_prestador = _get_value(df_prestador_actual, 'p031_quetipodeprestadores')
    ambito_prestador = _get_value(df_prestador_actual, 'p019_ambitodeprestador')

    context_const['ugm_rural_1'] = _get_value(df_prestador_actual, 'p031A01b_cuentaconordenanzamunicipal')
    context_const['ugm_rural_2'] = _get_value(df_prestador_actual, 'p031A01c_seencuentradentrodeestructuraorganicayrof')
    context_const['ugm_pc_1'] = _get_value(df_prestador_actual, 'p031A01d_anodecreaciondeugmantesde2017')
    context_const['ugm_pc_2'] = _get_value(df_prestador_actual, 'p031A01e_autorizacionsunassprestacionexcepcional')
    context_const['oc_1'] = _get_value(df_prestador_actual, 'p031B02e_laoccuentaconreconocimientodelamuni')
    context_const['oc_2'] = _get_value(df_prestador_actual, 'p031B02f_resolucionmunicipaldereconocimientodelaoc')
    context_const['oe_1'] = _get_value(df_prestador_actual, 'p031C01_fueconstituidosegunlalgdesociedades')
    context_const['oe_2'] = _get_value(df_prestador_actual, 'p031C02_tienecontratosuscritoconlamunicipalidad')

    es_formal_lab = '-'
    if tipo_prestador == 'Prestación Directa del Servicio - UGM':
        if ambito_prestador == 'Rural':
            if context_const['ugm_rural_1'] == 'Si' and context_const['ugm_rural_2'] == 'Si': es_formal_lab = 'Si'
            elif context_const['ugm_rural_1'] == 'No' or context_const['ugm_rural_2'] == 'No': es_formal_lab = 'No'
        elif ambito_prestador == 'Pequeña Ciudad':
            # El original tiene ugm_rural_2, ugm_pc_1, ugm_pc_2 para PC. Revisar si es correcto.
            if context_const['ugm_rural_2'] == 'Si' and context_const['ugm_pc_1'] == 'Si' and context_const['ugm_pc_2'] == 'Si': es_formal_lab = 'Si'
            elif context_const['ugm_rural_2'] == 'No' or context_const['ugm_pc_1'] == 'No' or context_const['ugm_pc_2'] == 'No': es_formal_lab = 'No'
    elif tipo_prestador == 'Prestación Indirecta del Servicio - Organización Comunal':
        if context_const['oc_1'] == 'Si' and context_const['oc_2'] == 'Si': es_formal_lab = 'Si'
        elif context_const['oc_1'] == 'No' or context_const['oc_2'] == 'No': es_formal_lab = 'No'
    elif tipo_prestador == 'Prestación Indirecta del Servicio - Operador Especializado':
        if context_const['oe_1'] == 'Si' and context_const['oe_2'] == 'Si': es_formal_lab = 'Si'
        elif context_const['oe_1'] == 'No' or context_const['oe_2'] == 'No': es_formal_lab = 'No'
    elif tipo_prestador == 'Prestación Directa del Servicio - Prestador Municipal': # Asumo este es el caso que faltaba
        if context_const['ugm_rural_2'] == 'Si': es_formal_lab = 'Si' # El original solo chequeaba esto
        elif context_const['ugm_rural_2'] == 'No': es_formal_lab = 'No'
    context_const['es_formal_lab'] = es_formal_lab
    
    return context_const


def preparar_capacitacion_asistencia(df_prestador_actual):
    context_cap = {}
    if df_prestador_actual.empty: return context_cap

    recibio_asistencia = _get_value(df_prestador_actual, 'p032_recibioasistenciatecnicaenlosultimos3anos')
    context_cap['recibio_asistencia'] = recibio_asistencia
    context_cap['recibio_asistencia_lab'] = f"{recibio_asistencia} cuenta" if recibio_asistencia != '-' else '-'

    nombres_institucion = {
        "p033_atm": "ATM", "p033_municipalidad": "Municipalidad", "p033_mvcs": "MVCS", "p033_cac": "CAC",
        "p033_pnsr": "PNSR", "p033_pnsu": "PNSU", "p033_drvcs": "DRVCS", "p033_sunass": "SUNASS",
        "p033_otro": "Otro", "p033_otass": "OTASS"
    }
    nombres_temas = {
        "p034_oym": "OyM", "p034_controldecalidad": "Control de calidad",
        "p034_adquisiciondeequiposeinsumos": "Adquisicion de equipos e insumos",
        "p034_gestiondelosservicios": "Gestión de los servicios", "p034_cuotafamiliar": "Cuota familiar",
        "p034_otro": "Otro", "p034_grd": "Gestión de riesgo de desastre", "p034_integracion": "Integración"
    }

    actor_asistencia_val = "-"
    tema_asistencia_val = "-"

    if recibio_asistencia == "Si":
        inst_asist = [nombres_institucion[col] for col in nombres_institucion if _get_value(df_prestador_actual, col) == "Si"]
        temas_asist = [nombres_temas[col] for col in nombres_temas if _get_value(df_prestador_actual, col) == "Si"]

        actor_asistencia_val = ", ".join(inst_asist)
        if "Otro" in inst_asist: # "Otro" es el valor, no la clave
            otro_detalle_inst = _get_value(df_prestador_actual, "p033a_otroasistenciatecnica")
            if otro_detalle_inst != "-":
                actor_asistencia_val += f" - {otro_detalle_inst}"
        
        tema_asistencia_val = ", ".join(temas_asist)
        if "Otro" in temas_asist:
            otro_detalle_tema = _get_value(df_prestador_actual, "p034a_otrotemaasistencia")
            if otro_detalle_tema != "-":
                tema_asistencia_val += f" - {otro_detalle_tema}"
    
    context_cap['actor_asistencia'] = actor_asistencia_val if actor_asistencia_val else "-"
    context_cap['tema_asistencia'] = tema_asistencia_val if tema_asistencia_val else "-"
    return context_cap

def preparar_capacidad_financiera(df_prestador_actual):
    context_fin = {}
    if df_prestador_actual.empty or df_prestador_actual.iloc[0] is None:
        default_keys = [
            'cobra_cuota', 'cobraporcadaservicio', 'elcobroquerealizaes', 'elpagoestructuradodependedelamicromedicion',
            'conex_act', 'conex_act_alca', 'monto_cuota', 'monto_agua', 'monto_alca', 'monto_de', 'monto_tar',
            'cx_domestico', 'cx_comercial', 'cx_industrial', 'cx_social',
            'agua_dom', 'agua_com', 'agua_indus', 'agua_social',
            'alca_dom', 'alca_com', 'alca_indus', 'alca_social',
            'otro_dom', 'otro_com', 'otro_indus', 'otro_social',
            'd_sol1', 'd_de1', 'd_hasta1', 'd_sol2', 'd_de2', 'd_hasta2',
            'c_sol1', 'c_de1', 'c_hasta1', 'c_sol2', 'c_de2', 'c_hasta2',
            'i_sol1', 'i_de1', 'i_hasta1', 'i_sol2', 'i_de2', 'i_hasta2',
            's_sol1', 's_de1', 's_hasta1', 's_sol2', 's_de2', 's_hasta2',
            'cuota_cubre_lab', 'frecuencia_cobro', 'metodologia_oc', 'antiguedad_cuota', 'flujo_cuota',
            'conex_morosidad', 'conex_exoner', 'colateral_agua', 'colateral_alca', 'colateral_micro', 'colateral_repo',
            'g1_si', 'g1_no', 'g2_si', 'g2_no', 'g3_si', 'g3_no', 'g4_si', 'g4_no', 'g5_si', 'g5_no',
            'op', 'costoAnual', 'costoAnual_lab', 'valor_ref'
        ]
        costo_item_keys = ['op1', 'op2', 'op3', 'm', 'adm', 're', 'rm', 'otro_costo']
        for item in costo_item_keys:
            default_keys.extend([item, f'{item}_frec', f'{item}_costo', f'{item}_anual'])
        for key in default_keys: context_fin[key] = "-"
        context_fin['costoAnual_lab'] = 'No cuenta'
        return context_fin

    context_fin['cobra_cuota'] = _get_value(df_prestador_actual, 'p035_cobracuota')
    context_fin['cobraporcadaservicio'] = _get_value(df_prestador_actual, 'cobraporcadaservicio')
    context_fin['elcobroquerealizaes'] = _get_value(df_prestador_actual, 'elcobroquerealizaes')
    context_fin['tipo_tarifa'] = context_fin['elcobroquerealizaes'] # Alias
    context_fin['elpagoestructuradodependedelamicromedicion'] = _get_value(df_prestador_actual, 'elpagoestructuradodependedelamicromedicion')
    
    context_fin['conex_act'] = formatear_valor(_get_value(df_prestador_actual, 'p022_conexionesdeaguaactivas', 0), defecto="-")
    context_fin['conex_act_alca'] = formatear_valor(_get_value(df_prestador_actual, 'p024_conexionesdealcantarilladoactivas', 0), defecto="-")
    
    cuota_cols = ['p040_acuantoasciendeelcobroquerealiza', 'acuantoasciendeelcobroquerealizaagua', 
                  'acuantoasciendeelcobroquerealizaalcantari', 'acuantoasciendeelcobroquerealizadisposici',
                  'acuantoasciendeelcobroquerealizatratamien']
    cuota_ctx_keys = ['monto_cuota', 'monto_agua', 'monto_alca', 'monto_de', 'monto_tar']
    for key, col in zip(cuota_ctx_keys, cuota_cols):
        context_fin[key] = formatear_valor(_get_value(df_prestador_actual, col))

    cx_cols = ['conexionesdomestico', 'conexionescomercial', 'conexionesindustrial', 'conexionessocial']
    cx_ctx_keys = ['cx_domestico', 'cx_comercial', 'cx_industrial', 'cx_social']
    for key, col in zip(cx_ctx_keys, cx_cols):
        context_fin[key] = formatear_valor(_get_value(df_prestador_actual, col, 0), defecto="-")

    monto_cats = ['agua', 'alcantarillado', 'otro']
    monto_tipos = ['domestico', 'comercial', 'industrial', 'social']
    for cat_df in monto_cats:
        for tipo_df in monto_tipos:
            col_name = f"monto{tipo_df}{cat_df}" # e.g., montodomesticoagua
            ctx_key = f"{cat_df[:4]}_{tipo_df[:(4 if tipo_df != 'industrial' else 5)]}" # e.g., agua_dome (o similar a tu original)
            # Para ser exacto con tu original:
            if cat_df == "agua": ctx_key_cat = "agua"
            elif cat_df == "alcantarillado": ctx_key_cat = "alca"
            else: ctx_key_cat = "otro"
            
            if tipo_df == "domestico": ctx_key_tipo = "dom"
            elif tipo_df == "comercial": ctx_key_tipo = "com"
            elif tipo_df == "industrial": ctx_key_tipo = "indus"
            else: ctx_key_tipo = "social"
            ctx_key = f"{ctx_key_cat}_{ctx_key_tipo}"

            context_fin[ctx_key] = formatear_valor(_get_value(df_prestador_actual, col_name))
    
    rangos_map = {'d': 'domestic', 'c': 'comercial', 'i': 'industrial', 's': 'social'}
    for r_prefix_ctx, tipo_col_orig_base in rangos_map.items():
        for n_rango in [1, 2]:
            col_soles = f'{tipo_col_orig_base}rango{n_rango}solesm3'
            col_v3de = f'{tipo_col_orig_base}rango{n_rango}v3de' if not (tipo_col_orig_base == 'domestic' and n_rango == 2) else f'{tipo_col_orig_base}rango{n_rango}volumenenm3de'
            col_v3a = f'{tipo_col_orig_base}rango{n_rango}v3a' if not (tipo_col_orig_base == 'domestic' and n_rango == 2) else f'{tipo_col_orig_base}rango{n_rango}volumenenm3a'

            context_fin[f'{r_prefix_ctx}_sol{n_rango}'] = formatear_valor(_get_value(df_prestador_actual, col_soles))
            context_fin[f'{r_prefix_ctx}_de{n_rango}'] = formatear_valor(_get_value(df_prestador_actual, col_v3de))
            context_fin[f'{r_prefix_ctx}_hasta{n_rango}'] = formatear_valor(_get_value(df_prestador_actual, col_v3a))

    cuota_cubre_val = _get_value(df_prestador_actual, 'p059_lacuotacubrecostosdeoaym')
    context_fin['cuota_cubre_lab'] = 'Superávit' if cuota_cubre_val == 'Si' else ('Déficit' if cuota_cubre_val == 'No' else '-')

    if context_fin['cobra_cuota'] == "Si":
        frec_cobro = _get_value(df_prestador_actual, 'p037_frecuenciadecobros')
        if frec_cobro == "Otro":
            frec_cobro_otro = _get_value(df_prestador_actual, 'p037a_frecuenciadecobrootro')
            frec_cobro = f"{frec_cobro}, {frec_cobro_otro}" if frec_cobro_otro and frec_cobro_otro != '-' else frec_cobro
        context_fin['frecuencia_cobro'] = frec_cobro
        
        tipo_prest = _get_value(df_prestador_actual, 'p031_quetipodeprestadores')
        if tipo_prest == "Prestación Indirecta del Servicio - Organización Comunal":
            context_fin['metodologia_oc'] = _get_value(df_prestador_actual, 'p039_laocaplicalametodologiadecuotafamiliar')
        else:
            context_fin['metodologia_oc'] = "-"
            
        context_fin['antiguedad_cuota'] = _get_value(df_prestador_actual, 'p036_antiguedaddelatarifacuotaactual')
        context_fin['flujo_cuota'] = _get_value(df_prestador_actual, 'cobraporcadaservicio')
        context_fin['conex_morosidad'] = formatear_valor(_get_value(df_prestador_actual, 'p046_numerodeusuariosmorosos', 0), defecto="-")
        context_fin['conex_exoner'] = formatear_valor(_get_value(df_prestador_actual, 'p047_numerodeusuariosexonerados', 0), defecto="-")
    else:
        context_fin.update({k: "-" for k in ['frecuencia_cobro', 'metodologia_oc', 'antiguedad_cuota', 'flujo_cuota', 'conex_morosidad', 'conex_exoner']})

    colateral_cols = ['p051a_conexionesdeagua', 'p051d_conexiondedesague', 'p051c_instalaciondemicromedidores', 'p051b_reposiciondelservicio']
    colateral_ctx_keys = ['colateral_agua', 'colateral_alca', 'colateral_micro', 'colateral_repo']
    for key, col in zip(colateral_ctx_keys, colateral_cols):
        context_fin[key] = formatear_valor(_get_value(df_prestador_actual, col, 0), defecto="-")

    doc_gestion_map = {
        'g1': 'p063_elprestadortieneunregistrocontableuotro', 'g2': 'p053_elprestadorcuentaconcuadernolibrodeinventa',
        'g3': 'p062_elprestadortieneunregistrodetodoslosrecib', 'g4': 'p061_elprestadortieneregistrodetodoslosrecibos',
        'g5': 'p038_emitereciboocomprobporelpagodeservicios'
    }
    for key, col in doc_gestion_map.items():
        val = _get_value(df_prestador_actual, col)
        context_fin[f'{key}_si'] = "X" if val == "Si" else ""
        context_fin[f'{key}_no'] = "X" if val == "No" else ("" if val == "Si" else "-")

    costos_detalle = {}
    costos_config_map = {
        'op1': {'tiene': 'p058a1_tieneenergiaelectrica', 'frec': 'p058a1a_periodoenergiaelectrica', 'frec_otro': 'p058a1b_periodoenergiaotro', 'costo_val': 'p058a1c_costototaldeenergiaelectrica'},
        'op2': {'tiene': 'p058a2_tienecostosdeinsumosquimicos', 'frec': 'p058a2a_periodoinsumosquimicos', 'frec_otro': 'p058a2b_periodoinsumosquimicosotro', 'costo_val': 'p058a2c_costototaldeinsumosquimicos'},
        'op3': {'tiene': 'p058a3_tienecostosdepersonal', 'frec': 'p058a3a_periodopersonal', 'frec_otro': 'p058a3b_periodopersonalotro', 'costo_val': 'p058a3c_costototaldepersonal'},
        'm': {'tiene': 'p058b_tienecostosdemantenimiento', 'frec': 'p058b1_periodomantenimiento', 'frec_otro': 'p058b2_periodomantenimientootro', 'costo_val': 'p058b3_costostotalenmantenimientosmensual'},
        'adm': {'tiene': 'p058c_tienecostosdeadministracion', 'frec': 'p058c1_periodoadministracion', 'frec_otro': 'p058c2_periodoadministracionotro', 'costo_val': 'p058c3_costostotalenadministracionsmensual'},
        're': {'tiene': 'p058d_tienecostosdereposiciondeequipos', 'frec': 'p058d1_periodoreposiciondeequipos', 'frec_otro': 'p058d2_periodoreposiciondeequiposotro', 'costo_val': 'p058d3_costototaldereposicionsmensual'},
        'rm': {'tiene': 'p058e_tienecostosderehabilitacionesmenores', 'frec': 'p058e1_periodorehabilitacionesmenores', 'frec_otro': 'p058e2_periodorehabilitacionesmenoresotro', 'costo_val': 'p058e3_costototalderehabilitamenoressmensual'},
        'otro_costo': {'tiene': 'p058f_tieneotroscostos', 'frec': 'p058f1_periodootroscostos', 'frec_otro': 'p058f2_periodootrootro', 'costo_val': 'p058f3_costototaldeotrosmensual'}
    }
    costos_detalle['op'] = _get_value(df_prestador_actual, 'p058a_tienecostosdeoperacion')
    
    valores_anuales_list = []
    for key_ctx_costo, cols_map in costos_config_map.items():
        costos_detalle[key_ctx_costo] = _get_value(df_prestador_actual, cols_map['tiene'])
        frec_val = _get_value(df_prestador_actual, cols_map['frec'])
        if frec_val == 'Otro':
            frec_otro_val = _get_value(df_prestador_actual, cols_map['frec_otro'])
            frec_val = f"{frec_val}, {frec_otro_val}" if frec_otro_val and frec_otro_val != '-' else frec_val
        costos_detalle[f'{key_ctx_costo}_frec'] = frec_val
        costo_num_raw = _get_value(df_prestador_actual, cols_map['costo_val'], None) # Obtener raw para chequear tipo
        costo_num_float = None
        if pd.notna(costo_num_raw):
            try:
                # costo_num_float = float(str(costo_num_raw).replace(",", ""))
                costo_num_float = formatear_valor(costo_num_raw)
            except ValueError:
                pass # Mantener como None
        
        costos_detalle[f'{key_ctx_costo}_costo'] = formatear_valor(costo_num_float)
        costo_anual_val = calcular_costo_anual(frec_val, costo_num_float) # calcular_costo_anual ya maneja nulos
        costos_detalle[f'{key_ctx_costo}_anual'] = formatear_valor(costo_anual_val)
        if isinstance(costo_anual_val, (int, float)):
            valores_anuales_list.append(costo_anual_val)

    costo_anual_total_num = sum(val for val in valores_anuales_list if isinstance(val, (int, float)))
    if costo_anual_total_num > 0 or any(isinstance(v, (int,float)) for v in valores_anuales_list):
        costo_anual_total_num_rounded = round(costo_anual_total_num, 1)
        context_fin['costoAnual'] = f"{costo_anual_total_num_rounded}(*)"
        context_fin['costoAnual_lab'] = f"S/. {costo_anual_total_num_rounded:,.0f} anual*".replace(",", " ")
        cargo_rep_val = _get_value(df_prestador_actual, 'p008b_cargo', "representante")
        context_fin['valor_ref'] = f"(*) Valor referencial. Declarado por el {str(cargo_rep_val).lower()}."
    else:
        context_fin['costoAnual'] = "-"
        context_fin['costoAnual_lab'] = "No cuenta"
        context_fin['valor_ref'] = ""
        
    context_fin.update(costos_detalle)
    return context_fin

def preparar_identificacion_peligros(df_prestador_actual):
    context_pel = {}
    if df_prestador_actual.empty: return context_pel
    
    peligros_map = {
        'peligro1': 'p064_cuentaconplandeemergenciauotroinstrumento',
        'peligro3': 'p067_cuentaconcuadrillacomitebrigadapararespuest'
    }
    for key, col in peligros_map.items():
        val = _get_value(df_prestador_actual, col)
        context_pel[f'{key}_si'] = "X" if val == "Si" else ""
        context_pel[f'{key}_no'] = "X" if val == "No" else ("" if val == "Si" else "-")

    ninguno_val = _get_value(df_prestador_actual, 'p065_ninguno') # El original es 'p065_ninguno'
    context_pel['peligro2_si'] = "X" if ninguno_val == "No" else ""
    context_pel['peligro2_no'] = "X" if ninguno_val == "Si" else ("" if ninguno_val == "No" else "-")
    
    return context_pel

def preparar_disponibilidad_recurso_hidrico(df_prestador_actual, df_fuente_actual):
    context_hid = {}
    fuentes_list = []
    licenciauso_lab_val = "-"

    if not df_fuente_actual.empty:
        for _, row_fuente in df_fuente_actual.iterrows():
            row = row_fuente.to_frame().T # Para usar _get_value consistentemente
            tipo_fuente = _get_value(row, 'tipodefuentedeagua')
            subtipo_val = "-"
            if tipo_fuente == 'Subterránea': subtipo_val = _get_value(row, 'subtipodefuentedeaguasubterranea')
            elif tipo_fuente == 'Superficial': subtipo_val = _get_value(row, 'subtipodefuentedeaguasuperficial')
            elif tipo_fuente == 'Pluvial': subtipo_val = 'Pluvial'
            
            fuentes_list.append({
                "nomfuente": _get_value(row, "nombredelafuente"),
                "tipofuente": tipo_fuente,
                "subtipofuente": subtipo_val,
                "licenciauso": _get_value(row, 'cuentaconlicenciauso')
            })

        contador_lic = {"Si": 0, "No": 0, "-": 0}
        for f_item in fuentes_list:
            lic = f_item['licenciauso'] if pd.notna(f_item['licenciauso']) else "-"
            contador_lic[lic] = contador_lic.get(lic, 0) + 1

        num_fuentes = len(fuentes_list)
        if num_fuentes == 1:
            if contador_lic["Si"] == 1: licenciauso_lab_val = "Si tiene"
            elif contador_lic["No"] == 1: licenciauso_lab_val = "No tiene"
            # else queda como "-"
        elif num_fuentes > 1:
            if contador_lic["Si"] == num_fuentes: licenciauso_lab_val = "Si"
            elif contador_lic["No"] == num_fuentes: licenciauso_lab_val = "No"
            elif contador_lic["Si"] > 0: licenciauso_lab_val = "Sólo algunas tienen" # Simplificado
            # else queda como "-"
            
    context_hid['fuentes'] = fuentes_list
    context_hid['licenciauso_lab'] = licenciauso_lab_val

    if not df_prestador_actual.empty:
        infra_configs = [
            ("in_1", {"p005_agriculturariego": "Agricultura (Riego)", "p005_industrial": "Industrial",
                      "p005_prestadoresdess": "Prestadores de servicios", "p005_mineria": "Minería", "p005_otro": "Otro"},
             "p005a_otrousodelafuente", "in_1lab"),
            ("in_2", {"p008_bofedal": "Bofedal", "p008_bosques": "Bosques", "p008_pajonal": "Pajonal", "p008_otro": "Otro"},
             "p008a_otrotipodeecosistema", "in_2lab"),
            ("in_3", {"p014_ninguno": "Ninguno", "p014_disminucion": "Disminución de agua (caudal) en época de estiaje",
                      "p014_aumento": "Aumento de turbidez (sedimentos)", "p014_contaminacion": "Presencia de contaminantes en el agua",
                      "p014_otros": "Otros"}, "p014a_problemasidentificadosotro", "in_3lab"),
            ("in_4", {"p015_agricultura": "Agricultura", "p015_basuradomestica": "Basura doméstica", "p015_mineria": "Minería",
                      "p015_deforestacion": "Deforestación", "p015_sobrepastoreo": "Sobrepastoreo",
                      "p015_ninguno": "Ninguno", 'p015_otros': "Otros"}, "p015a_otraactividadambitofuenteagua", "in_4lab")
        ]

        for key_ctx, nombres_map, col_otro_detalle, key_lab_ctx in infra_configs:
            lista_items = [nombres_map[col] for col in nombres_map if _get_value(df_prestador_actual, col) == "Si"]
            texto_items_val = "No cuenta"
            texto_lab_val = "No cuenta"
            if lista_items:
                texto_lab_val = "Si cuenta"
                texto_items_val = ", ".join(lista_items)
                key_otro_original = next((k for k, v in nombres_map.items() if v.lower() == "otro" or v.lower() == "otros"), None)
                if key_otro_original and (nombres_map[key_otro_original] in lista_items):
                    otro_detalle_val = _get_value(df_prestador_actual, col_otro_detalle)
                    if otro_detalle_val != "-":
                        texto_items_val += f" - {otro_detalle_val}"
            
            context_hid[key_ctx] = texto_items_val
            context_hid[key_lab_ctx] = texto_lab_val
    return context_hid


def preparar_sistemas_agua(df_prestador_actual, df_sistema_agua_actual, df_captacion_actual, 
                           df_conduccion_actual, df_reservorio_actual, df_ptap_actual, df_ps_actual):
    context_agua = {}
    sistemas_de_agua_list = [] # Lista combinada para referencia interna si es necesaria
    sistemas_de_agua_conv_list = []
    sistemas_de_agua_noconv_list = []
    coordenadas_agua_list_raw = [] # Lista de diccionarios {nombre, zona, este, norte, altitud} antes de formatear
    convencional_flag = "-"
    noconvencional_flag = "-"
    
    # Obtener el valor de es_prestador del df_prestador_actual (asumiendo que ya tiene los datos mergeados)
    es_prestador_val = _get_value(df_prestador_actual, 'existeprestadordessenelccppprincipal', default="-")

    if df_sistema_agua_actual.empty or not isinstance(df_sistema_agua_actual, pd.DataFrame) or \
       (es_prestador_val != "Si" and es_prestador_val != "No"):
        logger.warning(f"No hay datos de sistema de agua para procesar o 'es_prestador' no es Si/No para el prestador.")
        context_agua.update({"sistemasdeagua": [], "sistemas_de_agua_convecional": [], 
                             "sistemas_de_agua_noconvencional": [], "convencional": "-", "noconvencional": "-"})
        return context_agua, []

    # --- 1. Procesamiento de componentes individuales (Crear df_..._proc) ---
    logger.debug(f"Procesando componentes del sistema de agua...")

    # CAPTACION
    df_captacion_proc = pd.DataFrame()
    if not df_captacion_actual.empty and not df_sistema_agua_actual.empty:
        # Asumimos que df_captacion_actual ya fue renombrado y tipos corregidos en report_generator
        # Si no, hacer los renames aquí:
        df_captacion_actual_renamed = df_captacion_actual.rename(
            columns={'nombredelacaptacion':'nombre', 'anodeconstruccion':'aniodeconstruccion', 
                     'estadooperativodelacaptacion':'estadooperativo', 'justifiquesurespuestacaptacion':'descripcion'},
            errors='ignore' # Ignorar si alguna columna ya está renombrada
        )
        df_captacion_proc = pd.merge(
            df_sistema_agua_actual[['codigodesistemadeagua']], 
            df_captacion_actual_renamed, # Usar el renombrado
            on='codigodesistemadeagua', 
            how='inner'
        )
        if not df_captacion_proc.empty:
            df_captacion_proc['nombre'] = df_captacion_proc['nombre'].apply(
                lambda x: f'Captación {x}' if pd.notna(x) and 'capta' not in str(x).lower() else str(x)
            )
            df_captacion_proc['cuenta'] = 'Si'
    logger.debug(f"df_captacion_proc generado con {len(df_captacion_proc)} filas.")

    # CASETA Y EQUIPO DE BOMBEO (desde df_sistema_agua_actual)
    df_equipo_bombeo_list = []
    if not df_sistema_agua_actual.empty:
        df_eq_base = df_sistema_agua_actual[[
            'codigodesistemadeagua', 'p016_cuentaconequipodebombeo', 'aniodeconstruccioncasetabombeo',
            'zonacasetadebombeo', 'estecasetedebombeo', 'nortecasetadebombeo', 'altitudcasetadebombeo'
        ]].rename(columns={
            'p016_cuentaconequipodebombeo': 'cuenta', 'aniodeconstruccioncasetabombeo': 'aniodeconstruccion',
            'zonacasetadebombeo': 'zona', 'estecasetedebombeo': 'este',
            'nortecasetadebombeo': 'norte', 'altitudcasetadebombeo': 'altitud'
        }, errors='ignore')
        df_eq_base['nombre'] = 'Caseta y equipo de bombeo'
        df_eq_base['estadooperativo'] = '' # Placeholder como en original
        df_eq_base['descripcion'] = ''   # Placeholder
        df_equipo_bombeo_list.append(df_eq_base)

        componentes_bombeo_configs = [
            ('tienecasetadebombeo', 'estadooperativocasetadebombeo', 'justifiquerespuestaocasetabombeo', '   Caseta de bombeo'),
            ('tienecisternadebombeo', 'estadooperativocisternadebombeo', 'justifiquerespuestaocisternabombeo', '   Cisterna de bombeo'),
            ('tieneequipodebombeo', 'estadooperativoequipodebombeo', 'justifiquerespuestaoequipobombeo', '   Equipo de bombeo'),
            ('tienesistemaenergiaelectrica', 'estadooperativosistemaenergia', 'justifiquerespuestaoenergiaelectrica', '   Sistema de energía electrica')
        ]
        for col_cuenta, col_eo, col_desc, nombre_comp in componentes_bombeo_configs:
            if all(c in df_sistema_agua_actual.columns for c in ['codigodesistemadeagua', col_cuenta, col_eo, col_desc]):
                df_comp = df_sistema_agua_actual[['codigodesistemadeagua', col_cuenta, col_eo, col_desc]].rename(columns={
                    col_cuenta: 'cuenta', col_eo: 'estadooperativo', col_desc: 'descripcion'
                }, errors='ignore')
                df_comp['nombre'] = nombre_comp
                df_comp['aniodeconstruccion'] = pd.NA 
                for col_coord in ['zona', 'este', 'norte', 'altitud']: df_comp[col_coord] = pd.NA
                df_equipo_bombeo_list.append(df_comp)
    
    df_equipo_casete_bombeo = pd.concat(df_equipo_bombeo_list, ignore_index=True) if df_equipo_bombeo_list else pd.DataFrame()
    logger.debug(f"df_equipo_casete_bombeo generado con {len(df_equipo_casete_bombeo)} filas.")


    # LINEA DE CONDUCCION / IMPULSIÓN
    df_conduccion_proc = pd.DataFrame()
    if not df_conduccion_actual.empty and not df_sistema_agua_actual.empty:
        df_conduccion_actual_renamed = df_conduccion_actual.rename(columns={
            'anodeconstruccionconduccion':'aniodeconstruccion', 
            'estadooperativodelconductordeaguacruda':'estadooperativo',
            'justifiquesurespuestaconduccion':'descripcion'}, errors='ignore')
        # Seleccionar solo las columnas necesarias después del rename
        cols_conduccion = ['codigodesistemadeagua', 'aniodeconstruccion', 'estadooperativo', 'descripcion']
        df_conduccion_proc = pd.merge(
            df_sistema_agua_actual[['codigodesistemadeagua']], 
            df_conduccion_actual_renamed[[c for c in cols_conduccion if c in df_conduccion_actual_renamed.columns]],
            on='codigodesistemadeagua', how='inner'
        )
        if not df_conduccion_proc.empty:
            df_conduccion_proc['nombre'] = 'Línea de conducción / Impulsión'
            df_conduccion_proc['cuenta'] = 'Si'
            for col_coord in ['zona', 'este', 'norte', 'altitud']: df_conduccion_proc[col_coord] = pd.NA
    logger.debug(f"df_conduccion_proc generado con {len(df_conduccion_proc)} filas.")

    # PTAP y sus COMPONENTES
    df_ptap_componentes_final = pd.DataFrame() # DataFrame final que contendrá la PTAP principal y sus subcomponentes
    if not df_ptap_actual.empty and not df_sistema_agua_actual.empty:
        # df_ptap_actual ya debería tener las columnas renombradas de Dataverse
        df_ptap_merged = pd.merge(df_sistema_agua_actual[['codigodesistemadeagua']], df_ptap_actual, on='codigodesistemadeagua', how='inner')
        
        if not df_ptap_merged.empty:
            # PTAP Principal (General)
            df_ptap_general = df_ptap_merged[[
                'codigodesistemadeagua', 'anodeconstruccion', 'tipodeptap', 'zona', 'este', 'norte', 'altitud'
            ]].copy() # Renombrar 'anodeconstruccion' ya no es necesario si se hizo en _aplicar_limpieza_tipos
            df_ptap_general['nombre'] = df_ptap_general.apply(
                lambda r: f"PTAP ({r['tipodeptap']})" if pd.notna(r['tipodeptap']) and r['tipodeptap'] != '-' else "PTAP ()", axis=1
            )
            df_ptap_general['cuenta'] = 'Si'
            df_ptap_general['estadooperativo'] = pd.NA # Se calcula después o no aplica al general
            df_ptap_general['descripcion'] = pd.NA   # Se calcula después o no aplica al general
            df_ptap_componentes_final = pd.concat([df_ptap_componentes_final, df_ptap_general], ignore_index=True)

            # Sub-Componentes de PTAP
            ptap_subcomponent_configs = [
                # Filt. Lenta
                ('     Rejas (Filtración lenta)', 'tienerejaslenta', 'estadooperativorejaslenta', 'justifiquesurespuestarejas'),
                ('     Desarenador (Filtración lenta)', 'tienedesarenadorlenta', 'estadooperativodesarenadorlenta', 'justifiquesurespuestadesarenador'),
                ('     Pre sedimentador', 'tienepresedimentador', 'estadooperativopresedimentador', 'justifiquesurespuestapresedimentador'),
                ('     Sedimentador', 'tienesedimentador', 'estadooperativosedimentador', 'justifiquesurespuestasedimentador'),
                ('     Pre filtro de grava', 'tieneprefiltrodegrava', 'estadooperativoprefiltrodegrava', 'justifiquesurespuestaprefiltrograva'),
                ('     Filtro lento', 'tienefiltrolento', 'estadooperativofiltrolento', 'justifiquesurespuestafiltrolento'),
                # Filt. Rápida
                ('     Rejas (Filtración rápida)', 'tienerejasrapida', 'estadooperativorejasrapida', 'justifiquesurespuestarejasrapida'),
                ('     Desarenador (Filtración rápida)', 'tienedesarenadorrapida', 'estadooperativodesarenadorrapida', 'justifiquesurespuestadesarenadorrapido'),
                ('     Pre sedimentador (Filtración rápida)', 'tienepresedimentadorrapida', 'estadooperativopresedimentadorrapida', 'justifiquesurespuestapresedimentadorrapido'),
                ('     Sedimentador sin coagulación previa', 'tienesedimentadorsincoagulacionprevia', 'estadooperativosedimentadorsncoagulacion', 'justifiquesurespuestasedimentadorsc'),
                ('     Mezclador rápido', 'tienemezcladorrapido', 'estadooperativomezcladorrapido', 'justifiquesurespuestamezcladorrapido'),
                ('     Floculador hidráulico', 'tienefloculadorhidraulico', 'estadooperativofloculadorhidraulico', 'justifiquesurespuestafloculadorh'),
                ('     Floculador mecánico', 'tienefloculadormecanico', 'estadooperativofloculadormecanico', 'justifiquesurespuestafloculadormeca'),
                ('     Sedimentador con coagulación previa', 'tienesedimentacionconcoagulacionprevia', 'estadooperativosedimentacionccoagulacion', 'justifiquesurespuestasedimentacioncc'),
                ('     Decantador', 'tienedecantador', 'estadooperativodecantador', 'justifiquesurespuestadecantador'),
                ('     Filtro rápido', 'tienefiltrorapido', 'estadooperativofiltrorapido', 'justifiquesurespuestafiltrorapido'),
            ]
            
            temp_subcomponents_list = []
            for _, row_ptap in df_ptap_merged.iterrows(): # Iterar por cada PTAP si hubiera múltiples (normalmente 1 por sistema)
                for nombre_sub, col_cuenta_sub, col_eo_sub, col_desc_sub in ptap_subcomponent_configs:
                    if col_cuenta_sub in row_ptap and pd.notna(row_ptap[col_cuenta_sub]) and row_ptap[col_cuenta_sub] != 'No' and row_ptap[col_cuenta_sub] != '-': # Solo añadir si "tiene"
                        sub_comp_data = {
                            'codigodesistemadeagua': row_ptap['codigodesistemadeagua'],
                            'nombre': nombre_sub,
                            'cuenta': row_ptap[col_cuenta_sub],
                            'estadooperativo': row_ptap.get(col_eo_sub, pd.NA),
                            'descripcion': row_ptap.get(col_desc_sub, pd.NA),
                            'aniodeconstruccion': pd.NA, # Subcomponentes no tienen año individual en el original
                            'zona': pd.NA, 'este': pd.NA, 'norte': pd.NA, 'altitud': pd.NA
                        }
                        temp_subcomponents_list.append(sub_comp_data)
            
            if temp_subcomponents_list:
                df_ptap_componentes_final = pd.concat([df_ptap_componentes_final, pd.DataFrame(temp_subcomponents_list)], ignore_index=True)
    logger.debug(f"df_ptap_componentes_final generado con {len(df_ptap_componentes_final)} filas.")


    # RESERVORIO
    df_reservorio_proc = pd.DataFrame()
    if not df_reservorio_actual.empty and not df_sistema_agua_actual.empty:
        df_reservorio_actual_renamed = df_reservorio_actual.rename(columns={'anodeconstruccion':'aniodeconstruccion', 'estadooperativodereservorio':'estadooperativo', 'justifiquesurespuestareservorio':'descripcion'}, errors='ignore')
        df_reservorio_proc = pd.merge(df_sistema_agua_actual[['codigodesistemadeagua']], df_reservorio_actual_renamed, on='codigodesistemadeagua', how='inner')
        if not df_reservorio_proc.empty:
            df_reservorio_proc['nombre'] = 'Reservorio'
            df_reservorio_proc['cuenta'] = 'Si'
    logger.debug(f"df_reservorio_proc generado con {len(df_reservorio_proc)} filas.")

    # SISTEMA DE DISTRIBUCION
    df_distribucion_proc = pd.DataFrame()
    if not df_sistema_agua_actual.empty:
        # Columnas necesarias para distribución del df_sistema_agua_actual
        cols_dist = ['codigodesistemadeagua', 'aniodeconstrucciondistribucion', 'estadooperativoactual', 'justificasurespuestadistribucion']
        if all(c in df_sistema_agua_actual.columns for c in cols_dist):
            df_distribucion_proc = df_sistema_agua_actual[cols_dist].rename(columns={
                'aniodeconstrucciondistribucion':'aniodeconstruccion', 
                'estadooperativoactual':'estadooperativo',
                'justificasurespuestadistribucion':'descripcion'
            }, errors='ignore')
            if not df_distribucion_proc.empty:
                df_distribucion_proc['nombre'] = 'Red de distribución de agua'
                df_distribucion_proc['cuenta'] = 'Si'
                for col_coord in ['zona', 'este', 'norte', 'altitud']: df_distribucion_proc[col_coord] = pd.NA
    logger.debug(f"df_distribucion_proc generado con {len(df_distribucion_proc)} filas.")

    # --- 2. Consolidar todos los componentes del sistema de agua ---
    component_dfs_to_concat_final = [df for df in [
        df_captacion_proc, df_equipo_casete_bombeo, df_conduccion_proc, 
        df_ptap_componentes_final, df_reservorio_proc, df_distribucion_proc
    ] if df is not None and not df.empty] # Asegurar que no sean None y no estén vacíos

    df_sistema_general_agua = pd.DataFrame()
    if component_dfs_to_concat_final:
        df_sistema_general_agua = pd.concat(component_dfs_to_concat_final, ignore_index=True)
    logger.debug(f"df_sistema_general_agua (todos los componentes) generado con {len(df_sistema_general_agua)} filas.")

    # --- 3. Numeración y Formateo Final de Nombres de Componentes (df_sistema_nombre_general_2_agua) ---
    df_sistema_nombre_general_2_agua = pd.DataFrame() # Este será el DF final de componentes para las tablas
    if not df_sistema_general_agua.empty:
        # Filtrar solo los componentes que "cuentan" para la numeración y tienen coordenadas
        df_sistema_nombre_base = df_sistema_general_agua[
            df_sistema_general_agua['cuenta'].isin(['Si', 'si', True]) & # Aceptar varias formas de 'Si'
            df_sistema_general_agua['nombre'].notna() &
            ~df_sistema_general_agua['nombre'].astype(str).str.strip().str.startswith('   ') # No sub-items
        ].copy()

        if not df_sistema_nombre_base.empty:
            df_sistema_nombre_base.sort_values(by=['codigodesistemadeagua', 'nombre'], inplace=True) # Para numeración consistente
            df_sistema_nombre_base['N'] = df_sistema_nombre_base.groupby('codigodesistemadeagua').cumcount() + 1
            df_sistema_nombre_base['nombre_fin'] = df_sistema_nombre_base.apply(lambda r: f"{r['N']}. {r['nombre']}", axis=1)
        
        # Reconstruir df_sistema_nombre_general_2_agua con todos los items que "cuentan" y los sub-items.
        # La lógica original era compleja. Simplificaremos para mostrar todos los que tienen 'cuenta' == 'Si'.
        df_sistema_nombre_general_2_agua = df_sistema_general_agua[df_sistema_general_agua['cuenta'].isin(['Si', 'si', True])].copy()
        if not df_sistema_nombre_general_2_agua.empty:
            # Asignar nombre_fin a los componentes base
            if not df_sistema_nombre_base.empty:
                 # Crear Nombre_aux para el merge si no existe
                if 'Nombre_aux' not in df_sistema_nombre_general_2_agua:
                    df_sistema_nombre_general_2_agua['N_aux_temp'] = df_sistema_nombre_general_2_agua.groupby(['codigodesistemadeagua', 'nombre'], dropna=False).cumcount() + 1
                    df_sistema_nombre_general_2_agua['Nombre_aux'] = df_sistema_nombre_general_2_agua.apply(lambda r: str(r['nombre']) + str(r['N_aux_temp']), axis=1)
                if 'Nombre_aux' not in df_sistema_nombre_base:
                    df_sistema_nombre_base['N_aux_temp'] = df_sistema_nombre_base.groupby(['codigodesistemadeagua', 'nombre'], dropna=False).cumcount() + 1
                    df_sistema_nombre_base['Nombre_aux'] = df_sistema_nombre_base.apply(lambda r: str(r['nombre']) + str(r['N_aux_temp']), axis=1)
                
                df_sistema_nombre_general_2_agua = pd.merge(
                    df_sistema_nombre_general_2_agua,
                    df_sistema_nombre_base[['codigodesistemadeagua', 'Nombre_aux', 'nombre_fin']],
                    on=['codigodesistemadeagua', 'Nombre_aux'],
                    how='left'
                )
                df_sistema_nombre_general_2_agua['nombre'] = df_sistema_nombre_general_2_agua['nombre_fin'].fillna(df_sistema_nombre_general_2_agua['nombre'])
                df_sistema_nombre_general_2_agua.drop(columns=['nombre_fin', 'Nombre_aux'], errors='ignore', inplace=True)

            df_sistema_nombre_general_2_agua['antiguedad'] = df_sistema_nombre_general_2_agua['aniodeconstruccion'].apply(calcular_anios_antiguedad)
            
            # Lógica para numerar 'Línea de conducción / Impulsión' y 'Reservorio' si hay múltiples
            # Se basa en 'nombre_sin_numero' y 'auxiliar'
            if 'nombre' in df_sistema_nombre_general_2_agua.columns:
                df_sistema_nombre_general_2_agua['nombre_sin_numero'] = df_sistema_nombre_general_2_agua['nombre'].astype(str).str.replace(r'^\d+\.\s*', '', regex=True)
                
                filtro_condu_res = df_sistema_nombre_general_2_agua['nombre_sin_numero'].str.contains('Línea de conducción / Impulsión|Reservorio', na=False)
                if filtro_condu_res.any():
                    # Asegurar que las columnas para groupby no tengan NaN si se usan en groupby
                    cols_groupby_num = ['codigodesistemadeagua', 'nombre_sin_numero']
                    for col_g in cols_groupby_num:
                        if col_g in df_sistema_nombre_general_2_agua.columns:
                            df_sistema_nombre_general_2_agua[col_g] = df_sistema_nombre_general_2_agua[col_g].fillna("DESCONOCIDO_PARA_GROUPBY")

                    df_sistema_nombre_general_2_agua.loc[filtro_condu_res, 'auxiliar'] = df_sistema_nombre_general_2_agua[filtro_condu_res].groupby(cols_groupby_num).cumcount() + 1
                    df_sistema_nombre_general_2_agua['auxiliar'] = pd.to_numeric(df_sistema_nombre_general_2_agua['auxiliar'], errors='coerce').astype('Int64')
                    
                    df_sistema_nombre_general_2_agua['nombre'] = df_sistema_nombre_general_2_agua.apply(
                        lambda r: f"{r['nombre']} (N°{r['auxiliar']:02d})" if pd.notna(r['auxiliar']) and r['nombre_sin_numero'] != '-' and filtro_condu_res.loc[r.name] else r['nombre'], 
                        axis=1
                    )
                    df_sistema_nombre_general_2_agua['nombre_sin_numero'] = df_sistema_nombre_general_2_agua['nombre'].astype(str).str.replace(r'^\d+\.\s*', '', regex=True) # Recalcular

            # Seleccionar y rellenar columnas finales para la tabla de componentes
            cols_finales_componentes = ['codigodesistemadeagua', 'nombre', 'antiguedad', 'estadooperativo', 'descripcion']
            df_sistema_nombre_general_2_agua = df_sistema_nombre_general_2_agua[[c for c in cols_finales_componentes if c in df_sistema_nombre_general_2_agua.columns]]
            
            # Rellenar NaNs/NAs con "-" para presentación
            for col in df_sistema_nombre_general_2_agua.columns:
                 if df_sistema_nombre_general_2_agua[col].dtype == pd.Int64Dtype():
                     df_sistema_nombre_general_2_agua[col] = df_sistema_nombre_general_2_agua[col].astype(object) # Convertir para permitir "-"
            df_sistema_nombre_general_2_agua = df_sistema_nombre_general_2_agua.fillna("-")

    logger.debug(f"df_sistema_nombre_general_2_agua (componentes para tabla) generado con {len(df_sistema_nombre_general_2_agua)} filas.")
    
    # --- 4. Extraer Coordenadas de Agua para el Mapa ---
    if not df_sistema_general_agua.empty: # Usar df_sistema_general_agua que tiene las coordenadas originales
        coords_agua_raw_df = df_sistema_general_agua[df_sistema_general_agua['zona'].notna() & (df_sistema_general_agua['zona'] != "-")].copy()
        if not coords_agua_raw_df.empty:
            # Usar 'nombre_sin_numero' si existe y es relevante, o 'nombre'
            coords_agua_raw_df['nombre_mapa'] = coords_agua_raw_df['nombre'].astype(str).str.replace(r'^\d+\.\s*', '', regex=True).str.strip()
            # Quitar los "   " de los subcomponentes para el nombre del mapa
            coords_agua_raw_df['nombre_mapa'] = coords_agua_raw_df['nombre_mapa'].str.replace(r'^\s+', '', regex=True)
            
            coordenadas_agua_list_raw.extend(
                coords_agua_raw_df[['nombre_mapa', 'zona', 'este', 'norte', 'altitud']]
                .rename(columns={'nombre_mapa':'nombre'})
                .to_dict('records')
            )

    if not df_sistema_agua_actual.empty:
        df_noconv_coords = df_sistema_agua_actual[df_sistema_agua_actual['tipodesistemadeagua'] == 'Sistema de agua no convencional'].copy()
        if not df_noconv_coords.empty and _get_value(df_noconv_coords, 'p004_zona', pd.NA) not in [pd.NA, "-"]:
            coordenadas_agua_list_raw.append({
                "nombre": "Sistema no convencional",
                "zona": _get_value(df_noconv_coords, 'p004_zona'), "este": _get_value(df_noconv_coords, 'p004_este'),
                "norte": _get_value(df_noconv_coords, 'p004_norte'), "altitud": _get_value(df_noconv_coords, 'p004_altitud')
            })
    logger.debug(f"Coordenadas de agua crudas recolectadas: {len(coordenadas_agua_list_raw)} items.")

    # --- 5. Preparar Resumen del Sistema de Agua (df_sistema_agua_resumen) ---
    df_sistema_agua_resumen = df_sistema_agua_actual.copy()
    if not df_sistema_agua_resumen.empty:
        df_sistema_agua_resumen['N_group'] = df_sistema_agua_resumen.groupby('tipodesistemadeagua', dropna=False).cumcount() + 1
        df_sistema_agua_resumen['num'] = df_sistema_agua_resumen.apply(lambda r: f"S{r['N_group']}", axis=1)

        # Merge cloro residual del reservorio
        if not df_reservorio_proc.empty and 'clororesidualmgl' in df_reservorio_proc.columns and \
            not pd.api.types.is_string_dtype(df_reservorio_proc['clororesidualmgl']):
            df_res_cloro = df_reservorio_proc.groupby('codigodesistemadeagua')['clororesidualmgl'].mean().reset_index()
            df_res_cloro['clororesidualmgl'] = df_res_cloro['clororesidualmgl'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
            df_sistema_agua_resumen = pd.merge(df_sistema_agua_resumen, df_res_cloro, on='codigodesistemadeagua', how='left')
        else:
            df_sistema_agua_resumen['clororesidualmgl'] = "-"

        # Merge continuidad del servicio (desde df_ps_actual)
        # Asegurar que df_ps_actual tiene 'codigodeprestador'
        if not df_ps_actual.empty and 'codigodeprestador' in df_ps_actual.columns:
            cols_cont = ['p029a_continuidadpromedioenepocadelluviahorasdia', 'p029b_continuidadpromedioenepocadeestiajehorasdia']
            if all(c in df_ps_actual.columns for c in cols_cont):
                # Necesitamos agrupar por 'codigodeprestador' y luego hacer merge.
                # El df_sistema_agua_actual ya está filtrado por un prestador.
                # Si un prestador tiene múltiples sistemas de agua, y PS está a nivel de prestador,
                # el valor de continuidad será el mismo para todos sus sistemas de agua.
                # Si PS está a nivel de sistema de agua, el merge es directo por 'codigodesistemadeagua'.
                # El código original hace merge con df_sistema_agua_prueba[['codigodesistemadeagua', 'codigodeprestador']]
                # lo que implica que PS tiene 'codigodeprestador' y se busca la continuidad promedio por prestador.

                # Tomar el primer código de prestador (asumiendo que todos los sistemas de agua son del mismo prestador)
                current_prestador_codigo = _get_value(df_sistema_agua_resumen, 'codigodeprestador', None)
                if current_prestador_codigo:
                    df_ps_cont_prestador = df_ps_actual[df_ps_actual['codigodeprestador'] == current_prestador_codigo]
                    if not df_ps_cont_prestador.empty:
                        df_ps_cont_prestador[cols_cont[0]] = pd.to_numeric(df_ps_cont_prestador[cols_cont[0]], errors='coerce')
                        df_ps_cont_prestador[cols_cont[1]] = pd.to_numeric(df_ps_cont_prestador[cols_cont[1]], errors='coerce')
                        cont_lluvia_mean = df_ps_cont_prestador[cols_cont[0]].mean()                    
                        cont_estiaje_mean = df_ps_cont_prestador[cols_cont[1]].mean()
                        df_sistema_agua_resumen['contia_calc'] = formatear_valor(cont_lluvia_mean, defecto="-")
                        df_sistema_agua_resumen['contie_calc'] = formatear_valor(cont_estiaje_mean, defecto="-")
                    else:
                        df_sistema_agua_resumen['contia_calc'] = "-"
                        df_sistema_agua_resumen['contie_calc'] = "-"
            else: # Columnas de continuidad no existen en df_ps_actual
                df_sistema_agua_resumen['contia_calc'] = "-"
                df_sistema_agua_resumen['contie_calc'] = "-"
        else: # df_ps_actual vacío o sin codigodeprestador
            df_sistema_agua_resumen['contia_calc'] = "-"
            df_sistema_agua_resumen['contie_calc'] = "-"

        df_sistema_agua_resumen.rename(columns={
            'contia_calc': 'contia', 'contie_calc': 'contie', # Usar las calculadas
            'p027_elsistemadeaguacuentaconequipoclorador': 'tieneequipoclorador'
        }, inplace=True, errors='ignore')
        
        # Conversión de años ya hecha en _aplicar_limpieza_tipos_df
        
        # Rellenar NaNs con "-" después de todos los merges y cálculos numéricos
        # Pero antes, convertir columnas Int64 a object si van a ser llenadas con "-"
        for col in df_sistema_agua_resumen.select_dtypes(include=[pd.Int64Dtype()]).columns:
            df_sistema_agua_resumen[col] = df_sistema_agua_resumen[col].astype(object)
        df_sistema_agua_resumen = df_sistema_agua_resumen.fillna("-")


        if not df_sistema_nombre_general_2_agua.empty and 'estadooperativo' in df_sistema_nombre_general_2_agua.columns:
            # Asegurar que la columna para groupby no tenga NaNs
            df_sistema_nombre_general_2_agua_copy = df_sistema_nombre_general_2_agua.copy()
            df_sistema_nombre_general_2_agua_copy['codigodesistemadeagua'] = df_sistema_nombre_general_2_agua_copy['codigodesistemadeagua'].fillna("TEMP_NA_KEY")

            df_eo_agua_agrupado = df_sistema_nombre_general_2_agua_copy.groupby('codigodesistemadeagua').apply(
                lambda g: determinar_estado_operativo_grupo(g, 'estadooperativo')
            ).reset_index(name='EO')
            
            df_eo_agua_agrupado['codigodesistemadeagua'] = df_eo_agua_agrupado['codigodesistemadeagua'].replace("TEMP_NA_KEY", pd.NA)
            if not df_eo_agua_agrupado.empty:
                 df_sistema_agua_resumen = pd.merge(df_sistema_agua_resumen, df_eo_agua_agrupado, on='codigodesistemadeagua', how='left')
                 df_sistema_agua_resumen['EO'] = df_sistema_agua_resumen['EO'].fillna("-")
            else:
                df_sistema_agua_resumen['EO'] = "-"

        else:
            df_sistema_agua_resumen['EO'] = "-"

        df_sistema_agua_resumen['antiguedadnoconven'] = df_sistema_agua_resumen['p004_anodecontruccionnoconvencional'].apply(calcular_anios_antiguedad)
        df_sistema_agua_resumen['antiguedadconven'] = df_sistema_agua_resumen['p007_enqueanoseconstruyoelsistemadeagua'].apply(calcular_anios_antiguedad)
        
        mantenimiento_cols = ['codigodesistemadeagua', 'p012_mantenimientocaptacion', 'p012_mantenimientocasetayequipodebombeo', 'p012_mantenimientolineadeconduccion', 'p012_mantenimientoptap', 'p012_mantenimientoreservorio', 'p012_mantenimientoreddedistribucion']
        if all(c in df_sistema_agua_resumen.columns for c in mantenimiento_cols):
             df_sistema_agua_resumen['mantenimiento'] = df_sistema_agua_resumen.apply(
                 lambda row: determinar_estado_mantenimiento_fila(row[mantenimiento_cols], mantenimiento_cols[1:]), axis=1
             ) # Pasar solo las columnas relevantes a la función
        else:
            logger.warning(f"Faltan columnas de mantenimiento en df_sistema_agua_resumen. Columnas presentes: {df_sistema_agua_resumen.columns.tolist()}")
            df_sistema_agua_resumen['mantenimiento'] = "-"
            
        df_resumen_conv = df_sistema_agua_resumen[df_sistema_agua_resumen['tipodesistemadeagua'] == 'Sistema de agua convencional'].copy()
        df_resumen_noconv = df_sistema_agua_resumen[df_sistema_agua_resumen['tipodesistemadeagua'] == 'Sistema de agua no convencional'].copy()

        if not df_resumen_conv.empty: convencional_flag = "Si"
        if not df_resumen_noconv.empty: noconvencional_flag = "Si"

        for df_res, lista_target in [(df_resumen_conv, sistemas_de_agua_conv_list), (df_resumen_noconv, sistemas_de_agua_noconv_list)]:
            if not df_res.empty:
                for _, sistema_row in df_res.iterrows():
                    dict_sis = sistema_row.to_dict()
                    # Los componentes ya deberían estar limpios de NaN en df_sistema_nombre_general_2_agua
                    if not df_sistema_nombre_general_2_agua.empty:
                        componentes = df_sistema_nombre_general_2_agua[
                            df_sistema_nombre_general_2_agua['codigodesistemadeagua'] == sistema_row['codigodesistemadeagua']
                        ].to_dict('records')
                        dict_sis['componentes'] = componentes
                    else:
                        dict_sis['componentes'] = []
                    lista_target.append(dict_sis)
        sistemas_de_agua_list = sistemas_de_agua_conv_list + sistemas_de_agua_noconv_list

    context_agua['sistemasdeagua'] = sistemas_de_agua_list
    context_agua['sistemas_de_agua_convecional'] = sistemas_de_agua_conv_list
    context_agua['sistemas_de_agua_noconvencional'] = sistemas_de_agua_noconv_list
    context_agua['convencional'] = convencional_flag
    context_agua['noconvencional'] = noconvencional_flag
    
    # Limpiar coordenadas_agua_list de duplicados por nombre y convertir a valores finales
    final_coordenadas_agua = []
    seen_coords_agua_nombres = set()
    for coord_dict_raw in coordenadas_agua_list_raw:
        nombre_coord_raw = coord_dict_raw.get("nombre")
        if nombre_coord_raw not in seen_coords_agua_nombres and pd.notna(coord_dict_raw.get("este")): # Solo si tiene este y no se ha visto
            final_coordenadas_agua.append({
                "nombre": str(nombre_coord_raw) if pd.notna(nombre_coord_raw) else "-", 
                "zona": str(coord_dict_raw.get("zona")) if pd.notna(coord_dict_raw.get("zona")) else "-",
                "este": formatear_valor(coord_dict_raw.get("este")), 
                "norte": formatear_valor(coord_dict_raw.get("norte")),
                "altitud": formatear_valor(coord_dict_raw.get("altitud"))
            })
            if pd.notna(nombre_coord_raw):
                seen_coords_agua_nombres.add(nombre_coord_raw)
    logger.info("Preparación de sistemas de agua completada.")
    return context_agua, final_coordenadas_agua

def preparar_sistemas_alcantarillado_ptar_ubs(
    df_prestador_actual,  
    df_sistema_alca_actual, 
    df_ptar_actual, 
    df_disposicion_actual, 
    df_ubs_actual, 
    df_ps_actual, 
    coordenadas_agua_list_preformateadas 
):
    context_saneamiento = {}
    coordenadas_saneamiento_list_raw = [] # Para EBAR, PTAR, antes de formateo final

    # --- Manejo Inicial de DataFrames Vacíos ---
    # Si no hay sistema de alcantarillado, muchas cosas serán '-'
    df_sa_actual_filtrado = pd.DataFrame()
    if isinstance(df_sistema_alca_actual, pd.DataFrame) and not df_sistema_alca_actual.empty:
        # Asumimos que df_sistema_alca_actual ya está filtrado por el prestador correcto
        # y tomamos el primer sistema de alcantarillado si hay varios (comportamiento original)
        df_sa_actual_filtrado = df_sistema_alca_actual.head(1).copy()

    df_ptar_actual_filtrado = pd.DataFrame()
    if isinstance(df_ptar_actual, pd.DataFrame) and not df_ptar_actual.empty:
        df_ptar_actual_filtrado = df_ptar_actual.head(1).copy()
    
    df_disposicion_actual_filtrado = pd.DataFrame()
    if isinstance(df_disposicion_actual, pd.DataFrame) and not df_disposicion_actual.empty:
        df_disposicion_actual_filtrado = df_disposicion_actual[
            df_disposicion_actual['p029_autorizaciondevertimiento'].notna()
        ].head(1).copy()

    df_ubs_actual_filtrado = pd.DataFrame()
    if isinstance(df_ubs_actual, pd.DataFrame) and not df_ubs_actual.empty:
        df_ubs_actual_filtrado = df_ubs_actual.head(1).copy()

    # --- Sistema de Alcantarillado ---
    logger.debug("Preparando datos del sistema de alcantarillado...")
    context_saneamiento['tiene_alca'] = "No"
    eoalca_val = "-"
    eoebar_val = "-"
    
    default_alca_keys = [
        'tipodesistemadealcantarilladosanitario', 'alcantarilladoadministradoporunaeps',
        'anodeconstruccionalca', 'eoalca', 'descripcionalca', 'eoebar', 'descripcionebar',
        'comentariossistemaalcantarillado', 'antiguedadalca', 'p008_realizamantenimientoalareddealcantarillado'
    ]
    for k in default_alca_keys: context_saneamiento[k] = "-"

    if not df_sa_actual_filtrado.empty:
        context_saneamiento['tiene_alca'] = "Si"
        
        # Asegurar que las columnas existan antes de aplicar funciones
        if 'anodeconstruccion' in df_sa_actual_filtrado.columns:
            df_sa_actual_filtrado['antiguedadalca'] = df_sa_actual_filtrado['anodeconstruccion'].apply(calcular_anios_antiguedad)
            context_saneamiento['anodeconstruccionalca'] = _get_value(df_sa_actual_filtrado, 'anodeconstruccion') # Ya debería ser año
        else:
            df_sa_actual_filtrado['antiguedadalca'] = "-" # Crear columna para evitar KeyError
            context_saneamiento['anodeconstruccionalca'] = "-"
        
        if 'tieneebar' in df_sa_actual_filtrado.columns:
            df_sa_actual_filtrado['eoebar'] = df_sa_actual_filtrado.apply(
                lambda r: 'No cuenta' if _get_value(r.to_frame().T, 'tieneebar', 'No') == 'No' else _get_value(r.to_frame().T, 'estadooperativoebar', '-'), axis=1
            )
            df_sa_actual_filtrado['descripcionebar'] = df_sa_actual_filtrado.apply(
                lambda r: 'No cuenta' if _get_value(r.to_frame().T, 'tieneebar', 'No') == 'No' else _get_value(r.to_frame().T, 'justifiquesurespuestaalca', '-'), axis=1
            )
        else:
            df_sa_actual_filtrado['eoebar'] = "No cuenta"
            df_sa_actual_filtrado['descripcionebar'] = "No cuenta"

        for key in default_alca_keys: # Rellenar con valores reales si existen
            if key in df_sa_actual_filtrado.columns:
                context_saneamiento[key] = _get_value(df_sa_actual_filtrado, key)
        
        eoalca_val = context_saneamiento['eoalca']
        eoebar_val = context_saneamiento['eoebar']
        
        # Coordenadas EBAR
        tiene_ebar_val = _get_value(df_sa_actual_filtrado, 'tieneebar', default='No') # Usar un default que no sea pd.NA
        zona_val = _get_value(df_sa_actual_filtrado, 'zona', default=None) # Usar None como default para facilitar chequeo de pd.isna
        este_val = _get_value(df_sa_actual_filtrado, 'este', default=None)

        if tiene_ebar_val == 'Si' and \
           (not pd.isna(zona_val) and zona_val != "-") and \
           (not pd.isna(este_val)):
            coordenadas_saneamiento_list_raw.append({
                "nombre": "EBAR", 
                "zona": _get_value(df_sa_actual_filtrado, 'zona'), 
                "este": _get_value(df_sa_actual_filtrado, 'este'), 
                "norte": _get_value(df_sa_actual_filtrado, 'norte', default=None), 
                "altitud": _get_value(df_sa_actual_filtrado, 'altitud', default=None)
            })

    # --- PTAR ---
    logger.debug("Preparando datos de PTAR...")
    context_saneamiento['tiene_ptar'] = "No"
    eotar_val = "-"
    lista_total_ptar_componentes = []
    context_saneamiento.update({k: "-" for k in ['anodeconstruccionptar', 'comentariosptar']})

    if not df_ptar_actual_filtrado.empty:
        context_saneamiento['tiene_ptar'] = "Si"
        context_saneamiento['anodeconstruccionptar'] = _get_value(df_ptar_actual_filtrado, 'anodeconstruccionptar')
        context_saneamiento['comentariosptar'] = _get_value(df_ptar_actual_filtrado, 'comentarios')
        
        zona_ptar_val = _get_value(df_ptar_actual_filtrado, 'zona', default=None)
        este_ptar_val = _get_value(df_ptar_actual_filtrado, 'este', default=None)
        
        if (not pd.isna(zona_ptar_val) and zona_ptar_val != "-") and \
           (not pd.isna(este_ptar_val)):
            coordenadas_saneamiento_list_raw.append({
                "nombre": "PTAR", 
                "zona": _get_value(df_ptar_actual_filtrado, 'zona'), 
                "este": _get_value(df_ptar_actual_filtrado, 'este'), 
                "norte": _get_value(df_ptar_actual_filtrado, 'norte', default=None), 
                "altitud": _get_value(df_ptar_actual_filtrado, 'altitud', default=None)
            })

        tratamientos_config = {
            "TRATAMIENTO PRELIMINAR": [('Rejas', 'tienerejas', 'eorejas', 'justifiquesurespuestarejas'), ('Desarenador', 'tienedesarenador', 'eodesarenador', 'justifiquesurespuestadesarenador'), ('Medidor y repartidor de caudal', 'tienemedidoryrepartidordecaudal', 'eomedidoryrepartidorcaudal', 'justifiquesurespuestamedidorcaudal')],
            "TRATAMIENTO PRIMARIO": [('Tanque Imhoff', 'tieneimhoff', 'eoimhoff', 'justifiquesurespuestatanqueimhoff'), ('Tanque séptico', 'tienetanqueseptico', 'eotanqueseptico', 'justifiquesurespuestatanqueseptico'), ('Tanque de sedimentación', 'tienetanquedesedimentacion', 'eotanquesedimentacion', 'justifiquesurespuestatanquesedimento'), ('Tanque de flotación', 'tienetanquedeflotacion', 'eotanquedeflotacion', 'justifiquesurespuestatanqueflota'), ('RAFA/UASB', 'tienerafauasb', 'eorafauasb', 'justifiquesurespuestarafa')],
            "TRATAMIENTO SECUNDARIO": [('Lagunas de estabilizacion', 'tienelagunasdeestabilizacion', 'eolagunasestabilizacion', 'justifiquesurespuestalagunaestabilizacion'), ('Lodos activados', 'tienelodosactivados', 'eolodosactivados', 'justifiquesurespuestalodosactivados'), ('Filtros percoladores', 'tienefiltrospercoladores', 'eofiltrospercoladores', 'justifiquesurespuestafiltrospercoladores')]
        }
        todos_componentes_ptar_eo_list = []
        for tipo_trat, componentes_conf in tratamientos_config.items():
            componentes_para_tipo = []
            for nombre_comp, col_cuenta, col_eo, col_desc in componentes_conf:
                if _get_value(df_ptar_actual_filtrado, col_cuenta) == 'Si': # Asegurar que se usa el df correcto
                    comp_dict = {'nombre': nombre_comp, 'cuenta': 'Si', 
                                 'estadooperativo': _get_value(df_ptar_actual_filtrado, col_eo), 
                                 'descripcion': _get_value(df_ptar_actual_filtrado, col_desc)}
                    componentes_para_tipo.append(comp_dict)
                    todos_componentes_ptar_eo_list.append(comp_dict['estadooperativo'])
            if componentes_para_tipo:
                lista_total_ptar_componentes.append({
                    "tipo": tipo_trat, 
                    "codigosistemaalcantarillado": _get_value(df_ptar_actual_filtrado, 'codigosistemaalcantarillado', "-"), # Asumiendo esta columna existe
                    "componentes": componentes_para_tipo
                })
        if todos_componentes_ptar_eo_list:
             eotar_val = determinar_estado_operativo_grupo(pd.DataFrame({'estadooperativo': todos_componentes_ptar_eo_list}), 'estadooperativo')
    
    context_saneamiento['listadopreliminar'] = lista_total_ptar_componentes # Nombre original de la variable de contexto

    # --- Disposición Final ---
    logger.debug("Preparando datos de disposición final...")
    context_saneamiento['p029_autorizaciondevertimiento'] = "-"
    if not df_disposicion_actual_filtrado.empty:
        context_saneamiento['p029_autorizaciondevertimiento'] = _get_value(df_disposicion_actual_filtrado, 'p029_autorizaciondevertimiento')

    # EO Final Alcantarillado
    context_saneamiento['eofinalca'] = evaluar_estado_operativo_alcantarillado([eoalca_val, eoebar_val, eotar_val])

    # --- UBS ---
    logger.debug("Preparando datos de UBS...")
    context_saneamiento['tiene_ubs'] = "No"
    context_saneamiento.update({k: "-" for k in ['tipoubs', 'tipo_ubs_aux', 'anioubs', 'comentariosubs']})
    if not df_ubs_actual_filtrado.empty:
        context_saneamiento['tiene_ubs'] = "Si"
        tipo_ubs_val = _get_value(df_ubs_actual_filtrado, 'tipoubsodisposicionesinadecuadasdeexcretas')
        context_saneamiento['tipoubs'] = tipo_ubs_val
        ubs_aux_map = {'Arrastre hidráulico': 'UBS - AH', 'Compostera': 'UBS - C', 'Hoyo seco ventilado': 'UBS - HSV'}
        context_saneamiento['tipo_ubs_aux'] = ubs_aux_map.get(tipo_ubs_val, tipo_ubs_val if tipo_ubs_val != '-' else '-')
        context_saneamiento['anioubs'] = _get_value(df_ubs_actual_filtrado, 'enqueanoseconstruyolaubs') # Ya es año
        context_saneamiento['comentariosubs'] = _get_value(df_ubs_actual_filtrado, 'comentarios')

    # --- Disposición no adecuada (desde df_ps_actual) ---
    logger.debug("Preparando datos de disposición no adecuada...")
    context_saneamiento.update({k: "-" for k in ['tiene_noadecuado', 'tiponoadecuado', 'comentarionoadecuado']})
    if isinstance(df_ps_actual, pd.DataFrame) and not df_ps_actual.empty and 'viviendascondisposiciondeexcretasnoadecuadas' in df_ps_actual.columns:
        df_ps_alca_no_adecuada = df_ps_actual[
            (df_ps_actual['viviendascondisposiciondeexcretasnoadecuadas'].notna()) & 
            (df_ps_actual['viviendascondisposiciondeexcretasnoadecuadas'] == 'Si')
        ].head(1) # Tomar la primera ocurrencia
        if not df_ps_alca_no_adecuada.empty:
            context_saneamiento['tiene_noadecuado'] = "Si"
            context_saneamiento['tiponoadecuado'] = _get_value(df_ps_alca_no_adecuada, 'tiponoadecuado')
            context_saneamiento['comentarionoadecuado'] = _get_value(df_ps_alca_no_adecuada, 'comentarios') # Asumo columna 'comentarios' en df_ps_actual
    
    # --- Coordenadas Totales (Combinar y Formatear) ---
    logger.debug("Combinando y formateando coordenadas finales...")
    coordenadas_finales_list_fmt = []
    seen_coords_final_nombres = set() # Para evitar duplicados por nombre en la lista final
    
    # Primero las de agua (ya vienen formateadas de la función anterior)
    for coord_agua in coordenadas_agua_list_preformateadas:
        nombre_coord = coord_agua.get("nombre")
        if nombre_coord and nombre_coord != "-" and nombre_coord not in seen_coords_final_nombres:
            coordenadas_finales_list_fmt.append(coord_agua)
            seen_coords_final_nombres.add(nombre_coord)
            
    # Luego las de saneamiento (EBAR, PTAR - necesitan formateo)
    for coord_san_raw in coordenadas_saneamiento_list_raw:
        nombre_coord_san = coord_san_raw.get("nombre")
        if nombre_coord_san and nombre_coord_san != "-" and nombre_coord_san not in seen_coords_final_nombres:
            coordenadas_finales_list_fmt.append({
                "nombre": str(nombre_coord_san), 
                "zona": str(coord_san_raw.get("zona", "-")),
                "este": formatear_valor(coord_san_raw.get("este")), 
                "norte": formatear_valor(coord_san_raw.get("norte")),
                "altitud": formatear_valor(coord_san_raw.get("altitud"))
            })
            seen_coords_final_nombres.add(nombre_coord_san)
            
    context_saneamiento['coordenadas'] = coordenadas_finales_list_fmt
    logger.info("Preparación de sistemas de alcantarillado, PTAR y UBS completada.")
    return context_saneamiento

def preparar_percepcion_usuarios(df_usuario_actual, df_prestador_actual):
    context_usr = {}
    # DataFrames que se devolverán para ser graficados externamente
    df_resumen_abastecimiento_graf = pd.DataFrame(columns=['tipo', 'Cantidad', 'Gasto Promedio', 'Litros Promedio', 'Descripción', 'Porcentaje'])
    df_veces_abastecimiento_graf = pd.DataFrame(columns=['frecuencia', 'Cantidad', 'Porcentaje'])
    df_gastos_otros_servicios_graf = pd.DataFrame(columns=['Categoria', 'Promedio de Gasto'])

    # Inicializar listas de texto
    abastecimiento_list_text = []
    gastomensual_list_text = []
    litrosagua_list_text = []
    frecuencias_list_text = []
    gastos_otros_list_text = []

    # Valores por defecto para el contexto
    default_text_keys = ['texto_cobro', 'texto_satisfaccion', 'texto_disposicion', 'texto_uso', 
                         'texto_reutiliza', 'texto_abastecimiento', 'texto_gasto_agua', 
                         'texto_disposicion_recibir', 'texto_gasto_otroservicio']
    default_perc_keys = ['porcentaje_cobro_si', 'porcentaje_satisfaccion_si', 
                         'porcentaje_disposicion_si', 'porcentaje_reutiliza_si']
    
    for key in default_text_keys: context_usr[key] = "Información no disponible."
    for key in default_perc_keys: context_usr[key] = "- %"
    context_usr.update({'es_abastecido_todos': '-', 'es_abastecido_algunos': '-'})

    if not isinstance(df_usuario_actual, pd.DataFrame) or df_usuario_actual.empty:
        logger.warning("DataFrame de usuarios vacío o no es un DataFrame, no se procesará la percepción.")
        context_usr.update({'abastecimiento': ["-"], 'gastomensual': ["-"], 'litrosagua': ["-"], 
                            'frecuencias': ["-"], 'gastos': ["-"]})
        return context_usr, df_resumen_abastecimiento_graf, df_veces_abastecimiento_graf, df_gastos_otros_servicios_graf

    # --- Lógica general y para "Con Prestador" ---
    col_paga_serv = 'p006_pagaporlosserviciosdesaneamiento'
    if col_paga_serv in df_usuario_actual.columns:
        cant_cobro = df_usuario_actual[col_paga_serv].value_counts()
        total_resp_cobro = cant_cobro.sum()
        if total_resp_cobro > 0:
            porc_cobro_si_num = (cant_cobro.get('Si', 0) / total_resp_cobro * 100)
            context_usr['porcentaje_cobro_si'] = f"{porc_cobro_si_num:.1f} %"
            context_usr['texto_cobro'] = f"El {context_usr['porcentaje_cobro_si']} ({cant_cobro.get('Si',0)} de {total_resp_cobro}) de usuarios entrevistados pagan por los servicios de saneamiento."
        else:
            context_usr['texto_cobro'] = "No hay respuestas sobre el pago de servicios."
    
    col_satisfaccion = 'p010_niveldesatisfaccionconelservicio'
    if col_satisfaccion in df_usuario_actual.columns:
        cant_sat = df_usuario_actual[col_satisfaccion].value_counts()
        sat_si = cant_sat.get('Satisfecho', 0) + cant_sat.get('Muy satisfecho', 0)
        sat_total = df_usuario_actual[col_satisfaccion].count()
        if sat_total > 0:
            porc_sat_si_num = (sat_si / sat_total * 100)
            context_usr['porcentaje_satisfaccion_si'] = f"{porc_sat_si_num:.1f} %"
            context_usr['texto_satisfaccion'] = f"El {context_usr['porcentaje_satisfaccion_si']} ({sat_si} de {sat_total}) de usuarios entrevistados refieren estar satisfechos con el servicio brindado por el prestador."
        else:
            context_usr['texto_satisfaccion'] = "No hay respuestas sobre el nivel de satisfacción."

    col_paga_adicional = 'p012_pagariaunmontoadicionalporelservicio'
    if col_paga_adicional in df_usuario_actual.columns:
        cant_disp = df_usuario_actual[col_paga_adicional].value_counts()
        total_resp_disp = cant_disp.sum()
        if total_resp_disp > 0:
            porc_disp_si_num = (cant_disp.get('Si', 0) / total_resp_disp * 100)
            porc_disp_no_num = (cant_disp.get('No', 0) / total_resp_disp * 100)
            context_usr['porcentaje_disposicion_si'] = f"{porc_disp_si_num:.1f} %"
            context_usr['texto_disposicion'] = (
                f"El {context_usr['porcentaje_disposicion_si']} ({cant_disp.get('Si',0)} de {total_resp_disp}) de usuarios refieren que están de acuerdo "
                f"en pagar un monto adicional por una mejora en el servicio. En tanto, el otro {porc_disp_no_num:.1f} % "
                f"({cant_disp.get('No',0)} de {total_resp_disp}) no están de acuerdo con pagar un monto adicional."
            )
        else:
            context_usr['texto_disposicion'] = "No hay respuestas sobre disposición a pagar adicional."

    columnas_verificar_uso = ['p016_riegodehuertas', 'p016_lavadodevehiculos', 'p016_riegodecalle', 'p016_crianzadeanimales', 'p016_otro']
    if all(c in df_usuario_actual.columns for c in columnas_verificar_uso):
        df_usuario_actual_copy = df_usuario_actual.copy()
        df_usuario_actual_copy['uso_otros'] = df_usuario_actual_copy.apply(
            lambda row: 'Si' if any(row.get(col_uso) == 'Si' for col_uso in columnas_verificar_uso) else 'No', axis=1
        )
        cant_uso = df_usuario_actual_copy['uso_otros'].value_counts()
        total_resp_uso = cant_uso.sum()
        if total_resp_uso > 0:
            porc_uso_si_num = (cant_uso.get('Si', 0) / total_resp_uso * 100)
            porc_uso_no_num = (cant_uso.get('No', 0) / total_resp_uso * 100)
            
            nombres_uso_map = {'p016_riegodehuertas': 'riego de huertas', 'p016_lavadodevehiculos': 'lavado de vehículos', 
                               'p016_riegodecalle': 'riego de calle', 'p016_crianzadeanimales': 'crianza de animales', 'p016_otro': 'otro'}
            # Verificar si hay algún 'Si' en CUALQUIER fila para estas columnas
            usos_con_si_list = []
            for col_original, nombre_uso in nombres_uso_map.items():
                if (df_usuario_actual_copy[col_original] == 'Si').any():
                    usos_con_si_list.append(nombre_uso)
            usos_concat = ', '.join(usos_con_si_list) if usos_con_si_list else "ninguno especificado"

            if porc_uso_no_num >= 99.9: 
                context_usr['texto_uso'] = 'Ninguno de los usuarios entrevistados refieren que le dan otros usos al agua potable.'
            else:
                context_usr['texto_uso'] = f"El {porc_uso_si_num:.1f} % ({cant_uso.get('Si',0)} de {total_resp_uso}) de los entrevistados refieren que otros usos le dan al agua: {usos_concat}."
        else:
            context_usr['texto_uso'] = "No hay respuestas sobre otros usos del agua."
    
    col_reutiliza = 'p017_reutilizaelagua'
    if col_reutiliza in df_usuario_actual.columns:
        cant_reutiliza = df_usuario_actual[col_reutiliza].value_counts()
        total_resp_reutiliza = cant_reutiliza.sum()
        if total_resp_reutiliza > 0:
            porc_reutiliza_si_num = (cant_reutiliza.get('Si', 0) / total_resp_reutiliza * 100)
            context_usr['porcentaje_reutiliza_si'] = f"{porc_reutiliza_si_num:.1f} %"
            context_usr['texto_reutiliza'] = f"El {context_usr['porcentaje_reutiliza_si']} ({cant_reutiliza.get('Si',0)} de {total_resp_reutiliza}) de entrevistados manifiestan que reutilizan el agua."
        else:
            context_usr['texto_reutiliza'] = "No hay respuestas sobre reutilización del agua."

    # --- Caso: Usuarios que NO reciben servicio del prestador ---
    col_recibe_servicio = 'p005_elusuariorecibeelserviciodelprestador'
    df_usr_no_prest = pd.DataFrame()
    if col_recibe_servicio in df_usuario_actual.columns:
        # Asegurar que la columna no tenga NaNs antes de la comparación booleana
        all_si = (df_usuario_actual[col_recibe_servicio].fillna('No') == 'Si').all() if not df_usuario_actual.empty else False
        context_usr['es_abastecido_todos'] = 'Si' if all_si else '-'
        
        df_usr_no_prest = df_usuario_actual[df_usuario_actual[col_recibe_servicio] == 'No'].copy()
        context_usr['es_abastecido_algunos'] = 'Si' if not df_usr_no_prest.empty else '-'
    
    if not df_usr_no_prest.empty:
        logger.info(f"Procesando {len(df_usr_no_prest)} usuarios que no reciben servicio del prestador.")
        
        # Funciones helper internas para esta sección (ya definidas antes)
        def _count_si_no_prest_local(df, column): return (df[column] == 'Si').sum() if column in df else 0
        def _mean_if_si_no_prest_local(df, col_check, col_value):
            if col_check in df and col_value in df:
                subset_df = df.loc[df[col_check] == 'Si', col_value]
                subset_df_numeric = pd.to_numeric(subset_df, errors='coerce')
                if not subset_df_numeric.empty and subset_df_numeric.notna().any():
                    mean_val = subset_df_numeric.mean()
                    return round(mean_val, 1) if pd.notna(mean_val) else np.nan
            return np.nan
        
        abast_tipos_map_no_prest = {'p001_pozopropio': 'Pozos propios', 'p001_camiones': 'Camiones cisterna', 
                                    'p001_acarreo': 'Acarreo', 'p001_otro': 'Otros'}
        resumen_data_no_prest = []
        for col_key_np, desc_tipo_np in abast_tipos_map_no_prest.items():
            cantidad_np = _count_si_no_prest_local(df_usr_no_prest, col_key_np)
            if cantidad_np > 0:
                resumen_data_no_prest.append({
                    'tipo': desc_tipo_np, 'Cantidad': cantidad_np,
                    'Gasto Promedio': _mean_if_si_no_prest_local(df_usr_no_prest, col_key_np, 'p002_cuantoeselgastomensualenagua'),
                    'Litros Promedio': _mean_if_si_no_prest_local(df_usr_no_prest, col_key_np, 'p002a_litrosequivalencia')
                })
        
        if resumen_data_no_prest:
            df_resumen_abastecimiento_graf = pd.DataFrame(resumen_data_no_prest)
            
            otros_tipos_detalle_str_np = ""
            if 'p001_otro' in df_usr_no_prest.columns and 'p001a_otraformaabastecimiento' in df_usr_no_prest.columns:
                otros_tipos_detalle_list_np = df_usr_no_prest[df_usr_no_prest['p001_otro'] == 'Si']['p001a_otraformaabastecimiento'].dropna().astype(str).str.lower().unique()
                otros_tipos_detalle_str_np = ', '.join(otros_tipos_detalle_list_np) if otros_tipos_detalle_list_np.size > 0 else ""
            
            df_resumen_abastecimiento_graf['Descripción'] = df_resumen_abastecimiento_graf['tipo'].apply(
                lambda x: f'otra forma de abastecimiento ({otros_tipos_detalle_str_np})' if x == 'Otros' and otros_tipos_detalle_str_np else x.lower()
            )
            total_obs_abast_np = df_resumen_abastecimiento_graf['Cantidad'].sum()
            if total_obs_abast_np > 0:
                df_resumen_abastecimiento_graf['Porcentaje'] = (df_resumen_abastecimiento_graf['Cantidad'] / total_obs_abast_np * 100).round(1)
            else:
                df_resumen_abastecimiento_graf['Porcentaje'] = 0.0

            df_resumen_abastecimiento_texto_np = df_resumen_abastecimiento_graf.copy()
            df_resumen_abastecimiento_texto_np[['Gasto Promedio', 'Litros Promedio']] = df_resumen_abastecimiento_texto_np[['Gasto Promedio', 'Litros Promedio']].fillna("-")

            for _, row_np in df_resumen_abastecimiento_texto_np.iterrows():
                if row_np.get('Porcentaje', "-") != "-":
                    abastecimiento_list_text.append(f"El {row_np['Porcentaje']}% de los entrevistados mencionan que se abastecen mediante {row_np['Descripción']}.")
                if row_np.get('Gasto Promedio', "-") != "-":
                    gastomensual_list_text.append(f"En promedio, los usuarios que se abastecen mediante {row_np['Descripción']} gastan mensualmente S/. {row_np['Gasto Promedio']} soles para obtener el agua.")
                if row_np.get('Litros Promedio', "-") != "-":
                    litrosagua_list_text.append(f"En promedio, los usuarios que se abastecen mediante {row_np['Descripción']} consumen mensualmente {row_np['Litros Promedio']} litros de agua al mes.")
        
        col_frec_abast_np = 'p003_cuantasvecesalmesseabastece'
        if col_frec_abast_np in df_usr_no_prest.columns and df_usr_no_prest[col_frec_abast_np].notna().any():
            cant_veces_np = df_usr_no_prest[col_frec_abast_np].value_counts().reset_index()
            # Antes de renombrar, asegurar que 'index' existe si es el nombre por defecto de value_counts().reset_index()
            if 'index' in cant_veces_np.columns:
                 cant_veces_np.rename(columns={'index': 'frecuencia', cant_veces_np.columns[1]: 'Cantidad'}, inplace=True)
            else: # Si ya tiene nombre, usar el primer y segundo
                 cant_veces_np.columns = ['frecuencia', 'Cantidad']

            if not cant_veces_np.empty and cant_veces_np['Cantidad'].sum() > 0:
                porc_veces_np = df_usr_no_prest[col_frec_abast_np].value_counts(normalize=True).reset_index()
                if 'index' in porc_veces_np.columns:
                    porc_veces_np.rename(columns={'index': 'frecuencia', porc_veces_np.columns[1]: 'Porcentaje'}, inplace=True)
                else:
                    porc_veces_np.columns = ['frecuencia', 'Porcentaje']
                porc_veces_np['Porcentaje'] = (porc_veces_np['Porcentaje'] * 100)
                df_veces_abastecimiento_graf = pd.merge(cant_veces_np, porc_veces_np, on='frecuencia', how='inner')
                for _, row_frec_np in df_veces_abastecimiento_graf.iterrows():
                    frecuencias_list_text.append(f"El {row_frec_np['Porcentaje']:.1f} % de los entrevistados mencionan que su abastecimiento tiene periodicidad {row_frec_np['frecuencia']}.")
        
        gastos_otros_cols_map_np = {'Electricidad': 'p014a_gastomensualsolesenelectricidad', 'Telefonía': 'p014b_gastomensualsolesentelefoniacelular', 
                                 'Cable': 'p014c_gastomensualsolesencable', 'Internet': 'p014d_gastomensualsoleseninternet', 
                                 'Netflix': 'p014e_gastomensualsolesenstreamingnetflixetc', 'Gas': 'p014h_gastomensualsolesengas'}
        gastos_otros_data_np = []
        for cat_gasto_np, col_gasto_val_np in gastos_otros_cols_map_np.items():
            if col_gasto_val_np in df_usr_no_prest.columns:
                mean_gasto_val_numeric_np = pd.to_numeric(df_usr_no_prest[col_gasto_val_np], errors='coerce').mean()
                if pd.notna(mean_gasto_val_numeric_np):
                    gastos_otros_data_np.append({'Categoria': cat_gasto_np, 'Promedio de Gasto': round(mean_gasto_val_numeric_np,1)})
        if gastos_otros_data_np:
            df_gastos_otros_servicios_graf = pd.DataFrame(gastos_otros_data_np)
            for _, row_gasto_np in df_gastos_otros_servicios_graf.iterrows():
                gastos_otros_list_text.append(f"En promedio, los usuarios gastan S/. {row_gasto_np['Promedio de Gasto']} soles para el servicio de {row_gasto_np['Categoria']} al mes.")

        cols_abast_check_no_prest_local = ['p001_acarreo', 'p001_camiones', 'p001_pozopropio', 'p001_otro'] # Definida localmente
        if all(c in df_usr_no_prest.columns for c in cols_abast_check_no_prest_local):
            df_usr_no_prest_copy = df_usr_no_prest.copy()
            df_usr_no_prest_copy['abastecimiento_cat'] = df_usr_no_prest_copy.apply(lambda r: 'Si' if any(r.get(col) == 'Si' for col in cols_abast_check_no_prest_local) else 'No', axis=1)
            cant_abast_cat_np = df_usr_no_prest_copy['abastecimiento_cat'].value_counts()
            total_resp_abast_cat_np = cant_abast_cat_np.sum()
            if total_resp_abast_cat_np > 0:
                porc_abast_si_no_prest_val = (cant_abast_cat_np.get('Si', 0) / total_resp_abast_cat_np * 100)
                abast_nombres_map_no_prest_local = {'p001_acarreo': 'acarreo', 'p001_camiones': 'camiones cisterna', 'p001_pozopropio': 'pozos propios', 'p001_otro': 'otro'}
                abast_con_si_no_prest_list = [abast_nombres_map_no_prest_local[col] for col in cols_abast_check_no_prest_local if (df_usr_no_prest_copy[col] == 'Si').any()]
                abast_concat_no_prest_str = ', '.join(abast_con_si_no_prest_list) if abast_con_si_no_prest_list else "ninguna forma especificada"

                if porc_abast_si_no_prest_val < 0.1 :
                    context_usr['texto_abastecimiento'] = 'Ninguno de los usuarios entrevistados (que no reciben servicio del prestador) ha mencionado información sobre abastecimiento alternativo de agua potable.'
                else:
                    context_usr['texto_abastecimiento'] = f"El {porc_abast_si_no_prest_val:.1f} % ({cant_abast_cat_np.get('Si',0)} de {total_resp_abast_cat_np}) de los entrevistados (que no reciben servicio del prestador) menciona que el abastecimiento es a través de {abast_concat_no_prest_str}."
        
        col_gasto_agua_no_prest_val = 'p002_cuantoeselgastomensualenagua'
        if col_gasto_agua_no_prest_val in df_usr_no_prest.columns:
            gasto_agua_mean_no_prest_numeric_val = pd.to_numeric(df_usr_no_prest[col_gasto_agua_no_prest_val], errors='coerce').mean()
            cant_gasto_no_nulos_no_prest_val = pd.to_numeric(df_usr_no_prest[col_gasto_agua_no_prest_val], errors='coerce').notna().sum()
            total_usr_no_prest_count_val = len(df_usr_no_prest)
            if total_usr_no_prest_count_val > 0:
                porc_gasto_no_nulos_no_prest_val = (cant_gasto_no_nulos_no_prest_val / total_usr_no_prest_count_val * 100)
                if cant_gasto_no_nulos_no_prest_val == 0:
                    context_usr['texto_gasto_agua'] = 'Ninguno de los usuarios entrevistados (que no reciben servicio del prestador) refieren gasto promedio en abastecimiento de agua.'
                else:
                    context_usr['texto_gasto_agua'] = f"El {porc_gasto_no_nulos_no_prest_val:.1f} % de usuarios entrevistados (que no reciben servicio del prestador) refieren que para abastecerse de agua gastan en promedio {formatear_valor(gasto_agua_mean_no_prest_numeric_val)} soles mensuales."
        
        col_disp_recibir_val = 'p013a_estariadispuestoqueesteotrolebrindeserv'
        col_nom_otro_prest_val = 'p013_1_nombreyubicaciondeprestador'
        if col_disp_recibir_val in df_usr_no_prest.columns and col_nom_otro_prest_val in df_usr_no_prest.columns:
            cant_disp_rec_val = df_usr_no_prest[col_disp_recibir_val].value_counts()
            total_resp_disp_rec_val = cant_disp_rec_val.sum()
            if total_resp_disp_rec_val > 0:
                porc_disp_rec_si_val = (cant_disp_rec_val.get('Si', 0) / total_resp_disp_rec_val * 100)
                nombres_otro_prestador_list_val = df_usr_no_prest[col_nom_otro_prest_val].dropna().astype(str).unique()
                nombre_otro_prestador_str_val = nombres_otro_prestador_list_val[0] if nombres_otro_prestador_list_val.size > 0 else "otro prestador"
                context_usr['texto_disposicion_recibir'] = f"El {porc_disp_rec_si_val:.1f} % ({cant_disp_rec_val.get('Si',0)} de {total_resp_disp_rec_val}) de usuarios (que no reciben servicio del prestador) refieren que estarían de acuerdo con que el prestador {nombre_otro_prestador_str_val}, les provea del servicio."
    
    # Gasto mensual en otros servicios (general, usa df_usuario_actual)
    if not df_usuario_actual.empty:
        gasto_elec_todos = pd.to_numeric(df_usuario_actual.get('p014a_gastomensualsolesenelectricidad'), errors='coerce').mean()
        gasto_tel_todos = pd.to_numeric(df_usuario_actual.get('p014b_gastomensualsolesentelefoniacelular'), errors='coerce').mean()
        context_usr['texto_gasto_otroservicio'] = f"En promedio, el gasto en servicio de electricidad es de S/. {formatear_valor(gasto_elec_todos,1)} y en telefonía celular es de S/. {formatear_valor(gasto_tel_todos)}."


    context_usr['abastecimiento'] = abastecimiento_list_text if abastecimiento_list_text else ["-"]
    context_usr['gastomensual'] = gastomensual_list_text if gastomensual_list_text else ["-"]
    context_usr['litrosagua'] = litrosagua_list_text if litrosagua_list_text else ["-"]
    context_usr['frecuencias'] = frecuencias_list_text if frecuencias_list_text else ["-"]
    context_usr['gastos'] = gastos_otros_list_text if gastos_otros_list_text else ["-"]
    
    logger.info("Preparación de percepción de usuarios completada.")
    return context_usr, df_resumen_abastecimiento_graf, df_veces_abastecimiento_graf, df_gastos_otros_servicios_graf