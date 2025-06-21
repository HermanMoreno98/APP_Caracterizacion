import os
from dotenv import load_dotenv

load_dotenv()

# --- Dataverse / Azure AD ---
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
RESOURCE_DATAVERSE = os.getenv("RESOURCE") # Renombrado para claridad
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE_DATAVERSE = [f"{RESOURCE_DATAVERSE}/.default"]

# --- SharePoint / Microsoft Graph ---
RESOURCE_GRAPH = "https://graph.microsoft.com" # Usado como base para scopes
SCOPES_SHAREPOINT = [f"{RESOURCE_GRAPH}/.default"]
SHAREPOINT_DOMAIN = "sunassgobpe.sharepoint.com"
SHAREPOINT_SITE_PATH = "/sites/adp2"
# El ID de la biblioteca de documentos donde están las carpetas de prestadores (FOTOS, ACTAS)
SHAREPOINT_DOC_LIBRARY_ID_PRESTADORES = "2d1282da-c17d-4888-9111-d1ee867b9510" 
# Ruta en SharePoint al archivo INEI (relativa a la raíz del drive del sitio)
SHAREPOINT_PATH_INEI_FILE = "AUTOMATIZACION/BD/PedidoCCPP_validado.xlsx"
LOCAL_INEI_FILE_NAME = "PedidoCCPP_validado.xlsx" # Nombre local para el archivo INEI

# --- Nombres de carpetas locales temporales ---
DIR_TEMP_BASE = "temp_processing" # Carpeta base para todos los temporales
DIR_REPORTS = os.path.join(DIR_TEMP_BASE, "reports")
DIR_GRAPHS = os.path.join(DIR_TEMP_BASE, "graphs")
DIR_PRESTADOR_FILES = os.path.join(DIR_TEMP_BASE, "cr217_prestador") # Para fotos/actas descargadas
DIR_BD_TEMP = os.path.join(DIR_TEMP_BASE, "BD") # Para el Excel de INEI

# --- Plantillas ---
TEMPLATE_PRINCIPAL = "templates/modelo_final2.docx"
TEMPLATE_SIN_PRESTADOR = "templates/modelo_final2_sin_prestador.docx"

# --- API Headers Base ---
HEADERS_DATAVERSE_BASE = {
    "OData-MaxVersion": "4.0",
    "OData-Version": "4.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Prefer": 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
}
HEADERS_GRAPH_BASE = {
    "Accept": "application/json"
}

# --- Configuraciones para obtener_df_relaciones_prestador ---
# (El diccionario 'relaciones_config' es muy largo, considera ponerlo aquí o en un archivo JSON y cargarlo)
# Ejemplo:
RELACIONES_CONFIG_PRESTADOR = {
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

# CAPTACION (AGUA)
CAMPOS_CAPTACION_AGUA = ["cr217_codigodecaptacion", "cr217_nombredelacaptacion", "cr217_anodeconstruccion",
                "cr217_estadooperativodelacaptacion","cr217_justifiquesurespuestacaptacion","cr217_zona","cr217_este",
                "cr217_norte","cr217_altitud"]
NOMBRES_COLUMNAS_CAPTACION_AGUA = ["codigodecaptacion","nombredelacaptacion", "anodeconstruccion",
                        "estadooperativodelacaptacion","justifiquesurespuestacaptacion","zona","este",
                        "norte","altitud"]

# CONDUCCION (AGUA)
CAMPOS_CONDUCCION_AGUA = ["cr217_codigodeconduccion", "cr217_anodeconstruccionconduccion","cr217_estadooperativodelconductordeaguacruda",
                "cr217_justifiquesurespuestaconduccion"]
NOMBRES_COLUMNAS_CONDUCCION_AGUA = ["codigodeconduccion","anodeconstruccionconduccion", "estadooperativodelconductordeaguacruda",
                        "justifiquesurespuestaconduccion"]

# RESERVORIO (AGUA)
CAMPOS_RESERVORIO_AGUA = ["cr217_codigodereservorio", "cr217_anodeconstruccion","cr217_estadooperativodereservorio",
                "cr217_justifiquesurespuestareservorio","cr217_zona","cr217_este",
                "cr217_norte","cr217_altitud","cr217_clororesidualmgl"]
NOMBRES_COLUMNAS_RESERVORIO_AGUA = ["codigodereservorio","anodeconstruccion", "estadooperativodereservorio",
                        "justifiquesurespuestareservorio","zona","este",
                        "norte","altitud","clororesidualmgl"]

# PTAP (AGUA) - Esta lista es muy larga, la pongo abreviada como ejemplo
CAMPOS_PTAP_AGUA = ["cr217_codigodeptap", "cr217_anodeconstruccion","cr217_tipodeptap","cr217_zona","cr217_este",
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
                "cr217_tienefiltrorapido","cr217_estadooperativofiltrorapido","cr217_justifiquesurespuestafiltrorapido"]
NOMBRES_COLUMNAS_PTAP_AGUA = ["codigodeptap","anodeconstruccion", "tipodeptap","zona","este",
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
                        "tienefiltrorapido","estadooperativofiltrorapido","justifiquesurespuestafiltrorapido"]

# PTAR (ALCANTARILLADO) - Abreviada
CAMPOS_PTAR_ALCA = ["cr217_codigodeptar", "cr217_tienerejas","cr217_eorejas","cr217_justifiquesurespuestarejas",
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
                "cr217_anodeconstruccionptar","cr217_comentarios"]
NOMBRES_COLUMNAS_PTAR_ALCA = ["codigodeptar","tienerejas", "eorejas","justifiquesurespuestarejas",
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
                        "anodeconstruccionptar","comentarios"]

# DISPOSICION FINAL (ALCANTARILLADO)
CAMPOS_DISPOSICION_FINAL_ALCA = [
    "cr217_codigodedisposicionfinal", "cr217_autorizaciondevertimiento"
]
NOMBRES_COLUMNAS_DISPOSICION_FINAL_ALCA = [
    "codigodedisposicionfinal", "p029_autorizaciondevertimiento"
]

CAMPOS_POBLACION_SERVIDA = ["cr217_conexionesdeaguaactivas", "cr217_conexionesdealcantarilladoactivas",
            "cr217_conexionesdeaguatotales","cr217_conexionesdealcantarilladototales","cr217_cantidaddeubsenelccpp",
            "cr217_continuidadpromedioenepocadelluviahorasdia","cr217_continuidadpromedioenepocadeestiajehorasdia",
            "cr217_viviendascondisposiciondeexcretasnoadecuadas","cr217_tiponoadecuado","cr217_comentarios"]
NOMBRES_POBLACION_SERVIDA = ["p022_conexionesdeaguaactivas", "p024_conexionesdealcantarilladoactivas",
                        "p021_conexionesdeaguatotales", "p023_conexionesdealcantarilladototales","p027_cantidaddeubsenelccpp",
                        "p029a_continuidadpromedioenepocadelluviahorasdia","p029b_continuidadpromedioenepocadeestiajehorasdia",
                        "viviendascondisposiciondeexcretasnoadecuadas","tiponoadecuado","comentarios"]

# Lista de columnas para convertir a float
COLUMNAS_FLOAT_PRESTADOR = ['p010_gastomensualpromedioporfamiliaagua','p040_acuantoasciendeelcobroquerealiza',
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
COLUMNAS_FLOAT_PS = ["p022_conexionesdeaguaactivas", "p024_conexionesdealcantarilladoactivas",
                        "p021_conexionesdeaguatotales", "p023_conexionesdealcantarilladototales","p027_cantidaddeubsenelccpp",
                        "p029a_continuidadpromedioenepocadelluviahorasdia","p029b_continuidadpromedioenepocadeestiajehorasdia"]
COLUMNAS_FLOAT_USUARIO = ["p002_cuantoeselgastomensualenagua","p002a_litrosequivalencia","p014a_gastomensualsolesenelectricidad",
                                "p014b_gastomensualsolesentelefoniacelular","p014c_gastomensualsolesencable",
                                "p014d_gastomensualsoleseninternet","p014e_gastomensualsolesenstreamingnetflixetc",
                                "p014h_gastomensualsolesengas"]
COLUMNAS_FLOAT_COORDS = ["este", "norte", "altitud"]
COLUMNAS_FLOAT_RESERVORIO = ['clororesidualmgl']
COLUMNAS_FLOAT_SISTEMA_AGUA = ['p043_clororesidualpuntomaslejano','turbidezunt',"estecasetedebombeo","nortecasetadebombeo","altitudcasetadebombeo"]

# Verificar variables de entorno
REQUIRED_ENV_VARS = ["TENANT_ID", "CLIENT_ID", "CLIENT_SECRET", "RESOURCE"]
# missing_vars = [var for var in REQUIRED_ENV_VARS if not globals().get(var.replace("RESOURCE", "RESOURCE_DATAVERSE"))] # Ajuste por renombramiento
# if missing_vars:
#     raise EnvironmentError(f"Faltan las siguientes variables de entorno: {', '.join(missing_vars)}")

REQUIRED_ENV_VARS = {
    "TENANT_ID": TENANT_ID,
    "CLIENT_ID": CLIENT_ID,
    "CLIENT_SECRET": CLIENT_SECRET,
    "RESOURCE": RESOURCE_DATAVERSE
}
missing_vars = [key for key, val in REQUIRED_ENV_VARS.items() if not val]
if missing_vars:
    raise EnvironmentError(f"Faltan las siguientes variables de entorno: {', '.join(missing_vars)}")


import os
print("TENANT_ID:", os.getenv("TENANT_ID"))
print("CLIENT_ID:", os.getenv("CLIENT_ID"))
print("CLIENT_SECRET:", os.getenv("CLIENT_SECRET"))
print("RESOURCE:", os.getenv("RESOURCE"))