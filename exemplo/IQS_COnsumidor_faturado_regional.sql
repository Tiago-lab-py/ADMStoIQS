SELECT
    CASE 
        WHEN GROUPING(rd.SIGLA_RDIS) = 1 THEN 'COPEL'
        ELSE rd.SIGLA_RDIS 
    END AS REGIONAL_TOTAL,
    -- Nova coluna de mapeamento customizado
    CASE rd.SIGLA_RDIS
        WHEN 'CSL' THEN 'P'
        WHEN 'NRT' THEN 'L'
        WHEN 'NRO' THEN 'M'
        WHEN 'LES' THEN 'C'
        WHEN 'OES' THEN 'V'
        ELSE 'COPEL' -- Mantém a sigla original caso não esteja no mapeamento
    END AS SIGLA_REGIONAL,
     CASE rd.SIGLA_RDIS
        WHEN 'CSL' THEN 'SODPGO'
        WHEN 'NRT' THEN 'SODLNA'
        WHEN 'NRO' THEN 'SODMGA'
        WHEN 'LES' THEN 'SODCTA'
        WHEN 'OES' THEN 'SDOCEL'
        ELSE 'COPEL' -- Mantém a sigla original caso não esteja no mapeamento
    END AS SIGLA_SEVIDOR,
    to_char(ANO_MES_HQCL, 'yyyy-mm') AS anomes,
    sum(QTDE_CONS_FAT_URB_HQCL + QTDE_CONS_FAT_RUR_HQCL) AS UC_faturada
FROM
    iqs.HIST_QTDE_CONS_LOCAL hqcl
INNER JOIN cis.LOCALIDADE l ON
    l.COD_LOCAL = hqcl.COD_LOCAL_HQCL
LEFT JOIN cis.seccional_distribuicao sc ON
    l.COD_SECCION_DISTR_LOCAL = sc.COD_SDIS
LEFT JOIN cis.REGIONAL_DISTRIBUICAO rd ON
    sc.COD_REG_DISTR_SDIS = rd.COD_RDIS
WHERE
    ANO_MES_HQCL = TO_DATE('2026-05-01', 'yyyy-mm-dd') 
    AND rd.SIGLA_RDIS <> 'SCD'
GROUP BY 
    ROLLUP (rd.SIGLA_RDIS), 
    to_char(ANO_MES_HQCL, 'yyyy-mm')
ORDER BY 
    anomes DESC, 
    REGIONAL_TOTAL ASC;