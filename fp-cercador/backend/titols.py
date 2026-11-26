"""
titols.py — Títols en majúscules → text llegible (Pla 096).

El SEPE (i alguns títols en català del SOC) envia els títols TOT EN MAJÚSCULES.
Passar-los a minúscules a seques perd sigles i noms propis («azure», «html»).
`display_title()` és una funció pura que:

  1. passa cada paraula a minúscules i posa majúscula a l'inici del títol i
     després de «. » i «: »;
  2. conserva tal qual les paraules sense vocals (PRL, CNC, SQL), les que porten
     xifres (3D, HTML5, B2) i els números romans;
  3. aplica PRESERVE per als casos ambigus: sigles amb vocals (BIM, SAP, IA) i
     noms propis (Azure, Moodle, Red Hat).

Les paraules que ja vénen amb alguna minúscula es respecten: l'autor del títol
ja va triar com s'escrivien (p. ex. «IcadTAC», «I+D+i»).
"""
import re

# Clau: paraula (o seqüència de paraules separades per un espai) tal com surt en
# majúscules. Valor: com s'ha d'escriure. Llista preparada repassant les paraules
# més freqüents del catàleg del SEPE (2026-11-26).
PRESERVE = {
    # --- Sigles amb vocals ---
    'ABAP': 'ABAP', 'ABB': 'ABB', 'ACS': 'ACS', 'ADAS': 'ADAS', 'ADR': 'ADR', 'AI': 'AI',
    'AICLE': 'AICLE', 'AJAX': 'AJAX', 'AMFE': 'AMFE', 'API': 'API', 'APIS': 'APIs',
    'APPCC': 'APPCC', 'AR': 'AR', 'ASP': 'ASP', 'ATEX': 'ATEX', 'AWS': 'AWS', 'BI': 'BI',
    'BIM': 'BIM', 'CAD': 'CAD', 'CAE': 'CAE', 'CAM': 'CAM', 'CAP': 'CAP', 'CCNA': 'CCNA',
    'CEE': 'CEE', 'CEH': 'CEH', 'CMMI': 'CMMI', 'COEX': 'COEX', 'COVID': 'COVID', 'CTE': 'CTE', 'DORA': 'DORA',
    'EDAR': 'EDAR', 'EEUU': 'EEUU', 'EESS': 'EESS', 'EFQM': 'EFQM', 'ELA': 'ELA',
    'EPI': 'EPI', 'EPIS': 'EPIS', 'ERP': 'ERP', 'ERPS': 'ERPs', 'ESG': 'ESG', 'ETAP': 'ETAP', 'FCAW': 'FCAW',
    'GIS': 'GIS', 'GMAW': 'GMAW', 'IA': 'IA', 'IAG': 'IAG', 'IBM': 'IBM', 'IFS': 'IFS',
    'IMDG': 'IMDG', 'IOT': 'IoT', 'IP': 'IP', 'IPPC': 'IPPC', 'IRPF': 'IRPF', 'ISO': 'ISO',
    'ISTQB': 'ISTQB', 'IT': 'IT', 'ITIL': 'ITIL', 'ITV': 'ITV', 'IVA': 'IVA', 'JPA': 'JPA',
    'LGTBI': 'LGTBI', 'LOMCE': 'LOMCE', 'LOPD': 'LOPD', 'LOPDGDD': 'LOPDGDD', 'LPIC': 'LPIC',
    'MAG': 'MAG', 'MCER': 'MCER', 'MCSA': 'MCSA', 'MIFID': 'MiFID', 'MIG': 'MIG', 'MO': 'MO',
    'MOS': 'MOS', 'NEE': 'NEE', 'NET': 'NET', 'NNA': 'NNA', 'NOSQL': 'NoSQL', 'ODS': 'ODS',
    'OKR': 'OKR', 'OLAP': 'OLAP', 'ONU': 'ONU', 'OTRS': 'OTRS', 'PDA': 'PDA', 'PEMP': 'PEMP',
    'PMI': 'PMI', 'POO': 'POO', 'PWA': 'PWA', 'PYME': 'PYME', 'PYMES': 'PYMES',
    'RAEE': 'RAEE', 'RHCSA': 'RHCSA', 'ROI': 'ROI', 'RPA': 'RPA', 'RPAS': 'RPAS', 'SAP': 'SAP',
    'SATE': 'SATE', 'SCORM': 'SCORM', 'SEM': 'SEM', 'SEO': 'SEO', 'SEPA': 'SEPA', 'SIG': 'SIG',
    'SMAW': 'SMAW', 'SMED': 'SMED', 'TCAE': 'TCAE', 'TEA': 'TEA', 'TI': 'TI', 'TIC': 'TIC',
    'TICS': 'TIC', 'TIG': 'TIG', 'UAS': 'UAS', 'UCI': 'UCI', 'UE': 'UE', 'UI': 'UI', 'UML': 'UML',
    'UNE': 'UNE', 'UNE EN': 'UNE EN', 'UX': 'UX', 'VOIP': 'VoIP', 'QGIS': 'QGIS',
    # --- Noms propis, marques i productes ---
    '3DS MAX': '3ds Max',
    'ADOBE': 'Adobe', 'AFTER EFFECTS': 'After Effects', 'ALLPLAN': 'Allplan', 'ALZHEIMER': 'Alzheimer',
    'AMADEUS': 'Amadeus', 'AMAZON': 'Amazon', 'ANDROID': 'Android', 'ANGULAR': 'Angular',
    'ANSIBLE': 'Ansible', 'APACHE': 'Apache', 'ARCGIS': 'ArcGIS', 'ARDUINO': 'Arduino',
    'AUTOCAD': 'AutoCAD', 'AUTODESK': 'Autodesk', 'AZURE': 'Azure', 'BASILEA': 'Basilea',
    'BLENDER': 'Blender', 'CATIA': 'CATIA', 'CHATGPT': 'ChatGPT', 'CISCO': 'Cisco', 'CITRIX': 'Citrix',
    'CLOUDERA': 'Cloudera', 'COBOL': 'COBOL', 'CONTAPLUS': 'ContaPlus', 'COPILOT': 'Copilot',
    'CYPECAD': 'CYPECAD', 'DAVINCI': 'DaVinci', 'DEVOPS': 'DevOps', 'DIALUX': 'DIALux',
    'DJANGO': 'Django', 'DOCKER': 'Docker', 'ESPAÑA': 'España', 'ESRI': 'Esri', 'EUROPA': 'Europa',
    'EXCEL': 'Excel', 'FACEBOOK': 'Facebook', 'FACTURAPLUS': 'FacturaPlus', 'FANUC': 'Fanuc',
    'FINAL CUT': 'Final Cut', 'FLUTTER': 'Flutter', 'GOOGLE': 'Google', 'GVSIG': 'gvSIG',
    'HADOOP': 'Hadoop', 'HIBERNATE': 'Hibernate', 'HYPER': 'Hyper', 'ILLUSTRATOR': 'Illustrator',
    'INDESIGN': 'InDesign', 'IONIC': 'Ionic', 'INSTAGRAM': 'Instagram', 'IOS': 'iOS', 'IPAD': 'iPad', 'IPHONE': 'iPhone',
    'JAVA': 'Java', 'JAVASCRIPT': 'JavaScript', 'JBOSS': 'JBoss', 'JOOMLA': 'Joomla', 'KOTLIN': 'Kotlin',
    'KUBERNETES': 'Kubernetes', 'LARAVEL': 'Laravel', 'LIFERAY': 'Liferay', 'LIGHTROOM': 'Lightroom',
    'LINKEDIN': 'LinkedIn', 'LINUX': 'Linux', 'MAILCHIMP': 'Mailchimp', 'MASTERCAM': 'Mastercam',
    'MAYA': 'Maya', 'MICROSOFT': 'Microsoft', 'MICROSOFT PROJECT': 'Microsoft Project',
    'MICROSTATION': 'MicroStation', 'MONGODB': 'MongoDB',
    'MOODLE': 'Moodle', 'MYSQL': 'MySQL', 'NAVISWORKS': 'Navisworks', 'NODEJS': 'Node.js',
    'NOMINAPLUS': 'NominaPlus', 'OFFICE': 'Office', 'OMRON': 'Omron', 'OPENAI': 'OpenAI',
    'OPENSHIFT': 'OpenShift', 'OPENSTACK': 'OpenStack', 'ORACLE': 'Oracle', 'OUTLOOK': 'Outlook',
    'PARKINSON': 'Parkinson', 'PHOTOSHOP': 'Photoshop', 'POWER BI': 'Power BI',
    'POWER POINT': 'PowerPoint', 'POWERPOINT': 'PowerPoint', 'PREMIERE': 'Premiere',
    'PRESTASHOP': 'PrestaShop', 'PYTHON': 'Python', 'RASPBERRY': 'Raspberry', 'RED HAT': 'Red Hat',
    'REVIT': 'Revit', 'SAGE': 'Sage', 'SALESFORCE': 'Salesforce', 'SCRUM': 'Scrum',
    'SHAREPOINT': 'SharePoint', 'SIEMENS': 'Siemens', 'SKETCHUP': 'SketchUp', 'SOLID EDGE': 'Solid Edge', 'SOLIDWORKS': 'SolidWorks',
    'SPRING': 'Spring', 'SUCCESSFACTORS': 'SuccessFactors', 'SYMFONY': 'Symfony', 'TABLEAU': 'Tableau',
    'TEAMS': 'Teams', 'TENSORFLOW': 'TensorFlow', 'TIKTOK': 'TikTok', 'TRELLO': 'Trello',
    'UBUNTU': 'Ubuntu', 'UIPATH': 'UiPath', 'UNITY': 'Unity', 'UNIX': 'Unix', 'UNREAL': 'Unreal',
    'VMWARE': 'VMware', 'VSPHERE': 'vSphere', 'WEBLOGIC': 'WebLogic', 'WEBSPHERE': 'WebSphere',
    'WHATSAPP': 'WhatsApp', 'WINDOWS': 'Windows', 'WOOCOMMERCE': 'WooCommerce', 'WORD': 'Word',
    'WORDPRESS': 'WordPress', 'ZBRUSH': 'ZBrush',
}
_PHRASES = sorted((k.split(' ') for k in PRESERVE if ' ' in k), key=len, reverse=True)

_RE_WORD = re.compile(r'[^\W_]+')
_RE_DOTTED = re.compile(r'(?<![^\W_])(?:[^\W\d_]\.){2,}')    # F.E.V.S., I.T.
_ROMAN = re.compile(r'^(?:X{0,3})(?:IX|IV|V?I{0,3})$')
_VOWELS = set('AEIOUÁÉÍÓÚÀÈÒÏÜaeiouáéíóúàèòïü')
# Inici de títol o després de «. »/«: », però no després d'una sigla amb punts («F.E.V.S. que»).
_SENTENCE_GAP = re.compile(r'(?:^|(?<!\.[^\W\d_])[.:]\s+)[\W_]*$')


def _is_roman(word: str, before: str, after: str) -> bool:
    if not word or not _ROMAN.match(word):
        return False
    # «I» i «VI» també són paraules (conjunció i «vi» en català): només es prenen com a
    # números romans al final del títol o just abans de puntuació.
    if word in ('I', 'VI'):
        return after.strip() == '' or after.lstrip()[:1] in ':.,;)+-/'
    return True


def _word_case(word: str, before: str, after: str) -> tuple:
    """(text, és_minúscula_nostra)."""
    if any(ch.islower() for ch in word):
        return word, False
    if word in PRESERVE:
        return PRESERVE[word], False
    if any(ch.isdigit() for ch in word):
        return word, False
    if _is_roman(word, before, after):
        return word, False
    if len(word) == 1:
        # Elisions catalanes (D', L', S') i prefixos (e-learning): minúscula.
        if after[:1] in ("'", '’') or (after[:1] == '-' and after[1:2].isalpha()):
            return word.lower(), True
        if word in 'AEIOUY' or word in 'ÀÉÈÍÒÓÚ':
            if before[-1:] == '+' or after[:1] == '+':   # I+D+I
                return word, False
            return word.lower(), True
        return word, False                              # C, D, S… (llenguatge C, etc.)
    if not any(ch in _VOWELS for ch in word):
        return word, False
    return word.lower(), True


def display_title(text):
    """Títol en majúscules → títol amb majúscules només on toca."""
    if not text:
        return text or ''
    protected = [m.span() for m in _RE_DOTTED.finditer(text)]
    words = list(_RE_WORD.finditer(text))
    out = []
    pos = 0
    i = 0
    while i < len(words):
        m = words[i]
        out.append(text[pos:m.start()])
        # Frases de PRESERVE (RED HAT, POWER BI…): paraules separades per un sol espai.
        matched = None
        for phrase in _PHRASES:
            seq = words[i:i + len(phrase)]
            if (len(seq) == len(phrase) and [w.group() for w in seq] == phrase
                    and all(text[a.end():b.start()] == ' ' for a, b in zip(seq, seq[1:]))):
                matched = seq
                break
        if matched:
            out.append(PRESERVE[' '.join(w.group() for w in matched)])
            pos = matched[-1].end()
            i += len(matched)
            continue
        word = m.group()
        if any(a <= m.start() < b for a, b in protected):
            shown, ours = word, False
        else:
            shown, ours = _word_case(word, text[:m.start()], text[m.end():])
        if ours and _SENTENCE_GAP.search(''.join(out)):
            shown = shown[:1].upper() + shown[1:]
        out.append(shown)
        pos = m.end()
        i += 1
    out.append(text[pos:])
    return ''.join(out)
