# 🎯 Monitor de Falhas de Preço — Gaming & Tech (Amazon)

Ferramenta profissional e automatizada em Python para deteção contínua de *price glitches* (erros de preço) e promoções anómalas na **Amazon** (focado no mercado Ibérico / europeu: Portugal e Espanha através de `amazon.es`).

O sistema não depende de uma lista estática de produtos: **descobre dinamicamente** novos produtos varrendo categorias de Gaming e Tecnologia, armazena o histórico em **SQLite**, aplica múltiplas camadas de análise estatística e filtros de falsos positivos, e envia alertas formatados em tempo real para um canal do **Discord via Webhook**.

---

## 🚀 Funcionalidades Principais

- **Descoberta Dinâmica**:
  - Varre categorias como Processadores (CPUs), Placas Gráficas (GPUs), Monitores Gaming, Comandos/Consolas, Teclados e Ratos Mecânicos, Memória RAM, SSDs NVMe, Routers Gaming, e também Smartphones e Tablets de gama média-alta/topo.
- **Scraper com Evasão Anti-Bot (Playwright)**:
  - Navegador Chromium com cabeçalhos humanos, evasão de flags de automação (`navigator.webdriver`), suporte a cookies da UE e atrasos aleatórios com *jitter*.
- **Motor Heurístico de Deteção de Falhas**:
  1. **Desconto Riscado Anormal**: Deteta quando a Amazon lista um corte de preço oficial fora do comum (ex: $\ge 55\%$).
  2. **Queda Face à Média Histórica Individual**: Analisa flutuações temporais do próprio produto (ex: $\ge 40\%$ de redução).
  3. **Mediana da Categoria (Cold Start)**: Para produtos sem histórico ou novos no catálogo, compara com a mediana de preços de itens semelhantes na mesma categoria.
- **Filtro Anti-Falsos Positivos**:
  - Exclui capas, películas, cabos, suportes e adaptadores através de uma *blacklist* abrangente de palavras-chave.
  - Exige piso mínimo de preço por categoria (evita que cabos HDMI sejam confundidos com GPUs).
  - Exige um mínimo de avaliações e nota média mínima para descartar listagens fraudulentas de contas recém-criadas.
  - Sistema de *cooldown* para não repetir o mesmo alerta várias vezes no mesmo dia.
- **Alertas Formatados no Discord**:
  - Envia *Rich Embeds* visuais com miniatura da foto, título com link direto, preço atual, preço de referência, percentagem de desconto, vendedor e avaliação.
- **Agendador Autónomo (APScheduler)**:
  - Executa rondas periódicas contínuas 24/7 sem intervenção manual.

---

## 📁 Estrutura do Projeto

```
Amazon_Preço_Certo/
├── config/
│   ├── config.yaml          # Categorias, termos de busca, limiares e delays
│   └── settings.py          # Leitor tipado de configurações com Pydantic
├── src/
│   ├── database/
│   │   ├── db.py            # Conexão SQLite com modo WAL
│   │   └── repository.py    # CRUD de produtos, preços, histórico e alertas
│   ├── scrapers/
│   │   ├── base.py          # Interface abstrata BaseScraper e modelo ScrapedProduct
│   │   ├── selectors.py     # Extratores CSS e parsers de moeda europeia (€)
│   │   └── amazon.py        # Scraper Playwright com proteções anti-deteção
│   ├── detector/
│   │   ├── filters.py       # Filtro rigoroso de falsos positivos e acessórios
│   │   └── engine.py        # Algoritmo de deteção de glitches e anomalias
│   ├── notifiers/
│   │   ├── base.py          # Interface abstrata de notificação
│   │   └── discord.py       # Notificador de Rich Embeds via Discord Webhook
│   └── scheduler/
│       └── runner.py        # Orquestrador com APScheduler e jitter
├── tests/
│   ├── test_detector.py     # Testes de regras de anomalia, filtros e cooldown
│   └── test_parsing.py      # Testes de parsing de preços, notas e reviews
├── data/                    # Base de dados SQLite (criada automaticamente)
├── .env.example             # Modelo para as chaves secretas
├── .env                     # As suas configurações locais (não partilhar)
├── requirements.txt         # Dependências Python
├── run.py                   # Ponto de entrada CLI
└── README.md                # Este manual
```

---

## 🛠️ Instalação e Preparação

### 1. Pré-requisitos
- Python 3.10 ou superior instalado.

### 2. Instalar Dependências Python
No terminal (PowerShell ou Command Prompt), na pasta do projeto:
```powershell
pip install -r requirements.txt
```

### 3. Instalar o Navegador do Playwright
O Playwright precisa do binário do Chromium para navegar na Amazon:
```powershell
playwright install chromium
```

---

## ⚙️ Configuração

### 1. Configurar o Webhook do Discord

1. No seu Discord, abra as **Definições do Canal** de texto onde deseja receber os alertas (ou crie um canal específico, ex: `#falhas-amazon`).
2. Clique em **Integrações** > **Webhooks** > **Novo Webhook**.
3. Dê um nome (ex: `Amazon Price Glitch`) e clique em **Copiar URL do Webhook**.
4. Abra o ficheiro `.env` na raiz do projeto e cole a URL:
```ini
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/abcdef...
```

### 2. Ajustar Limiares e Categorias (`config/config.yaml`)

Pode personalizar sem tocar em código:
- `detection.min_strikethrough_discount`: Percentagem mínima de desconto riscado para alertar (padrão: `0.55` = 55%).
- `detection.min_historical_discount`: Queda mínima face à média histórica (padrão: `0.40` = 40%).
- `detection.min_review_count`: Mínimo de reviews para considerar o produto fiável (padrão: `15`).
- `scheduler.interval_minutes`: Intervalo entre rondas completas (padrão: `30` minutos).
- `categories`: Lista de categorias ativas, URLs de busca, pisos mínimos de preço e palavras banidas adicionais.

---

## 🎮 Como Utilizar (Comandos)

O ficheiro `run.py` disponibiliza vários modos de operação:

### 1. Testar o Webhook do Discord
Valide se o bot consegue publicar no seu servidor:
```powershell
python run.py --test-discord
```

### 2. Executar um Scan Imediato de Teste
Para verificar a extração e salvar produtos na base de dados imediatamente:
```powershell
# Todas as categorias configuradas
python run.py --scan

# Ou apenas uma categoria específica (ex: 'gpu', 'ram', 'controllers', 'smartphones')
python run.py --scan --category ram
```

### 3. Consultar Estatísticas da Base de Dados
Veja quantos produtos, preços históricos e alertas estão registados:
```powershell
python run.py --stats
```

### 4. Iniciar o Agendador Contínuo 24/7 (Modo Recomendado)
Executa de forma contínua em segundo plano, varrendo periodicamente com pausas humanas e alertando sempre que uma falha surgir:
```powershell
python run.py --daemon
```

---

## 🧪 Executar Testes Automatizados

Para garantir que a lógica de conversão de preços e as regras de anomalia estão 100% íntegras:
```powershell
python -m pytest
```

---

## 🔄 Extensibilidade Futura

O projeto foi desenhado segundo princípios de inversão de dependência:
- **Novo Canal de Notificação (ex: Telegram)**: Crie `src/notifiers/telegram.py` herdando de `BaseNotifier` e registe-o no orquestrador.
- **Novas Lojas (ex: Worten, PCComponentes)**: Crie `src/scrapers/worten.py` herdando de `BaseScraper`.
- **Novas Categorias**: Basta adicionar mais entradas na lista `categories` em `config/config.yaml`.
