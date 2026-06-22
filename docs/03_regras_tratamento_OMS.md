# Regras de Tratamento OMS

## Objetivo

Definir a sequência de páginas e as regras de tratamento operacional sobre o mart:

```text
data/mart/OMS_union.parquet
```

Este mart deve ser a fonte principal das telas de verificação, pois contém colunas de apoio como:

- `duracao`
- `erro_duracao`
- `duracao_longa`
- `REGIONAL_ORIGEM`
- `ANOMES_PROCESSAMENTO`

As regras desta etapa devem gerar sugestões auditáveis. A aplicação automática das correções deve acontecer apenas após registro em governança.

## Sequência de Páginas

1. **Dashboard**
   - Resumo por competência.
   - Total de registros.
   - Total por regional.
   - Quantidade de pendências por tipo.

2. **Horário Negativo**
   - Registros com `erro_duracao = true`.
   - Sugestão de ajuste de fuso horário quando o erro estiver entre 0 e 3 horas.

3. **Sobreposição de Interrupção**
   - Sobreposição temporal por equipamento/interrupção.
   - Agrupamento por `ALIM_INTRP_PIN` e `NUM_OPER_CHV_INTRP`.
   - Avaliação por `DATA_HORA_INIC_INTRP` e `DATA_HORA_FIM_INTRP`.

4. **Sobreposição de UC**
   - Sobreposição temporal da mesma UC.
   - Agrupamento por `NUM_UC_UCI` e `NUM_POSTO_UCI`.
   - Avaliação por `DTHR_INICIO_INTRP_UC` e `DATA_HORA_FIM_INTRP`.

5. **Sem Causa ou Componente**
   - Registros sem `COD_CAUSA_INTRP`.
   - Registros sem `COD_COMP_INTRP`.
   - Sugestão posterior de causa/componente com base na ocorrência.

6. **Solicitação de Alteração**
   - Tela de revisão da sugestão.
   - Registro da alteração em `log_alteracoes.parquet`.
   - Associação nominal ao usuário autenticado, IP e user-agent.

## Regra 1 — Horário Negativo

### Detecção

Registro com:

```text
erro_duracao = true
```

Ou:

```text
DATA_HORA_FIM_INTRP < DATA_HORA_INIC_INTRP
```

### Sugestão

Quando a diferença negativa absoluta estiver entre `0` e `3` horas:

```text
0 < abs(duracao) <= 180 minutos
```

Sugerir alteração de `DATA_HORA_FIM_INTRP`, acrescentando `3` horas ao horário fim original, por provável problema de fuso horário.

Campo sugerido:

```text
DATA_HORA_FIM_INTRP
```

Ação sugerida:

```text
fim_sugerido = DATA_HORA_FIM_INTRP + 3 horas
```

Quando a diferença negativa for maior que 3 horas, sugerir revisão manual.

## Regra 2 — Sobreposição Temporal de Interrupção

### Agrupamento

Avaliar sobreposição temporal para registros com mesmo:

```text
ALIM_INTRP_PIN
NUM_OPER_CHV_INTRP
```

Intervalo:

```text
DATA_HORA_INIC_INTRP
DATA_HORA_FIM_INTRP
```

### Ordenação

Quando houver sobreposição, considerar como primeira interrupção o registro com menor:

```text
NUM_SEQ_INTRP
```

### Sugestão para Interrupção Longa

Se a segunda interrupção tiver:

```text
duracao_longa = true
```

Sugerir deslocar o início da segunda interrupção para o término da primeira.

Campo sugerido:

```text
DATA_HORA_INIC_INTRP
```

Valor sugerido:

```text
DATA_HORA_FIM_INTRP da primeira interrupção
```

Também sugerir popular:

```text
NUM_INTRP_INIC_MANOBRA_UCI
```

Com o número da primeira interrupção:

```text
NUM_INTRP_UCI da primeira interrupção
```

### Sugestão para Interrupção Curta

Se a segunda interrupção tiver:

```text
duracao_longa = false
```

Sugerir exclusão/tratamento diferenciado:

```text
NUM_MOTIVO_TRAT_DIF_UCI = 91
```

## Regra 3 — Sobreposição Temporal da Mesma UC

### Agrupamento

Avaliar sobreposição temporal para mesma UC:

```text
NUM_UC_UCI
NUM_POSTO_UCI
```

Intervalo:

```text
DTHR_INICIO_INTRP_UC
DATA_HORA_FIM_INTRP
```

### Sugestão

Aplicar a mesma lógica operacional da sobreposição de interrupção:

- Para evento longo, sugerir deslocamento do início do segundo evento.
- Para evento curto, sugerir tratamento diferenciado com `NUM_MOTIVO_TRAT_DIF_UCI = 91`.
- Quando houver deslocamento, preencher `NUM_INTRP_INIC_MANOBRA_UCI` com a interrupção de origem.

## Regra 4 — Registros Sem Componente ou Causa

### Detecção

Registros com:

```text
COD_CAUSA_INTRP vazio ou nulo
COD_COMP_INTRP vazio ou nulo
```

### Sugestão

Nesta etapa, os registros devem ser apresentados para revisão.

A sugestão de causa ou componente deve ser implementada posteriormente, usando como base:

- `NUM_OCORRENCIA_ADMS`
- `DESC_INTRP`
- `TIPO_EQP_INTRP`
- `NUM_OPER_CHV_INTRP`
- Histórico de registros similares já corrigidos.

## Governança

Toda sugestão enviada para alteração deve registrar:

- Usuário autenticado.
- Perfil do usuário.
- IP de origem.
- User-agent.
- Competência.
- Chave do registro.
- Campo alterado.
- Valor anterior.
- Valor sugerido.
- Justificativa.
- Status da alteração.

Arquivo de auditoria:

```text
data/logs/log_alteracoes.parquet
```

