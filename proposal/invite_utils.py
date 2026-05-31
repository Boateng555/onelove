import secrets

from django.urls import reverse


def generate_invite_token():
    return secrets.token_urlsafe(9)[:12]


def invite_session_key(invite, key):
    return f'inv_{invite.id}_{key}'


def get_invite_session(request, invite, key, default=None):
    return request.session.get(invite_session_key(invite, key), default)


def set_invite_session(request, invite, key, value):
    request.session[invite_session_key(invite, key)] = value


def invite_public_path(token, page=''):
    base = reverse('invite_ask', kwargs={'token': token})
    if not page:
        return base
    return base.rstrip('/') + f'/{page}/'


def format_name_line(line, name):
    if name:
        return line.replace('{name}', name)
    cleaned = line.replace('{name}', '')
    while '  ' in cleaned:
        cleaned = cleaned.replace('  ', ' ')
    return cleaned.replace(' ?', '?').replace(' .', '.').strip(' ,.')
