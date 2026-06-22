# Objetivo do Programa (V4)

## Base da especificacao
Este documento resume o topico **Objetivos do projeto** e as linhas gerais da especificacao V4 em:
- governanca de dados,
- ciberseguranca,
- auditoria corporativa.

Referencia principal: `especificacao/especificacao.md` (versao consolidada V4 de 23/05/2026).

## Objetivos centrais do programa
1. Controlar dias anomalos por conjunto eletrico com base em historico 2024/2025.
2. Avaliar ocorrencias de protocolo `0` quando coexistirem com protocolo `1` (Dia Critico) ou `6` (ISE), com foco em expurgo correto.
3. Agrupar interrupcoes para evitar dupla contagem operacional.
4. Calcular pre-analise de dia critico com regra estatistica (`media + 3*desvio`).
5. Comparar comportamento de ISE contra historico por conjunto, causa, componente, equipamento e duracao.
6. Detectar anomalias de impacto (`CI`, `CHI`, duracao) com apoio de z-score e distancia.
7. Permitir validacao de pos-operacao (validar, alterar, cancelar, pendente, efetivacao).
8. Registrar trilha completa de decisao tecnica e comparador antes/depois.

## Linhas gerais de governanca de dados
- Separacao obrigatoria de camadas: `RAW`, `PROCESSED`, `MART`, `SNAPSHOTS`, `VALIDACOES`.
- Imutabilidade da camada `RAW` (sem alteracao direta de dado original).
- Rastreabilidade de alteracoes com usuario, data/hora, valor original, valor proposto e status.
- Snapshot diario para detectar alteracoes retroativas.
- Retencao historica e versionamento de regras operacionais.
- Segregacao entre dado de origem e dado proposto pela operacao.

## Linhas gerais de ciberseguranca
- Controle de acesso por perfil (RBAC): usuario, admin, gestor/auditor, fiscalizacao, desenvolvedor.
- Registro de login/logout, tentativas invalidas, sessao e trilha de uso.
- Segregacao de ambientes (homologacao/producao).
- Credenciais fora do codigo e preferencia por cofre corporativo.
- Senhas e chaves sensiveis sem armazenamento em texto claro.
- Menor privilegio para contas tecnicas de integracao.

## Linhas gerais de auditoria
- Auditoria operacional de alteracoes entre snapshots.
- Trilha imutavel de acoes de usuarios e automatismos.
- Relatorios de produtividade, efetividade e eficiencia das alteracoes.
- Comparacao `Original x Proposto x Efetivado` por registro.
- Evidencia de impacto em indicadores regulatórios (ex.: CI/CHI, DEC/FEC).

## Resultado esperado do programa
Disponibilizar uma plataforma corporativa de pos-operacao com confiabilidade tecnica, governanca de dados, seguranca operacional e auditoria ponta-a-ponta para decisao regulatoria e fiscalizacao.

