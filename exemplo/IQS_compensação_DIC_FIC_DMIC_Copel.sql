WITH limites_mensais AS (
    -- Busca os limites regulatórios de DEC e FEC para o mês e ano digitados
    SELECT
        miq.NUM_CONJTO_ANEEL_MAIQ AS cea,
        EXTRACT(YEAR FROM miq.DATA_INI_VIG_MAIQ) AS ano_ref,
        vmai.MES_VMAI AS mes_ref,
        MAX(
            CASE
                WHEN miq.NUM_TIPO_INDIC_MAIQ = 13
                THEN TO_NUMBER(
                         REPLACE(vmai.VAL_VMAI, ',', '.')
                         DEFAULT NULL ON CONVERSION ERROR
                     )
            END
        ) AS limite_dec,
        MAX(
            CASE
                WHEN miq.NUM_TIPO_INDIC_MAIQ = 14
                THEN TO_NUMBER(
                         REPLACE(vmai.VAL_VMAI, ',', '.')
                         DEFAULT NULL ON CONVERSION ERROR
                     )
            END
        ) AS limite_fec
    FROM IQS.META_ANEEL_INDIC_QUALID_SERV miq
    JOIN IQS.VAL_META_ANEEL_INDIC_QUALID vmai
      ON vmai.NUM_META_ANEEL_VMAI = miq.NUM_SEQ_MAIQ
    WHERE miq.NUM_TIPO_INDIC_MAIQ IN (13,14)
      AND EXTRACT(YEAR FROM miq.DATA_INI_VIG_MAIQ) = :ano_apuracao  -- 📅 FILTRO DE ANO
      AND vmai.MES_VMAI = :mes_apuracao                            -- 📅 FILTRO DE MÊS
    GROUP BY
        miq.NUM_CONJTO_ANEEL_MAIQ,
        EXTRACT(YEAR FROM miq.DATA_INI_VIG_MAIQ),
        vmai.MES_VMAI
),
uc_base AS (
    -- Varre a base completa de UCs ativas/ligadas da empresa
    SELECT
        ue.ISN_UC,
        ue.NUM_CONJTO_ANEEL_FIXO_UC AS cea,
        ue.INDIC_LOCAL_TEC_UC AS urb_rur,
        ue.COD_GRUPO_NIVEL_TENSAO_UC,
        ue.COD_NIVEL_TENSAO_UC,
        NVL(ue.VAL_BASE_CALC_COMPEN_UC, 0) AS VRC
    FROM CIS.UC_ENERGIA ue
    WHERE ue.TIPO_SIT_UC IN ('LG','CR')
),
realizado_mensal AS (
    -- Agrupa todas as interrupções válidas do mês de apuração escolhido
    SELECT 
        hc.NUM_UC_HCAI AS ISN_UC,
        EXTRACT(YEAR FROM i.DATA_HORA_INIC_INTRP) AS ano_ref,
        EXTRACT(MONTH FROM i.DATA_HORA_INIC_INTRP) AS mes_ref,        
        COUNT(i.NUM_SEQ_INTRP) AS REALIZADO_FIC,        
        SUM((i.DATA_HORA_FIM_INTRP - hc.DATA_INTRP_HCAI) * 24) AS REALIZADO_DIC,        
        MAX((i.DATA_HORA_FIM_INTRP - hc.DATA_INTRP_HCAI) * 24) AS REALIZADO_DMIC        
    FROM iqs.HIST_CONS_AFETADO_INTERRUPCAO hc
    JOIN INTERRUPCAO i ON i.NUM_SEQ_INTRP = hc.NUM_INTRP_HCAI
    WHERE hc.NUM_MOTIVO_TRAT_DIF_HCAI IS NULL
      -- 📅 FILTRO DINÂMICO BASEADO NAS VARIÁVEIS DO DBEAVER
      AND i.DATA_HORA_INIC_INTRP >= TO_DATE(:ano_apuracao || '-' || LPAD(:mes_apuracao, 2, '0') || '-01', 'YYYY-MM-DD')
	  AND i.DATA_HORA_INIC_INTRP < ADD_MONTHS( TO_DATE(:ano_apuracao || '-' || LPAD(:mes_apuracao, 2, '0') || '-01', 'YYYY-MM-DD'),1)
      AND ((i.DATA_HORA_FIM_INTRP - i.DATA_HORA_INIC_INTRP) * 24 * 60) >= 3            
      AND (hc.TIPO_PROTOC_JUSTIF_HCAI IS NULL OR hc.TIPO_PROTOC_JUSTIF_HCAI NOT IN ('2','3','4','5','7','8','9'))
      AND NOT ((tipo_eqp_intrp = 'C' AND indic_propr_posto_intrp = 'P') OR (tipo_eqp_intrp = 'T' AND indic_propr_posto_intrp = 'P'))
    GROUP BY 
        hc.NUM_UC_HCAI,
        EXTRACT(YEAR FROM i.DATA_HORA_INIC_INTRP),
        EXTRACT(MONTH FROM i.DATA_HORA_INIC_INTRP)
),
calculo_individual AS (
    -- Une cadastro, metas e realizados para aplicar as regras do PRODIST por UC
    SELECT 
        u.ISN_UC,
        u.VRC,
        l.ano_ref,
        l.mes_ref,
        u.COD_GRUPO_NIVEL_TENSAO_UC AS GRUPO_TENSAO,        
        -- Fator KEI regulatório
        CASE 
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('1','2','3')  THEN 108
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') THEN 40 
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B'                                             THEN 34
            ELSE 0
        END AS KEI,        
        -- Determinação da Meta DIC da UC no mês
        CASE 
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('1','2','3') AND u.urb_rur = 'U' THEN 3
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('1','2','3') AND u.urb_rur = 'R' THEN 5
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 5 THEN 3
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 10 THEN 5
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 15 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 20 THEN 9
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 25 THEN 10
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' THEN 12
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 5 THEN 8
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 10 THEN 13
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 15 THEN 19
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 20 THEN 24
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 25 THEN 28
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 40 THEN 33    
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' THEN 37
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 5 THEN 4
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 10 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 15 THEN 10
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 20 THEN 12
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 25 THEN 14
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 40 THEN 15
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 50 THEN 18  
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' THEN 21
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 5 THEN 10
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 10 THEN 16
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 15 THEN 20
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 20 THEN 24
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 25 THEN 28
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 40 THEN 33
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' THEN 40
        END AS meta_dic,
        NVL(r.REALIZADO_DIC, 0) AS realizado_dic,
        -- Determinação da Meta FIC da UC no mês
        CASE
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('1','2','3') AND u.urb_rur = 'U' THEN 2
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('1','2','3') AND u.urb_rur = 'R' THEN 4
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_fec <= 5  THEN 3
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_fec <= 10 THEN 4
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_fec <= 15 THEN 5
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_fec <= 20 THEN 6
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_fec <= 25 THEN 6
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_fec <= 5  THEN 4
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_fec <= 10 THEN 5
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_fec <= 15 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_fec <= 20 THEN 8
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_fec <= 25 THEN 9
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_fec <= 40 THEN 10     
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' THEN 11
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_fec <= 5  THEN 3
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_fec <= 10 THEN 4
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_fec <= 15 THEN 5
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_fec <= 20 THEN 6
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_fec <= 25 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_fec <= 40 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_fec <= 50 THEN 8       
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' THEN 9
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_fec <= 5  THEN 4
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_fec <= 10 THEN 6
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_fec <= 15 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_fec <= 20 THEN 8
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_fec <= 25 THEN 9
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_fec <= 40 THEN 10      
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' THEN 12
        END AS meta_fic,
        NVL(r.REALIZADO_FIC, 0) AS realizado_fic,
        -- Determinação da Meta DMIC da UC no mês
        CASE 
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('1','2','3') AND u.urb_rur = 'U' THEN 2
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('1','2','3') AND u.urb_rur = 'R' THEN 4
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 5 THEN 3
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 10 THEN 5
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 15 THEN 6
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 20 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' AND l.limite_dec <= 25 THEN 8
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'U' THEN 8
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 5 THEN 6
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 10 THEN 10
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 15 THEN 14
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 20 THEN 18
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 25 THEN 20
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' AND l.limite_dec <= 40 THEN 24    
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'A' AND u.COD_NIVEL_TENSAO_UC IN ('3a','4','S') AND u.urb_rur = 'R' THEN 24
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 5 THEN 3
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 10 THEN 5
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 15 THEN 7
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 20 THEN 9
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 25 THEN 10
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 40 THEN 12
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' AND l.limite_dec <= 50 THEN 12  
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'U' THEN 12
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 5 THEN 8
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 10 THEN 12
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 15 THEN 15
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 20 THEN 18
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 25 THEN 20
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' AND l.limite_dec <= 40 THEN 24
            WHEN u.COD_GRUPO_NIVEL_TENSAO_UC = 'B' AND u.urb_rur = 'R' THEN 24
        END AS meta_dmic,
        NVL(r.REALIZADO_DMIC, 0) AS realizado_dmic
    FROM uc_base u
    JOIN limites_mensais l ON l.cea = u.cea
    LEFT JOIN realizado_mensal r 
      ON u.ISN_UC = r.ISN_UC 
     AND l.ano_ref = r.ano_ref
     AND l.mes_ref = r.mes_ref
),
calculo_por_uc AS (
    -- 🟢 ESTA CTE TRABALHA LINHA POR LINHA NO NÍVEL DE UC
    -- Aqui calculamos o valor financeiro de cada indicador e elegemos o MAIOR para cada UC separadamente.
    SELECT
        ano_ref,
        mes_ref,
        GRUPO_TENSAO,
        ISN_UC,
        realizado_dic, meta_dic,
        realizado_fic, meta_fic,
        realizado_dmic, meta_dmic,
        -- Valores individuais calculados da UC
        CASE WHEN realizado_dic > meta_dic   THEN VRC * (realizado_dic / 730) * KEI ELSE 0 END AS COMP_DIC,
        CASE WHEN realizado_fic > meta_fic   THEN VRC * (realizado_fic / 730) * KEI ELSE 0 END AS COMP_FIC,
        CASE WHEN realizado_dmic > meta_dmic THEN VRC * (realizado_dmic / 730) * KEI ELSE 0 END AS COMP_DMIC,        
        -- 🎯 REGRA PRODIST CRÍTICA: Filtra o maior valor individual da UC ANTES do agrupamento geral.
        GREATEST(
            CASE WHEN realizado_dic > meta_dic   THEN VRC * (realizado_dic / 730) * KEI ELSE 0 END,
            CASE WHEN realizado_fic > meta_fic   THEN VRC * (realizado_fic / 730) * KEI ELSE 0 END,
            CASE WHEN realizado_dmic > meta_dmic THEN VRC * (realizado_dmic / 730) * KEI ELSE 0 END
        ) AS MAIOR_COMPENSACAO_DA_UC
    FROM calculo_individual
)
-- ======= RELATÓRIO FINAL CONSOLIDADO POR AGRUPAMENTO =======
SELECT 
    ano_ref AS ANO,
    mes_ref AS MES,
    GRUPO_TENSAO,
    COUNT(DISTINCT ISN_UC) AS UCS_PROCESSADAS,    
    -- Contadores estatísticos por indicador
    SUM(CASE WHEN realizado_dic > meta_dic THEN 1 ELSE 0 END) AS QTD_UCS_COMPENSADAS_DIC,
    SUM(CASE WHEN realizado_fic > meta_fic THEN 1 ELSE 0 END) AS QTD_UCS_COMPENSADAS_FIC,
    SUM(CASE WHEN realizado_dmic > meta_dmic THEN 1 ELSE 0 END) AS QTD_UCS_COMPENSADAS_DMIC,
    -- Totais brutos calculados (Para fins de auditoria)
    ROUND(SUM(COMP_DIC), 2) AS TOTAL_COMPENSACAO_DIC,
    ROUND(SUM(COMP_FIC), 2) AS TOTAL_COMPENSACAO_FIC,
    ROUND(SUM(COMP_DMIC), 2) AS TOTAL_COMPENSACAO_DMIC,    
    -- 💰 O TOTAL FINANCEIRO AGORA É A SOMA DOS MAIORES VALORES DE CADA UC INDIVIDUALMENTE
    ROUND(SUM(MAIOR_COMPENSACAO_DA_UC), 2) AS TOTAL_GERAL_COMPENSACOES
FROM calculo_por_uc
GROUP BY 
    ano_ref,
    mes_ref,
    GRUPO_TENSAO;