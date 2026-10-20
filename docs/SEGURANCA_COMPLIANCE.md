# Segurança, privacidade e auditabilidade

Revisão técnica do POC. Não é parecer jurídico nem atestado de conformidade regulatória; lista o que foi verificado, o que foi corrigido e o que falta para um ambiente produtivo de instituição regulada.

## 1. Dados pessoais (PII) e dados sensíveis

| Item | Situação verificada |
|---|---|
| Identificação direta (nome, CPF, e-mail, telefone, endereço) | **Não existe nos dados.** As ocorrências de "email" são rótulos (`campaign_type = Email`, `emails_enviados`). O JSON do CRM só tem `campaign_name`, `open_count`, `link`, `source`, `reason`, `audience` e `platform` |
| Identificadores pseudonimizados | `user_id`, `account_id`, `device_id`, `order_id`, `cart_id`. Continuam sendo **dado pessoal** pela LGPD, porque o controlador consegue reidentificar |
| Dados pessoais sensíveis (LGPD, art. 5º, II) | Não há (saúde, origem racial, biometria etc.) |
| Número de cartão (PAN) exposto como identificador | **Não há.** `python -m pipeline.pan_check` testa todas as colunas de ID. Todas têm 12 dígitos (um PAN tem 13 a 19), passam no Luhn em 9,7–10,3% dos valores (o acaso esperado para números aleatórios é ~10%; um PAN passaria em ~100%) e não concentram prefixos de bandeira. `account_id` e `cart_id` são identificadores de sistema |
| Dados sob sigilo bancário | Classe e bandeira do cartão e o histórico de resgates por cliente são dados de relacionamento bancário. Ficam na bronze, na silver e em 2 tabelas gold de grão individual |

**Exposição por canal**

| Canal | Antes | Depois |
|---|---|---|
| Dashboard | Só agregados (mês, modalidade, grupo). Nenhum identificador é exibido | Sem mudança |
| Agente | Conseguia devolver `user_id` e `order_id`. A recusa dependia só do prompt da LLM | **Guarda determinística:** valores devolvidos que sejam IDs reais de cliente ou pedido bloqueiam a resposta **antes** de ir à LLM ou à tela. Alias e conversão de tipo não burlam. Contagens continuam permitidas |
| Envio a LLM externa (Gemini) | A pergunta e o resultado agregado vão ao provedor | Com a guarda, nenhum identificador individual sai do ambiente. Alternativa on-premise: `LLM_PROVIDER=ollama` |
| Logs (`alertas.jsonl`, `dq_historico.jsonl`, `auditoria_agente.jsonl`) | — | Só métricas, SQL e respostas agregadas; nenhum identificador individual |
| Rede | Porta 8501 publicada em todas as interfaces, sem autenticação | **Publicada só em `127.0.0.1`.** Para expor, colocar atrás de proxy com SSO |
| Mensagem de erro do agente | Exceção crua na tela | Mensagem genérica; o detalhe vai para o log do servidor |
| Segredos | Chave lida de variável de ambiente; `.env` no `.gitignore` e no `.dockerignore` | Sem mudança |

## 2. Informação financeira e auditabilidade

**Que números financeiros saem do dashboard e do agente:** valor de produto, copagamento, custo coberto por pontos, custo por ponto (conversão pontos → R$), taxa do Pix (R$ 0,019) e passivo de pontos (quantidade, não valor).

**O que não existe nos dados e, portanto, não é calculado:**
- valores a receber do banco;
- receita por ponto;
- descontos concedidos;
- margem;
- provisão contábil do passivo.

O agente está instruído a recusar essas perguntas (exemplos reais no README).

**Rastreabilidade implementada**

| Requisito | Como é atendido |
|---|---|
| Origem de cada número | SQL versionado no git, por camada, com o grão declarado. Linhagem bronze (`_source_file`, `_loaded_at`) → silver → gold |
| Versão dos dados | `run_id` da carga, gravado em `dq_resultados` e exibido no dashboard e no rodapé de cada resposta do agente |
| Integridade da carga | 48 guardrails; conciliação ao ponto entre ledger e pedidos; publicação atômica, sem carga parcial |
| Trilha do agente | `warehouse/auditoria_agente.jsonl`, uma linha por pergunta. Registra data e hora UTC, pergunta, provedor, modelo, versão dos dados, SQL executado, SHA-256 do resultado, número de linhas, resposta e status (`respondido`, `recusado`, `bloqueado_dado_individual`, `erro`) |
| Natureza do número | Dashboard e respostas trazem "valores gerenciais, não contábeis" |
| Reprodutibilidade | Com o mesmo CSV (hash do manifesto) e o mesmo commit, `pipeline.build` gera os mesmos números. Os testes garantem os valores de referência |

## 3. Lacunas para produção (não resolvidas no POC)

1. **Precisão monetária:** os valores estão em `REAL` (ponto flutuante) e são arredondados no fim. Para auditoria em centavos, gravar em centavos (`INTEGER`) já na silver.
2. **Trilha imutável:** os JSONL são append-only por convenção. Em produção, usar armazenamento WORM ou log centralizado com retenção definida pela política da instituição.
3. **Identidade do usuário:** o dashboard e o agente não têm autenticação, então a trilha não registra **quem** perguntou. Exigir SSO e gravar o usuário em cada registro.
4. **Controle de acesso:** bronze e silver (com identificadores) estão no mesmo arquivo SQLite que a gold. Em produção: schemas separados, perfil de leitura só da gold para dashboard e agente, e mascaramento ou tokenização de IDs.
5. **Contratação de LLM externa:** enviar dados (mesmo agregados) a provedor de nuvem exige avaliação de terceiros, contrato e enquadramento na política de segurança cibernética e de contratação de nuvem da instituição (Resolução CMN nº 4.893/2021). Validar com segurança da informação e jurídico, ou usar modelo on-premise.
6. **Respostas do LLM:** o SQL é auditável, mas o texto da resposta é gerado e pode resumir errado. Para uso decisório, os números devem ser conferidos contra o resultado registrado (o hash está na trilha).
7. **Base legal e retenção (LGPD):** definir finalidade, base legal e prazo de retenção para os dados de resgate por cliente e para os próprios logs.
