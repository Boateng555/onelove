"""Create default content, food, and times for each new private page."""

from .models import FoodOption, InviteContent, SiteContent, TimeSlot

DEFAULT_FOODS = [
    ('pizza', 'Pizza', '🍕', 0),
    ('sushi', 'Sushi', '🍣', 1),
    ('burgers', 'Burgers', '🍔', 2),
    ('pasta', 'Pasta', '🍝', 3),
    ('tacos', 'Tacos', '🌮', 4),
    ('ramen', 'Ramen', '🍜', 5),
]

DEFAULT_TIMES = [
    '12:00 PM', '1:00 PM', '2:00 PM', '3:00 PM', '4:00 PM',
    '5:00 PM', '6:00 PM', '7:00 PM', '8:00 PM',
]

CONTENT_FIELD_NAMES = [
    'ask_title', 'ask_yes_button', 'ask_no_button', 'no_runaway_messages',
    'yay_title', 'yay_subtitle', 'yay_button',
    'food_title', 'food_button',
    'schedule_title', 'schedule_date_label', 'schedule_time_label', 'schedule_button',
    'final_title', 'final_note', 'final_video_url',
]


def _template_content():
    site = SiteContent.load()
    return {field: getattr(site, field) for field in CONTENT_FIELD_NAMES}


def setup_invite(invite):
    """Give this person their own pages, food list, and time slots."""
    defaults = _template_content()
    InviteContent.objects.get_or_create(invite=invite, defaults=defaults)

    if not FoodOption.objects.filter(invite=invite).exists():
        for slug, label, emoji, order in DEFAULT_FOODS:
            FoodOption.objects.create(
                invite=invite,
                slug=slug,
                label=label,
                emoji=emoji,
                order=order,
            )

    if not TimeSlot.objects.filter(invite=invite).exists():
        for i, label in enumerate(DEFAULT_TIMES):
            TimeSlot.objects.create(invite=invite, label=label, order=i)

    return invite.content
