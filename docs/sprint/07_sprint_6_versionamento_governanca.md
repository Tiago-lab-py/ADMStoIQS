# Sprint 6 — Versionamento, segurança e governança de desenvolvimento

## 1. Objetivo

Colocar o ADMStoIQS sob versionamento seguro, com processo de desenvolvimento controlado e proteção contra publicação acidental de dados sensíveis.

## 2. Documento base

```text
docs/15_versionamento_github.md
```

## 3. Escopo

### 3.1 GitHub

- Criar repositório privado.
- Configurar `.gitignore`.
- Fazer commit inicial.
- Criar branches `main` e `develop`.
- Criar branch da próxima sprint.

### 3.2 Segurança

- Garantir que `data/` não seja versionado.
- Garantir que `.venv/` não seja versionado.
- Garantir que `node_modules/` não seja versionado.
- Garantir que CSV/Parquet não sejam versionados.
- Criar `.env.example` sem segredo.

### 3.3 Governança de desenvolvimento

- Definir padrão de commits.
- Definir uso de pull request.
- Definir proteção da branch `main`.
- Definir checklist antes de merge.

## 4. Fora de escopo

Não faz parte desta sprint:

- publicar dados;
- configurar deploy;
- hospedar aplicação;
- criar pipeline CI/CD completo;
- criar banco corporativo.

## 5. Entregáveis

- `.gitignore` revisado.
- `README.md` atualizado.
- Repositório remoto criado.
- Primeiro commit seguro.
- Branch `develop`.
- Branch da próxima sprint.
- Checklist de PR.

## 6. Checklist pré-commit

- [ ] `git status` não mostra `data/`.
- [ ] `git status` não mostra `.venv/`.
- [ ] `git status` não mostra `node_modules/`.
- [ ] `git status` não mostra `*.parquet`.
- [ ] `git status` não mostra `*.csv`.
- [ ] Não há senha ou token em arquivos.
- [ ] Documentação principal está atualizada.
- [ ] Scripts rodam localmente.

## 7. Critérios de aceite

- Código e documentação estão no GitHub.
- Dados locais não foram publicados.
- Histórico inicial está preservado.
- Há procedimento claro para próximas sprints.
- O projeto pode ser recuperado em outra máquina sem carregar dados sensíveis.

## 8. Comandos sugeridos

```cmd
git init
git status
git add .gitignore README.md backend frontend docs
git commit -m "chore: estrutura inicial do ADMStoIQS"
git branch -M main
git remote add origin https://github.com/ORGANIZACAO/ADMStoIQS.git
git push -u origin main
git checkout -b develop
git push -u origin develop
```

## 9. Decisão pendente

Definir destino:

```text
GitHub privado
GitHub Enterprise
Azure DevOps corporativo
```

A recomendação é usar ambiente corporativo ou repositório privado, por envolver regras e caminhos operacionais internos.

