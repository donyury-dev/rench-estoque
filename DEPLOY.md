# RENCH Estoque - Deploy no Render (PostgreSQL/Supabase)

## Passo a passo para hospedar em equipamentos.rench.com.br

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
  - `DATABASE_URL` = `postgresql://postgres.yfxfmwrasjukbsjjqbzs:kaio82046697@aws-1-us-west-2.pooler.supabase.com:6543/postgres`

> Sem o `DATABASE_URL`, o sistema não conecta no banco e não funciona!

### 4. Configurar subdomínio na Hostgator
- Acesse o cPanel da Hostgator
- Vá em **Domínios** → **Zone Editor** (Editor de Zona DNS)
- Adicione um registro **CNAME**:
  - Nome: `equipamentos`
  - Tipo: `CNAME`
  - Valor: (URL do Render, ex: `rench-estoque.onrender.com`)
  - TTL: 14400

### 5. Configurar domínio customizado no Render
- No painel do Web Service, vá em **Settings → Custom Domains**
- Adicione: `equipamentos.rench.com.br`
- O Render gera um certificado SSL automaticamente (HTTPS)

### 6. Pronto!
- Aguarde 5-10 minutos para o DNS propagar
- Acesse: https://equipamentos.rench.com.br
- Login: `admin` | Senha: `ipascnma`

## Atualizações futuras
Para atualizar o sistema, basta fazer `git push` para o GitHub. O Render faz deploy automático.

## Observações importantes
- Plano Free: o servidor "dorme" após 15 minutos de inatividade. A primeira requisição pode demorar ~30 segundos para "acordar".
- Para evitar isso, use um serviço de "ping" gratuito (ex: [UptimeRobot](https://uptimerobot.com)) para manter o site acordado.
- O banco agora é PostgreSQL no Supabase: os dados são persistentes e não somem a cada deploy.

## Depois do primeiro deploy
1. Acesse o Shell do Render
2. Verifique se a conexão com o banco funciona:
   ```bash
   cd rench_web && python -c "from app import get_db; cur=get_db().cursor(); cur.execute('SELECT COUNT(*) FROM equipamentos'); print(cur.fetchone())"
   ```
