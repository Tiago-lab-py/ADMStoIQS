# Plano de Testes

## 1. Escopo
Validar integridade funcional da plataforma nas dimensoes:
- ETL
- regras de negocio
- interface
- seguranca de acesso
- governanca operacional

## 2. Testes ETL
### 2.1 Execucao base
- Comando: `python run_etl_diario.py --mode sample --competencia YYYY-MM`
- Esperado: retorno `ETL finalizado com sucesso`.

### 2.2 Artefatos gerados
Validar existencia de:
- `dados/processed/interrupcao_tratada.parquet`
- marts em `dados/mart/*.parquet`
- snapshot em `dados/snapshots/`

### 2.3 Regras de qualidade
Validar flags:
- `dq_crit_002_dt_fim_menor_dt_ini`
- `flag_duracao_menor_3m`
- `dq_crit_007_sobreposicao_ocorrencia`

## 3. Testes de negocio
- Dias anomalos: verificar limite `media + 3*desvio`.
- ISE: verificar score de anomalia por z-score.
- Mistura de protocolo: identificar `0` coexistindo com `1/6`.
- CHI elevado: validar flag de revisao obrigatoria.

## 4. Testes de interface
- Navegacao por todas as paginas.
- Layout wide ativo.
- Tema escuro consistente.
- Downloads CSV/Parquet funcionando.

## 5. Testes de seguranca e acesso
- Login com credenciais validas/invalidas.
- Bloqueio por falta de permissao de funcionalidade.
- Admin acessivel apenas para perfis autorizados.

## 6. Testes de administracao
- Criar/editar usuario.
- Alterar perfil e funcionalidades.
- Salvar configuracao de app/etl.
- Executar ETL manual pela aba Admin.

## 7. Criticidade
- P0: falha de ETL, acesso indevido, corrompimento de dados.
- P1: regra de negocio inconsistente, dashboard incorreto.
- P2: problema visual sem impacto de dado.
