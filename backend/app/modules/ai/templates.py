"""Deterministic, local language support; financial facts are never recomputed."""
import re
from decimal import Decimal
import unicodedata


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


KEYWORDS = {
    'shelter': ('flood', 'flooded', 'shelter', 'dry place', 'inundado', 'inundada', 'inundacion', 'refugio', 'ngap', 'cho o'),
    'warmth': ('cold', 'freezing', 'no heat', 'frio', 'calefaccion', 'lanh', 'suoi'),
    'claim': ('claim', 'reclamo', 'bao hiem'),
    'repair': ('repair', 'roof', 'techo', 'pipe', 'tuberia', 'sua chua', 'mai nha'),
    'medical': ('hurt', 'injured', 'oxygen', 'medical', 'herido', 'herida', 'oxigeno', 'medico', 'bi thuong', 'oxy', 'y te'),
    'food_water': ('food', 'water', 'agua', 'comida', 'nuoc', 'thuc an'),
}


def classify(text, language_hint):
    value = normalized(text)
    if re.search(r'\b(mi|papa|oxigeno|luz|inundado|inundada|personas|ninos|frio|refugio|reclamo|agua|comida)\b', value):
        language = 'es'
    elif re.search(r'\b(ngap|lanh|nguoi|tre|nuoc|toi|can|oxy)\b', value) and (language_hint == 'vi' or any(c in text for c in 'ăâđêôơưạảấầếệịọớợụứự')):
        language = 'vi'
    else:
        language = language_hint if language_hint in ('en', 'es', 'vi') else 'en'
    needs = [need for need, words in KEYWORDS.items() if any(re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)', value) for word in words)] or ['info']
    totals = re.findall(r'\b(\d+)\s*(?:people|persons|personas|nguoi)\b', value)
    children = re.findall(r'\b(\d+)\s*(?:kids|children|ninos|ninas|tre)\b', value)
    people = max(1, int(totals[0])) if totals else 1 + sum(map(int, children))
    labels = {'shelter': 'shelter', 'warmth': 'warmth', 'claim': 'claim assistance', 'repair': 'repairs', 'medical': 'medical assistance', 'food_water': 'food or water', 'info': 'information'}
    return {'needs': needs, 'people': people, 'urgent': 'medical' in needs, 'language': language, 'summary': ('Needs ' + ', '.join(labels[n] for n in needs))[:100]}


RESIDENT = {
    'en': {'redirect': 'Go to {site_name}, {address}. {details}', 'reroute': 'Your previous site is unavailable. Go to {site_name}, {address}. {details}', 'ack': 'We received your request. {details}'},
    'es': {'redirect': 'Vaya a {site_name}, {address}. {details}', 'reroute': 'El sitio anterior no está disponible. Vaya a {site_name}, {address}. {details}', 'ack': 'Recibimos su solicitud. {details}'},
    'vi': {'redirect': 'Hãy đến {site_name}, {address}. {details}', 'reroute': 'Địa điểm cũ không còn phục vụ. Hãy đến {site_name}, {address}. {details}', 'ack': 'Chúng tôi đã nhận yêu cầu. {details}'},
}
ENGLISH = {'task': 'Operation Storm task {work_order_id}: {building_name}. {task_text} Reply DONE, BLOCKED or send a photo.', 'tenant_notice': 'Notice from {building_name}: {notice}', 'exec_summary_intro': 'Portfolio disaster impact: {summary}'}


def compose(purpose, facts, language):
    if purpose not in ENGLISH and purpose not in RESIDENT['en']:
        raise ValueError(f'Unknown compose purpose: {purpose}')
    data = {key: str(value) for key, value in facts.items() if value is not None}
    # Callers should supply explicit facts; aliases accept contract resource/work-order names.
    defaults = {'site_name': data.get('resource_name', data.get('name', 'help site')), 'address': '', 'details': '', 'work_order_id': data.get('id', ''), 'building_name': '', 'task_text': data.get('text', ''), 'notice': data.get('tenant_notice_text', data.get('text', '')), 'summary': ''}
    data = defaults | data
    template = RESIDENT.get(language, RESIDENT['en']).get(purpose) or ENGLISH.get(purpose)
    result = template.format_map(data).strip()
    if len(result) <= 320:
        return result
    # Never silently truncate the routing address or task instructions.
    if purpose in ('redirect', 'reroute'):
        minimal = RESIDENT.get(language, RESIDENT['en'])[purpose].format_map(data | {'details': '', 'site_name': ''}).strip()
        if len(minimal) <= 320:
            return minimal
    raise ValueError('Required message facts exceed the 320-character SMS limit')


def dollars(cents):
    return '${:,.2f}'.format(cents / 100)


def compact_dollars(cents):
    amount = Decimal(str(cents)) / 100
    magnitude = abs(amount)
    for scale, suffix in [(10**9, 'B'), (10**6, 'M'), (10**3, 'k')]:
        if magnitude >= scale:
            value = format(amount / scale, '.2f').rstrip('0').rstrip('.')
            return '${}{}'.format(value, suffix)
    return '${}'.format(format(amount, '.2f').rstrip('0').rstrip('.'))


def rationale(facts):
    return 'Cost {cost}; avoids {avoided} in estimated losses.'.format(cost=compact_dollars(facts.get('cost_cents', 0)), avoided=compact_dollars(facts.get('avoided_cents', 0)))


def report(kind, facts):
    if kind not in ('executive_summary', 'tenant_notice'):
        raise ValueError(f'Unknown report kind: {kind}')
    title = 'Executive summary' if kind == 'executive_summary' else 'Tenant notice'
    # Consumers must sanitize Markdown before rendering HTML.
    rows = ['# ' + title, '', 'Illustrative disaster model; synthetic portfolio and financial estimates.', '']
    for key, value in facts.items():
        display = dollars(value) if key.endswith('_cents') and isinstance(value, (int, float)) else str(value)
        rows.append('- {}: {}'.format(key.replace('_', ' '), display.replace('\n', ' ').replace('\r', ' ')))
    return '\n'.join(rows)
