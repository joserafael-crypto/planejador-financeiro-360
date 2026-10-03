# Planejador Financeiro 360° — V2.4 Full Stack

## Arquitetura

- Frontend: HTML/JS, pronto para migração para React.
- Backend: FastAPI.
- Banco: PostgreSQL.
- Segurança: bcrypt, JWT de curta duração, refresh tokens rotativos/revogáveis, MFA/TOTP, sessões, auditoria, headers de segurança e CORS restritivo.
- IA: chamada exclusivamente pelo backend; chave nunca vai para o navegador.
- Financeiro: contas, cartões, transações, recorrências e parcelas modeladas; endpoints iniciais de contas/transações/metas/dívidas.
- Inteligência: endpoint de IA com contexto financeiro do usuário.
- Futuro: camada de Open Finance pode ser adicionada como serviço/adaptador.

## Executar

Requer Docker Desktop.

```bash
docker compose up --build
```

Frontend: http://localhost:5173  
API: http://localhost:8000  
Health: http://localhost:8000/health

## Produção — antes de dados reais

1. Trocar JWT_SECRET e credenciais PostgreSQL.
2. Usar HTTPS.
3. Migrar criação automática de tabelas para Alembic.
4. Habilitar MFA/TOTP no fluxo completo.
5. Adicionar rate limiting, CSRF quando aplicável, headers de segurança e rotação de tokens.
6. Criptografar dados sensíveis em repouso e proteger backups.
7. Implementar LGPD: consentimento/base legal, finalidade, minimização, exportação, correção e exclusão.
8. Integrar Open Finance somente por instituição/provedor autorizado e com consentimento explícito.
9. Adicionar fila para tarefas recorrentes, alertas e processamento de importações.
10. Adicionar testes unitários, integração e E2E.

## Modelo de evolução

- V2.1: faturas/cartões completos + recorrências + parcelas + transferências.
- V2.2: orçamento, alertas e dashboard avançado.
- V2.3: MFA completo, sessões/revogação, auditoria e controles LGPD (consentimentos, exportação, atualização e exclusão).
- V2.4: IA com ferramentas de projeção/simulação.
- V3: Open Finance via adaptador de provedor.

## V2.1 — Motor financeiro funcional

A V2.1 transforma os modelos iniciais em fluxos operacionais:

- **Cartões:** cadastro, limite, fechamento e vencimento.
- **Faturas:** geração por competência, totalização de compras, pagamento parcial/total e atualização de status.
- **Parcelas:** criação do plano, divisão com ajuste de centavos, agenda das parcelas e marcação de pagamento.
- **Recorrências:** cadastro por frequência e lançamento operacional da próxima ocorrência.
- **Transferências:** movimentação entre contas com validação de propriedade e saldo.
- **Orçamentos:** limite por categoria/mês, cálculo de gasto, percentual utilizado e saldo restante.
- **Alertas:** alertas de orçamento e faturas vencidas, com atualização sob demanda.
- **Contas:** saldo inicial e atualização por lançamentos/transferências/pagamentos.
- **Segurança de dados:** endpoints financeiros sempre filtrados pelo usuário autenticado e validação de propriedade das contas/cartões.

## Estado atual

Esta versão é uma base Full Stack funcional com agente financeiro controlado para evolução do Planejador Financeiro 360°. Ela já separa frontend, API e PostgreSQL e mantém a chave da IA exclusivamente no backend.

Antes de utilizar dados financeiros reais, os itens da seção **Produção — antes de dados reais** devem ser implementados e validados.

## Estrutura

```text
planejador_financeiro_360_v2/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── index.html
├── infra/
├── .env.example
├── docker-compose.yml
└── README.md
```


## Observação sobre migração da V2 para V2.1

A V2.1 usa uma migration inicial (`backend/alembic/versions/0001_v21_finance_engine.py`) e executa `alembic upgrade head` antes de iniciar a API no Docker. Para uma instalação que já possua dados reais da V2 anterior, faça backup e valide a migração em ambiente separado antes de aplicar em produção.

## Fluxo financeiro principal

**Conta → Lançamento → Saldo**

**Cartão → Compra → Fatura → Pagamento**

**Compra parcelada → Plano → Parcelas → Faturas futuras**

**Recorrência → Próximo lançamento → Atualização da próxima ocorrência**

**Conta A → Transferência → Conta B**

**Categoria → Orçamento mensal → Percentual de uso → Alerta**


# V2.2 — Inteligência Financeira

A V2.2 preserva o motor financeiro da V2.1 e adiciona uma camada de inteligência operacional baseada nos dados do próprio usuário.

## Dashboard avançado

- saldo consolidado em contas
- receita, despesa e resultado do mês
- faturas em aberto
- saldo de dívidas
- histórico de seis meses
- alertas pendentes
- visão da saúde financeira

## Orçamento inteligente

O endpoint `/api/intelligence/budget-smart` analisa os gastos dos três meses anteriores e sugere limites por categoria com margem de 5% sobre a média histórica. A sugestão não altera o orçamento automaticamente.

## Alertas automáticos

O dashboard atualiza alertas derivados dos dados cadastrados:

- orçamento próximo ou acima do limite
- fatura vencida
- projeção de caixa negativa

## Projeção de fluxo de caixa

`GET /api/intelligence/cashflow-projection?months=6`

Projeta até 24 meses usando a média histórica e recorrências mensais cadastradas. A metodologia fica explícita na resposta.

## Metas

- criação de metas
- progresso percentual
- contribuição incremental
- acompanhamento no dashboard

## Saúde financeira

`GET /api/intelligence/health`

Gera um indicador de 0 a 100 com componentes separados para:

- reserva
- fluxo de caixa
- dívidas
- orçamento
- metas

O indicador é explicável e não substitui aconselhamento financeiro profissional.

## Simulador de decisões

`POST /api/intelligence/simulate`

Permite testar:

- aumento/redução mensal de receitas
- aumento/redução mensal de despesas
- impacto financeiro inicial
- taxa anual estimada
- horizonte de até 120 meses

A simulação é independente dos dados reais e não altera o banco.

# Próximas versões

## V2.3 — Segurança, privacidade e controle de sessão

Implementada nesta versão:
- MFA/TOTP com enrollment, confirmação e desativação
- access tokens curtos e refresh tokens opacos com rotação e revogação
- sessões persistentes, consulta e revogação individual ou global
- auditoria com ação, usuário, IP, user-agent e data/hora
- headers de segurança e CORS restritivo
- controles LGPD: perfil, consentimentos versionados, exportação e exclusão da conta
- isolamento das operações pelo usuário autenticado

Próximo endurecimento para produção: rate limiting distribuído (Redis/API gateway), fluxo de recuperação de senha e verificação de e-mail com provedor transacional, gestão de chaves/segredos e testes de segurança automatizados.

## V2.4 — IA com ferramentas financeiras

A IA deixará de ser somente um chat e passará a operar sobre ferramentas controladas pelo backend, como:

- consultar fluxo de caixa
- explicar gastos
- identificar categorias fora do padrão
- consultar metas
- consultar projeções
- executar simulações
- comparar cenários
- gerar planos de ação
- responder com dados e cálculos verificáveis

A chave do provedor de IA continuará exclusivamente no backend.

## V3 — Open Finance

- adaptador para provedor autorizado
- consentimento explícito
- importação de contas e movimentações
- categorização
- conciliação
- processamento de atualizações
- controles de consentimento e revogação

# V2.3 Hardening / Gate

A V2.3 foi endurecida antes da evolução para o agente financeiro:
- testes automatizados de simulação, limite de horizonte, refresh token e TOTP;
- JWT_SECRET e POSTGRES_PASSWORD removidos do compose como valores fixos;
- validação de segredo JWT forte quando `ENVIRONMENT=production`;
- sessões e refresh tokens revogáveis/rotativos;
- auditoria dos eventos de segurança e uso de ferramentas do agente;
- fronteira explícita para Open Finance, sem conectar provedor na V2.4.

## V2.4 — Agente financeiro com ferramentas reais

O endpoint `POST /api/agent/ask` executa ferramentas determinísticas no backend:
- `consultar_resumo_financeiro`
- `analisar_categorias`
- `consultar_metas`
- `simular_fluxo_caixa`

A ferramenta pode ser escolhida pelo agente/cliente, mas somente ferramentas de uma allowlist são executadas. Nenhuma ferramenta da V2.4 movimenta dinheiro, altera contas ou contrata produtos.

## Gate V2.3

O gate local desta entrega registra: Python/AST OK e suíte automatizada OK. A validação Docker/PostgreSQL de integração deve ser executada no ambiente com Docker antes de dados reais.

## V3 — Open Finance

`backend/app/openfinance/adapter.py` define somente o contrato de integração. Nenhuma instituição/provedor está conectado. A V3 deverá implementar consentimento, revogação, sincronização, reconciliação e tratamento seguro de credenciais conforme o provedor autorizado escolhido.

## V2.4 — Agente de IA com planejamento e tool-calling controlado

O endpoint `POST /api/agent/ask` agora usa um provedor de IA compatível com a Responses API para decidir quais ferramentas financeiras consultar. O modelo não recebe credenciais, SQL, sessão do banco ou acesso direto ao ORM.

Fluxo:

`pergunta → planejamento implícito → tool call allowlisted → validação Pydantic → função financeira determinística → resultado → resposta final`

As ferramentas atuais são somente leitura. O loop é limitado a 4 chamadas, `tool_choice=auto`, chamadas paralelas desabilitadas e cada chamada é registrada na auditoria sem registrar dados financeiros sensíveis.

Configuração mínima no `.env`:

```env
AI_API_KEY=...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-6-luna
AI_TIMEOUT_SECONDS=45
AGENT_ENABLED=true
```

O endpoint `/api/agent/ask/deterministic` permanece para testes e compatibilidade de clientes legados.
