from django.conf import settings
from django.forms import ClearableFileInput


class MobileImageInput(ClearableFileInput):
    template_name = 'proposal/widgets/mobile_file_input.html'
    upload_hint = 'From camera or gallery · auto-optimized'
    button_text = 'Tap to add photo'
    button_icon = '📷'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context['widget']
        widget.setdefault('attrs', {})
        widget['attrs'].setdefault('accept', 'image/*,.gif,image/gif')
        widget['attrs']['class'] = (widget['attrs'].get('class', '') + ' dash-file-input-hidden').strip()
        widget['file_kind'] = 'photo'
        widget['max_video_mb'] = getattr(settings, 'MAX_VIDEO_SIZE_MB', 80)
        widget['upload_hint'] = self.upload_hint
        widget['button_text'] = self.button_text
        widget['button_icon'] = self.button_icon
        return context


class MobileAnimatedImageInput(MobileImageInput):
    upload_hint = 'Live GIF works 🎁 — auto-slowed so it feels sweet'
    button_text = 'Tap to add photo or live GIF'
    button_icon = '🎁'


class MobileVideoInput(ClearableFileInput):
    template_name = 'proposal/widgets/mobile_file_input.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context['widget']
        widget.setdefault('attrs', {})
        widget['attrs'].setdefault('accept', 'video/*')
        widget['attrs']['class'] = (widget['attrs'].get('class', '') + ' dash-file-input-hidden').strip()
        widget['file_kind'] = 'video'
        widget['max_video_mb'] = getattr(settings, 'MAX_VIDEO_SIZE_MB', 80)
        return context


class MobileGiftVideoInput(ClearableFileInput):
    """Tiny looping gift video for the ask card — auto-compressed in the browser."""

    template_name = 'proposal/widgets/mobile_file_input.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context['widget']
        widget.setdefault('attrs', {})
        widget['attrs'].setdefault('accept', 'video/*,.mp4,.mov,.webm')
        widget['attrs']['class'] = (widget['attrs'].get('class', '') + ' dash-file-input-hidden').strip()
        widget['attrs']['data-gift-video'] = '1'
        widget['file_kind'] = 'gift-video'
        widget['max_video_mb'] = getattr(settings, 'MAX_GIFT_VIDEO_MB', 2)
        widget['button_icon'] = '🎁'
        widget['button_text'] = 'Tap to add gift video'
        widget['upload_hint'] = (
            f'Short loop · auto-compressed small · max {widget["max_video_mb"]}MB'
        )
        return context
