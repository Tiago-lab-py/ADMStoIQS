# Estilo de Paginas e Atributos de UX

## Objetivo
Padronizar experiencia visual e ergonomia para uso continuo pela operacao.

## Base visual
- Tema escuro default
- Layout `wide`
- Contraste alto para textos e tabelas
- Acento ciano para foco operacional

## Mapeamento semantico de cores
### Protocolo
- `0` Normal: verde (`#10b981`)
- `1` Dia Critico: amarelo (`#fbbf24`)
- `6` ISE: vermelho (`#ef4444`)

### Severidade
- Critica: vermelho
- Alta: laranja
- Media: amarelo
- Baixa: verde

## Componentes de interface
- Cards executivos com borda e gradiente suave
- Graficos com paleta semantica de negocio
- Tabelas com destaque por classe/severidade
- Download de tabela em CSV e Parquet

## Regras de consistencia
- Evitar uso arbitrario de cor fora do dicionario semantico.
- Sempre manter equivalencia entre legenda, card e grafico.
- Priorizar legibilidade em telas de baixa luminosidade.

## Referencias no codigo
- Tema e componentes: `biblioteca/ui.py`
- Config streamlit: `.streamlit/config.toml`
- Dashboard executivo: `app/pages/0_Dashboard_Executivo.py`
