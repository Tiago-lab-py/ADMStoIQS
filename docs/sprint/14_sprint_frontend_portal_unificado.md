# Sprint 14 — Portal unificado e governança visual

## Objetivo

Evoluir o frontend enquanto os processos pesados de parquet rodam no backend, sem alterar a lógica de dados já em processamento.

## Decisões

- `gestor.html` será a tela inicial para todos os usuários.
- `operacional.html` permanece como tela especializada para ETL, apuração e ações operacionais.
- As antigas frentes de `Sobreposição interrupção` e `Sobreposição UC` serão apresentadas como uma única jornada chamada `Sobreposição`.
- Módulos ainda não concluídos ficam visíveis, mas marcados como `Em desenvolvimento`.

## Módulos visíveis em desenvolvimento

- Administração de usuários e perfis.
- Causa/componente.
- Janela ISE.
- Dia crítico.

## Entregas desta etapa

- Criar flags de frontend para módulos ativos e em desenvolvimento.
- Incluir aba `Sobreposição` no portal gestor.
- Incluir aba `Administração` como casca governada.
- Preservar a tela operacional existente sem alterar scripts ou parquets.

## Critério de aceite

- O portal gestor abre sem depender de novo backend.
- A navegação para `operacional.html` continua disponível.
- Módulos futuros aparecem claramente como em desenvolvimento.
- Nenhuma rotina de ETL, tratamento massivo, indicador ou exportação é disparada automaticamente.
