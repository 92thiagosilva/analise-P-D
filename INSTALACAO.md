# Instalação — App de Análise de Fabricantes (Fotus Solar)

Guia passo a passo para instalar e rodar a aplicação em um computador novo, já com todas as
análises de fabricantes feitas até hoje incluídas.

## O que você vai precisar

1. **Python 3.10 ou superior** instalado no computador.
   - Baixe em: https://www.python.org/downloads/
   - **Importante:** na tela de instalação, marque a caixa **"Add Python to PATH"** antes de clicar em Instalar.
2. **Uma chave de API da Anthropic** (pessoal, sua).
   - Crie/pegue a sua em: https://console.anthropic.com/settings/keys
   - Essa chave é o que permite a aplicação chamar a IA (Claude) para gerar as análises. Sem ela, o app abre e mostra o histórico normalmente, mas não consegue analisar novos documentos.
3. **A pasta `uploads/`** com os documentos originais de cada fabricante (será enviada separadamente por fora do GitHub, pois é grande demais para o repositório — veja o Passo 3).

## Passo 1 — Baixar o projeto

**Opção A — com Git instalado** (recomendado):
```
git clone https://github.com/92thiagosilva/analise-P-D.git
```

**Opção B — sem Git:**
1. Acesse https://github.com/92thiagosilva/analise-P-D
2. Clique em **Code → Download ZIP**
3. Extraia o ZIP em uma pasta de sua preferência (ex.: `C:\FotusApp\`)

## Passo 2 — Rodar o instalador

Dentro da pasta do projeto, dê **duplo clique em `run.bat`**.

Na primeira vez que você rodar, ele vai:
1. Criar um arquivo `.env` a partir do modelo `.env.example`.
2. Abrir automaticamente o **Bloco de Notas** com esse arquivo.
3. Você deve substituir o texto `cole_aqui_sua_chave_da_anthropic` pela sua chave real (a que você pegou no Passo 0), assim:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
4. Salve o arquivo (`Ctrl+S`) e feche o Bloco de Notas.
5. **Dê duplo clique em `run.bat` de novo.**

Dessa segunda vez em diante, o `run.bat` vai:
- Criar um ambiente Python isolado (`.venv`) na primeira execução, para não bagunçar outros programas Python que você já tenha instalado.
- Instalar as dependências automaticamente.
- Abrir a aplicação no navegador em **http://localhost:5000**.

Nas próximas vezes que quiser usar o app, é só dar duplo clique em `run.bat` de novo — ele já estará tudo configurado.

## Passo 3 — Colocar a pasta `uploads/` no lugar certo

O repositório do GitHub traz o **código** e o **banco de dados** (`data/analyses.db`) já com todas
as análises, scores e resumos prontos — isso é o suficiente para navegar no ranking, comparar
fabricantes e exportar relatórios em PDF.

A pasta `uploads/` (os PDFs/imagens originais que foram enviados de cada fabricante) é grande
(quase 1 GB) e por isso não vai pelo GitHub. Ela será compartilhada com você separadamente.
Quando receber, copie a pasta `uploads` inteira para dentro da pasta do projeto, no mesmo nível
de `app.py`, substituindo a pasta `uploads` vazia que já existe lá:

```
analise-P-D/
├── app.py
├── run.bat
├── data/
│   └── analyses.db      ← já vem pronto do GitHub
├── uploads/              ← copie aqui os arquivos recebidos separadamente
│   ├── <id-fabricante-1>/
│   ├── <id-fabricante-2>/
│   └── ...
└── templates/
```

**Sem a pasta `uploads/` preenchida:** o app funciona normalmente (ranking, scores, resumos,
comparação, PDF), só os botões de "baixar arquivo original" e o reprocessamento de fabricantes
antigos com "Adicionar Arquivos" não vão encontrar os arquivos de origem.

## Confirmando que deu tudo certo

Depois do Passo 2, o navegador deve abrir sozinho em `http://localhost:5000` e mostrar o
**Ranking de Fabricantes já populado** com as análises existentes (não uma tela vazia). Isso
confirma que o banco de dados veio corretamente com o repositório.

Para testar uma análise nova, clique em **"Novo Fabricante"**, envie um PDF de teste e clique em
**"Analisar com IA"** — se a chave da Anthropic estiver certa, o resultado aparece em segundos.

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `run.bat` fecha na hora, dizendo "Python não encontrado" | Python não instalado ou não marcado "Add to PATH" | Reinstale o Python marcando essa opção |
| Erro `Configure a variável de ambiente ANTHROPIC_API_KEY` ao analisar | Arquivo `.env` ainda com o valor de exemplo, ou chave errada/expirada | Edite o `.env`, confira a chave em console.anthropic.com/settings/keys |
| Navegador não abre sozinho | Firewall/antivírus bloqueou | Abra manualmente `http://localhost:5000` |
| "Porta 5000 já em uso" | Outro programa (ou uma instância anterior do app) já está usando a porta | Feche a janela anterior do `run.bat` ou reinicie o computador |
| Ranking aparece vazio | O arquivo `data/analyses.db` não veio junto, ou está em outra pasta | Confirme que `data/analyses.db` existe dentro da pasta do projeto |

## Documentação complementar

A metodologia completa de análise e pontuação (pesos, régua de notas, regras de decisão, ajuste
por times internos) está documentada em [`docs/metodologia-analise-fabricantes.pdf`](docs/metodologia-analise-fabricantes.pdf).
