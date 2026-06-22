# Resumo materializado do Dashboard

## Decisão

Os cards do Dashboard não devem ser calculados na abertura da tela.

Para o volume atual de dados, o cálculo dinâmico de indicadores como
sobreposição temporal por equipamento pode ser pesado e instável. A regra
passa a ser:

1. calcular os indicadores durante a preparação da apuração;
2. salvar uma fotografia pequena de resumo;
3. fazer o Dashboard ler apenas essa fotografia.

Ao clicar em **Atualizar** no Dashboard, a API deve materializar novamente o
resumo da apuração atual antes de devolver os cards. Assim, o botão atualiza
tanto a visualização quanto os arquivos físicos dos indicadores.

## Arquivos

Para cada mês de apuração:

- `data/mart/apuracao/resumo_APURACAO_[anomes].parquet`;
- `data/mart/apuracao/resumo_APURACAO_ATUAL.parquet`.

## Indicadores mínimos

O resumo materializado deve conter:

- `anomes`;
- `total_registros`;
- `pendencias_totais`;
- `horario_negativo`;
- `sobreposicao_interrupcao`;
- `sobreposicao_uc`;
- `sem_causa_componente`;
- `rejeitados`;
- `validado`;
- `gerado_em`.

## Rejeitados por atividade

Quando existir `log_alteracoes.parquet`, o Dashboard também pode exibir
`rejeitados_por_atividade`, consolidando registros rejeitados por motivo ou
atividade.

## Benefícios

- Dashboard rápido.
- Indicadores reproduzíveis.
- Menor risco de timeout.
- Separação clara entre preparação de dados e análise visual.
