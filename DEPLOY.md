# RENCH Estoque - Deploy no Render

## Passo a passo para hospedar em estoque.rench.com.br

### 1. Criar conta no Render
- Acesse https://render.com
- Faça login com GitHub ou Google (gratuito)

### 2. Criar um novo Web Service
- Dashboard → New → Web Service
- Conecte sua conta GitHub e escolha o repositório `rench-stock-manager`
- Branch: `main`
- Runtime: Python 3
- Build Command: `pip install -r rench_web/requirements.txt`
- Start Command: `cd rench_web && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`
- Plano: Free

### 3. Configurar variáveis de ambiente (ESSENCIAL)
No painel do serviço, vá em **Environment**:
  - `SECRET_KEY` = crie uma senha longa e aleatória (ex: `rench2026#seguranca@estoque!`)
  - `RENDER` = `1`

> Sem o `SECRET_KEY`, o login NÃO vai funcionar!

### 4. Fazer upload do banco de dados
- No Render, vá em **Shell**
- Faça upload do arquivo `rench_web/rench_web.db` (contém todos os 509 equipamentos)
- O arquivo deve ficar na pasta `rench_web/`

### 5. Configurar subdomínio na Hostgator
- Acesse o cPanel da Hostgator
- Vá em **Domínios** → **Zone Editor** (Editor de Zona DNS)
- Adicione um registro **CNAME**:
  - Nome: `estoque`
  - Tipo: `CNAME`
  - Valor: (URL do Render, ex: `rench-estoque.onrender.com`)
  - TTL: 14400

### 6. Configurar domínio customizado no Render
- No painel do Web Service, vá em **Settings → Custom Domains**
- Adicione: `estoque.rench.com.br`
- O Render gera um certificado SSL automaticamente (HTTPS)

### 7. Pronto!
- Aguarde 5-10 minutos para o DNS propagar
- Acesse: https://estoque.rench.com.br
- Login: `admin` | Senha: `ipascnma`

## Atualizações futuras
Para atualizar o sistema, basta fazer `git push` para o GitHub. O Render faz deploy automático.

## Observações importantes
- Plano Free: o servidor "dorme" após 15 minutos de inatividade. A primeira requisição pode demorar ~30 segundos para "acordar".
- Para evitar isso, use um serviço de "ping" gratuito (ex: [UptimeRobot](https://uptimerobot.com)) para manter o site acordado.
- O banco SQLite é persistente no disco do Render (plano Free tem 1GB de disco).

## Depois do primeiro deploy
1. Acesse o Shell do Render
2. Verifique se o banco está na pasta correta:
   ```bash
   ls -la rench_web/
   ```
3. Se precisar reimportar a planilha, rode:
   ```bash
   cd rench_web && python -c "from app import importar_planilha_para_banco; importar_planilha_para_banco()"
   ```
