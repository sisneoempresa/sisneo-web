# SISNEO - site Flask para Azure App Service (Linux)

## Arquivos que começam com ponto
No zip de publicação, estes dois arquivos precisam ter o ponto no nome:
- `_deployment` deve se chamar `.deployment`
- `_gitignore` deve se chamar `.gitignore`

Sem o `.deployment`, o Azure não instala o `requirements.txt` sozinho.

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
5. Endereço padrão do Azure (`sisneoweb.azurewebsites.net`): o `app.py` redireciona (301) tudo
   para `https://sisneo.com.br`. Assim o Google não indexa duas cópias do site.
   Não altere a variável `SITE_URL` para outro endereço: ela define o domínio oficial usado em
   canonical, sitemap, robots e dados estruturados.

## Onde ficam os dados (persistem entre deploys)
- `/home/data/contador.txt`  contador de visitantes únicos
- `/home/data/leads.jsonl`   leads do formulário
- Painel: `/admin/leads` (usuário `admin`, senha em ADMIN_PASSWORD) com download em CSV.

## Depois de publicar
- Google Search Console: adicionar sisneo.com.br como **propriedade de domínio** (verificação por DNS),
  enviar https://sisneo.com.br/sitemap.xml e usar "Inspeção de URL" > "Solicitar indexação"
  para a página inicial e para /privacidade.
- Google Meu Negócio (Perfil da Empresa): cadastrar com o mesmo nome, telefone e cidade do rodapé.
- Teste: PageSpeed Insights e https://search.google.com/test/rich-results

## Ajustes rápidos
- Textos de serviços e FAQ: lista no topo de `app.py` (SERVICOS, FAQ).
- Esconder o contador: variável `SHOW_COUNTER` = `0`.
- Cores: variáveis no início de `static/css/style.css`.

## Conferir se o Google vai reconhecer o site
Depois de publicar, confira (o resultado deve ser exatamente o descrito):
1. `https://sisneoweb.azurewebsites.net/` abre e vai para `https://sisneo.com.br/` (redirecionamento 301).
2. `https://www.sisneo.com.br/` vai para `https://sisneo.com.br/`.
3. No código-fonte da página inicial (Ctrl+U), a tag `canonical` e o `og:url` apontam para `https://sisneo.com.br/`.
4. `https://sisneo.com.br/robots.txt` mostra `Allow: /` e a linha `Sitemap:` com o domínio oficial.
5. `https://sisneo.com.br/sitemap.xml` lista só endereços de `sisneo.com.br`.
6. Após alguns dias, a busca `site:sisneo.com.br` no Google deve mostrar as páginas.
   A indexação pode levar de alguns dias a algumas semanas, mesmo com tudo certo.

