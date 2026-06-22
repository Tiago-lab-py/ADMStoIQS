/*
Consistência IQS por UC afetada (HCAI) com agregação regional.
Parâmetro obrigatório:
  :p_yyyymm  (ex.: '202604')

Importante:
- A regional responsável é derivada da UC afetada (UC_ENERGIA -> LOCALIDADE -> REGIONAL_DISTRIBUICAO).
- Não usar somente o conjunto da interrupção para inferir regional.
*/
WITH
uc_consideradas AS (
    SELECT DISTINCT TRIM(TO_CHAR(h.NUM_UC_HCAI)) AS num_uc
    FROM iqs.HIST_CONS_AFETADO_INTERRUPCAO h
    WHERE h.INDIC_FAT_HCAI = 'S'
      AND TO_CHAR(h.DATA_INTRP_HCAI, 'YYYYMM') = :p_yyyymm
),
divisor_oficial AS (
    SELECT
        CASE rd.SIGLA_RDIS
            WHEN 'CSL' THEN 'CSL'
            WHEN 'LES' THEN 'LES'
            WHEN 'NRO' THEN 'NRO'
            WHEN 'NRT' THEN 'NRT'
            WHEN 'OES' THEN 'OES'
            ELSE 'OUTROS'
        END AS arquivo_origem,
        SUM(QTDE_CONS_FAT_URB_HQCL + QTDE_CONS_FAT_RUR_HQCL) AS uc_faturada
    FROM iqs.HIST_QTDE_CONS_LOCAL hqcl
    INNER JOIN cis.LOCALIDADE l ON l.COD_LOCAL = hqcl.COD_LOCAL_HQCL
    LEFT JOIN cis.SECCIONAL_DISTRIBUICAO sc ON l.COD_SECCION_DISTR_LOCAL = sc.COD_SDIS
    LEFT JOIN cis.REGIONAL_DISTRIBUICAO rd ON sc.COD_REG_DISTR_SDIS = rd.COD_RDIS
    WHERE TO_CHAR(ANO_MES_HQCL, 'YYYYMM') = :p_yyyymm
      AND rd.SIGLA_RDIS <> 'SCD'
    GROUP BY rd.SIGLA_RDIS
),
divisor_total AS (
    SELECT SUM(uc_faturada) AS total_faturado
    FROM divisor_oficial
),
base_dados AS (
    SELECT
        NVL(rd.SIGLA_RDIS, 'COPEL') AS arquivo_origem,
        TRIM(TO_CHAR(h.NUM_UC_HCAI)) AS num_uc,
        TRIM(TO_CHAR(h.NUM_POSTO_HCAI)) AS num_posto,
        CAST(h.DATA_INTRP_HCAI AS DATE) AS dt_ini,
        CAST(i.DATA_HORA_FIM_INTRP AS DATE) AS dt_fim,
        NVL(NULLIF(TRIM(TO_CHAR(h.NUM_INTRP_INIC_MANOBRA_HCAI)), ''), TRIM(TO_CHAR(h.NUM_INTRP_HCAI))) AS num_intrp_key,
        TRIM(NVL(TO_CHAR(h.TIPO_PROTOC_JUSTIF_HCAI), NVL(TO_CHAR(i.TIPO_PROTOC_JUSTIF_INTRP), '0'))) AS prot_hcai,
        TRIM(TO_CHAR(h.NUM_MOTIVO_TRAT_DIF_HCAI)) AS num_motivo_trat_dif_hcai
    FROM iqs.HIST_CONS_AFETADO_INTERRUPCAO h
    LEFT JOIN sod.INTERRUPCAO i ON i.NUM_SEQ_INTRP = h.NUM_INTRP_HCAI
    LEFT JOIN cis.UC_ENERGIA uce ON uce.ISN_UC = h.NUM_UC_HCAI
    LEFT JOIN cis.LOCALIDADE l ON l.COD_LOCAL = uce.COD_LOCAL_UC
    LEFT JOIN cis.SECCIONAL_DISTRIBUICAO sc ON l.COD_SECCION_DISTR_LOCAL = sc.COD_SDIS
    LEFT JOIN cis.REGIONAL_DISTRIBUICAO rd ON sc.COD_REG_DISTR_SDIS = rd.COD_RDIS
    JOIN uc_consideradas uc ON uc.num_uc = TRIM(TO_CHAR(h.NUM_UC_HCAI))
    WHERE TO_CHAR(h.DATA_INTRP_HCAI, 'YYYYMM') = :p_yyyymm
      AND rd.SIGLA_RDIS <> 'SCD'
),
classificada AS (
    SELECT
        b.*,
        CASE
            WHEN b.num_motivo_trat_dif_hcai IS NOT NULL AND b.num_motivo_trat_dif_hcai NOT IN ('', '0') THEN 'Ignorar'
            WHEN b.prot_hcai = '0' THEN 'Liquido'
            ELSE 'Expurgo'
        END AS classificacao
    FROM base_dados b
),
filtrada AS (
    SELECT *
    FROM classificada
    WHERE classificacao IN ('Expurgo', 'Liquido')
),
dedupe AS (
    SELECT
        f.*,
        ROW_NUMBER() OVER (
            PARTITION BY f.num_intrp_key, f.num_posto, f.num_uc
            ORDER BY f.dt_fim DESC NULLS LAST
        ) AS rn_key
    FROM filtrada f
),
validos AS (
    SELECT *
    FROM dedupe
    WHERE rn_key = 1
      AND dt_ini IS NOT NULL
      AND dt_fim IS NOT NULL
      AND dt_fim >= dt_ini
),
ordenados AS (
    SELECT
        v.*,
        MAX(v.dt_fim) OVER (
            PARTITION BY v.arquivo_origem, v.num_uc
            ORDER BY v.dt_ini
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS max_fim_ate_agora
    FROM validos v
),
identifica_novo AS (
    SELECT
        o.*,
        LAG(o.max_fim_ate_agora) OVER (
            PARTITION BY o.arquivo_origem, o.num_uc
            ORDER BY o.dt_ini
        ) AS fim_anterior
    FROM ordenados o
),
periodo_marcado AS (
    SELECT
        i.*,
        CASE
            WHEN i.fim_anterior IS NULL OR i.dt_ini > i.fim_anterior THEN 1
            ELSE 0
        END AS is_novo
    FROM identifica_novo i
),
periodo_id AS (
    SELECT
        p.*,
        SUM(p.is_novo) OVER (
            PARTITION BY p.arquivo_origem, p.num_uc
            ORDER BY p.dt_ini
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS p_id
    FROM periodo_marcado p
),
merged_uc AS (
    SELECT
        arquivo_origem,
        num_uc,
        classificacao,
        MIN(dt_ini) AS dt_ini,
        MAX(dt_fim) AS dt_fim
    FROM periodo_id
    GROUP BY arquivo_origem, num_uc, classificacao, p_id
),
metricas_uc AS (
    SELECT
        m.*,
        ((m.dt_fim - m.dt_ini) * 24) AS chi_h,
        CASE
            WHEN ((m.dt_fim - m.dt_ini) * 1440) >= 3 THEN 'Longa'
            ELSE 'Curta'
        END AS tipo
    FROM merged_uc m
),
agregado_base AS (
    SELECT
        arquivo_origem,
        classificacao,
        COUNT(*) AS ci,
        SUM(chi_h) AS chi,
        SUM(CASE WHEN tipo = 'Longa' THEN 1 ELSE 0 END) AS ci_longa,
        SUM(CASE WHEN tipo = 'Longa' THEN chi_h ELSE 0 END) AS chi_longa_s
    FROM metricas_uc
    GROUP BY arquivo_origem, classificacao
),
resultado_regional AS (
    SELECT
        a.arquivo_origem,
        a.classificacao,
        a.ci,
        a.chi,
        a.ci_longa,
        a.chi_longa_s,
        d.uc_faturada AS mercado_faturado
    FROM agregado_base a
    LEFT JOIN divisor_oficial d ON d.arquivo_origem = a.arquivo_origem
    UNION ALL
    SELECT
        a.arquivo_origem,
        'Bruto' AS classificacao,
        SUM(a.ci),
        SUM(a.chi),
        SUM(a.ci_longa),
        SUM(a.chi_longa_s),
        MAX(d.uc_faturada)
    FROM agregado_base a
    LEFT JOIN divisor_oficial d ON d.arquivo_origem = a.arquivo_origem
    GROUP BY a.arquivo_origem
),
resultado_copel AS (
    SELECT
        'COPEL' AS arquivo_origem,
        r.classificacao,
        SUM(r.ci) AS ci,
        SUM(r.chi) AS chi,
        SUM(r.ci_longa) AS ci_longa,
        SUM(r.chi_longa_s) AS chi_longa_s,
        (SELECT total_faturado FROM divisor_total) AS mercado_faturado
    FROM resultado_regional r
    WHERE r.classificacao <> 'Bruto'
    GROUP BY r.classificacao
    UNION ALL
    SELECT
        'COPEL' AS arquivo_origem,
        'Bruto' AS classificacao,
        SUM(r.ci),
        SUM(r.chi),
        SUM(r.ci_longa),
        SUM(r.chi_longa_s),
        (SELECT total_faturado FROM divisor_total)
    FROM resultado_regional r
    WHERE r.classificacao <> 'Bruto'
    GROUP BY 'COPEL', 'Bruto'
)
SELECT
    :p_yyyymm AS yyyymm,
    t.arquivo_origem,
    t.classificacao,
    t.ci,
    t.chi,
    t.ci_longa,
    t.chi_longa_s,
    t.mercado_faturado,
    CASE WHEN t.mercado_faturado > 0 THEN t.ci_longa / t.mercado_faturado ELSE 0 END AS fec,
    CASE WHEN t.mercado_faturado > 0 THEN t.chi_longa_s / t.mercado_faturado ELSE 0 END AS dec
FROM (
    SELECT r.arquivo_origem, r.classificacao, r.ci, r.chi, r.ci_longa, r.chi_longa_s, r.mercado_faturado
    FROM resultado_regional r
    UNION ALL
    SELECT c.arquivo_origem, c.classificacao, c.ci, c.chi, c.ci_longa, c.chi_longa_s, c.mercado_faturado
    FROM resultado_copel c
) t
ORDER BY
    CASE t.arquivo_origem
        WHEN 'CSL' THEN 1
        WHEN 'LES' THEN 2
        WHEN 'NRO' THEN 3
        WHEN 'NRT' THEN 4
        WHEN 'OES' THEN 5
        WHEN 'COPEL' THEN 999
        ELSE 998
    END,
    CASE t.classificacao
        WHEN 'Liquido' THEN 1
        WHEN 'Expurgo' THEN 2
        WHEN 'Bruto' THEN 3
        ELSE 9
    END
