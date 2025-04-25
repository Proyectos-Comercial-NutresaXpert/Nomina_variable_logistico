# historico_bonificacion.py
import pandas as pd
from loguru import logger

class HistoricoBonificacion:
    def __init__(self, config, PBT, GF):
        """
        Inicializa la clase HistoricoBonificacion con la configuración, el módulo de transformación PBT, 
        y el módulo de funciones generales GF.

        Args:
            config (dict): Diccionario de configuración.
            PBT (module): Módulo de funciones de transformación de datos.
            GF (module): Módulo de funciones generales para exportación y otras tareas.
        """
        self.config = config
        self.PBT = PBT
        self.GF = GF
        # Acceso a las constantes desde la configuración
        self.cedula_col = config["dict_constantes"]["CEDULA"]
        self.cargo_col = config["dict_constantes"]["CARGO"]
        self.observaciones_col = config["dict_constantes"]["OBSERVACIONES"]
        self.mes_act_col = config["dict_constantes"]["MES_ACT"]
        self.novedad_text = config["dict_constantes"]["NOVEDAD"]

    def _cargar_datos(self):
        """Carga el histórico y la base de pago actual desde archivos Excel."""
        historico = pd.read_excel(self.config["Resultados"]["Historico_act"]["path_leer"])
        base_para_pago_act = pd.read_excel(self.config["Resultados"]["Base_para_pago"]["path_leer"])
        return historico, base_para_pago_act

    def _concatenar_datos(self, base_para_pago_act, historico):
        """Concatena el histórico y la base para pago actual en un solo DataFrame."""
        return self.PBT.concatenate_dataframes(dataframes=[base_para_pago_act, historico])

    def _exportar_historico_actualizado(self, historico_act):
        """Exporta el DataFrame concatenado a un archivo Excel."""
        self.GF.exportar_a_excel(
            df=historico_act,
            ruta_guardado=self.config["Resultados"]["path_resultados"],
            nom_base=self.config["Resultados"]["Historico_act"]["nom_base"],
            nom_hoja=self.config["Resultados"]["hoja_general"],
        )

    def _calcular_mes_anterior(self, mes_act):
        """Calcula el mes anterior, devolviendo None si es enero."""
        return mes_act - 1 if mes_act != 1 else None

    def _filtrar_por_mes(self, df, mes_act, mes_ant):
        """Filtra el DataFrame por los valores de mes actual y mes anterior."""
        return self.PBT.Filtrar_por_valores_pd(
            df=df, columna=self.mes_act_col, valores_filtrar=[mes_act, mes_ant]
        )

    def _obtener_cedulas_duplicadas(self, df):
        """Obtiene una lista de cédulas duplicadas en el DataFrame."""
        cedulas_duplicadas = df[self.cedula_col].value_counts()
        return cedulas_duplicadas[cedulas_duplicadas > 1].index.tolist()

    def _crear_diccionario_novedades(self, cedulas_duplicadas):
        """Crea un diccionario de novedades para cédulas duplicadas."""
        return {cedula: self.novedad_text for cedula in cedulas_duplicadas}

    def _reemplazar_observaciones_con_novedades(self, df, dict_novedades):
        """Reemplaza la columna de observaciones con novedades para cédulas duplicadas."""
        return self.PBT.Reemplazar_columna_en_funcion_de_otra(
            df=df,
            nom_columna_de_referencia=self.cedula_col,
            nom_columna_a_reemplazar=self.observaciones_col,
            mapeo=dict_novedades,
        )

    def _exportar_novedades_actualizadas(self, df):
        """Exporta el DataFrame actualizado con novedades a un archivo Excel."""
        self.GF.exportar_a_excel(
            df=df,
            ruta_guardado=self.config["Resultados"]["path_resultados"],
            nom_base=self.config["Resultados"]["Base_para_pago"]["nom_base"],
            nom_hoja=self.config["Resultados"]["hoja_general"],
        )

    def ejecutar_proceso(self):
        """Ejecuta el proceso completo de generación del histórico de bonificación."""
        # Cargar los datos
        historico, base_para_pago_act = self._cargar_datos()

        # Concatenar el histórico con la base para pago actual
        historico_act = self._concatenar_datos(base_para_pago_act, historico)

        # Exportar el histórico actualizado
        self._exportar_historico_actualizado(historico_act)

        # Calcular el mes anterior
        mes_act = int(self.config["mes_a_medir"])
        mes_ant = self._calcular_mes_anterior(mes_act)
        if mes_ant is None:
            logger.info("El histórico de bonificación ha sido generado con éxito (no se realizó filtrado de mes anterior por ser enero).")
            return

        # Filtrar por el mes actual y el mes anterior
        hist_mes_mes_ant = self._filtrar_por_mes(historico_act, mes_act, mes_ant)

        # Seleccionar columnas necesarias y eliminar duplicados
        hist_mes_mes_ant_select = self.PBT.Seleccionar_columnas_pd(
            df=hist_mes_mes_ant, cols_elegidas=[self.cedula_col, self.cargo_col, self.mes_act_col]
        )
        hist_mes_mes_ant_select = self.PBT.Eliminar_duplicados_x_cols(
            df=hist_mes_mes_ant_select, cols=[self.cedula_col, self.cargo_col]
        )

        # Obtener cédulas duplicadas y crear diccionario de novedades
        cedulas_duplicadas = self._obtener_cedulas_duplicadas(hist_mes_mes_ant_select)
        dict_novedades = self._crear_diccionario_novedades(cedulas_duplicadas)

        # Reemplazar observaciones con novedades y exportar
        base_para_pago_act_nov = self._reemplazar_observaciones_con_novedades(
            base_para_pago_act, dict_novedades
        )
        self._exportar_novedades_actualizadas(base_para_pago_act_nov)

        logger.info("El histórico de bonificación ha sido generado con éxito.")
