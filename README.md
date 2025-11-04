# SPI - Sistema do Pescador de Ipixuna

## Usuario
.venv/bin/python manage.py createsuperuser --username admin --email admin@example.com

docker compose -f docker-compose.prod.yml exec web \
  python manage.py createsuperuser --username admin --email admin@example.com


Aplicação web em Django para gestão de pescadores, documentos, mensalidades, recibos e relatórios, com módulo de Caixa e geração de PDFs (recibos e Dossiê do Defeso).

## Requisitos
- Python 3.11+ (para execução local) ou Docker

## via bash
.venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

## via docker
docker compose -f docker-compose.prod.yml run --rm web \
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

## via python
python -c "import secrets; print(secrets.token_urlsafe(64))"

## Ambiente de desenvolvimento (sem Docker)
1. Criar venv e instalar dependências:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install -r requirements.txt
   ```
2. Migrações e executar:
   ```bash
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py runserver
   ```
3. Acessar:
   - App: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Ambiente de desenvolvimento (Docker)
1. Subir:
   ```bash
   docker compose up --build
   ```
2. Acessar: http://127.0.0.1:8000/

## Produção (Docker Compose)
Arquivos relevantes:
- `docker-compose.prod.yml` (web + nginx + postgres)
- `entrypoint.prod.sh` (migra, coleta estáticos e inicia gunicorn)
- `nginx.conf` (estáticos/media e proxy para gunicorn)

1. Crie um arquivo `.env` na raiz:
   ```env
   DEBUG=0
   SECRET_KEY=troque-por-uma-chave-secreta
   ALLOWED_HOSTS=seu.dominio,localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=https://seu.dominio,http://localhost,http://127.0.0.1
   DATABASE_URL=postgres://spi:spi@db:5432/spi
   ```
2. Subir em produção (local):
   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```
3. Criar superusuário:
   ```bash
   docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
   ```
4. Logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs -f web
   docker compose -f docker-compose.prod.yml logs -f nginx
   ```

## Configurações importantes
- `spi/settings.py` lê variáveis de ambiente:
  - `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
  - `DATABASE_URL` (ex.: Postgres no Docker)
- Estáticos:
  - `collectstatic` coloca arquivos em `staticfiles/` (servidos pelo Nginx)
- Media (uploads):
  - Persistidos no volume `media`

## Funcionalidades principais
- Cadastro de Pescadores (com endereço e documentos)
- Upload de documentos por tipo (PDF/JPG/PNG)
- Mensalidades: criação manual e em lote (12 competências), pagamento e recibo em PDF (com logo, número sequencial e QR Code)
- Ficha do Pescador (imprimível)
- Dossiê do Defeso (PDF) com checklist automático (12 competências pagas e documentos obrigatórios)
- Configurações da Associação (nome, CNPJ, presidente, logo e assinatura)
- Relatórios: totais de associados, pagas/pendentes, devedores, total recebido (R$), receitas/despesas/saldo
- Caixa: lançamentos de receitas/despesas, auto-lançamento de receita ao pagar mensalidade

## Rotas úteis
- `/` Lista de pescadores
- `/associacao/` Configurações da associação
- `/relatorios/` Relatórios com filtros
- `/caixa/` Módulo de caixa
- `/admin/` Admin do Django

## Segurança e produção
- Configure `SECRET_KEY` e desabilite `DEBUG` em produção
- Ajuste `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` para o seu domínio
- Configure HTTPS no Nginx (Let's Encrypt) e defina `SECURE_PROXY_SSL_HEADER`

## Backup e Restore
- Banco (Postgres): volume `pgdata`
- Uploads: volume `media`
- Faça snapshots dos volumes e mantenha-os seguros

## Roadmap (sugestões)
- Máscaras (CPF/CEP/telefone) e ViaCEP
- Exportação CSV/PDF dos relatórios
- Gráficos (Chart.js) nos relatórios
- Perfis/permissões e auditoria
- Deploy com HTTPS automatizado e CI/CD
