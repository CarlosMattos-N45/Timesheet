# TimeSheet Terceiros — Web

Frontend SPA do TimeSheet Terceiros: React 18 + TypeScript + Vite + Material UI v5.

## Pré-requisitos

- Node.js >= 20
- npm >= 10

## Instalação

```bash
npm install
```

## Desenvolvimento

```bash
npm run dev
```

Abre em `http://127.0.0.1:5173/`. Requisições para `/api` são proxiadas para `http://127.0.0.1:8765`.

## Testes

```bash
npm test
```

Modo watch (CI):

```bash
npm test -- --run
```

## Build de Produção

```bash
npm run build
```

Gera `dist/` com `index.html` e assets.

## Lint e Typecheck

```bash
npm run lint
npm run typecheck
```

## Formatação

```bash
npm run format
npm run format:check
```
