# Frontend ADMStoIQS

Frontend React para acesso autenticado, consulta dos Parquets processados, amostra operacional e geração do CSV oficial.

## Perfis de Desenvolvimento

| Usuário | Senha | Perfil |
|---|---|---|
| `admin` | `admin123` | `admin` |
| `gestor` | `gestor123` | `gestor` |
| `usuario` | `usuario123` | `usuario` |

O perfil `usuario` consulta dados e solicita alteração. Os perfis `gestor` e `admin` também podem exportar CSV.

## Node.js Local

O projeto deve usar o Node.js disponível no repositório:

```text
tools/nodejs
```

Executáveis esperados:

```text
tools/nodejs/node.exe
tools/nodejs/npm.cmd
tools/nodejs/npx.cmd
```

## Comandos Previstos

Quando a Sprint 3 for implementada, os comandos devem preferir o Node local:

```text
install.cmd
dev.cmd
build.cmd
```

Os comandos devem ser executados a partir da pasta `frontend`.

Os scripts `.cmd` adicionam `tools/nodejs` ao `PATH` da sessão antes de chamar o `npm`, permitindo que dependências como `esbuild` encontrem `node.exe` durante a instalação.

## URL Local

```text
http://127.0.0.1:5173
```
