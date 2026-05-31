import os
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    HEIF_SUPPORTED = False

from PIL import Image, ImageSequence, UnidentifiedImageError

ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm', '.3gp'}
VIDEO_MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.m4v': 'video/mp4',
    '.webm': 'video/webm',
    '.3gp': 'video/3gpp',
}


def _is_gif(file_obj) -> bool:
    name = getattr(file_obj, 'name', '') or ''
    if Path(name).suffix.lower() == '.gif':
        return True
    if hasattr(file_obj, 'read'):
        pos = file_obj.tell()
        file_obj.seek(0)
        header = file_obj.read(6)
        file_obj.seek(pos)
        return header[:6] in (b'GIF87a', b'GIF89a')
    return False


def slow_down_gif(file_obj, speed_factor=2.2):
    """Make animated GIFs play slower and softer — perfect for emoji gifts."""
    file_obj.seek(0)
    image = Image.open(file_obj)
    frames = []
    durations = []

    for frame in ImageSequence.Iterator(image):
        frames.append(frame.copy().convert('RGBA'))
        ms = frame.info.get('duration', 100)
        durations.append(max(int(ms * speed_factor), 80))

    if len(frames) <= 1:
        file_obj.seek(0)
        return file_obj

    # Resize large emoji GIFs so they stay crisp but not huge
    max_side = 480
    w, h = frames[0].size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        frames = [f.resize(new_size, Image.Resampling.LANCZOS) for f in frames]

    buffer = BytesIO()
    frames[0].save(
        buffer,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )
    buffer.seek(0)

    stem = Path(getattr(file_obj, 'name', 'gift')).stem or 'gift'
    safe_name = ''.join(c for c in stem if c.isalnum() or c in ('-', '_'))[:60] or 'gift'
    return ContentFile(buffer.read(), name=f'{safe_name}.gif')


def optimize_uploaded_image(file_obj, max_side=1600, quality=82):
    """Resize and compress phone photos for fast loading. GIFs stay animated."""
    if not file_obj or not hasattr(file_obj, 'read'):
        return file_obj

    if _is_gif(file_obj):
        size = getattr(file_obj, 'size', 0) or 0
        max_gif_mb = 15
        if size > max_gif_mb * 1024 * 1024:
            raise ValidationError(
                f'Animated GIF is too large. Keep it under {max_gif_mb}MB — emoji GIFs are usually tiny.'
            )
        try:
            return slow_down_gif(file_obj)
        except Exception:
            file_obj.seek(0)
            return file_obj

    try:
        file_obj.seek(0)
        image = Image.open(file_obj)
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        hint = ' Try saving as JPG from your phone.' if not HEIF_SUPPORTED else ''
        raise ValidationError(f'Could not read that image.{hint}') from exc

    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        alpha = image.split()[-1] if image.mode in ('RGBA', 'LA') else None
        background.paste(image, mask=alpha)
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=quality, optimize=True)
    buffer.seek(0)

    stem = Path(getattr(file_obj, 'name', 'photo')).stem or 'photo'
    safe_name = ''.join(c for c in stem if c.isalnum() or c in ('-', '_'))[:60] or 'photo'
    return ContentFile(buffer.read(), name=f'{safe_name}.jpg')


def is_video_upload(file_obj) -> bool:
    if not file_obj:
        return False
    content_type = getattr(file_obj, 'content_type', '') or ''
    if content_type.startswith('video/'):
        return True
    ext = Path(getattr(file_obj, 'name', '')).suffix.lower()
    return ext in ALLOWED_VIDEO_EXTENSIONS


def validate_video_upload(file_obj, max_mb=80, label='Video'):
    """Accept common phone video formats and enforce a size limit."""
    if not file_obj or not hasattr(file_obj, 'read'):
        return file_obj

    ext = Path(getattr(file_obj, 'name', '')).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise ValidationError(f'{label}: use {allowed}')

    size = getattr(file_obj, 'size', None)
    if size is None:
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(0)

    max_bytes = max_mb * 1024 * 1024
    if size > max_bytes:
        raise ValidationError(
            f'{label} is too large ({size // (1024 * 1024)}MB). Max is {max_mb}MB — '
            'trim to a short clip or let the dashboard compress it.'
        )

    if ext == '.webm' and label == 'Video':
        raise ValidationError(
            f'{label}: WebM does not play on iPhones. Upload MP4 or MOV from your phone.'
        )

    return file_obj


def video_mime_type(file_field, url='') -> str:
    if file_field and file_field.name:
        ext = Path(file_field.name).suffix.lower()
        return VIDEO_MIME_TYPES.get(ext, 'video/mp4')
    if url:
        ext = Path(url.split('?')[0]).suffix.lower()
        return VIDEO_MIME_TYPES.get(ext, 'video/mp4')
    return 'video/mp4'
