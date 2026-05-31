from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory

from .media_utils import optimize_uploaded_image, validate_video_upload
from .models import FoodOption, SiteContent, TimeSlot
from .widgets import MobileAnimatedImageInput, MobileImageInput, MobileVideoInput

DEFAULT_NO_MESSAGES = (
    'please {name}...\n'
    '{name} wait 🥺\n'
    'pretty please {name}?\n'
    'please say yes 💗'
)


class MediaOptimizedForm(forms.ModelForm):
    """Auto-compress images and validate videos from phone uploads."""

    image_sizes = {}
    video_fields = []

    def clean(self):
        cleaned = super().clean()
        if any(self.errors):
            return cleaned

        max_video_mb = getattr(settings, 'MAX_VIDEO_SIZE_MB', 80)

        for field_name, max_side in self.image_sizes.items():
            uploaded = cleaned.get(field_name)
            if uploaded:
                try:
                    cleaned[field_name] = optimize_uploaded_image(uploaded, max_side=max_side)
                except ValidationError as exc:
                    self.add_error(field_name, exc)

        for field_name in self.video_fields:
            uploaded = cleaned.get(field_name)
            if uploaded:
                try:
                    cleaned[field_name] = validate_video_upload(uploaded, max_mb=max_video_mb)
                except ValidationError as exc:
                    self.add_error(field_name, exc)

        return cleaned


class AskPageForm(MediaOptimizedForm):
    image_sizes = {
        'ask_image': 1200,
        'background_image': 1920,
    }

    class Meta:
        model = SiteContent
        fields = [
            'her_name',
            'ask_title',
            'ask_yes_button',
            'ask_no_button',
            'no_runaway_messages',
            'ask_image',
            'background_image',
        ]
        widgets = {
            'her_name': forms.TextInput(attrs={
                'class': 'dash-input',
                'placeholder': 'Her real name',
                'id': 'field-her-name',
            }),
            'ask_title': forms.TextInput(attrs={
                'class': 'dash-input',
                'placeholder': '🌸 {name}, will you go on a date with me? 🌸',
                'id': 'field-ask-title',
            }),
            'ask_yes_button': forms.TextInput(attrs={'class': 'dash-input'}),
            'ask_no_button': forms.TextInput(attrs={'class': 'dash-input'}),
            'no_runaway_messages': forms.Textarea(attrs={
                'class': 'dash-input dash-textarea',
                'rows': 5,
                'placeholder': DEFAULT_NO_MESSAGES,
                'id': 'field-runaway-messages',
            }),
            'ask_image': MobileAnimatedImageInput(),
            'background_image': MobileImageInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.no_runaway_messages.strip():
            self.initial['no_runaway_messages'] = DEFAULT_NO_MESSAGES


class OtherPagesForm(MediaOptimizedForm):
    image_sizes = {
        'yay_image': 1200,
        'final_profile_image': 800,
        'final_video_poster': 1200,
    }
    video_fields = ['final_video']

    class Meta:
        model = SiteContent
        fields = [
            'yay_title', 'yay_subtitle', 'yay_button', 'yay_image',
            'food_title', 'food_button',
            'schedule_title', 'schedule_date_label', 'schedule_time_label', 'schedule_button',
            'final_title', 'final_note', 'final_profile_image', 'final_video', 'final_video_poster',
        ]
        widgets = {
            'yay_title': forms.TextInput(attrs={'class': 'dash-input'}),
            'yay_subtitle': forms.TextInput(attrs={'class': 'dash-input'}),
            'yay_button': forms.TextInput(attrs={'class': 'dash-input'}),
            'yay_image': MobileAnimatedImageInput(),
            'food_title': forms.TextInput(attrs={'class': 'dash-input'}),
            'food_button': forms.TextInput(attrs={'class': 'dash-input'}),
            'schedule_title': forms.TextInput(attrs={'class': 'dash-input'}),
            'schedule_date_label': forms.TextInput(attrs={'class': 'dash-input'}),
            'schedule_time_label': forms.TextInput(attrs={'class': 'dash-input'}),
            'schedule_button': forms.TextInput(attrs={'class': 'dash-input'}),
            'final_title': forms.Textarea(attrs={'class': 'dash-input dash-textarea', 'rows': 2}),
            'final_note': forms.Textarea(attrs={'class': 'dash-input dash-textarea', 'rows': 3}),
            'final_profile_image': MobileAnimatedImageInput(),
            'final_video': MobileVideoInput(),
            'final_video_poster': MobileImageInput(),
        }


class FoodOptionForm(MediaOptimizedForm):
    image_sizes = {'image': 400}

    class Meta:
        model = FoodOption
        fields = ['slug', 'label', 'emoji', 'image', 'order', 'is_active']
        widgets = {
            'slug': forms.TextInput(attrs={'class': 'dash-input'}),
            'label': forms.TextInput(attrs={'class': 'dash-input'}),
            'emoji': forms.TextInput(attrs={'class': 'dash-input dash-input-sm'}),
            'image': MobileImageInput(),
            'order': forms.NumberInput(attrs={'class': 'dash-input dash-input-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'dash-check'}),
        }


class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ['label', 'order', 'is_active']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'dash-input'}),
            'order': forms.NumberInput(attrs={'class': 'dash-input dash-input-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'dash-check'}),
        }


FoodOptionFormSet = modelformset_factory(
    FoodOption,
    form=FoodOptionForm,
    extra=1,
    can_delete=True,
)

TimeSlotFormSet = modelformset_factory(
    TimeSlot,
    form=TimeSlotForm,
    extra=1,
    can_delete=True,
)


class DashboardLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'dash-input',
        'placeholder': 'Username',
        'autocomplete': 'username',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'dash-input',
        'placeholder': 'Password',
        'autocomplete': 'current-password',
    }))
