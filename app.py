"""SISNEO TI - site institucional (Flask), otimizado para SEO local Porto Alegre e Azure App Service."""
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

try:
    import fcntl
except ImportError:
    fcntl = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------
# Dados da empresa - NAP consistente para SEO local
# ----------------------------------------------------------------------------
SITE_URL = os.environ.get("SITE_URL", "https://sisneo.com.br").rstrip("/")
SITE_HOST = urlparse(SITE_URL).netloc.lower()
EMPRESA = {
    "nome": "SISNEO TI",
    "cnpj": "62.486.265/0001-07",
    "responsavel": "Giani Maldaner",
    "whatsapp_digits": "5551998365106",
    "whatsapp_fmt": "(51) 99836-5106",
    "email": "gianimaldaner@gmail.com",
    "cidade": "Porto Alegre",
    "uf": "RS",
    "endereco": "Porto Alegre - RS",
    "cep": "91430",
}
WA_BASE = "https://wa.me/" + EMPRESA["whatsapp_digits"]

# Serviços com slug SEO para páginas dedicadas - ESSENCIAL para rankear
SERVICOS = [
    {
        "id": "redes", "slug": "redes-cisco",
        "titulo": "Redes corporativas e Wi-Fi",
        "titulo_seo": "Redes Cisco e Wi-Fi Corporativo em Porto Alegre",
        "texto": "Projeto, configuração e sustentação de redes com switches e roteadores Cisco, VLANs, VPN e Wi-Fi com cobertura planejada. Rede estável, segmentada e documentada para empresas em Porto Alegre.",
        "desc_seo": "Empresa de redes Cisco em Porto Alegre: switches, roteadores, VLANs, VPN e Wi-Fi corporativo. 35 anos, atendimento direto com Giani Maldaner.",
        "tags": ["Switches Cisco", "Roteadores Cisco", "VLAN e VPN", "Wi-Fi corporativo", "TCP/IP Porto Alegre"]
    },
    {
        "id": "servidores", "slug": "suporte-servidores",
        "titulo": "Servidores e virtualização",
        "texto": "Windows Server, Active Directory, Exchange, SharePoint, Hyper-V e Citrix. Instalação, migração, backup com teste de restore e monitoramento preventivo.",
        "titulo_seo": "Suporte de Servidores Windows Server em Porto Alegre",
        "desc_seo": "Suporte de servidores Windows Server em Porto Alegre: Active Directory, Hyper-V, backup e virtualização. 35 anos, MCSE, presencial no RS e remoto no Brasil.",
        "tags": ["Windows Server", "Active Directory", "Hyper-V", "Citrix", "Backup Porto Alegre"]
    },
    {
        "id": "seguranca", "slug": "firewall-lgpd",
        "titulo": "Firewall e segurança",
        "texto": "Firewall Fortigate, Cisco e Linux, segmentação de rede, antivírus, controle de acessos e plano de continuidade para LGPD. Backup local + nuvem com teste.",
        "titulo_seo": "Firewall e LGPD para Empresas em Porto Alegre",
        "desc_seo": "Firewall e adequação LGPD em Porto Alegre: firewall configurado, VPN, backup testado e políticas de segurança. 35 anos, atendimento direto.",
        "tags": ["Firewall", "LGPD Porto Alegre", "Antivírus", "Backup", "VPN"]
    },
    {
        "id": "cloud", "slug": "migracao-azure",
        "titulo": "Migração para Azure e Microsoft 365",
        "texto": "Levantamento do ambiente, plano de migração e execução em janelas planejadas para reduzir a parada. Do servidor local para a nuvem Microsoft com acompanhamento.",
        "titulo_seo": "Migração para Azure e Microsoft 365 em Porto Alegre",
        "desc_seo": "Migração para Azure e Microsoft 365 em Porto Alegre: servidores, AD e e-mails para nuvem sem parar operação. Atendimento direto com Giani Maldaner.",
        "tags": ["Microsoft Azure", "Microsoft 365", "Exchange Online", "Migração Porto Alegre"]
    },
    {
        "id": "ia", "slug": "agentes-ia",
        "titulo": "Agentes de IA para atendimento e vendas",
        "texto": "Assistentes que respondem com base nos seus manuais e processos (RAG), qualificam contatos e encaminham para WhatsApp da equipe. Atendimento 24h com material da sua empresa.",
        "titulo_seo": "Agentes de IA para Atendimento em Porto Alegre",
        "desc_seo": "Agentes de IA para empresas em Porto Alegre: atendimento 24h com RAG, LLMs e integração WhatsApp. Automação com base nos seus manuais.",
        "tags": ["Agentes de IA", "RAG", "LLMs", "WhatsApp", "Automação Porto Alegre"]
    },
    {
        "id": "web", "slug": "site-institucional",
        "titulo": "Site institucional e presença digital",
        "texto": "Sites rápidos, seguros e preparados para aparecer no Google em Porto Alegre, com formulário LGPD e SEO local. Python/Flask e performance.",
        "titulo_seo": "Site Institucional e SEO Local em Porto Alegre",
        "desc_seo": "Criação de site institucional com SEO local em Porto Alegre: sites rápidos, seguros e preparados para Google. LGPD e performance.",
        "tags": ["SEO local Porto Alegre", "Python / Flask", "LGPD", "Site rápido"]
    },
]

# ----------------------------------------------------------------------------
# Histórico profissional (E-E-A-T). EDITE AQUI: tudo que aparece em /sobre/,
# /certificacoes/, na home e no schema Person vem destes dados.
# ----------------------------------------------------------------------------
ANOS_EXPERIENCIA = 35
INICIO_CARREIRA = 1990

# Perfis públicos reais (LinkedIn, Google Perfil da Empresa, etc.). Entram no
# schema como sameAs. Deixe vazio até ter as URLs reais.
SAME_AS = [
    # "https://www.linkedin.com/in/SEU-PERFIL",
]

TIMELINE = [
    {"periodo": "1990-1995", "titulo": "Novell NetWare e as primeiras redes",
     "resumo": "Início da carreira em redes com Novell NetWare. Certificações Novell CNE e CNA.",
     "texto": "Primeiros projetos e suporte de redes de empresas com Novell NetWare, que era a base das redes corporativas da época. Certificações Novell CNE e CNA."},
    {"periodo": "1995", "titulo": "Primeiras certificações Microsoft",
     "resumo": "MCSE e MCT: base para projetar redes Windows e dar treinamentos oficiais.",
     "texto": "Certificado Microsoft desde 1995: MCSE (Microsoft Certified Systems Engineer) e MCT (Microsoft Certified Trainer), a base para projetar redes com servidores Windows e ministrar treinamentos oficiais."},
    {"periodo": "1995-2020", "titulo": "Sisnema Soluções, Porto Alegre",
     "resumo": "Gerente de TI e instrutor Cisco e Microsoft. Migração de ambientes locais para a nuvem.",
     "texto": "Gerente de TI e instrutor de cursos Cisco e Microsoft na Sisnema Soluções. Projetos de redes e servidores para clientes, equipes de suporte dentro de SLAs e migração de ambientes locais para a nuvem em clientes de médio e grande porte."},
    {"periodo": "2020-hoje", "titulo": "SISNEO TI: atendimento direto",
     "resumo": "Suporte direto, migração para Azure e agentes de IA para empresas.",
     "texto": "Atendimento direto a empresas: redes, servidores, migração para Azure e Microsoft 365 e agentes de IA aplicados a atendimento e vendas, com os manuais e processos de cada cliente."},
]

# Fotos da página /sobre/. "arquivo" é o caminho em static/img/ SEM extensão;
# o site procura .webp, .jpg, .jpeg e .png. Só aparece na página quem tiver arquivo.
FOTOS = [
    {"arquivo": "historia/rack-1998", "ano": "1998",
     "alt": "Giani Maldaner Porto Alegre 1998 rede Novell - rack de servidores",
     "legenda": "Rack de rede e servidores, 1998"},
    {"arquivo": "historia/cracha-sisnema", "ano": "",
     "alt": "Giani Maldaner crachá Sisnema Soluções Porto Alegre",
     "legenda": "Crachá da Sisnema Soluções"},
    {"arquivo": "historia/instrutor", "ano": "",
     "alt": "Giani Maldaner instrutor de redes Cisco e Microsoft em Porto Alegre",
     "legenda": "Em sala de treinamento como instrutor"},
]

# Certificações. "periodo" só deve ser preenchido com data confirmada.
# "imagens": nomes SEM extensão em static/img/certificados/. Só aparecem se existirem.
CERTIFICACOES = [
    {"emissor": "Microsoft", "periodo": "desde 1995",
     "itens": ["MCSE - Microsoft Certified Systems Engineer", "MCT - Microsoft Certified Trainer", "MCP + Internet"],
     "imagens": [{"arquivo": "certificados/mcse-1995", "alt": "Certificado MCSE Microsoft 1995 Giani Maldaner", "legenda": "MCSE Microsoft, 1995"}]},
    {"emissor": "Novell", "periodo": "primeira metade dos anos 1990 (CNE e CNA)",
     "itens": ["CNE - Certified Novell Engineer", "CNA - Certified Novell Administrator", "CNI - Certified Novell Instructor", "CLP - Certified Linux Professional (SUSE Linux)"],
     "imagens": [{"arquivo": "certificados/novell-cne", "alt": "Certificado Novell CNE Giani Maldaner Porto Alegre", "legenda": "Novell CNE"}]},
    {"emissor": "Citrix", "periodo": "",
     "itens": ["CCA MetaFrame", "XenApp", "Password Manager"],
     "imagens": [{"arquivo": "certificados/citrix-cca", "alt": "Certificado Citrix CCA Giani Maldaner", "legenda": "Citrix CCA"}]},
    {"emissor": "CompTIA", "periodo": "",
     "itens": ["Security+", "Network+", "CTT+"],
     "imagens": [{"arquivo": "certificados/comptia", "alt": "Certificado CompTIA Giani Maldaner", "legenda": "CompTIA"}]},
    {"emissor": "McAfee", "periodo": "",
     "itens": ["Security University", "Defense"],
     "imagens": []},
]

# Casos reais com ano. Fica VAZIO de propósito: só publique o que realmente
# aconteceu e o que o cliente autorizou. Formato:
#   {"ano": "2018", "titulo": "Migração de 80 caixas Exchange para Microsoft 365",
#    "cliente": "Empresa de serviços, Porto Alegre", "texto": "O que foi feito e o resultado."}
CASOS = []

# Mapa slug -> serviço para rota dinâmica
SERVICOS_MAP = {s["slug"]: s for s in SERVICOS}

# Compatibilidade: slugs antigos e variações
SLUG_ALIASES = {
    "redes": "redes-cisco",
    "servidores": "suporte-servidores",
    "seguranca": "firewall-lgpd",
    "cloud": "migracao-azure",
    "azure": "migracao-azure",
    "firewall": "firewall-lgpd",
    "suporte-ti": "suporte-servidores",
    "empresa-ti": "suporte-servidores",
    "redes-corporativas": "redes-cisco",
}

# Páginas fixas (não são serviços) que também aceitam a URL sem barra final
PAGINAS_FIXAS = {"sobre", "certificacoes"}
PAGINAS_ALIASES = {"quem-somos": "sobre", "quem-atende": "sobre", "giani-maldaner": "sobre", "certificados": "certificacoes"}

FAQ = [
    ("A SISNEO TI atende presencialmente em Porto Alegre?",
     "Sim. O atendimento presencial é em Porto Alegre e região, no Rio Grande do Sul, incluindo Zona Norte, Centro, Guaíba, Canoas e região metropolitana. Para o restante do Brasil, o trabalho é feito remotamente com acesso seguro."),
    ("Vocês atendem empresas de fora do Rio Grande do Sul?",
     "Sim. Diagnóstico, configuração de servidores, firewall, migração para Azure e suporte podem ser feitos por acesso remoto seguro, em todo o Brasil."),
    ("Como funciona a migração para o Azure?",
     "Começa com o levantamento do que existe hoje (servidores, e-mail, arquivos, usuários). Depois vem o plano com janelas de mudança, a migração em etapas e o acompanhamento nos primeiros dias, para reduzir o tempo de parada."),
    ("Quem faz o atendimento?",
     "O atendimento é direto com Giani Maldaner, profissional de redes e servidores em Porto Alegre desde 1990, certificado MCSE, MCT, Citrix, CompTIA e Novell, com certificação Microsoft desde 1995. Foi gerente de TI e instrutor Cisco e Microsoft na Sisnema Soluções antes de atender pela SISNEO TI. Sem intermediários."),
    ("O que a IA pode fazer pela minha empresa?",
     "Um agente de IA pode responder dúvidas de clientes usando os seus próprios manuais e regras (RAG), separar contatos que realmente querem comprar e encaminhar para o WhatsApp da equipe. A conversa é construída a partir do material da sua empresa."),
    ("Meus dados enviados no formulário estão protegidos?",
     "Os dados são usados apenas para retornar o seu contato e ficam armazenados em ambiente protegido no Azure. Detalhes na Política de Privacidade, de acordo com a LGPD."),
]

NECESSIDADES = [
    ("rede", "Rede, Wi-Fi, switches ou roteadores"),
    ("servidor", "Servidores, Active Directory ou virtualização"),
    ("firewall", "Firewall e segurança / LGPD"),
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
    except FileExistsError:
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

BOT_RE = re.compile(r"bot|crawl|spider|slurp|facebookexternalhit|preview|monitor|uptime|lighthouse|headless", re.I)
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
            _flock(fd)
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
            os.close(fd)
    return n

def client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    ip = xff.split(",")[0].strip() if xff else (request.remote_addr or "")
    if ip.count(":") == 1 and "." in ip:
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
    return time.time() - int(ts) >= 3

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

IMG_EXTS = (".webp", ".jpg", ".jpeg", ".png")

def resolve_img(base):
    """Retorna o caminho relativo a /static/ do primeiro arquivo existente, ou None."""
    for ext in IMG_EXTS:
        rel = base + ext
        if os.path.isfile(os.path.join(BASE_DIR, "static", "img", rel)):
            return "img/" + rel
    return None

def person_node():
    org_id = SITE_URL + "/#organization"
    person_id = SITE_URL + "/#giani"
    creds = []
    for c in CERTIFICACOES:
        for item in c["itens"]:
            creds.append({
                "@type": "EducationalOccupationalCredential",
                "name": f"{c['emissor']} {item}",
                "credentialCategory": "certification",
                "recognizedBy": {"@type": "Organization", "name": c["emissor"]},
            })
    node = {
        "@context": "https://schema.org",
        "@type": "Person",
        "@id": person_id,
        "name": "Giani Maldaner",
        "url": SITE_URL + "/sobre/",
        "mainEntityOfPage": SITE_URL + "/sobre/",
        "jobTitle": f"Especialista em redes, servidores e infraestrutura de TI - {ANOS_EXPERIENCIA} anos de experiência",
        "description": (f"Profissional de redes e servidores em Porto Alegre desde {INICIO_CARREIRA}. "
                        "Certificado Microsoft desde 1995 (MCSE, MCT), com certificações Novell, Citrix e CompTIA. "
                        "Foi gerente de TI e instrutor Cisco e Microsoft na Sisnema Soluções e hoje atende pela SISNEO TI."),
        "image": SITE_URL + "/static/img/giani.webp",
        "email": EMPRESA["email"],
        "workLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "Porto Alegre", "addressRegion": "RS", "addressCountry": "BR"}},
        "worksFor": [
            {"@type": "Organization", "@id": org_id, "name": "SISNEO TI", "url": SITE_URL + "/"},
            {"@type": "OrganizationRole", "roleName": "Gerente de TI e instrutor Cisco e Microsoft",
             "startDate": "1995", "endDate": "2020",
             "worksFor": {"@type": "Organization", "name": "Sisnema Soluções",
                          "address": {"@type": "PostalAddress", "addressLocality": "Porto Alegre", "addressRegion": "RS", "addressCountry": "BR"}}},
        ],
        "knowsAbout": ["Redes Cisco", "Novell NetWare", "Windows Server", "Active Directory", "Azure", "Microsoft 365",
                       "Firewall", "LGPD", "Inteligência Artificial", "RAG", "Wi-Fi corporativo"],
        "hasCredential": creds,
    }
    if SAME_AS:
        node["sameAs"] = SAME_AS
    return node

def person_ld():
    return json.dumps(person_node(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def json_ld_sobre():
    data = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Sobre Giani Maldaner", "item": SITE_URL + "/sobre/"}]},
        {"@context": "https://schema.org", "@type": "ProfilePage", "@id": SITE_URL + "/sobre/#profile",
         "url": SITE_URL + "/sobre/", "inLanguage": "pt-BR",
         "name": f"Giani Maldaner - Redes e Servidores em Porto Alegre desde {INICIO_CARREIRA}",
         "mainEntity": {"@id": SITE_URL + "/#giani"}, "about": {"@id": SITE_URL + "/#giani"}},
    ]
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def json_ld_certificacoes():
    data = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": "Sobre Giani Maldaner", "item": SITE_URL + "/sobre/"},
        {"@type": "ListItem", "position": 3, "name": "Certificações", "item": SITE_URL + "/certificacoes/"}]}]
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def json_ld_home():
    org_id = SITE_URL + "/#organization"
    person_id = SITE_URL + "/#giani"
    geo = {"@type": "GeoCoordinates", "latitude": -30.0346, "longitude": -51.2177}
    address = {"@type": "PostalAddress", "addressLocality": "Porto Alegre", "addressRegion": "RS", "addressCountry": "BR", "postalCode": "91430"}
    data = [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": org_id,
            "name": "SISNEO TI",
            "alternateName": ["SISNEO", "sisneo.com.br"],
            "url": SITE_URL + "/",
            "logo": SITE_URL + "/static/favicon.svg",
            "image": SITE_URL + "/static/img/og-sisneo.jpg",
            "taxID": EMPRESA["cnpj"],
            "email": EMPRESA["email"],
            "telephone": "+5551998365106",
            "founder": {"@id": person_id},
            "employee": {"@id": person_id},
            "address": address,
            "contactPoint": [{"@type": "ContactPoint", "contactType": "sales", "telephone": "+5551998365106", "email": EMPRESA["email"], "areaServed": "BR", "availableLanguage": ["pt-BR"]}],
        },
        {
            "@context": "https://schema.org",
            "@type": ["LocalBusiness", "ProfessionalService"],
            "@id": SITE_URL + "/#localbusiness",
            "name": "SISNEO TI - Suporte em Redes, Servidores e Azure em Porto Alegre",
            "description": "Redes de computadores, servidores, firewall, migração para Azure e agentes de IA para empresas em Porto Alegre, no Rio Grande do Sul e em todo o Brasil.",
            "url": SITE_URL + "/",
            "image": SITE_URL + "/static/img/og-sisneo.jpg",
            "telephone": "+5551998365106",
            "email": EMPRESA["email"],
            "taxID": EMPRESA["cnpj"],
            "priceRange": "$$",
            "address": address,
            "geo": geo,
            "areaServed": [
                {"@type": "City", "name": "Porto Alegre"},
                {"@type": "City", "name": "Guaíba"},
                {"@type": "City", "name": "Canoas"},
                {"@type": "AdministrativeArea", "name": "Rio Grande do Sul"},
                {"@type": "Country", "name": "Brasil"},
            ],
            "parentOrganization": {"@id": org_id},
            "hasOfferCatalog": {
                "@type": "OfferCatalog", "name": "Serviços SISNEO TI Porto Alegre",
                "itemListElement": [
                    {"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["titulo_seo"], "url": SITE_URL + "/" + s["slug"] + "/", "description": s["desc_seo"]}} for s in SERVICOS
                ],
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": SITE_URL + "/#website",
            "url": SITE_URL + "/",
            "name": "SISNEO TI - Suporte de TI Porto Alegre",
            "inLanguage": "pt-BR",
            "publisher": {"@id": org_id},
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ],
        },
    ]
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return out.replace("</", "<\\/")

def json_ld_service(servico):
    data = [
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": servico["titulo_seo"], "item": SITE_URL + "/" + servico["slug"] + "/"}
            ]
        },
        {
            "@context": "https://schema.org",
            "@type": "Service",
            "name": servico["titulo_seo"],
            "description": servico["desc_seo"],
            "provider": {"@id": SITE_URL + "/#organization"},
            "areaServed": {"@type": "City", "name": "Porto Alegre"},
            "serviceType": servico["titulo"],
            "url": SITE_URL + "/" + servico["slug"] + "/",
            "image": SITE_URL + "/static/img/og-sisneo.jpg"
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ[:3]],
        }
    ]
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

@app.context_processor
def inject_globals():
    return {"E": EMPRESA, "SITE_URL": SITE_URL, "asset": asset, "wa_link": wa_link, "year": datetime.now().year,
            "SERVICOS": SERVICOS, "TIMELINE": TIMELINE, "ANOS": ANOS_EXPERIENCIA, "INICIO": INICIO_CARREIRA,
            "person_ld": person_ld()}

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
        token=new_form_token(), jsonld=json_ld_home(), counter=fmt_int(total),
        show_counter=os.environ.get("SHOW_COUNTER", "1") != "0", noindex=noindex)
    resp = make_response(html, status)
    if is_new:
        resp.set_cookie(COOKIE_UV, "1", max_age=86400, secure=request.is_secure, httponly=True, samesite="Lax", path="/")
    return resp

@app.route("/")
def index():
    return render_home()

@app.route("/sobre/")
def sobre():
    fotos = []
    for f in FOTOS:
        src = resolve_img(f["arquivo"])
        if src:
            fotos.append(dict(f, src=src))
    return render_template("sobre.html", fotos=fotos, casos=CASOS, certs=CERTIFICACOES,
                           jsonld=json_ld_sobre(), noindex=False)

@app.route("/certificacoes/")
def certificacoes():
    certs = []
    for c in CERTIFICACOES:
        imgs = []
        for im in c["imagens"]:
            src = resolve_img(im["arquivo"])
            if src:
                imgs.append(dict(im, src=src))
        certs.append(dict(c, imgs=imgs))
    return render_template("certificacoes.html", certs=certs, jsonld=json_ld_certificacoes(), noindex=False)

# --- NOVAS ROTAS SEO: páginas dedicadas para cada serviço (essencial para rankear) ---
@app.route("/<slug>/")
def servico_page(slug):
    # Normaliza slug
    slug = slug.strip("/").lower()
    # Alias
    if slug in PAGINAS_ALIASES:
        return redirect(f"/{PAGINAS_ALIASES[slug]}/", code=301)
    if slug in SLUG_ALIASES:
        return redirect(f"/{SLUG_ALIASES[slug]}/", code=301)
    # Verifica se é serviço válido
    if slug not in SERVICOS_MAP:
        abort(404)
    serv = SERVICOS_MAP[slug]
    # FAQ específico por serviço para SEO
    faq_serv = {
        "redes-cisco": [
            ("Vocês configuram VLAN e VPN Cisco em Porto Alegre?", "Sim. VLANs, trunk, roteamento inter-VLAN e VPN IPsec/SSL site-to-site e cliente, presencial em Porto Alegre e remoto."),
            ("Fazem Wi-Fi corporativo que não cai?", "Sim. Site survey, ajuste de canais, potência e 802.1X para acabar com queda."),
            ("Atendem PMEs?", "Sim, empresas de 10 a 100 usuários em Porto Alegre e região metropolitana."),
        ],
        "suporte-servidores": [
            ("Suporte para Windows Server antigo?", "Sim, de 2008 a 2022. Avalio risco e planejo upgrade ou migração Azure."),
            ("Fazem AD do zero?", "Sim. AD, DNS, DHCP, GPO e políticas de segurança."),
        ],
        "firewall-lgpd": [
            ("Firewall resolve LGPD?", "É parte. Implemento controle de acesso, backup com teste e trilha para seu jurídico."),
            ("Backup que funciona?", "Sim, local + Azure com teste de restore. Backup não testado não é backup."),
        ],
        "migracao-azure": [
            ("Quanto tempo leva migrar para Azure?", "PMEs 20-50 usuários: 2 a 4 semanas com janelas noturnas."),
            ("E-mail para?", "Não. Coexistência e TTL baixo, sem perda."),
        ],
    }
    faq = faq_serv.get(slug, FAQ[:3])
    html = render_template(
        "servico.html",
        servico=serv,
        servicos=SERVICOS,
        faq=faq,
        jsonld=json_ld_service(serv),
        token=new_form_token(),
        noindex=False
    )
    return html

# Compatibilidade com URLs antigas sem trailing slash
@app.route("/<slug>")
def servico_page_no_slash(slug):
    if slug in PAGINAS_ALIASES:
        return redirect(f"/{PAGINAS_ALIASES[slug]}/", code=301)
    if slug in SERVICOS_MAP or slug in SLUG_ALIASES or slug in PAGINAS_FIXAS:
        return redirect(f"/{slug.strip('/')}/", code=301)
    abort(404)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

@app.route("/contato", methods=["POST"])
def contato():
    f = request.form
    values = {k: f.get(k, "").strip() for k in
              ("nome", "whatsapp", "email", "empresa", "necessidade", "porte", "urgencia", "mensagem")}
    values["lgpd"] = f.get("lgpd", "")
    errors = []
    if f.get("website"):
        errors.append("Erro de validação.")
    if not valid_form_token(f.get("t", "")):
        errors.append("Formulário expirado. Recarregue a página e tente novamente.")
    if rate_limited():
        errors.append("Muitas tentativas. Aguarde alguns minutos.")
    if len(values["nome"]) < 2:
        errors.append("Informe seu nome.")
    if len(values["whatsapp"]) < 10:
        errors.append("Informe WhatsApp com DDD.")
    if values["email"] and not EMAIL_RE.match(values["email"]):
        errors.append("E-mail inválido.")
    if not values["necessidade"] or values["necessidade"] not in [k for k,_ in NECESSIDADES]:
        errors.append("Selecione o que você precisa.")
    if not values["porte"] or values["porte"] not in [k for k,_ in PORTES]:
        errors.append("Selecione o tamanho da empresa.")
    if not values["urgencia"] or values["urgencia"] not in [k for k,_ in URGENCIAS]:
        errors.append("Selecione a urgência.")
    if not values["lgpd"]:
        errors.append("É necessário aceitar a política de privacidade.")
    if errors:
        return render_home(errors=errors, values=values, status=400, noindex=True)

    # Salva lead
    try:
        rec = {
            "data_hora": datetime.now(timezone.utc).isoformat(),
            "ip_hash": ip_hash(),
            "nome": values["nome"],
            "whatsapp": values["whatsapp"],
            "email": values["email"],
            "empresa": values["empresa"],
            "necessidade": values["necessidade"],
            "porte": values["porte"],
            "urgencia": values["urgencia"],
            "mensagem": values["mensagem"][:1000],
            "origem": request.referrer or "",
            "pagina": values.get("necessidade", "") + " - " + request.path
        }
        with _proc_lock:
            with open(LEADS_FILE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass

    # Token de obrigado
    payload = {"n": values["nome"].split()[0][:30], "ts": int(time.time())}
    tok = _thanks.dumps(payload)
    return redirect(f"/obrigado?t={tok}", code=303)

@app.route("/obrigado")
def obrigado():
    tok = request.args.get("t", "")
    try:
        data = _thanks.loads(tok, max_age=3600)
        nome = data.get("n", "")
    except (BadSignature, SignatureExpired):
        abort(404)
    msg = f"Olá, Giani! Enviei o formulário pelo site. Sou {nome} e gostaria de falar sobre TI."
    wa = wa_link(msg)
    return render_template("obrigado.html", nome=nome, wa=wa)

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
    # URLs principais + todas as páginas de serviço - ESSENCIAL para SEO
    urls = [
        ("/", lm("index.html"), "1.0", "weekly"),
        ("/sobre/", lm("sobre.html"), "0.8", "monthly"),
        ("/certificacoes/", lm("certificacoes.html"), "0.7", "monthly"),
        ("/privacidade", lm("privacidade.html"), "0.3", "yearly"),
    ]
    # Adiciona páginas de serviço com prioridade alta
    for s in SERVICOS:
        urls.append((f"/{s['slug']}/", lm("servico.html") if os.path.exists(os.path.join(BASE_DIR, "templates", "servico.html")) else lm("index.html"), "0.9", "weekly"))
    
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

def _check_admin():
    pwd = os.environ.get("ADMIN_PASSWORD")
    if not pwd:
        abort(404)
    auth = request.authorization
    user = os.environ.get("ADMIN_USER", "admin")
    ok = (auth and auth.username is not None and auth.password is not None
          and secrets.compare_digest(auth.username, user) and secrets.compare_digest(auth.password, pwd))
    if not ok:
        resp = Response("Acesso restrito.", 401, {"WWW-Authenticate": 'Basic realm="SISNEO TI"'})
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

@app.errorhandler(404)
def not_found(_e):
    return render_template("erro.html", titulo="Página não encontrada",
                           texto="O endereço não existe ou foi movido. Veja nossos serviços em Porto Alegre."), 404

@app.errorhandler(413)
@app.errorhandler(500)
def server_error(e):
    return render_template("erro.html", titulo="Algo deu errado",
                           texto="Tente novamente em instantes ou fale direto pelo WhatsApp."), getattr(e, "code", 500)

@app.before_request
def canonical_host():
    if request.path == "/healthz":
        return None
    host = request.host.split(":")[0].lower()
    if host == SITE_HOST:
        return None
    if host == "www." + SITE_HOST or host.endswith(".azurewebsites.net"):
        target = SITE_URL + request.full_path.rstrip("?")
        code = 301 if request.method in ("GET", "HEAD") else 308
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
