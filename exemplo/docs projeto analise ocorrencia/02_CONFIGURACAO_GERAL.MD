# Configuracao Geral

## Requisitos
- Python 3.11+
- Pip atualizado
- Ambiente Windows ou Linux com permissao de escrita no projeto

## Instalacao
```bash
pip install -r requirements.txt
```

## Variaveis de ambiente
1. Copiar `.env.example` para `.env`.
2. Ajustar os parametros de execucao.

Variaveis principais:
- `ETL_MODE`: `sample` ou `db`
- `DB_URL`: conexao SQLAlchemy (obrigatoria em `db`)
- `SNAPSHOT_RETENTION_DAYS`: retencao de snapshots

## Arquivos de configuracao de operacao
- `config/app_config.yml`: parametros funcionais e ETL
- `config/perfis.yml`: matriz de funcionalidades por perfil
- `config/usuarios.yml`: usuarios, perfis e hash de senha

## Carga de dados para desenvolvimento local
Opcao A - CSV remoto:
1. Executar SQL no ambiente corporativo
2. Exportar CSV
3. Salvar em `dados/raw/amostras/`

Opcao B - Reaproveitar legado:
```bash
python etl/00_import_legacy_samples.py --overwrite --limit-rows 200000
```

## Execucao ETL
```bash
python run_etl_diario.py --mode sample --competencia 2026-05
```

## Execucao da aplicacao
```bash
streamlit run app/Home.py
```

## Login inicial
- `admin@empresa.com`
- `pos@empresa.com`
- `gestor@empresa.com`
- `tiago.aquino@copel.com`

Senha inicial padrao: `123456`

## Perfis
- `admin`: acesso total
- `desenvolvedor`: acesso total
- `usuario`: acesso operacional
- `gestor`: acesso de acompanhamento e auditoria
