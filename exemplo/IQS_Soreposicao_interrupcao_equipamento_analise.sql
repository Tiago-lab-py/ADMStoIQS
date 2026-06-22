WITH interrupcoes_filtradas AS (
    SELECT
        PID_OCOR_INTRP AS ocorrencia,
        NUM_SEQ_INTRP AS interrupcao,
        TIPO_CHV_INTRP AS tipo_chave,
        NUM_OPER_CHV_INTRP AS NUMERO_OPERACIONAL,
        DATA_HORA_INIC_INTRP AS DATA_INICIO,
        DATA_HORA_FIM_INTRP AS DATA_FIM,	
        COD_CAUSA_INTRP,
        COD_COMP_INTRP,
        COD_TIPO_INTRP,
        TIPO_PROTOC_JUSTIF_INTRP		
    FROM
        SOD.INTERRUPCAO
    WHERE
        TO_CHAR(DATA_HORA_INIC_INTRP, 'yyyymm') = '202605'
        AND TIPO_EQP_INTRP = 'C'
        AND NUM_OPER_CHV_INTRP IS NOT NULL
),
mapeamento_sobreposicao AS (
    SELECT 
        A.*,
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM interrupcoes_filtradas B
                WHERE A.NUMERO_OPERACIONAL = B.NUMERO_OPERACIONAL
                  AND A.interrupcao <> B.interrupcao
                  AND B.DATA_INICIO <= A.DATA_INICIO
                  AND B.DATA_FIM >= A.DATA_FIM
                  AND (B.DATA_INICIO < A.DATA_INICIO OR B.DATA_FIM > A.DATA_FIM OR B.interrupcao < A.interrupcao)
            ) THEN 'EXCLUIR (Contido em outra)'
            ELSE 'MANTER (OK)'
        END AS SITUACAO
    FROM 
        interrupcoes_filtradas A
)
SELECT 
    ms.NUMERO_OPERACIONAL,
    ms.ocorrencia,
    ms.interrupcao,
    ms.tipo_chave,
    ms.DATA_INICIO,
    ms.DATA_FIM,
    ms.SITUACAO,
    ms.COD_CAUSA_INTRP,
    ms.COD_COMP_INTRP,
    ms.COD_TIPO_INTRP,
    ms.TIPO_PROTOC_JUSTIF_INTRP,
    hcai.TIPO_PROTOC_JUSTIF_HCAI AS tipo_protocolo_hcai,
    COUNT(hcai.NUM_UC_HCAI) AS UC_afetadas -- Correção do COUNT
FROM 
    mapeamento_sobreposicao ms
INNER JOIN 
    iqs.HIST_CONS_AFETADO_INTERRUPCAO hcai ON ms.interrupcao = hcai.NUM_INTRP_HCAI 
GROUP BY -- Cláusula GROUP BY adicionada com todos os campos não agregados
    ms.NUMERO_OPERACIONAL,
    ms.ocorrencia,
    ms.interrupcao,
    ms.tipo_chave,
    ms.DATA_INICIO,
    ms.DATA_FIM,
    ms.SITUACAO,
    ms.COD_CAUSA_INTRP,
    ms.COD_COMP_INTRP,
    ms.COD_TIPO_INTRP,
    ms.TIPO_PROTOC_JUSTIF_INTRP,
    hcai.TIPO_PROTOC_JUSTIF_HCAI
ORDER BY 
    ms.NUMERO_OPERACIONAL, 
    ms.DATA_INICIO, 
    ms.SITUACAO DESC;