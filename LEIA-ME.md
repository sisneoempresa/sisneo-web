# SISNEO - site Flask para Azure App Service (Linux)

## Publicar (ZipDeploy)
1. Azure Portal > seu App Service > Configuration > General settings:
   - Stack: Python 3.11 (ou 3.12)
   - Startup Command: `bash startup.sh`
     (ou: `gunicorn --bind=0.0.0.0 --workers=2 --threads=4 --timeout=120 app:app`)
   - HTTPS Only: ligado
2. Configuration > Application settings (recomendado):
   - `SCM_DO_BUILD_DURING_DEPLOYMENT` = `true`  (instala o requirements.txt sozinho)
   - `ADMIN_PASSWORD` = uma senha forte (ativa o painel https://sisneo.com.br/admin/leads)
   - `SECRET_KEY` = texto aleatório longo (opcional; senão é gerado e guardado em /home/data)
3. Enviar o zip: `az webapp deploy --resource-group <grupo> --name <app> --src-path sisneo-site.zip --type zip`
   (ou Advanced Tools/Kudu > Zip Push Deploy).
4. Domínio: App Service > Custom domains > adicionar sisneo.com.br e www.sisneo.com.br,
   com o certificado gerenciado gratuito. O `www` redireciona para o domínio sem www.

## Onde ficam os dados (persistem entre deploys)
- `/home/data/contador.txt`  contador de visitantes únicos
- `/home/data/leads.jsonl`   leads do formulário
- Painel: `/admin/leads` (usuário `admin`, senha em ADMIN_PASSWORD) com download em CSV.

## Depois de publicar
- Google Search Console: adicionar sisneo.com.br e enviar https://sisneo.com.br/sitemap.xml
- Google Meu Negócio (Perfil da Empresa): cadastrar com o mesmo nome, telefone e cidade do rodapé.
- Teste: PageSpeed Insights e https://search.google.com/test/rich-results

## Ajustes rápidos
- Textos de serviços e FAQ: lista no topo de `app.py` (SERVICOS, FAQ).
- Esconder o contador: variável `SHOW_COUNTER` = `0`.
- Cores: variáveis no início de `static/css/style.css`.
