"""SISNEO - site institucional (Flask), pronto para Azure App Service (Linux)."""
import csv
import gzip
import hashlib
import io
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import (Flask, Response, abort, make_response, redirect,
                   render_template, request, url_for)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.middleware.proxy_fix import ProxyFix

try:  # Azure App Service roda em Linux; no Windows local o lock de arquivo é ignorado
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------
# Dados da empresa
# ----------------------------------------------------------------------------
SITE_URL = os.environ.get("SITE_URL", "https://sisneo.com.br").rstrip("/")
SITE_HOST = urlparse(SITE_URL).netloc.lower()
EMPRESA = {
    "nome": "SISNEO",
    "cnpj": "62.486.265/0001-07",
    "responsavel": "Giani Maldaner",
    "whatsapp_digits": "5551998365106",
    "whatsapp_fmt": "(51) 99836-5106",
    "email": "gianimaldaner@gmail.com",
    "cidade": "Porto Alegre",
    "uf": "RS",
}
WA_BASE = "https://wa.me/" + EMPRESA["whatsapp_digits"]

SERVICOS = [
    {"id": "redes", "slug": "redes-corporativas-wifi-cisco", "titulo": "Redes corporativas e Wi-Fi",
     "texto": "Projeto, configuração e sustentação de redes com switches e roteadores Cisco, VLANs, VPN e Wi-Fi com cobertura planejada. Rede estável, segmentada e documentada.",
     "tags": ["Switches", "Roteadores Cisco", "VLAN e VPN", "Wi-Fi", "TCP/IP"]},
    {"id": "servidores", "slug": "servidores-virtualizacao-windows", "titulo": "Servidores e virtualização",
     "texto": "Windows Server, Active Directory, Exchange, SharePoint, Hyper-V e Citrix, além de Linux quando fizer sentido. Instalação, migração, backup e monitoramento.",
     "tags": ["Windows Server", "Active Directory", "Hyper-V", "Citrix", "Backup"]},
    {"id": "seguranca", "slug": "firewall-seguranca-lgpd", "titulo": "Firewall e segurança",
     "texto": "Firewall, segmentação de rede, antivírus e antispam, controle de acessos e plano de continuidade para reduzir risco e proteger os dados da empresa.",
     "tags": ["Firewall", "Antispam", "Controle de acesso", "Continuidade"]},
    {"id": "cloud", "slug": "migracao-azure-microsoft365", "titulo": "Migração para Azure e Microsoft 365",
     "texto": "Levantamento do ambiente, plano de migração e execução em janelas planejadas para reduzir a parada. Do servidor local para a nuvem Microsoft.",
     "tags": ["Microsoft Azure", "Microsoft 365", "Exchange Online", "Migração"]},
    {"id": "ia", "slug": "agentes-ia-atendimento-vendas", "titulo": "Agentes de IA para atendimento e vendas",
     "texto": "Assistentes que respondem com base nos seus manuais e processos (RAG), qualificam contatos e encaminham a conversa para o WhatsApp da equipe.",
     "tags": ["LLMs", "RAG", "Agentes de IA", "WhatsApp"]},
    {"id": "web", "slug": "site-institucional-seo", "titulo": "Site institucional e presença digital",
     "texto": "Sites rápidos, seguros e preparados para aparecer no Google, com formulário que transforma visitas em pedidos de contato.",
     "tags": ["SEO local", "Python / Flask", "LGPD", "Formulário de contatos"]},
]



SERVICE_PAGES = {
    "redes-corporativas-wifi-cisco": {
        "titulo": "Redes corporativas e Wi-Fi",
        "title_seo": "Redes Corporativas e Wi-Fi Cisco em Porto Alegre | SISNEO - Projeto e Suporte",
        "desc_seo": "Projeto e sustentação de redes com switches e roteadores Cisco, VLANs, VPN e Wi-Fi com cobertura planejada em Porto Alegre. Rede estável, segmentada e documentada. Atendimento direto.",
        "h1": "Redes Corporativas e Wi-Fi com Switches e Roteadores Cisco em Porto Alegre",
        "lead": "Projeto de rede estável, segmentada e documentada. De VLANs e VPN a Wi-Fi com site survey, com quem tem 20+ anos de Cisco e atende direto.",
        "h2": "O que entregamos em redes e Wi-Fi",
        "conteudo": "<p>Empresas perdem venda com Wi-Fi instável e rede sem segmentação. Projetamos e sustentamos redes com switches e roteadores Cisco, VLANs, VPN, QoS para VoIP Asterisk, firewall Linux e ISA Server.</p><p><strong>Inclui:</strong> levantamento, mapa de cobertura Wi-Fi, configuração de VLANs, VPN site-to-site, documentação e monitoramento.</p>"
    },
    "servidores-virtualizacao-windows": {
        "titulo": "Servidores e virtualização",
        "title_seo": "Servidores Windows Server e Virtualização em Porto Alegre | SISNEO",
        "desc_seo": "Suporte e instalação de Windows Server, Active Directory, Exchange, SharePoint, Hyper-V e Citrix em Porto Alegre. Backup, monitoramento e virtualização. 20+ anos.",
        "h1": "Servidores Windows Server, Active Directory e Virtualização em Porto Alegre",
        "lead": "Instalação, migração, backup e monitoramento de servidores Microsoft e Linux. Com documentação e janelas de manutenção.",
        "h2": "Servidores que não param sua operação",
        "conteudo": "<p>Windows Server 2008 a 2019, AD, DNS, DHCP, Exchange, SharePoint, Hyper-V, System Center VMM, WDS e Citrix. Além de Linux quando fizer sentido.</p><p>Atuamos com ITIL, SLA e KPIs, com relacionamento direto com Microsoft, Cisco e Dell.</p>"
    },
    "firewall-seguranca-lgpd": {
        "titulo": "Firewall e segurança",
        "title_seo": "Firewall e Segurança de Rede LGPD em Porto Alegre | SISNEO",
        "desc_seo": "Firewall, segmentação de rede, antivírus, antispam, controle de acesso e plano de continuidade para LGPD em Porto Alegre. Presencial no RS e remoto no Brasil.",
        "h1": "Firewall e Segurança de Rede para LGPD em Porto Alegre",
        "lead": "Reduza risco com segmentação, controle de acesso, antivírus, antispam e plano de continuidade alinhado à LGPD.",
        "h2": "Proteção de dados e continuidade",
        "conteudo": "<p>Firewall, segmentação, controle de acessos e plano de continuidade. Antivírus e antispam gerenciados.</p><p>Implementamos políticas que reduzem exposição e facilitam auditoria LGPD.</p>"
    },
    "migracao-azure-microsoft365": {
        "titulo": "Migração para Azure e Microsoft 365",
        "title_seo": "Migração para Azure e Microsoft 365 em Porto Alegre sem Parar | SISNEO",
        "desc_seo": "Migração de servidores locais para Azure e Microsoft 365 em Porto Alegre. Levantamento, plano com janelas de manutenção e acompanhamento pós-migração. 20+ anos, ex-Sisnema.",
        "h1": "Migração para Azure e Microsoft 365 em Porto Alegre sem parar sua operação",
        "lead": "Do servidor local para a nuvem Microsoft com risco mínimo. Experiência em clientes de médio e grande porte, com SLA e pré-venda técnica.",
        "h2": "Como fazemos a migração para Azure",
        "conteudo": "<ol style='list-style:decimal;padding-left:1.2rem'><li>Levantamento completo: servidores, e-mail, arquivos, usuários, permissões</li><li>Plano com janelas de manutenção e rollback documentado</li><li>Migração em etapas: AD, Exchange Online, arquivos para SharePoint/OneDrive</li><li>Acompanhamento nos primeiros dias para estabilização</li></ol>"
    },
    "agentes-ia-atendimento-vendas": {
        "titulo": "Agentes de IA para atendimento e vendas",
        "title_seo": "Agentes de IA para Atendimento e Vendas com RAG | SISNEO Porto Alegre",
        "desc_seo": "Agentes de IA que respondem com base nos seus manuais (RAG), qualificam leads e encaminham para WhatsApp. Python, LangChain, LangGraph. Porto Alegre e remoto Brasil.",
        "h1": "Agentes de IA que Atendem com Base nos Seus Manuais (RAG) em Porto Alegre",
        "lead": "LLMs, RAG, MCP, Chroma, Pinecone, LangChain, LangGraph e Gemini API. Atendimento 24h que qualifica e encaminha para sua equipe.",
        "h2": "O que o agente de IA faz pela sua empresa",
        "conteudo": "<p>Responde dúvidas usando seus próprios manuais e regras, separa contatos que realmente querem comprar e encaminha para o WhatsApp da equipe com contexto.</p><p>Construído a partir do material da sua empresa, não respostas genéricas.</p>"
    },
    "site-institucional-seo": {
        "titulo": "Site institucional e presença digital",
        "title_seo": "Site Institucional Rápido e Otimizado para Google | SISNEO Porto Alegre",
        "desc_seo": "Criação de sites rápidos, seguros e preparados para aparecer no Google em Porto Alegre. Flask, SEO local, LGPD e formulário que gera leads. SISNEO.",
        "h1": "Site Institucional Rápido, Seguro e Preparado para Aparecer no Google",
        "lead": "Sites em Flask/Python otimizados para SEO local, com formulário que transforma visitas em pedidos de contato e painel de leads.",
        "h2": "Site que gera contato, não só visita",
        "conteudo": "<p>Site leve, com canonical único, sitemap, robots, schema LocalBusiness e FAQ, PageSpeed otimizado e hospedagem Azure.</p><p>Inclui formulário com proteção anti-spam, painel de leads e integração WhatsApp.</p>"
    }
}

FAQ = [
    ("A SISNEO atende presencialmente em Porto Alegre?",
     "Sim. O atendimento presencial é em Porto Alegre e região, no Rio Grande do Sul. Para o restante do Brasil, o trabalho é feito remotamente."),
    ("Vocês atendem empresas de fora do Rio Grande do Sul?",
     "Sim. Diagnóstico, configuração de servidores, firewall, migração para Azure e suporte podem ser feitos por acesso remoto seguro, em todo o Brasil."),
    ("Como funciona a migração para o Azure?",
     "Começa com o levantamento do que existe hoje (servidores, e-mail, arquivos, usuários). Depois vem o plano com janelas de mudança, a migração em etapas e o acompanhamento nos primeiros dias, para reduzir o tempo de parada."),
    ("Quem faz o atendimento?",
     "O atendimento é direto com Giani Maldaner, profissional de redes e servidores com mais de 20 anos de experiência. Sem intermediários."),
    ("O que a IA pode fazer pela minha empresa?",
     "Um agente de IA pode responder dúvidas de clientes usando os seus próprios manuais e regras, separar contatos que realmente querem comprar e encaminhar para o WhatsApp da equipe. A conversa é construída a partir do material da sua empresa."),
    ("Meus dados enviados no formulário estão protegidos?",
     "Os dados são usados apenas para retornar o seu contato e ficam armazenados em ambiente protegido. Detalhes na Política de Privacidade, de acordo com a LGPD."),
]

NECESSIDADES = [
    ("rede", "Rede, Wi-Fi, switches ou roteadores"),
    ("servidor", "Servidores, Active Directory ou virtualização"),
    ("firewall", "Firewall e segurança"),
    ("azure", "Migração para Azure / Microsoft 365"),
    ("ia", "Agente de IA para atendimento ou vendas"),
    ("site", "Site institucional / presença digital"),
    ("suporte", "Suporte técnico contínuo (contrato mensal)"),
    ("outro", "Outro assunto"),
]
PORTES = [
    ("ate10", "Até 10 usuários"),
    ("11a50", "De 11 a 50 usuários"),
    ("51a200", "De 51 a 200 usuários"),
    ("200mais", "Mais de 200 usuários"),
]
URGENCIAS = [
    ("urgente", "Urgente: algo parado agora"),
    ("semana", "Nesta semana"),
    ("planejando", "Estou planejando / orçando"),
]
LABEL = {k: v for lst in (NECESSIDADES, PORTES, URGENCIAS) for k, v in lst}

# ----------------------------------------------------------------------------
# App e armazenamento
# ----------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


def _pick_data_dir():
    env = os.environ.get("DATA_DIR")
    if env:
        return env
    # Em App Service Linux, /home é persistente entre reinícios e deploys
    if os.path.isdir("/home") and os.access("/home", os.W_OK) and os.environ.get("WEBSITE_SITE_NAME"):
        return "/home/data"
    return os.path.join(BASE_DIR, "data")


DATA_DIR = _pick_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)
COUNTER_FILE = os.path.join(DATA_DIR, "contador.txt")
LEADS_FILE = os.path.join(DATA_DIR, "leads.jsonl")


def _load_secret():
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    path = os.path.join(DATA_DIR, "secret.key")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            val = fh.read().strip()
            if val:
                return val
    except OSError:
        pass
    val = secrets.token_hex(32)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(val)
    except FileExistsError:  # outro worker criou primeiro
        with open(path, "r", encoding="utf-8") as fh:
            val = fh.read().strip()
    except OSError:
        pass
    return val


app.secret_key = _load_secret()
_signer = URLSafeTimedSerializer(app.secret_key, salt="sisneo-form")
_thanks = URLSafeTimedSerializer(app.secret_key, salt="sisneo-thanks")

_proc_lock = threading.Lock()


def _flock(fd):
    if fcntl:
        fcntl.flock(fd, fcntl.LOCK_EX)


# ----------------------------------------------------------------------------
# Contador de acessos únicos (trava entre threads e workers + cookie de 24h)
# ----------------------------------------------------------------------------
BOT_RE = re.compile(r"bot|crawl|spider|slurp|facebookexternalhit|preview|monitor|uptime|lighthouse|headless",
                    re.I)
COOKIE_UV = "sisneo_uv"


def read_counter():
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as fh:
            return int((fh.read() or "0").strip() or 0)
    except (OSError, ValueError):
        return 0


def increment_counter():
    with _proc_lock:
        fd = os.open(COUNTER_FILE, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            _flock(fd)  # lock entre processos (gunicorn workers)
            raw = os.read(fd, 32).decode("utf-8", "ignore").strip()
            try:
                n = int(raw or 0) + 1
            except ValueError:
                n = 1
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, str(n).encode())
            os.fsync(fd)
        finally:
            os.close(fd)  # fechar libera o lock
    return n


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    ip = xff.split(",")[0].strip() if xff else (request.remote_addr or "")
    if ip.count(":") == 1 and "." in ip:  # Azure envia IPv4:porta
        ip = ip.split(":")[0]
    return ip


def ip_hash():
    return hashlib.sha256((app.secret_key + client_ip()).encode()).hexdigest()[:16]


_rate = {}


def rate_limited(limit=5, window=3600):
    now = time.time()
    key = ip_hash()
    with _proc_lock:
        hits = [t for t in _rate.get(key, []) if now - t < window]
        if len(hits) >= limit:
            _rate[key] = hits
            return True
        hits.append(now)
        _rate[key] = hits
        if len(_rate) > 5000:
            _rate.clear()
    return False


def new_form_token():
    return _signer.dumps(int(time.time()))


def valid_form_token(tok):
    try:
        ts = _signer.loads(tok, max_age=7200)
    except (BadSignature, SignatureExpired):
        return False
    return time.time() - int(ts) >= 3  # formulário preenchido por humano leva > 3s


def asset(path):
    full = os.path.join(BASE_DIR, "static", path)
    try:
        v = int(os.path.getmtime(full))
    except OSError:
        v = 0
    return url_for("static", filename=path, v=v)


def fmt_int(n):
    return f"{n:,}".replace(",", ".")


def wa_link(msg=None):
    if not msg:
        return WA_BASE
    from urllib.parse import quote
    return f"{WA_BASE}?text={quote(msg)}"


def json_ld():
    org_id = SITE_URL + "/#organization"
    person_id = SITE_URL + "/#giani"
    geo = {"@type": "GeoCoordinates", "latitude": -30.0346, "longitude": -51.2177}
    address = {"@type": "PostalAddress", "addressLocality": "Porto Alegre",
               "addressRegion": "RS", "addressCountry": "BR"}
    data = [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": org_id,
            "name": "SISNEO",
            "url": SITE_URL + "/",
            "logo": SITE_URL + "/static/favicon.svg",
            "image": SITE_URL + "/static/img/og-sisneo.png",
            "taxID": EMPRESA["cnpj"],
            "email": EMPRESA["email"],
            "telephone": "+5551998365106",
            "founder": {"@id": person_id},
            "address": address,
            "contactPoint": [{
                "@type": "ContactPoint", "contactType": "sales",
                "telephone": "+5551998365106", "email": EMPRESA["email"],
                "areaServed": "BR", "availableLanguage": ["pt-BR"]}],
        },
        {
            "@context": "https://schema.org",
            "@type": ["LocalBusiness", "ProfessionalService"],
            "@id": SITE_URL + "/#localbusiness",
            "name": "SISNEO - Suporte em Redes, Servidores e Azure",
            "description": "Redes de computadores, servidores, firewall, migração para Azure e agentes de IA para empresas em Porto Alegre, no Rio Grande do Sul e em todo o Brasil.",
            "url": SITE_URL + "/",
            "image": SITE_URL + "/static/img/og-sisneo.png",
            "telephone": "+5551998365106",
            "email": EMPRESA["email"],
            "taxID": EMPRESA["cnpj"],
            "priceRange": "$$",
            "address": address,
            "geo": geo,
            "areaServed": [
                {"@type": "City", "name": "Porto Alegre"},
                {"@type": "AdministrativeArea", "name": "Rio Grande do Sul"},
                {"@type": "Country", "name": "Brasil"},
            ],
            "parentOrganization": {"@id": org_id},
            "hasOfferCatalog": {
                "@type": "OfferCatalog", "name": "Serviços SISNEO",
                "itemListElement": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["titulo"],
                                                       "description": s["texto"]}}
                    for s in SERVICOS],
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "Person",
            "@id": person_id,
            "name": "Giani Maldaner",
            "jobTitle": "Especialista em redes, servidores e infraestrutura de TI",
            "image": SITE_URL + "/static/img/giani.jpg",
            "worksFor": {"@id": org_id},
            "email": EMPRESA["email"],
            "knowsAbout": ["Redes de computadores", "Servidores Windows", "Cisco", "Microsoft Azure",
                           "Active Directory", "Virtualização", "Inteligência Artificial", "RAG"],
            "hasCredential": [
                {"@type": "EducationalOccupationalCredential", "name": "MCSE - Microsoft Certified Systems Engineer"},
                {"@type": "EducationalOccupationalCredential", "name": "MCT - Microsoft Certified Trainer"},
                {"@type": "EducationalOccupationalCredential", "name": "CompTIA Security+ e Network+"},
                {"@type": "EducationalOccupationalCredential", "name": "Citrix Certified Administrator"},
                {"@type": "EducationalOccupationalCredential", "name": "Novell CNE e CNI"},
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": SITE_URL + "/#website",
            "url": SITE_URL + "/",
            "name": "SISNEO",
            "inLanguage": "pt-BR",
            "publisher": {"@id": org_id},
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ],
        },
    ]
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return out.replace("</", "<\\/")


@app.context_processor
def inject_globals():
    return {"E": EMPRESA, "SITE_URL": SITE_URL, "asset": asset, "wa_link": wa_link,
            "year": datetime.now().year}


# ----------------------------------------------------------------------------
# Rotas
# ----------------------------------------------------------------------------
def render_home(errors=None, values=None, status=200, noindex=False):
    counted_cookie = request.cookies.get(COOKIE_UV)
    ua = request.headers.get("User-Agent", "")
    is_new = False
    if request.method == "GET" and not counted_cookie and not BOT_RE.search(ua) and ua:
        total = increment_counter()
        is_new = True
    else:
        total = read_counter()
    html = render_template(
        "index.html", servicos=SERVICOS, faq=FAQ, necessidades=NECESSIDADES,
        portes=PORTES, urgencias=URGENCIAS, errors=errors or [], values=values or {},
        token=new_form_token(), jsonld=json_ld(), counter=fmt_int(total),
        show_counter=os.environ.get("SHOW_COUNTER", "1") != "0", noindex=noindex)
    resp = make_response(html, status)
    if is_new:
        resp.set_cookie(COOKIE_UV, "1", max_age=86400, secure=request.is_secure,
                        httponly=True, samesite="Lax", path="/")
    return resp


@app.route("/")
def index():
    return render_home()


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


@app.route("/contato", methods=["POST"])
def contato():
    f = request.form
    values = {k: f.get(k, "").strip() for k in
              ("nome", "whatsapp", "email", "empresa", "necessidade", "porte", "urgencia", "mensagem")}
    values["lgpd"] = f.get("lgpd", "")
    errors = []

    if f.get("website"):  # honeypot: robôs preenchem
        return redirect(url_for("index"), 303)
    if not valid_form_token(f.get("t", "")):
        errors.append("O formulário expirou ou foi enviado rápido demais. Confira os dados e envie novamente.")
    if rate_limited():
        errors.append("Muitos envios em pouco tempo. Para falar agora, use o WhatsApp.")

    nome = values["nome"]
    if not (2 <= len(nome) <= 100):
        errors.append("Informe seu nome.")
    digits = re.sub(r"\D", "", values["whatsapp"])
    if digits.startswith("55") and len(digits) > 11:
        digits = digits[2:]
    if not (10 <= len(digits) <= 11):
        errors.append("Informe um WhatsApp com DDD, por exemplo (51) 99999-9999.")
    if values["email"] and (len(values["email"]) > 150 or not EMAIL_RE.match(values["email"])):
        errors.append("O e-mail informado não parece válido.")
    if values["necessidade"] not in dict(NECESSIDADES):
        errors.append("Escolha o que você precisa.")
    if values["porte"] not in dict(PORTES):
        errors.append("Escolha o tamanho da sua empresa.")
    if values["urgencia"] not in dict(URGENCIAS):
        errors.append("Escolha a urgência.")
    if len(values["mensagem"]) > 1000 or len(values["empresa"]) > 120:
        errors.append("Texto muito longo. Resuma a mensagem em até 1000 caracteres.")
    if not values["lgpd"]:
        errors.append("Para enviar, concorde com o uso dos dados descrito na Política de Privacidade.")

    if errors:
        return render_home(errors=errors, values=values, status=400, noindex=True)

    lead = {
        "data_hora": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nome": nome,
        "whatsapp": digits,
        "email": values["email"],
        "empresa": values["empresa"],
        "necessidade": LABEL[values["necessidade"]],
        "porte": LABEL[values["porte"]],
        "urgencia": LABEL[values["urgencia"]],
        "mensagem": values["mensagem"],
        "consentimento_lgpd": True,
        "origem": request.headers.get("Referer", "")[:200],
        "ip_hash": ip_hash(),
    }
    line = json.dumps(lead, ensure_ascii=False) + "\n"
    with _proc_lock:
        fd = os.open(LEADS_FILE, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            _flock(fd)
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    app.logger.info("Novo lead: %s (%s)", nome, LABEL[values["necessidade"]])

    token = _thanks.dumps({"n": nome.split()[0][:30], "need": LABEL[values["necessidade"]],
                           "urg": LABEL[values["urgencia"]]})
    return redirect(url_for("obrigado", t=token), 303)


@app.route("/obrigado")
def obrigado():
    try:
        d = _thanks.loads(request.args.get("t", ""), max_age=3600)
    except (BadSignature, SignatureExpired):
        return redirect(url_for("index"))
    msg = (f"Olá, Giani! Sou {d['n']}. Acabei de enviar o formulário no site da SISNEO. "
           f"Preciso de: {d['need']}. Urgência: {d['urg']}.")
    return render_template("obrigado.html", nome=d["n"], wa=wa_link(msg))



@app.route("/<slug>/")
def servico_page(slug):
    slug = slug.strip("/").lower()
    if slug not in SERVICE_PAGES:
        abort(404)
    data = SERVICE_PAGES[slug]
    # JSON-LD específico do serviço
    service_jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Service",
        "name": data["titulo"],
        "serviceType": data["titulo"],
        "provider": {"@id": SITE_URL + "/#organization"},
        "areaServed": {"@type": "City", "name": "Porto Alegre"},
        "description": data["desc_seo"],
        "url": f"{SITE_URL}/{slug}/"
    }, ensure_ascii=False)
    servico = {
        "slug": slug,
        "titulo": data["titulo"],
        "title_seo": data["title_seo"],
        "desc_seo": data["desc_seo"],
        "h1": data["h1"],
        "lead": data["lead"],
        "h2": data["h2"],
        "conteudo": data["conteudo"],
        "jsonld": service_jsonld
    }
    return render_template("servico.html", servico=servico)


@app.route("/privacidade")
def privacidade():
    return render_template("privacidade.html")


@app.route("/robots.txt")
def robots():
    body = ("User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /contato\nDisallow: /obrigado\n\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n")
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    def lm(name):
        try:
            ts = os.path.getmtime(os.path.join(BASE_DIR, "templates", name))
            return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
        except OSError:
            return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [("/", lm("index.html"), "1.0", "weekly")]
    for slug in SERVICE_PAGES.keys():
        urls.append((f"/{slug}/", lm("servico.html"), "0.9", "weekly"))
    urls.append(("/privacidade", lm("privacidade.html"), "0.3", "yearly"))
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, mod, prio, freq in urls:
        xml.append(f"<url><loc>{SITE_URL}{path}</loc><lastmod>{mod}</lastmod>"
                   f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/healthz")
def healthz():
    return Response("ok", mimetype="text/plain")


# --- Painel simples de leads (desativado se ADMIN_PASSWORD não estiver definido) ---
def _check_admin():
    pwd = os.environ.get("ADMIN_PASSWORD")
    if not pwd:
        abort(404)
    auth = request.authorization
    user = os.environ.get("ADMIN_USER", "admin")
    ok = (auth and auth.username is not None and auth.password is not None
          and secrets.compare_digest(auth.username, user) and secrets.compare_digest(auth.password, pwd))
    if not ok:
        resp = Response("Acesso restrito.", 401, {"WWW-Authenticate": 'Basic realm="SISNEO"'})
        abort(resp)


def _read_leads():
    rows = []
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return list(reversed(rows))


def _csv_safe(v):
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


@app.route("/admin/leads")
def admin_leads():
    _check_admin()
    rows = _read_leads()
    if request.args.get("format") == "csv":
        cols = ["data_hora", "nome", "whatsapp", "email", "empresa", "necessidade", "porte",
                "urgencia", "mensagem"]
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(cols)
        for r in rows:
            w.writerow([_csv_safe(r.get(c)) for c in cols])
        return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=leads-sisneo.csv"})
    return render_template("admin_leads.html", rows=rows, visitas=fmt_int(read_counter()))


# ----------------------------------------------------------------------------
# Erros, cabeçalhos de segurança, compressão e cache
# ----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_e):
    return render_template("erro.html", titulo="Página não encontrada",
                           texto="O endereço não existe ou foi movido."), 404


@app.errorhandler(413)
@app.errorhandler(500)
def server_error(e):
    return render_template("erro.html", titulo="Algo deu errado",
                           texto="Tente novamente em instantes ou fale direto pelo WhatsApp."), \
        getattr(e, "code", 500)


@app.before_request
def canonical_host():
    """Mantém um único endereço público para o site.

    Redireciona (301) o www e o endereço padrão do Azure (*.azurewebsites.net)
    para o domínio oficial. Assim o Google não enxerga conteúdo duplicado e
    junta toda a relevância em sisneo.com.br.
    """
    if request.path == "/healthz":  # verificação de saúde do Azure não deve ser redirecionada
        return None
    host = request.host.split(":")[0].lower()
    if host == SITE_HOST:
        return None
    if host == "www." + SITE_HOST or host.endswith(".azurewebsites.net"):
        target = SITE_URL + request.full_path.rstrip("?")
        code = 301 if request.method in ("GET", "HEAD") else 308  # 308 preserva o POST do formulário
        return redirect(target, code)


CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
       "base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'")
COMPRESSIBLE = ("text/", "application/json", "application/xml", "image/svg+xml", "application/javascript")


@app.after_request
def harden_and_compress(resp):
    h = resp.headers
    h["Content-Security-Policy"] = CSP
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"
    h["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    if request.is_secure:
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.path.startswith("/admin") or request.path.startswith("/obrigado"):
        h["X-Robots-Tag"] = "noindex, nofollow"
        h["Cache-Control"] = "no-store"
    elif request.path.startswith("/static/"):
        h["Cache-Control"] = "public, max-age=31536000, immutable"
    elif resp.mimetype == "text/html":
        h["Cache-Control"] = "no-cache"

    if (resp.status_code == 200
            and "gzip" in request.headers.get("Accept-Encoding", "")
            and "Content-Encoding" not in h
            and resp.mimetype and resp.mimetype.startswith(COMPRESSIBLE)):
        resp.direct_passthrough = False
        data = resp.get_data()
        if len(data) > 600:
            resp.set_data(gzip.compress(data, compresslevel=6))
            h["Content-Encoding"] = "gzip"
            h.add("Vary", "Accept-Encoding")
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
