import General_Functions as GF
from Transformation_Functions import PandasBaseTransformer as PBT
from typing import Dict
from pandas import DataFrame, Timestamp


class GenerarMaestraTemporales:
    """
    Clase para generar la maestra de empleados, procesando datos temporales y
    aplicando diversos filtros y transformaciones.

    Esta clase utiliza el módulo PBT (PandasBaseTransformer) para realizar
    operaciones sobre el DataFrame de empleados temporales, con base en la
    configuración proporcionada.

    Args:
        df_temporales (pd.DataFrame): El DataFrame con los datos temporales de empleados.
        config (dict): Diccionario de configuración que contiene todas las
                       subsecciones necesarias para el proceso (maestra_temporales, dict_constantes,
                       maestra_post_proceso, dict_constantes, etc.).
    """

    def __init__(self, config):
        """
        Inicializa la clase GenerarMaestraTemporales con el DataFrame y la configuración proporcionada.

        Args:
            config (dict): Diccionario de configuración que contiene todas las
                           subsecciones necesarias para el proceso.
        """
        self.config = config
        self.valor_inicial_bonf = 0

        self.conf_ma_tmp = self.config["maestra_temporales"]
        self.dict_obs = self.config["Drivers"]["dict_observaciones"]
        self.conf_maes_pago = self.config["maestra_para_pago"]["maestra_post_proceso"]

        # Guardar referencias a constantes de uso frecuente en atributos
        self.col_pri_apelli = self.config["dict_constantes"]["PRIMER APELLIDO"]
        self.col_seg_apelli = self.config["dict_constantes"]["SEGUNDO APELLIDO"]
        self.col_apellidos = self.config["dict_constantes"]["APELLIDOS COMPLETOS"]
        self.col_nombres = self.config["dict_constantes"]["NOMBRES COMPLETOS"]
        self.col_observaciones = self.config["dict_constantes"]["OBSERVACIONES"]

        # Configurar las variables que se referencian en 3 querys alojados en "config"
        self.mes_a_medir = self.config["mes_a_medir"]
        self.an_actual = self.config["an_actual"]
        self.dict_query = {
            "mes_a_medir": int(self.mes_a_medir),
            "an_actual": self.an_actual,
        }

    def ejecutar_proceso(self):
        """
        Ejecuta el proceso completo de generación de la maestra, aplicando
        filtros, transformaciones y cálculos según la configuración.

        Returns:
            pd.DataFrame: El DataFrame resultante después de aplicar todos los
                          pasos del proceso.
        """

        df_temporales = self._cargar_maestra_temporales()
        df_seleccionado = self._seleccionar_columnas(df_temporales)
        df_fil_x_cargo = self._filtrar_por_cargos(df_seleccionado)
        
        df_fil_fechas = df_fil_x_cargo[
            (df_fil_x_cargo["FECHA DE INGRESO"].astype(str).str.len() == 19)
            | (df_fil_x_cargo["FECHA DE RETIRO"].astype(str).str.len() == 19)
        ]
        df_convertido = self._convertir_formatos_fecha(df_fil_fechas)
        
        df_filtrado_final = self._filtrar_por_fecha(df_convertido)
        personal_observaciones = self._marcar_ingresos_retiros(df_filtrado_final)
        df_con_observaciones = self._agregar_observaciones(df_filtrado_final)
        df_insumo_proceso = self._reemplazar_observaciones(
            df_con_observaciones, personal_observaciones
        )
        df_insumo_proceso_fechas_mod = self._ajustar_fechas_irrelevantes(
            df_insumo_proceso,
        )
        df_insumo_proceso = self._asignar_valores(df_insumo_proceso_fechas_mod)
        df_nom_ajust = self._ajustar_nombre(df_insumo_proceso)
        df_cols_insumo = self._eliminar_cols_innecesarias(df_nom_ajust)
        df_nom_ajust_rename = self._renombrar_columnas(df_cols_insumo)
        df_con_valores = self._reemplazar_por_salarios(df_nom_ajust_rename)

        return df_con_valores

    def _cargar_maestra_temporales(self):
        """
        Carga los insumos necesarios para el proceso, incluyendo los DataFrames
        temporales y vinculados.
        """
        Lector_insumos = GF.ExcelReader(path=self.config["path_insumos"])

        # Cargar DataFrame de temporales
        df_temporales = Lector_insumos.Lectura_simple_excel(
            nom_insumo=self.conf_ma_tmp["nom_base"],
            nom_hoja=self.conf_ma_tmp["nom_hoja"],
        )

        return df_temporales

    def _seleccionar_columnas(self, df_temporales):
        """Selecciona columnas específicas del DataFrame temporal."""
        return PBT.Seleccionar_columnas_pd(
            df=df_temporales,
            cols_elegidas=[*self.conf_ma_tmp["cols_renombrar"]],
        )


    def _filtrar_por_cargos(self, df):
        """Filtra el DataFrame por los cargos definidos en la configuración."""
        return PBT.Filtrar_por_valores_pd(
            df=df,
            columna=self.conf_ma_tmp["cols_mods"]["CARGO"],
            valores_filtrar=list(self.config["Drivers"]["dict_salarios_log"].keys()),
        )

    def _convertir_formatos_fecha(self, df):
        """
        Convierte las columnas de fechas a un formato datetime.

        Args:
            df (pd.DataFrame): El DataFrame que contiene las columnas a convertir.

        Returns:
            pd.DataFrame: DataFrame con las columnas de fechas convertidas a formato datetime64[ns].
        """
        return PBT.Cambiar_tipo_dato_multiples_columnas_pd(
            base=df,
            list_columns=list(self.conf_ma_tmp["cols_fechas"].keys()),
            type_data="datetime64[ns]",
        )

    def _ajustar_nombre(self, df):
        df.loc[:, "NOMBRE"] = df[self.col_nombres].str.cat(
            df[self.col_apellidos], sep=" ", na_rep=""
        )

        return PBT._eliminar_espacios_blanco_columnas(df=df, columnas="NOMBRE")

    def _eliminar_cols_innecesarias(self, df):
        return PBT.Eliminar_columnas_pd(
            df,
            columnas_a_eliminar=[
                self.col_nombres,
                self.col_apellidos,
                self.conf_ma_tmp["cols_mods"]["ESTADO"],
            ],
        )

    def _renombrar_columnas(self, df):
        return PBT.Renombrar_columnas_con_diccionario(
            base=df, cols_to_rename=self.conf_ma_tmp["cols_renombrar"]
        )

    def _filtrar_por_fecha(self, df):
        """Filtra el DataFrame utilizando una consulta definida en la configuración."""
        df_filtrado_query1 = df.query(
            self.conf_ma_tmp["query_filtrar_maestra"],
            local_dict=self.dict_query,
        )
        df_filtrado_query2 = df_filtrado_query1.query(
            self.conf_ma_tmp["query_depurador_ingreso"],
            local_dict=self.dict_query,
        )
        return df_filtrado_query2

    def _marcar_ingresos_retiros(self, df):
        """
        Crea un diccionario para marcar ingresos y retiros de empleados en función de su número de identificación.

        Args:
            df (pd.DataFrame): El DataFrame sobre el cual se aplica la lógica para determinar
                            los ingresos y retiros.

        Returns:
            dict: Diccionario donde las claves son los números de identificación y los valores
                indican si es un ingreso o un retiro.
        """

        personal_observaciones = {
            cada_persona: self.dict_obs["Ingresos"]
            for cada_persona in df.query(
                self.conf_ma_tmp["query_ingresos"],
                local_dict=self.dict_query,
            )[self.conf_ma_tmp["cols_mods"]["NUMERO DE IDENTIFICACIÓN"]]
        }

        df_filtrado = df[df["FECHA DE RETIRO"].notna()]

        personal_observaciones.update(
            {
                cada_persona: self.dict_obs["Retiros"]
                for cada_persona in df_filtrado.query(
                    self.conf_ma_tmp["query_retiros"],
                    local_dict=self.dict_query,
                )[self.conf_ma_tmp["cols_mods"]["NUMERO DE IDENTIFICACIÓN"]]
            }
        )
        return personal_observaciones

    def _agregar_observaciones(self, df):
        """Agrega una columna de observaciones con un valor constante al DataFrame."""
        return PBT.Agregar_columna_constante(
            dataframe=df,
            nombre_columna=self.col_observaciones,
            valor_constante=self.dict_obs["Activos"],
        )

    def _reemplazar_observaciones(self, df, mapeo):
        """Reemplaza las observaciones en el DataFrame según el mapeo proporcionado."""
        return PBT.Reemplazar_columna_en_funcion_de_otra(
            df=df,
            nom_columna_a_reemplazar=self.col_observaciones,
            nom_columna_de_referencia=self.conf_ma_tmp["cols_mods"][
                "NUMERO DE IDENTIFICACIÓN"
            ],
            mapeo=mapeo,
        )

    def _ajustar_fechas_irrelevantes(self, df):
        df.loc[
            df[self.col_observaciones].isin(
                [self.dict_obs["Ingresos"], self.dict_obs["Activos"]]
            ),
            self.conf_ma_tmp["cols_fechas"]["FECHA DE RETIRO"],
        ] = ""

        df.loc[
            df[self.col_observaciones].isin(
                [self.dict_obs["Retiros"], self.dict_obs["Activos"]]
            ),
            self.conf_ma_tmp["cols_fechas"]["FECHA DE INGRESO"],
        ] = ""

        return df

    def _asignar_valores(self, df):
        """Asigna un valor constante en una columna específica del DataFrame."""
        return PBT.Agregar_columna_constante(
            dataframe=df,
            nombre_columna=self.conf_maes_pago["cols_calculos"]["VALOR"],
            valor_constante=self.valor_inicial_bonf,
        )

    def _reemplazar_por_salarios(self, df):
        """Reemplaza los valores en el DataFrame con base en el mapeo de salarios."""
        return PBT.Reemplazar_columna_en_funcion_de_otra(
            df=df,
            nom_columna_a_reemplazar=self.conf_maes_pago["dict_reemplazos"][
                "col_reemplazo"
            ],
            nom_columna_de_referencia=self.conf_maes_pago["dict_reemplazos"][
                "col_referencia"
            ],
            mapeo=self.config["Drivers"]["dict_salarios_log"],
        )


class GenerarMaestraVinculados:
    """
    Clase para generar la maestra de empleados vinculados, procesando datos temporales y
    aplicando diversos filtros y transformaciones.

    Esta clase utiliza el módulo PBT (PandasBaseTransformer) para realizar
    operaciones sobre el DataFrame de empleados vinculados, con base en la
    configuración proporcionada.

    Args:
        config (dict): Diccionario de configuración que contiene todas las
                       subsecciones necesarias para el proceso.
    """

    def __init__(self, config: dict):
        """
        Inicializa la clase GenerarMaestraVinculados con la configuración proporcionada.

        Args:
            config (dict): Diccionario de configuración que contiene todas las
                           subsecciones necesarias para el proceso.
        """
        self.config = config
        self.valor_inicial_bonf = 0
        self.temporales = GenerarMaestraTemporales(self.config)
        self.col_observaciones = self.temporales.col_observaciones
        self.col_pri_apelli = self.temporales.col_pri_apelli
        self.col_seg_apelli = self.temporales.col_seg_apelli

        # Inicialización de configuraciones frecuentemente usadas
        self.nom_hojas = self.config["maestra_vinculados"]["nom_hojas"]
        self.cols_necesarias = self.config["maestra_vinculados"][
            "cols_necesarias_indiv"
        ]
        self.dict_salarios_log = list(
            self.config["Drivers"]["dict_salarios_log"].keys()
        )
        self.dict_obs = self.temporales.dict_obs

    def ejecutar_proceso(self):
        """
        Ejecuta el proceso completo de generación de la maestra, aplicando
        filtros, transformaciones y cálculos según la configuración.

        Returns:
            pd.DataFrame: El DataFrame resultante después de aplicar todos los
                          pasos del proceso.
        """
        hoja_act = self.nom_hojas["Activos"]

        dict_dfs_leidos = self.cargar_maestras_vinculados_publico()

        # Selecionar solo cols necesarias de los dfs
        dict_dfs_vincds_select = self._seleccionar_dfs_vinculados(dict_dfs_leidos)

        dict_dfs_vincds_select[hoja_act] = self._ajustar_nombres_cargos_activos(
            df=dict_dfs_vincds_select[hoja_act]
        )
        dict_dfs_vincds_select[hoja_act] = self._ajustar_nombre_vinculados(
            df=dict_dfs_vincds_select[hoja_act]
        )
        # Filtrar solo cargos de activos
        dict_dfs_vincds_select[hoja_act] = self.temporales._filtrar_por_cargos(
            df=dict_dfs_vincds_select[hoja_act]
        )
        dict_dfs_vincds_select[hoja_act] = self._filtrar_por_no_firmantes(
            df=dict_dfs_vincds_select[hoja_act]
        )
        
        dict_dfs_vincds_select[hoja_act] = self._traer_fechas_ingresos(
            dict_dfs_vincds_select[hoja_act], dict_dfs_vincds_select
        )
        df_vinculados_obs = self._ajustar_observaciones(dict_dfs_vincds_select)
        df_vinculados_obs = self.temporales._asignar_valores(df_vinculados_obs)
        df_con_valores = self.temporales._reemplazar_por_salarios(df_vinculados_obs)

        return df_con_valores

    def cargar_maestras_vinculados_publico(self):
        return self._cargar_dfs_maestra_vinculados()

    def _cargar_dfs_maestra_vinculados(self):
        """
        Carga los insumos necesarios para el proceso, incluyendo los DataFrames
        temporales y vinculados.

        Returns:
            dict: Un diccionario con los DataFrames cargados desde las hojas de Excel.
        """
        Lector_insumos = GF.ExcelReader(path=self.config["path_insumos"])
        dict_dfs_vinculados = {}

        for cada_hoja, cada_clave in self.nom_hojas.items():
            df_leido = Lector_insumos.Lectura_simple_excel(
                nom_insumo=self.config["maestra_vinculados"]["nom_base"],
                nom_hoja=cada_hoja,
            )
            dict_dfs_vinculados[cada_clave] = df_leido

        return dict_dfs_vinculados

    def _seleccionar_dfs_vinculados(self, dict_dfs_vinculados):
        """
        Ajusta los DataFrames vinculados seleccionando solo las columnas necesarias
        según la configuración.

        Args:
            dict_dfs_vinculados (dict): Un diccionario donde las claves son los
                                        identificadores de los DataFrames y los
                                        valores son los DataFrames correspondientes.

        Returns:
            dict: Un diccionario con los DataFrames filtrados.
        """
        dict_dfs_vincds_select = {}
        for cada_hoja, cada_clave in self.nom_hojas.items():

            df_leido = dict_dfs_vinculados[cada_clave]
            list_cols_x_df = list(self.cols_necesarias[cada_hoja].keys())

            df_leido_fil = PBT.Seleccionar_columnas_pd(
                df=df_leido, cols_elegidas=list_cols_x_df
            )

            dict_dfs_vincds_select[cada_clave] = df_leido_fil

        return dict_dfs_vincds_select

    def _ajustar_nombre_vinculados(self, df):
        # Usamos str.cat para manipular valores nulos y reemplazarlos por una cadena vacia.
        df.loc[:, "NOMBRE"] = df["NOMBRE"].str.cat(
            [df[self.col_pri_apelli], df[self.col_seg_apelli]], sep=" ", na_rep=""
        )
        df = PBT._eliminar_espacios_blanco_columnas(df=df, columnas="NOMBRE")

        # Eliminar espacios múltiples en la columna "texto"
        df["NOMBRE"] = df["NOMBRE"].str.replace(r"\s+", " ", regex=True).str.strip()
        return df

    def _ajustar_observaciones(self, dict_df):
        dict_copy = dict_df.copy()

        # Agregar tipo de observacion por df.
        for cada_hoja, cada_df in dict_df.items():
            if cada_hoja == self.cols_necesarias["Activos"]:
                pass
            else:
                dict_copy[cada_hoja] = PBT.Agregar_columna_constante(
                    dataframe=cada_df,
                    nombre_columna=self.col_observaciones,
                    valor_constante=self.dict_obs[cada_hoja],
                )
        # Combinar observaciones.
        df_observaciones = PBT.concatenate_dataframes(
            dataframes=(list(dict_copy.values())[1:]), join="inner"
        )

        # Actualizar todas las observaciones a activos
        df_vinculados_obs = PBT.pd_left_merge(
            base_left=dict_df[self.nom_hojas["Activos"]],
            base_right=df_observaciones,
            key=self.cols_necesarias["Activos"]["CEDULA"],
        )

        df_vinculados_obs = PBT.Remplazar_nulos_multiples_columnas_pd(
            base=df_vinculados_obs,
            list_columns=self.col_observaciones,
            value=self.dict_obs["Activos"],
        )

        return df_vinculados_obs

    def _filtrar_por_no_firmantes(self, df):
        """Filtra el DataFrame elimiando las cedulas definidas en   en la configuración."""
        return PBT.Filtrar_por_valores_excluidos(
            df=df,
            columna=self.cols_necesarias["Activos"]["CEDULA"],
            valores_excluir=self.config["Drivers"]["cedulas_no_medibles"],
        )

    def _traer_fechas_ingresos(self, df, dict_dfs):
        df_fecha_ing_ajust = PBT.pd_left_merge(
            base_left=df,
            base_right=dict_dfs[self.nom_hojas["Ingresos"]],
            key=self.cols_necesarias["Activos"]["CEDULA"],
        )
        return df_fecha_ing_ajust

    def _ajustar_nombres_cargos_activos(self, df):
        """
        Ajusta los nombres de cargos para los activos en el DataFrame.

        Args:
            df (dict): Dataframe con los cargos a ajustar.

        Returns:
            dict: Diccionario de DataFrames con los nombres de cargos ajustados.
        """

        df_ajustado = PBT._eliminar_espacios_blanco_columnas(
            df=df, columnas=self.cols_necesarias["Activos"]["CARGO"]
        )

        return df_ajustado


class CombinarMaestras:
    def __init__(
        self,
        config: dict,
        df_maestra_vinculados: DataFrame,
        df_maestra_temporales: DataFrame,
    ):
        self.temporales = GenerarMaestraTemporales(config)
        self.col_observaciones = self.temporales.col_observaciones
        self.dict_obs = self.temporales.dict_obs

        self.config = config
        self.maestra_vinculados = df_maestra_vinculados
        self.maestra_temporales = df_maestra_temporales

        self.list_ingresos_retiros = [
            self.dict_obs["Ingresos"],
            self.dict_obs["Retiros"],
        ]

    def ejecutar_proceso(self):
        df_vincds_completo, df_temp_completo = self._agregar_cols()

        df_para_pago = self._combinar_maestras(
            lista_maestras=[df_vincds_completo, df_temp_completo]
        )

        df_para_pago = PBT.Seleccionar_columnas_pd(
            df=df_para_pago,
            cols_elegidas=self.config["maestra_para_pago"]["cols_insumo_finales"],
        )

        df_para_proceso = PBT.Filtrar_por_valores_excluidos(
            df=df_para_pago,
            columna=self.col_observaciones,
            valores_excluir=self.list_ingresos_retiros,
        )

        df_ingr_ret_completo = PBT.Filtrar_por_valores_pd(
            df=df_para_pago,
            columna=self.col_observaciones,
            valores_filtrar=self.list_ingresos_retiros,
        )

        return df_para_proceso, df_ingr_ret_completo

    def _agregar_cols(self):
        df_vincds_completo = PBT.Agregar_multiples_cols_constantes(
            df=self.maestra_vinculados,
            dict_cols=self.config["maestra_para_pago"]["maestra_vinculados"][
                "cols_agregar"
            ],
        )
        df_temp_completo = PBT.Agregar_multiples_cols_constantes(
            df=self.maestra_temporales,
            dict_cols=self.config["maestra_para_pago"]["maestra_temporales"][
                "cols_agregar"
            ],
        )
        return df_vincds_completo, df_temp_completo

    def _combinar_maestras(df, lista_maestras):
        df_concat = PBT.concatenate_dataframes(dataframes=lista_maestras)
        return df_concat
