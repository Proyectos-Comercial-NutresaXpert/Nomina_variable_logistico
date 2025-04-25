## Funciones básicas - Generales del proyecto_CxS Parte3
import pandas as pd
import os
import time
import inspect
import yaml
import time
from typing import Dict
from loguru import logger
from pathlib import Path
import openpyxl


def Registro_tiempo(original_func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = original_func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(
            f"Tiempo de ejecución de {original_func.__name__}: {execution_time} segundos"
        )
        return result

    return wrapper


class ErrorHandler:
    @staticmethod
    def log_error(e, message):
        # Usamos inspect para capturar el marco de la llamada actual
        current_frame = inspect.currentframe()
        # Vamos dos niveles arriba para capturar el punto desde donde fue llamada la función 'seleccionar_columnas_pd'
        call_frame = inspect.getouterframes(current_frame, 2)[2]
        logger.critical(
            f"{message} - Error occurred in file {call_frame.filename}, line {call_frame.lineno}"
        )

def exportar_a_excel(
    df: pd.DataFrame, ruta_guardado: str, nom_base: str,  nom_hoja: str, index: bool = False
) -> None:
    """
    Exporta un dataframe de pandas a un archivo excel en la ruta especificada.

    Args:
        ruta_guardado: Ruta donde se guardará el archivo excel.
        df: Dataframe de pandas que se exportará.
        nom_hoja: Nombre de la hoja de cálculo donde se exportará el dataframe.
        index: Indica si se debe incluir el índice del dataframe en el archivo excel.

    Returns:
        None.

    Raises:
        FileNotFoundError: Si la ruta de guardado no existe.
    """

    # Comprobar que la ruta de guardado existe
    try:
        logger.info(f"Exportando a excel: {nom_base}")
        df.to_excel(
            ruta_guardado + nom_base , sheet_name=nom_hoja, index=index
        )
    except Exception as e:
        raise Exception


def Obtener_lugar_de_ejecucion() -> str:
    """
    Captura la respuesta del usuario sobre el lugar de ejecución y ajusta la ruta actual si es necesario.

    Returns:
        str: La respuesta del usuario, validada para ser 'si' o 'no'.
    """
    while True:
        lugar_de_ejecucion = (
            input(
                "¿Está ejecutando esta automatización desde Python IDLE ó desde cmd?: (si/no): "
            )
            .strip()
            .lower()
        )
        if lugar_de_ejecucion in ["si", "no"]:
            break
        else:
            print("Respuesta no válida. Por favor, ingrese 'si' o 'no'.")

    if lugar_de_ejecucion == "si":
        ruta_actual = os.getcwd()
        ruta_padre = os.path.dirname(ruta_actual)
        os.chdir(ruta_padre)

    return lugar_de_ejecucion


def Crear_diccionario_desde_dataframe(
    df: pd.DataFrame, col_clave: str, col_valor: str
) -> dict:
    """
    Crea un diccionario a partir de un DataFrame utilizando dos columnas especificadas.

    Args:
        df (pd.DataFrame): El DataFrame de entrada.
        col_clave (str): El nombre de la columna que se utilizará como clave en el diccionario.
        col_valor (str): El nombre de la columna que se utilizará como valor en el diccionario.

    Returns:
        dict: Un diccionario creado a partir de las columnas especificadas.
    """
    try:
        # Verificar si las columnas existen en el DataFrame
        if col_clave not in df.columns or col_valor not in df.columns:
            raise ValueError("Las columnas especificadas no existen en el DataFrame.")

        if col_clave == col_valor:
            resultado_dict = df[col_clave].to_dict()
        else:
            resultado_dict = df.set_index(col_clave)[col_valor].to_dict()
        return resultado_dict

    except ValueError as ve:
        # Registrar un mensaje crítico si hay un error
        logger.critical(f"Error: {ve}")
        raise ve


def Procesar_configuracion(nom_archivo_configuracion: str) -> dict:
    """Lee un archivo YAML de configuración para un proyecto.

    Args:
        nom_archivo_configuracion (str): Nombre del archivo YAML que contiene
            la configuración del proyecto.

    Returns:
        dict: Un diccionario con la información de configuración leída del archivo YAML.
    """
    try:
        with open(nom_archivo_configuracion, "r", encoding="utf-8") as archivo:
            configuracion_yaml = yaml.safe_load(archivo)
        logger.success("Proceso de obtención de configuración satisfactorio")
    except Exception as e:
        logger.critical(f"Proceso de lectura de configuración fallido {e}")
        raise e

    return configuracion_yaml


class ExcelReader:
    def __init__(self, path: str):
        self.path = path

    @Registro_tiempo
    def Lectura_insumos_excel(
        self, nom_insumo: str, nom_hoja: str, cols: int | list, skiprows: int
    ) -> pd.DataFrame:
        """
        Lee archivos de Excel especificando hoja y columnas.
        """
        if isinstance(cols, list):
            range_cols = cols
        else:
            range_cols = list(range(cols))

        try:
            logger.info(f"Inicio lectura {nom_insumo} Hoja: {nom_hoja}")
            base_leida = pd.read_excel(
                self.path + nom_insumo,
                sheet_name=nom_hoja,
                skiprows=skiprows,
                usecols=range_cols,
                dtype=str,
                engine="openpyxl",
            )
            logger.success(
                f"Lectura de {nom_insumo} Hoja: {nom_hoja} realizada con éxito"
            )
            return base_leida
        except Exception as e:
            logger.error(f"Proceso de lectura fallido: {e}")
            raise Exception(f"Error al leer el archivo: {e}")

    @Registro_tiempo
    def Lectura_simple_excel(self, nom_insumo: str, nom_hoja: str) -> pd.DataFrame:
        """
        Lee un archivo de Excel únicamente utilizando el nombre de su hoja sin parámetros adicionales.
        """
        try:
            logger.info(f"Inicio lectura simple de {nom_insumo}")
            base_leida = pd.read_excel(
                self.path + nom_insumo,
                sheet_name=nom_hoja,
                dtype=str,
            )
            logger.success(f"Lectura simple de {nom_insumo} realizada con éxito")
            return base_leida
        except Exception as e:
            logger.error(f"Proceso de lectura fallido: {e}")
            raise Exception(f"Error al leer el archivo: {e}")


def List_to_sql(values: list[str]):
    """
    Convierte una lista de valores en una cadena de valores SQL correctamenteformateada.
    Parameters:
    values (list of str): Lista de valores a convertir. Cada valor en la lista debeser una cadena (str).
    Returns:
    str: Una cadena de valores SQL separada por comas y entre comillas simples.
    Raises:
    TypeError: Si algún elemento de la lista no es una cadena (str).
    ValueError: Si la lista está vacía.
    """
    if not values:
        raise ValueError("La lista de valores no puede estar vacía.")
    for value in values:
        if not isinstance(value, str):
            raise TypeError(
                f"Todos los elementos de la lista deben ser cadenas (str). Elementoinválido: {value}"
            )
    return ", ".join(f"'{value}'" for value in values)



def crear_dict_col_llave_col_valores(df, columna_clave, columna_valores):
    """
    Crea un diccionario donde cada clave es un elemento único de una columna,
    y cada valor es una lista con los elementos correspondientes de otra columna.

    Parámetros:
    df (pd.DataFrame): El DataFrame del cual se extraerán los datos.
    columna_clave (str): El nombre de la columna que se usará como claves del diccionario.
    columna_valores (str): El nombre de la columna que se usará para los valores del diccionario.

    Retorna:
    dict: Un diccionario con las claves y valores especificados.
    """
    diccionario = {}
    for clave in df[columna_clave].unique():
        diccionario[clave] = (
            df.loc[df[columna_clave] == clave, columna_valores].unique().tolist()
        )
    return diccionario
