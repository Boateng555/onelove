import mimetypes
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import Storage


class DatabaseStorage(Storage):
    """Store uploaded media in Postgres — works on Vercel after Django optimizes files."""

    def _open(self, name, mode='rb'):
        from .models import StoredMedia

        obj = StoredMedia.objects.get(name=name)
        return ContentFile(bytes(obj.data), name=name)

    def _save(self, name, content):
        from .models import StoredMedia

        content.seek(0)
        data = content.read()
        content_type = (
            getattr(content, 'content_type', None)
            or mimetypes.guess_type(name)[0]
            or 'application/octet-stream'
        )
        if name.lower().endswith('.mp4'):
            content_type = 'video/mp4'
        elif name.lower().endswith('.webm'):
            content_type = 'video/webm'
        elif name.lower().endswith('.mov'):
            content_type = 'video/quicktime'
        StoredMedia.objects.update_or_create(
            name=name,
            defaults={
                'data': data,
                'content_type': content_type,
                'size': len(data),
            },
        )
        return name

    def delete(self, name):
        from .models import StoredMedia

        StoredMedia.objects.filter(name=name).delete()

    def exists(self, name):
        from .models import StoredMedia

        return StoredMedia.objects.filter(name=name).exists()

    def url(self, name):
        if not name:
            return ''
        return f'/media/{name}'

    def size(self, name):
        from .models import StoredMedia

        return StoredMedia.objects.get(name=name).size

    def get_available_name(self, name, max_length=None):
        stem = Path(name).stem
        suffix = Path(name).suffix
        folder = str(Path(name).parent)
        if folder == '.':
            folder = ''

        candidate = name
        while self.exists(candidate):
            token = uuid.uuid4().hex[:8]
            base = f'{folder}/{stem}_{token}{suffix}' if folder else f'{stem}_{token}{suffix}'
            candidate = base.lstrip('/')

        if max_length and len(candidate) > max_length:
            candidate = candidate[-max_length:]
        return candidate
