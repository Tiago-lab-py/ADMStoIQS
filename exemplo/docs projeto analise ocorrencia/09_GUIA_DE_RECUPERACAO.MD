# Guia de Recuperacao

## Objetivo
Padronizar a recuperacao rapida em incidentes operacionais.

## Cenarios e acao

### 1) ETL falhou
1. Verificar log em `logs/etl.log`.
2. Corrigir causa raiz (dados ausentes, formato invalido, permissao).
3. Reexecutar ETL com a mesma competencia.

### 2) Dados processados inconsistentes
1. Substituir arquivos de entrada em `dados/raw/amostras/`.
2. Remover apenas artefatos processados afetados (`processed`/`mart`).
3. Rodar ETL novamente.

### 3) Problema de permissao por perfil
1. Acessar Admin com perfil `admin`/`desenvolvedor`.
2. Revisar matriz em `config/perfis.yml`.
3. Ajustar funcionalidades e salvar.

### 4) Usuario sem acesso (senha/perfil)
1. Abrir aba Admin > Usuarios.
2. Resetar senha ou ajustar perfil.
3. Validar novo login.

### 5) Falha de import legado
1. Executar `python etl/00_import_legacy_samples.py --overwrite --limit-rows 120000`.
2. Verificar linhas carregadas no retorno do script.
3. Reprocessar com ETL diario.

## Boas praticas
- Nunca alterar camada `raw` manualmente sem backup.
- Evitar apagar snapshots sem criterio de retencao.
- Sempre registrar incidente e resolucao em log tecnico.
