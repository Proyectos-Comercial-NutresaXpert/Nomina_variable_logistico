from numpy import where
from pandas import DataFrame, to_datetime, Series, concat, merge
from loguru import logger


class ColsCalculadasDfProceso:
    """
    Clase que define los nombres de las columnas a partir de un archivo de configuración
    y aplica las transformaciones necesarias al DataFrame.
    """

    def __init__(
        self, config: dict, lista_garantizados: list, lista_no_garantizados: list
    ):
        """
        Inicializa la clase con los nombres de las columnas a partir de la configuración.

        Parámetros:
        cols_base (dict): Diccionario con los nombres de las columnas.
        """
        self.config = config
        self.cols_base = self.config["maestra_para_pago"]["maestra_post_proceso"][
            "cols_calculos"
        ]
        self.col_cedula = self.config["maestra_vinculados"]["col_cedula"]["CEDULA"]
        self.VALOR = self.cols_base["VALOR"]
        self.EJECUCION = self.cols_base["EJECUCION"]
        self.RESULTADO_EGL = self.cols_base["RESULTADO EGL"]
        self.META_EGL = self.cols_base["META EGL"]
        self.VALOR_PARCIAL = self.cols_base["VALOR PARCIAL"]
        self.VALOR_REAL = self.cols_base["VALOR REAL"]
        self.CONFIABILIDAD = self.cols_base["% CONFIABILIDAD"]
        self.META_CONFIABILIDAD = self.cols_base["% META CONFIABILIDAD"]
        self.lista_garantizados = lista_garantizados
        self.lista_no_garantizados = lista_no_garantizados

    def calcular_ejecucion(self, df: DataFrame):
        """
        Calcula la columna 'Ejecución' en el DataFrame.

        Parámetros:
        df (pandas.DataFrame): El DataFrame al que se le aplicará el cálculo de 'Ejecución'.

        Retorno:
        pandas.DataFrame: El DataFrame con la columna 'Ejecución' calculada y añadida.
        """
        df[self.EJECUCION] = ((df[self.RESULTADO_EGL] / df[self.META_EGL]) * 100).round(
            2
        )
        return df

    def calcular_valor_parcial(self, df: DataFrame):
        """
        Calcula la columna 'Valor Parcial' en el DataFrame.

        Parámetros:
        df (pandas.DataFrame): El DataFrame al que se le aplicará el cálculo de 'Valor Parcial'.

        Retorno:
        pandas.DataFrame: El DataFrame con la columna 'Valor Parcial' calculada y añadida.
        """
        df[self.VALOR_PARCIAL] = where(
            df[self.EJECUCION] >= 100,
            df[self.VALOR] * 1,
            where(
                df[self.EJECUCION] >= 80, df[self.VALOR] * (df[self.EJECUCION] / 100), 0
            ),
        )
        return df

    def calcular_valor_real(self, df: DataFrame):
        """
        Calcula la columna 'Valor Real' en el DataFrame.

        Parámetros:
        df (pandas.DataFrame): El DataFrame al que se le aplicará el cálculo de 'Valor Real'.

        Retorno:
        pandas.DataFrame: El DataFrame con la columna 'Valor Real' calculada y añadida.
        """

        df[self.VALOR_REAL] = where(
            df[self.CONFIABILIDAD] >= df[self.META_CONFIABILIDAD],
            df[self.VALOR_PARCIAL],
            0,
        )

        return df

    def ajustar_garantizados(self, df):
        """
        Ajusta el valor real de los empleados garantizados y no garantizados en el DataFrame proporcionado.

        Esta función utiliza listas de cédulas para clasificar a los empleados en dos grupos:
        "garantizados" y "no garantizados". Si un empleado es identificado como garantizado (su cédula
        está en `self.lista_garantizados`), el valor de la columna `VALOR_REAL` se establece igual al
        valor en la columna `VALOR`. Para los empleados no garantizados (cuyas cédulas están en
        `self.lista_no_garantizados`), el valor de `VALOR_REAL` se establece en 0.

        Parámetros:
        - df (pd.DataFrame): DataFrame que contiene los datos de los empleados, incluyendo las columnas
        necesarias para identificar a los garantizados y los no garantizados y las columnas `VALOR` y `VALOR_REAL`.

        Atributos:
        - self.col_cedula (str): Nombre de la columna en `df` que contiene las cédulas de los empleados.
        - self.VALOR (str): Nombre de la columna en `df` que contiene el valor base.
        - self.VALOR_REAL (str): Nombre de la columna en `df` donde se almacenará el valor ajustado.
        - self.lista_garantizados (list): Lista de cédulas de empleados que deben tener el valor de `VALOR` en `VALOR_REAL`.
        - self.lista_no_garantizados (list): Lista de cédulas de empleados cuyo `VALOR_REAL` debe ajustarse a 0.

        Retorna:
        - pd.DataFrame: El DataFrame actualizado con los valores ajustados en la columna `VALOR_REAL`
        para los empleados garantizados y no garantizados.

        """

        # Asignar el valor de `VALOR` a `VALOR_REAL` para los empleados garantizados
        df.loc[df[self.col_cedula].isin(self.lista_garantizados), self.VALOR_REAL] = df[
            self.VALOR
        ]

        # Asignar 0 a `VALOR_REAL` para los empleados no garantizados
        df.loc[
            df[self.col_cedula].isin(self.lista_no_garantizados), self.VALOR_REAL
        ] = 0

        return df

    def estatus_garantizado(self):
        
        col_estatus = self.config["dict_constantes"]["ESTATUS_GARANTIZADO"]
        serie_garant = Series(data=self.lista_garantizados, name=self.col_cedula)
        serie_no_garant = Series(self.lista_no_garantizados, name=self.col_cedula)

        df_garant = DataFrame(serie_garant)
        df_nogarant = DataFrame(serie_no_garant)

        df_garant[col_estatus] = "Garantizado"
        df_nogarant[col_estatus] = "No Garantizado"

        df_estatus_garant = concat([df_garant, df_nogarant], ignore_index=True)

        return df_estatus_garant

    def procesar_dataframe(self, df: DataFrame):
        """
        Procesa el DataFrame aplicando las transformaciones de 'Ejecución',
        'Valor Parcial' y 'Valor Real'.

        Parámetros:
        df (pandas.DataFrame): El DataFrame que contiene las columnas requeridas.

        Retorno:
        pandas.DataFrame: El DataFrame procesado con las columnas calculadas añadidas.
        """
        df = self.calcular_ejecucion(df)
        df = self.calcular_valor_parcial(df)
        df = self.calcular_valor_real(df)
        df = self.ajustar_garantizados(df)
        df_estatus_garant = self.estatus_garantizado()

        df_merge = merge(left=df, right=df_estatus_garant, on=self.col_cedula, how="left")
        return df_merge


class ColsCalculadasIngRet:
    def __init__(self, config, df):
        self.config = config
        self.df = df
        self.cols = self.config["maestra_para_pago"]["cols_insumo_finales"]

    def ejecutar_proceso(self):
        dict_cols_finales = self._construir_diccionario_cols()
        df_ajust = self._ajustar_tipo_fecha(dict_cols_finales)
        df_ing_ret_compt = self._calcular_valor_final(df_ajust)

        return df_ing_ret_compt

    def _construir_diccionario_cols(self):
        dict_cols = {cada_col: cada_col for cada_col in self.cols}
        return dict_cols

    def _ajustar_tipo_fecha(self, dict_cols):
        for cada_col in [dict_cols["FECHA INGRESO"], dict_cols["FECHA RETIRO"]]:
            self.df[cada_col] = to_datetime(self.df[cada_col], errors="coerce")
        return self.df

    def _calcular_dias_trabajados(self, df: DataFrame, fecha: str) -> DataFrame:
        """
        Calcula el número de días trabajados hasta la fecha de retiro o desde la fecha de ingreso
        y los asigna a la columna configurada.

        Parámetros:
        - df (pd.DataFrame): DataFrame que contiene los datos.
        - fecha (str): Nombre de la fecha a utilizar para el cálculo (puede ser 'FECHA DE RETIRO' o 'FECHA DE INGRESO').

        Retorna:
        - pd.DataFrame: DataFrame con la columna de días trabajados actualizada.
        """
        dias_mes = self.config["dias_en_mes"][self.config["mes_a_medir"]]
        if (
            fecha
            == self.config["maestra_temporales"]["cols_renombrar"]["FECHA DE RETIRO"]
        ):
            dias_trabajados = df[fecha].dt.day
        else:
            
            dias_trabajados = (dias_mes - df[fecha].dt.day) + 1

        df[self.config["dict_constantes"]["DIAS_TRABAJADOS"]] = dias_trabajados
        return df

    def _calcular_valor_por_dia(self, df: DataFrame) -> DataFrame:
        """
        Calcula el valor diario dividiendo el valor total por los días en el mes y los asigna a la columna configurada.

        Parámetros:
        - df (pd.DataFrame): DataFrame que contiene los datos.

        Retorna:
        - pd.DataFrame: DataFrame con la columna de valor por día actualizada.
        """
        dias_mes = self.config["dias_en_mes"][self.config["mes_a_medir"]]
        df[self.config["dict_constantes"]["VALOR_DIA"]] = (
            df[self.config["dict_constantes"]["VALOR"]] / dias_mes
        )
        return df

    def _calcular_valor_a_pagar(self, df: DataFrame, tipo_fecha: str) -> DataFrame:
        """
        Calcula el valor total a pagar multiplicando los días trabajados por el valor diario y los asigna a la columna configurada.

        Parámetros:
        - df (pd.DataFrame): DataFrame que contiene los datos.
        - tipo_fecha (str): Condición que determina los días trabajados para el cálculo.

        Retorna:
        - pd.DataFrame: DataFrame con la columna de valor total a pagar actualizada.
        """
        df.loc[
            ~df[tipo_fecha].isnull(),
            self.config["dict_constantes"]["VALOR REAL"],
        ] = df[self.config["dict_constantes"]["DIAS_TRABAJADOS"]] * df[
            self.config["dict_constantes"]["VALOR_DIA"]
        ].round(
            0
        )
        return df

    def _calcular_valor_final(self, df: DataFrame) -> DataFrame:
        """
        Calcula el valor a pagar aplicando una serie de transformaciones al DataFrame.

        Parámetros:
        - df (pd.DataFrame): DataFrame que contiene los datos.

        Retorna:
        - pd.DataFrame: DataFrame con todas las columnas calculadas.
        """
        # Obtener las configuraciones de columnas
        FECHA_RET = self.config["maestra_temporales"]["cols_renombrar"][
            "FECHA DE RETIRO"
        ]
        FECHA_ING = self.config["maestra_temporales"]["cols_renombrar"][
            "FECHA DE INGRESO"
        ]

        # Paso 1: Calcular días trabajados para "FECHA DE RETIRO"
        df_dias_retiro = self._calcular_dias_trabajados(df, fecha=FECHA_RET)

        # Paso 2: Calcular valor diario
        df_valor_por_dia = self._calcular_valor_por_dia(df_dias_retiro)

        # Paso 3: Calcular valor a pagar para "FECHA DE INGRESO"
        df_valor_retiro = self._calcular_valor_a_pagar(
            df_valor_por_dia, tipo_fecha=FECHA_RET
        )

        # Paso 4: Calcular días trabajados para "FECHA DE INGRESO"
        df_dias_ingreso = self._calcular_dias_trabajados(
            df_valor_retiro, fecha=FECHA_ING,
        )
        
        # Paso 5: Calcular valor a pagar para "FECHA DE INGRESO" sin sobrescribir los anteriores
        df_valor_total = self._calcular_valor_a_pagar(
            df_dias_ingreso, tipo_fecha=FECHA_ING
        )

        return df_valor_total
