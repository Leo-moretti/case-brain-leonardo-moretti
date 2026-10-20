# Classificação de dados

Proposta para o POC. Os níveis devem ser alinhados à política de classificação da instituição.

## Níveis

| Nível | Critério | Quem acessa | Controles |
|---|---|---|---|
| **Público** | Pode ser divulgado sem dano | Qualquer pessoa | — |
| **Interno** | Informação gerencial agregada, sem dado de cliente | Colaboradores autorizados | Autenticação |
| **Confidencial** | Dado de negócio sensível (custos, contratos, desempenho de parceiros) ou agregado que permita inferência comercial | Diretoria e áreas responsáveis | Autenticação, perfil de acesso, trilha de auditoria |
| **Restrito** | Dado pessoal (LGPD), inclusive pseudonimizado, ou dado de relacionamento bancário (sigilo bancário, LC 105/2001) em grão individual | Engenharia de dados e times com finalidade justificada | Perfil mínimo, mascaramento/tokenização, proibido envio a terceiros sem base legal e contrato, auditoria de acesso |

Não há no dataset dado pessoal direto (nome, CPF, contato), dado pessoal sensível (LGPD, art. 5º, II) nem número de cartão (verificado por Luhn em `pipeline/pan_check.py`). Se aparecerem, a classificação sobe para **Restrito** com proibição de carga na camada analítica sem tokenização.

## Classificação por campo (fontes)

| Campo | Nível | Categoria | Justificativa |
|---|---|---|---|
| user_id, account_id, device_id | Restrito | Dado pessoal pseudonimizado | Reidentificável pelo controlador |
| order_id, order_item_id, cart_id, movement_id | Restrito | Dado pessoal indireto | Liga a transação ao cliente |
| card_class, card_flag, cards.created_at | Restrito | Relacionamento bancário | Perfil do produto financeiro do cliente |
| points, paid_points, refunded_points, valid_until (por conta) | Restrito | Relacionamento bancário | Saldo e movimentação individual |
| paid_currency, product_value (por item) | Restrito | Relacionamento bancário | Valor de transação individual |
| created_at, status, channel, product_type (por item) | Restrito | Comportamento do cliente | Grão individual |
| supplier_name, supplier_responsible, category_macro | Confidencial | Parceiros comerciais | Relação comercial do programa |
| event_ts, event_name, campaign_*, event_properties | Restrito (grão individual) | Comportamento/marketing | Ligado a usuário e dispositivo |
| dim_operation | Interno | Referência | Cadastro técnico |
| relatorio_mensal_cliente | Confidencial | Prestação de contas contratual | Relatório entre operador e banco |

## Classificação por camada e saída

| Objeto | Nível | Observação |
|---|---|---|
| bronze_*, silver_* | Restrito | Grão individual; só o pipeline acessa |
| gold_fct_resgate, gold_dim_usuario | Restrito | Grão individual. O agente consulta, mas a guarda bloqueia a saída de identificadores |
| gold_resgates_mensal, gold_metas_mensal, gold_pontos_mensal, gold_breakage | Confidencial | Agregados com custos e metas contratuais |
| gold_conciliacao_operador | Confidencial | Expõe divergência do relatório do operador |
| gold_campanha_pix | Interno | Agregado por grupo (milhares de usuários por grupo) |
| dq_resultados, dq_historico, alertas | Interno | Métricas de qualidade, sem dado de cliente |
| auditoria_agente.jsonl | Confidencial | Perguntas e respostas da diretoria |
| Dashboard | Confidencial | Só agregados; exige autenticação em produção |
| Resposta do agente | Confidencial | Só agregados (guarda determinística); trilha de auditoria |
| CSVs em `dados/` | Restrito em produção | No case são fictícios e publicados no repositório do exercício |

## Regras de tratamento

1. Dado **Restrito** não sai do ambiente analítico em grão individual: nem pelo dashboard, nem pelo agente, nem para o provedor de LLM.
2. Agregados exibidos devem ter grupos grandes o suficiente para não permitir reidentificação. Hoje o menor grupo exposto é mês × modalidade, com centenas de usuários; para cortes novos, sugerimos k ≥ 10 (ver melhorias futuras de guardrails no README).
3. Retenção, base legal e finalidade devem ser definidas pelo controlador antes de produção (ver [SEGURANCA_COMPLIANCE.md](SEGURANCA_COMPLIANCE.md)).
