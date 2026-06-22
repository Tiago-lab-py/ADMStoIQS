# Versionamento GitHub — ADMStoIQS

## 1. Objetivo

Garantir segurança no desenvolvimento, histórico de alterações e capacidade de recuperação do projeto ADMStoIQS.

O GitHub deve versionar código, documentação e contratos, mas nunca dados operacionais sensíveis.

## 2. O que deve ir para o GitHub

Versionar:

```text
backend/
frontend/
docs/
tools/README ou instruções
README.md
.gitignore
requirements.txt
package.json
package-lock.json
```

Também versionar:

- scripts de processamento;
- contratos de colunas;
- documentação de sprints;
- documentação de regras;
- templates de configuração sem segredo.

## 3. O que não deve ir para o GitHub

Não versionar:

```text
data/
data/external/
*.parquet
*.csv
*.duckdb
*.db
.venv/
node_modules/
logs operacionais
exports gerados
arquivos com senha/token
.env
```

Motivo:

- dados ADMS/IQS podem conter informação operacional sensível;
- parquets podem ter dezenas de GB;
- logs podem conter caminhos internos, usuário, máquina e IP.

## 4. `.gitignore` recomendado

```gitignore
# Ambientes
.venv/
venv/
__pycache__/
*.pyc

# Frontend
node_modules/
frontend/node_modules/
frontend/dist/

# Dados locais
data/
*.parquet
*.duckdb
*.db
*.csv

# Logs e temporários
*.log
.tmp/
tmp/
data/raw_temp/

# Segredos
.env
.env.*
!.env.example

# Dados externos IQS
data/external/

# IDE
.vscode/
!.vscode/extensions.json
!.vscode/settings.example.json
```

## 5. Estratégia de repositório

Recomendação:

- repositório privado;
- nome sugerido: `ADMStoIQS`;
- branch principal: `main`;
- branch de desenvolvimento: `develop`;
- branches por sprint:

```text
feature/sprint-4-design-system
feature/sprint-5-pendencias-regulatorio
feature/sprint-6-governanca-exportacao
```

## 6. Fluxo de trabalho

Fluxo simples e seguro:

```text
main
  ↑ pull request aprovado
develop
  ↑ merge de sprint
feature/sprint-x
```

Regras:

- não desenvolver direto na `main`;
- cada sprint em uma branch;
- abrir pull request;
- revisar diff antes de merge;
- não commitar dados.

## 7. Commits recomendados

Padrão:

```text
docs: atualiza proposta de middleware
feat: adiciona materialização de pendências
fix: corrige contagem de horário negativo
refactor: organiza componentes do frontend
chore: atualiza gitignore
test: adiciona validação de contratos
```

## 8. Primeiro push sugerido

Antes do primeiro push:

1. Conferir `.gitignore`.
2. Conferir se `data/` não aparece no Git.
3. Conferir se `.venv/` não aparece.
4. Conferir se `node_modules/` não aparece.
5. Conferir se não há senha/token em arquivos.

Comandos sugeridos:

```cmd
git init
git status
git add .gitignore README.md backend frontend docs
git status
git commit -m "chore: estrutura inicial do ADMStoIQS"
git branch -M main
git remote add origin https://github.com/ORGANIZACAO/ADMStoIQS.git
git push -u origin main
```

## 9. Cuidados antes de subir

Executar:

```cmd
git status --short
```

Não pode aparecer:

```text
data/
.venv/
node_modules/
*.parquet
*.csv
```

Se aparecer, corrigir `.gitignore` antes do commit.

## 10. Recomendação de segurança

Usar repositório privado.

Se houver política corporativa:

- preferir GitHub Enterprise ou Azure DevOps interno;
- evitar repositório pessoal se houver dado ou regra interna sensível;
- confirmar com governança/segurança antes de publicar fora do ambiente corporativo.

## 11. Checklist GitHub

- [ ] Definir se será GitHub privado, GitHub Enterprise ou Azure DevOps.
- [ ] Criar repositório vazio.
- [ ] Validar `.gitignore`.
- [ ] Remover qualquer dado sensível do controle de versão.
- [ ] Fazer commit inicial.
- [ ] Subir branch `main`.
- [ ] Criar branch `develop`.
- [ ] Abrir branch da próxima sprint.
- [ ] Proteger branch `main`.
- [ ] Exigir pull request para merge.
