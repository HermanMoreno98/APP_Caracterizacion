import matplotlib
matplotlib.use("Agg") # Configurar backend antes de importar pyplot
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd # Necesario para la lógica de ejemplo, ajustar según sea necesario

# Directorio para guardar gráficos
PLOTS_DIR = "graphs"
os.makedirs(PLOTS_DIR, exist_ok=True) # Crear directorio si no existe

def _formato_etiqueta_pie(pct, allvals):
    absolute = int(round(pct/100.*np.sum(allvals)))
    return f"{pct:.1f}%\n({absolute:d})"

def _func_sum_total_pie(allvalues): # Para cuando autopct debe mostrar suma total
    total = allvalues.sum()
    return f"{total:.1f}"


def generar_grafico_pie_abastecimiento(df_resumen_abastecimiento, nombre_archivo="grafico_abastecimiento.png"):
    """Genera un gráfico de pie para tipos de abastecimiento."""
    ruta_guardado = os.path.join(PLOTS_DIR, nombre_archivo)
    if df_resumen_abastecimiento.empty or 'Porcentaje' not in df_resumen_abastecimiento.columns or df_resumen_abastecimiento['Porcentaje'].sum() == 0:
        plt.figure(figsize=(6,4)) # Ajustar tamaño según necesidad
        plt.text(0.5, 0.5, "Sin datos para graficar", ha='center', va='center', fontsize=12)
        plt.axis('off')
        plt.savefig(ruta_guardado)
        plt.close()
        return ruta_guardado

    plt.figure(figsize=(8,8)) # Ajustar tamaño
    colormap = plt.get_cmap('Blues')
    num_items = len(df_resumen_abastecimiento)
    colors = [colormap(i / num_items * 0.8 + 0.2) for i in range(num_items)] # Ajustar rango de color

    plt.pie(
        df_resumen_abastecimiento['Porcentaje'],
        labels=df_resumen_abastecimiento['tipo'],
        autopct='%1.1f%%', # Usar directamente el porcentaje
        startangle=90,
        colors=colors,
        textprops={'fontsize': 10} # Ajustar tamaño de fuente
    )
    plt.title("Formas de Abastecimiento", fontsize=14)
    plt.tight_layout()
    plt.savefig(ruta_guardado)
    plt.close()
    return ruta_guardado

def generar_grafico_barras(df_datos, columna_valores, columna_etiquetas, titulo_grafico, etiqueta_y, nombre_archivo, rotacion_x=45, fontsize=10):
    """Genera un gráfico de barras genérico."""
    ruta_guardado = os.path.join(PLOTS_DIR, nombre_archivo)
    if df_datos.empty or columna_valores not in df_datos.columns or df_datos[columna_valores].isnull().all():
        plt.figure(figsize=(6,4))
        plt.text(0.5, 0.5, "Sin datos para graficar", ha='center', va='center', fontsize=12)
        plt.axis('off')
        plt.savefig(ruta_guardado)
        plt.close()
        return ruta_guardado

    plt.figure(figsize=(10, 6)) # Ajustar
    colormap = plt.get_cmap('Blues')
    num_items = len(df_datos)
    
    # Usar un solo color o una paleta, aquí un ejemplo con un color base
    bar_color = colormap(0.6) 
    
    fig, ax = plt.subplots(figsize=(10,7)) # Crear figura y ejes
    bars = ax.bar(df_datos[columna_etiquetas], df_datos[columna_valores], color=bar_color, width=0.5)

    ax.set_ylabel(etiqueta_y, fontsize=fontsize + 2)
    ax.set_title(titulo_grafico, fontsize=fontsize + 4)
    ax.tick_params(axis='x', rotation=rotacion_x, labelsize=fontsize, ha="right" if rotacion_x > 0 else "center")
    ax.tick_params(axis='y', labelsize=fontsize)

    for bar in bars:
        height = bar.get_height()
        if pd.notna(height):
             ax.annotate(f'{height:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=fontsize -1)
    
    plt.tight_layout()
    plt.savefig(ruta_guardado)
    plt.close(fig) # Cerrar la figura explícitamente
    return ruta_guardado

def generar_grafico_abastecimiento_pie(df_resumen_abastecimiento, nombre_archivo="grafico_1.png"):
    """Genera un gráfico de pie para porcentaje de abastecimiento por tipo."""
    ruta_guardado = os.path.join(PLOTS_DIR, nombre_archivo)
    num_items = len(df_resumen_abastecimiento)
    if num_items == 0 or 'Porcentaje' not in df_resumen_abastecimiento.columns:
        plt.figure(figsize=(6,4))
        plt.text(0.5, 0.5, "Sin datos para graficar", ha='center', va='center', fontsize=12)
        plt.axis('off')
        plt.savefig(ruta_guardado)
        plt.close()
        return ruta_guardado
    colormap = plt.get_cmap('Blues')
    colors = [colormap(i / num_items * 0.5 + 0.5) for i in range(num_items)]
    plt.figure(figsize=(8,8))
    plt.pie(df_resumen_abastecimiento['Porcentaje'], labels=df_resumen_abastecimiento['tipo'], autopct='%1.1f%%', startangle=90, colors=colors, textprops={'fontsize': 20})
    plt.tight_layout()
    plt.savefig(ruta_guardado)
    plt.close()
    return ruta_guardado


def generar_grafico_gasto_promedio_abastecimiento(df_resumen_abastecimiento, nombre_archivo="grafico_2.png"):
    """Genera gráfico de gasto promedio por tipo de abastecimiento (pie si 1, barras si >1)."""
    ruta_guardado = os.path.join(PLOTS_DIR, nombre_archivo)
    num_items = len(df_resumen_abastecimiento)
    if num_items == 0 or 'Gasto Promedio' not in df_resumen_abastecimiento.columns:
        plt.figure(figsize=(6,4))
        plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
        plt.axis('off')
        plt.savefig(ruta_guardado)
        plt.close()
        return ruta_guardado
    if num_items == 1:
        if df_resumen_abastecimiento['Gasto Promedio'].notnull().all():
            plt.figure(figsize=(8,8))
            colormap = plt.get_cmap('Blues')
            colors = [colormap(0.5)]
            def func(allvalues):
                total = allvalues.sum()
                return "{:.1f}".format(total)
            plt.pie(df_resumen_abastecimiento['Gasto Promedio'], labels=df_resumen_abastecimiento['tipo'], startangle=90, colors=colors, autopct=lambda _: func(df_resumen_abastecimiento['Gasto Promedio']), textprops={'fontsize': 20})
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close()
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    else:
        if df_resumen_abastecimiento['Gasto Promedio'].notnull().all():
            colormap = plt.get_cmap('Blues')
            color = colormap(0.5)
            fig, ax = plt.subplots(figsize=(10,7))
            bar_positions = range(num_items)
            bars = ax.bar(bar_positions, df_resumen_abastecimiento['Gasto Promedio'], color=color, width=0.4)
            plt.xticks(rotation=90)
            ax.set_xticks(bar_positions)
            ax.set_xticklabels(df_resumen_abastecimiento['tipo'], fontsize=20)
            for bar in bars:
                height = bar.get_height()
                ax.annotate('{}'.format(height), xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=20)
            ax.tick_params(axis='y', labelsize=20)
            ax.margins(y=0.2)
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close(fig)
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    return ruta_guardado


def generar_grafico_litros_promedio_abastecimiento(df_resumen_abastecimiento, nombre_archivo="grafico_3.png"):
    """Genera gráfico de litros promedio por tipo de abastecimiento (pie si 1, barras si >1)."""
    ruta_guardado = os.path.join(PLOTS_DIR, nombre_archivo)
    num_items = len(df_resumen_abastecimiento)
    if num_items == 0 or 'Litros Promedio' not in df_resumen_abastecimiento.columns:
        plt.figure(figsize=(6,4))
        plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
        plt.axis('off')
        plt.savefig(ruta_guardado)
        plt.close()
        return ruta_guardado
    if num_items == 1:
        if df_resumen_abastecimiento['Litros Promedio'].notnull().all():
            plt.figure(figsize=(8,8))
            colormap = plt.get_cmap('Blues')
            colors = [colormap(0.5)]
            def func(allvalues):
                total = allvalues.sum()
                return "{:.1f}".format(total)
            plt.pie(df_resumen_abastecimiento['Litros Promedio'], labels=df_resumen_abastecimiento['tipo'], startangle=90, colors=colors, autopct=lambda _: func(df_resumen_abastecimiento['Litros Promedio']), textprops={'fontsize': 20})
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close()
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    else:
        if df_resumen_abastecimiento['Litros Promedio'].notnull().all():
            colormap = plt.get_cmap('Blues')
            color = colormap(0.5)
            fig, ax = plt.subplots(figsize=(10,7))
            bar_positions = range(num_items)
            bars = ax.bar(bar_positions, df_resumen_abastecimiento['Litros Promedio'], color=color, width=0.4)
            plt.xticks(rotation=90)
            ax.set_xticks(bar_positions)
            ax.set_xticklabels(df_resumen_abastecimiento['tipo'], fontsize=20)
            for bar in bars:
                height = bar.get_height()
                ax.annotate('{}'.format(height), xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=20)
            ax.tick_params(axis='y', labelsize=20)
            ax.margins(y=0.2)
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close(fig)
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    return ruta_guardado


def generar_grafico_frecuencia_abastecimiento(df_vecesabast, nombre_archivo="grafico_4.png"):
    """Genera gráfico de frecuencia de abastecimiento (pie si 1, barras si >1)."""
    ruta_guardado = os.path.join(PLOTS_DIR, nombre_archivo)
    num_items = len(df_vecesabast)
    if num_items == 0 or 'Cantidad' not in df_vecesabast.columns:
        plt.figure(figsize=(6,4))
        plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
        plt.axis('off')
        plt.savefig(ruta_guardado)
        plt.close()
        return ruta_guardado
    if num_items == 1:
        if df_vecesabast['Cantidad'].notnull().all():
            plt.figure(figsize=(8,8))
            colormap = plt.get_cmap('Blues')
            colors = [colormap(0.5)]
            def func(allvalues):
                total = allvalues.sum()
                return "{:.1f}".format(total)
            plt.pie(df_vecesabast['Cantidad'], labels=df_vecesabast['frecuencia'], startangle=90, colors=colors, autopct=lambda _: func(df_vecesabast['Cantidad']), textprops={'fontsize': 20})
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close()
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    else:
        if df_vecesabast['Cantidad'].notnull().all():
            colormap = plt.get_cmap('Blues')
            color = colormap(0.5)
            fig, ax = plt.subplots(figsize=(10,7))
            bar_positions = range(num_items)
            bars = ax.bar(bar_positions, df_vecesabast['Cantidad'], color=color, width=0.4)
            plt.xticks(rotation=90)
            ax.set_xticks(bar_positions)
            ax.set_xticklabels(df_vecesabast['frecuencia'], fontsize=20)
            for bar in bars:
                height = bar.get_height()
                ax.annotate('{}'.format(height), xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=20)
            ax.tick_params(axis='y', labelsize=20)
            ax.margins(y=0.2)
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close(fig)
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    return ruta_guardado


def generar_grafico_gasto_otros_servicios(df_gastos, nombre_archivo="grafico_5.png"):
    """Genera gráfico de gasto promedio en otros servicios (pie si 1, barras si >1)."""
    ruta_guardado = os.path.join(PLOTS_DIR, nombre_archivo)
    num_items = len(df_gastos)
    if num_items == 0 or 'Promedio de Gasto' not in df_gastos.columns:
        plt.figure(figsize=(6,4))
        plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
        plt.axis('off')
        plt.savefig(ruta_guardado)
        plt.close()
        return ruta_guardado
    if num_items == 1:
        if df_gastos['Promedio de Gasto'].notnull().all():
            plt.figure(figsize=(8,8))
            colormap = plt.get_cmap('Blues')
            colors = [colormap(0.5)]
            def func(allvalues):
                total = allvalues.sum()
                return "{:.1f}".format(total)
            plt.pie(df_gastos['Promedio de Gasto'], labels=df_gastos['Categoria'], startangle=90, colors=colors, autopct=lambda _: func(df_gastos['Promedio de Gasto']), textprops={'fontsize': 20})
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close()
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    else:
        if df_gastos['Promedio de Gasto'].notnull().all():
            colormap = plt.get_cmap('Blues')
            color = colormap(0.5)
            fig, ax = plt.subplots(figsize=(10,7))
            bar_positions = range(num_items)
            bars = ax.bar(bar_positions, df_gastos['Promedio de Gasto'], color=color, width=0.4)
            plt.xticks(rotation=90)
            ax.set_xticks(bar_positions)
            ax.set_xticklabels(df_gastos['Categoria'], fontsize=20)
            for bar in bars:
                height = bar.get_height()
                ax.annotate('{}'.format(height), xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=20)
            ax.tick_params(axis='y', labelsize=20)
            ax.margins(y=0.2)
            plt.tight_layout()
            plt.savefig(ruta_guardado)
            plt.close(fig)
        else:
            plt.figure(figsize=(6,4))
            plt.text(0.5, 0.5, "Sin información", fontsize=20, ha='center')
            plt.axis('off')
            plt.savefig(ruta_guardado)
            plt.close()
    return ruta_guardado

# Aquí irían las funciones específicas que llaman a generar_grafico_pie o generar_grafico_barras
# Por ejemplo:
# def generar_grafico_gasto_promedio_abastecimiento(df_resumen_abastecimiento, nombre_archivo="grafico_gasto_promedio.png"):
#     return generar_grafico_barras(
#         df_datos=df_resumen_abastecimiento,
#         columna_valores='Gasto Promedio',
#         columna_etiquetas='tipo',
#         titulo_grafico='Gasto Mensual Promedio por Tipo de Abastecimiento (S/.)',
#         etiqueta_y='Gasto Promedio (S/.)',
#         nombre_archivo=nombre_archivo
#     )
# Y así para los otros gráficos...