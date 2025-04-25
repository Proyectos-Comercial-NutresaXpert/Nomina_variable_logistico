# Importaciones de librerias.
import config_path_routes
import os
import exclusive_functions as EF
import General_Functions as GF
import pandas as pd
from datetime import datetime
from loguru import logger
from numpy import nan
from Transformation_Functions import PandasBaseTransformer as PBT
from generar_maestra import (
    GenerarMaestraTemporales,
    GenerarMaestraVinculados,
    CombinarMaestras,
)
from calculos_maestra import CalculosPostProceso
from historico_bonificacion import HistoricoBonificacion

# Comentar las proximas 3 lineas para ejecutar en Visual estudio.
#ruta_actual = os.getcwd()
#ruta_padre = os.path.dirname(ruta_actual)
#os.chdir(ruta_padre)

# Cargar configuración del proyecto
config = GF.Procesar_configuracion("config.yml")


# Seleccion parte del proceso a ejecutar:
def mostrar_menu():
    """Muestra el menú de opciones al usuario."""
    print("\nMenú de Opciones:")
    print("1. Generar las maestras para enviar al proceso")
    print("2. Realizar cálculos de bonificaciones")
    print("3. Generar el histórico de bonificación")
    print("0. Salir")


def ejecutar_opcion(opcion):
    """Ejecuta la opción seleccionada por el usuario."""
    if opcion == "1":
        logger.info("Generando las maestras para enviar al proceso...")
        # Llamar a la función para generar las maestras
        generar_maestras()
    elif opcion == "2":
        logger.info("Realizando cálculos de bonificaciones...")
        calcular_bonificaciones()
    elif opcion == "3":
        logger.info("Generando el histórico de bonificación...")
        generar_historico_bonificacion()
    elif opcion == "0":
        logger.info("Saliendo del programa...")
    else:
        print("Opción no válida. Por favor, seleccione una opción del menú.")


def generar_maestras():
    """Función para generar las maestras para el proceso."""
    # Crear las instancias para el proceso de generación de maestras
    generador_temporal = GenerarMaestraTemporales(config)
    df_maestra_temporales = generador_temporal.ejecutar_proceso()

    generador_vinculados = GenerarMaestraVinculados(config)
    df_maestra_vinculados = generador_vinculados.ejecutar_proceso()

    generador_maestra_pagos = CombinarMaestras(
        config, df_maestra_vinculados, df_maestra_temporales
    )

    df_para_proceso, df_ingr_ret_complto = generador_maestra_pagos.ejecutar_proceso()

    GF.exportar_a_excel(
        df=df_para_proceso,
        ruta_guardado=config["Resultados"]["path_resultados"],
        nom_base=config["Resultados"]["Maestra_para_procesos"]["nom_base"],
        nom_hoja=config["Resultados"]["hoja_general"],
    )

    GF.exportar_a_excel(
        df=df_ingr_ret_complto,
        ruta_guardado=config["path_insumos"],
        nom_base=config["Resultados"]["Maestra_ingresos_ret"]["nom_base"],
        nom_hoja=config["Resultados"]["hoja_general"],
    )


def calcular_bonificaciones():
    """Función para realizar los cálculos de bonificaciones."""
    calcular_bonif = CalculosPostProceso(config)
    df_calculos_post_proceso = calcular_bonif.ejecutar_proceso()

    print("Inicio exportación de resultados...")

    GF.exportar_a_excel(
        df=df_calculos_post_proceso,
        ruta_guardado=config["Resultados"]["path_resultados"],
        nom_base=config["Resultados"]["Base_para_pago"]["nom_base"],
        nom_hoja=config["Resultados"]["hoja_general"],
    )

    print("Los cálculos de bonificaciones se han realizado con éxito.")


def generar_historico_bonificacion():
    """Función para generar el historico de bonificación."""
    generador_historico = HistoricoBonificacion(config, PBT, GF)
    generador_historico.ejecutar_proceso()
    

mostrar_menu()
opcion = input("Seleccione una opción: ")
ejecutar_opcion(opcion)
