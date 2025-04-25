import General_Functions as GF
from Transformation_Functions import PandasBaseTransformer as PBT
from exclusive_functions import ColsCalculadasDfProceso, ColsCalculadasIngRet
from typing import Dict
from pandas import DataFrame, read_excel
from generar_maestra import GenerarMaestraVinculados


class CalculosPostProceso:
    def __init__(self, config):
        self.config = config
        self.nom_hojas = self.config["maestra_vinculados"]["nom_hojas"]
        self.conf_maes_pago = self.config["maestra_para_pago"]["maestra_post_proceso"]
        self.cols_necesarias = self.config["maestra_vinculados"][
            "cols_necesarias_indiv"
        ]

    def ejecutar_proceso(self):
        df_post_proceso, df_ing_ret, dict_dfs = self._cargar_maes_tempols_dicts()

        df_post_proceso = self._ajustar_type_data(df_post_proceso)

        list_garatzds, list_no_garatzds = self._extraer_garantizados_no_garantizados(
            dict_dfs
        )

        df_post_proceso_calculos = self._calculos_post_proceso(
            df_post_proceso,
            lista_no_garantizados=list_no_garatzds,
            lista_garantizados=list_garatzds,
        )
        df_ing_ret_post_calculos = self._calculos_ingresos_ret(df=df_ing_ret)

        # Agregar columna Estatus_garantizado a ingresos y Ret
        df_ing_ret_post_calculos = PBT.Agregar_columna_constante(
            dataframe=df_ing_ret_post_calculos,
            nombre_columna=self.config["dict_constantes"]["ESTATUS_GARANTIZADO"],
            valor_constante="-",
        )

        # Tratar valores nulos.
        df_ing_ret_post_calculos = df_ing_ret_post_calculos.fillna("-")
        df_post_proceso_calculos = df_post_proceso_calculos.fillna("-")

        # Unir ambas bases como resultado final
        df_completo_post_calculos = PBT.concatenate_dataframes(
            dataframes=[df_post_proceso_calculos, df_ing_ret_post_calculos],
            join="inner",
        )
        
        df_completo_post_calculos = PBT.Agregar_columna_constante(
            dataframe=df_completo_post_calculos,
            nombre_columna=self.config["dict_constantes"]["MES_ACT"],
            valor_constante=self.config["mes_a_medir"],
        )
        
        return df_completo_post_calculos

    def _ajustar_type_data(self, df):
        cols = [self.conf_maes_pago["cols_calculos"]["VALOR"]] + [
            *self.conf_maes_pago["cols_numericas"]
        ]

        return PBT.Cambiar_tipo_dato_multiples_columnas_pd(
            base=df, list_columns=cols, type_data=float
        )

    def _extraer_garantizados_no_garantizados(self, dict_dfs):
        conf_filtros = self.conf_maes_pago["filtros"]
        cols_transformar = self.conf_maes_pago["cambiar_type_data"]
        col_cedula = self.cols_necesarias["Activos"]["CEDULA"]

        df_lic_n_rem = dict_dfs[self.nom_hojas["Licen no remun variab"]]
        df_vac = dict_dfs[self.nom_hojas["Vacac cargos espec Logist"]]
        df_incap = dict_dfs[self.nom_hojas["Incap cargos espec Logist"]]

        # Convertir tipos de datos en las columnas
        df_vac = PBT.Cambiar_tipo_dato_multiples_columnas_pd(
            base=df_vac,
            list_columns=[conf_filtros["dias_habiles_en_el_mes"]["columna"]],
            type_data=cols_transformar["dias_habiles_tipo"],
        )

        df_incap = PBT.Cambiar_tipo_dato_multiples_columnas_pd(
            base=df_incap,
            list_columns=[conf_filtros["total_incap"]["columna"]],
            type_data=cols_transformar["total_incap_tipo"],
        )

        # Filtrar garant_vac_n_rem
        garant_vac_n_rem = PBT.Filtrar_por_operacion(
            df=df_vac,
            columna=conf_filtros["dias_habiles_en_el_mes"]["columna"],
            operacion=conf_filtros["dias_habiles_en_el_mes"]["operacion"],
            valor_umbral=conf_filtros["dias_habiles_en_el_mes"]["valor_umbral"],
        )[col_cedula].to_list()

        # Filtrar garant_incap
        garant_incap = PBT.Filtrar_por_operacion(
            df=df_incap,
            columna=conf_filtros["total_incap"]["columna"],
            operacion=conf_filtros["total_incap"]["operacion_entre"]["operacion"],
            valor_min=conf_filtros["total_incap"]["operacion_entre"]["valor_min"],
            valor_max=conf_filtros["total_incap"]["operacion_entre"]["valor_max"],
        )[col_cedula].to_list()

        # Obtener no_garant_lic_n_rem
        no_garant_lic_n_rem = df_lic_n_rem[col_cedula].to_list()

        # Filtrar no_garant_incp
        no_garant_incp = PBT.Filtrar_por_operacion(
            df=df_incap,
            columna=conf_filtros["total_incap"]["columna"],
            operacion=conf_filtros["total_incap"]["operacion_mayor_igual"]["operacion"],
            valor_umbral=conf_filtros["total_incap"]["operacion_mayor_igual"][
                "valor_umbral"
            ],
        )[col_cedula].to_list()

        # Crear listas grantizados y no garantizados.
        lista_garantizados = garant_vac_n_rem + garant_incap
        lista_no_garantizados = no_garant_lic_n_rem + no_garant_incp

        return lista_garantizados, lista_no_garantizados

    def _calculos_post_proceso(self, df, lista_garantizados, lista_no_garantizados):
        calculador = ColsCalculadasDfProceso(
            config=self.config,
            lista_garantizados=lista_garantizados,
            lista_no_garantizados=lista_no_garantizados,
        )
        df_post_proceso_calculos = calculador.procesar_dataframe(df=df)

        return df_post_proceso_calculos

    def _calculos_ingresos_ret(self, df):
        calculador_ing_ret = ColsCalculadasIngRet(config=self.config, df=df)
        df_ing_ret_compt = calculador_ing_ret.ejecutar_proceso()

        return df_ing_ret_compt

    def _cargar_maes_tempols_dicts(self):
        """
        Carga los insumos necesarios para el proceso, la base de personal luego de ser devuelta por el proceso.
        """
        Lector_insumos = GF.ExcelReader(path=self.config["path_insumos"])

        # Cargar DataFrame de temporales
        df_post_proceso = Lector_insumos.Lectura_simple_excel(
            nom_insumo=self.config["maestra_para_pago"]["maestra_post_proceso"][
                "nom_base"
            ],
            nom_hoja=self.config["maestra_para_pago"]["maestra_post_proceso"][
                "nom_hoja"
            ],
        )
        df_ing_ret = read_excel("Insumos/Maestra_ingresos_ret.xlsx")

        instancia_gmv = GenerarMaestraVinculados(self.config)
        dict_dfs = instancia_gmv.cargar_maestras_vinculados_publico()

        return df_post_proceso, df_ing_ret, dict_dfs
