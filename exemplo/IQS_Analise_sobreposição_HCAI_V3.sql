-- Parametro: :p_yyyymm ex.: '202604'
WITH uc_consideradAS AS
  (SELECT DISTINCT TRIM(TO_CHAR(h.NUM_UC_HCAI)) AS num_uc
   FROM iqs.HIST_CONS_AFETADO_INTERRUPCAO h
   WHERE h.INDIC_FAT_HCAI = 'S'
     AND TO_CHAR(h.DATA_INTRP_HCAI, 'YYYYMM') = :p_yyyymm),
     base AS
  (SELECT NVL(rd.SIGLA_RDIS, 'COPEL') AS arquivo_origem,
          TRIM(TO_CHAR(h.NUM_UC_HCAI)) AS num_uc,
          TRIM(TO_CHAR(h.NUM_POSTO_HCAI)) AS num_posto,
          CAST(h.DATA_INTRP_HCAI AS DATE) AS dt_ini,
          CAST(i.DATA_HORA_FIM_INTRP AS DATE) AS dt_fim,
          NVL(NULLIF(TRIM(TO_CHAR(h.NUM_INTRP_INIC_MANOBRA_HCAI)), ''), TRIM(TO_CHAR(h.NUM_INTRP_HCAI))) AS num_intrp_key,
          TRIM(NVL(TO_CHAR(h.TIPO_PROTOC_JUSTIF_HCAI),
             NVL(TO_CHAR(i.TIPO_PROTOC_JUSTIF_INTRP), '0'))) AS prot_hcai,
          TRIM(TO_CHAR(h.NUM_MOTIVO_TRAT_DIF_HCAI)) AS num_motivo_trat_dif_hcai
   FROM iqs.HIST_CONS_AFETADO_INTERRUPCAO h
   LEFT JOIN sod.INTERRUPCAO i ON i.NUM_SEQ_INTRP = h.NUM_INTRP_HCAI
   LEFT JOIN cis.UC_ENERGIA uce ON uce.ISN_UC = h.NUM_UC_HCAI
   LEFT JOIN cis.LOCALIDADE l ON l.COD_LOCAL = uce.COD_LOCAL_UC
   LEFT JOIN cis.seccional_distribuicao sc ON l.COD_SECCION_DISTR_LOCAL = sc.COD_SDIS
   LEFT JOIN cis.REGIONAL_DISTRIBUICAO rd ON sc.COD_REG_DISTR_SDIS = rd.COD_RDIS
   JOIN uc_consideradAS uc ON uc.num_uc = TRIM(TO_CHAR(h.NUM_UC_HCAI))
   WHERE TO_CHAR(h.DATA_INTRP_HCAI, 'YYYYMM') = :p_yyyymm),
     classificada AS
  (SELECT b.*,
          CASE
              WHEN b.num_motivo_trat_dif_hcai IS NOT NULL
                   AND b.num_motivo_trat_dif_hcai NOT IN ('',
                                                          '0') THEN 'Ignorar'
              WHEN b.prot_hcai = '0'
                    THEN 'Liquido'
              ELSE 'Expurgo'
          END AS classificacao
   FROM base b),
     filtrada AS
  (SELECT *
   FROM classificada
   WHERE classificacao IN ('Expurgo',
                           'Liquido')),
     dedupe AS
  (SELECT f.*,
          ROW_NUMBER() OVER (PARTITION BY f.num_intrp_key, f.num_posto, f.num_uc
                             ORDER BY f.dt_fim DESC NULLS LAST) AS rn_key
   FROM filtrada f),
     validos AS
  (SELECT *
   FROM dedupe
   WHERE rn_key = 1
     AND dt_ini IS NOT NULL
     AND dt_fim IS NOT NULL
     AND dt_fim >= dt_ini),
     ordenados AS
  (SELECT v.*,
          MAX(v.dt_fim) OVER (PARTITION BY v.arquivo_origem, v.num_uc
                              ORDER BY v.dt_ini ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS max_fim_ate_agora
   FROM validos v),
     identifica_novo AS
  (SELECT o.*,
          LAG(o.max_fim_ate_agora) OVER (PARTITION BY o.arquivo_origem, o.num_uc
                                         ORDER BY o.dt_ini) AS fim_anterior
   FROM ordenados o),
     periodo_marcado AS
  (SELECT i.*,
          CASE
              WHEN i.fim_anteriOR IS NULL
                   OR i.dt_ini > i.fim_anteriOR + (1 / 1440) THEN 1
              ELSE 0
          END AS is_novo
   FROM identifica_novo i),
     periodo_id AS
  (SELECT p.*,
          SUM(p.is_novo) OVER (PARTITION BY p.arquivo_origem, p.num_uc
                               ORDER BY p.dt_ini ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS p_id
   FROM periodo_marcado p),
     eventos_formados AS
  (SELECT ROW_NUMBER() OVER (
                             ORDER BY arquivo_origem, num_uc, MIN(dt_ini)) AS id,
          arquivo_origem,
          num_uc AS uc,
          MIN(num_intrp_key) KEEP (DENSE_RANK FIRST
                                   ORDER BY dt_ini, dt_fim) AS interrupcao_inicial,
          MIN(dt_ini) AS data_inicio,
          MAX(dt_fim) AS data_fim,
          CASE
              WHEN SUM(CASE
                           WHEN classificacao = 'Expurgo' THEN 1
                           ELSE 0
                       END) > 0 THEN 'Expurgo'
              ELSE 'Liquido'
          END AS classificacao,
          MIN(CASE
                  WHEN prot_hcai <> '0' THEN prot_hcai
                  ELSE '0'
              END) KEEP (DENSE_RANK FIRST
                         ORDER BY dt_ini, dt_fim) AS tipo_protocolo,
          LISTAGG(DISTINCT CASE
                               WHEN prot_hcai <> '0' THEN prot_hcai
                               ELSE '0'
                           END, '|') WITHIN GROUP (
                                                   ORDER BY CASE
                                                                WHEN prot_hcai <> '0' THEN prot_hcai
                                                                ELSE '0'
                                                            END) AS tipo_protocolo_agrupados,
                                                  LISTAGG(DISTINCT num_intrp_key, '|') WITHIN GROUP (
                                                                                                     ORDER BY num_intrp_key) AS interrupcao_agrupadas,
                                                                                                    COUNT(*) AS qtde_registros_agrupados,
                                                                                                    ROUND((MAX(dt_fim)-MIN(dt_ini))* 1440, 4) AS duracao_minutos,
                                                                                                    ROUND((MAX(dt_fim)-MIN(dt_ini))* 24, 6) AS chi_h,
                                                                                                    CASE
                                                                                                        WHEN ((MAX(dt_fim)-MIN(dt_ini))* 1440) >= 3 THEN 'Longa'
                                                                                                        ELSE 'Curta'
                                                                                                    END AS tipo
   FROM periodo_id
   GROUP BY arquivo_origem,
            num_uc,
            p_id)
SELECT id,
       arquivo_origem,
       uc,
       interrupcao_inicial,
       data_inicio,
       data_fim,
       classificacao,
       tipo_protocolo,
       tipo_protocolo_agrupados,
       interrupcao_agrupadas,
       qtde_registros_agrupados,
       duracao_minutos,
       chi_h,
       tipo
FROM eventos_formados
ORDER BY arquivo_origem,
         uc,
         data_inicio;
