from django.db import models
from django.urls import reverse
from django.utils import timezone

from .invite_utils import format_name_line, generate_invite_token


class StoredMedia(models.Model):
    name = models.CharField(max_length=512, unique=True, db_index=True)
    data = models.BinaryField()
    content_type = models.CharField(max_length=128, default='application/octet-stream')
    size = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'stored media'
        verbose_name_plural = 'stored media'

    def __str__(self):
        return self.name


class SiteContent(models.Model):
    """Default template copied when creating a new person's page."""

    ask_title = models.CharField(max_length=200, default='🌸 Will you go on a date with me? 🌸')
    ask_yes_button = models.CharField(max_length=50, default='YES 💗')
    ask_no_button = models.CharField(max_length=50, default='no... 🙈')
    ask_image = models.ImageField(upload_to='site/', blank=True, null=True)
    ask_gift_video = models.FileField(upload_to='site/gift/', blank=True, null=True)
    background_image = models.ImageField(upload_to='site/backgrounds/', blank=True, null=True)
    her_name = models.CharField(max_length=50, blank=True, default='')
    no_runaway_messages = models.TextField(
        blank=True,
        default='please {name}...\n{name} wait 🥺\npretty please {name}?\nplease {name} say yes 💗',
    )
    yay_title = models.CharField(max_length=200, default='WAIT YOU ACTUALLY SAID YES?? 😭')
    yay_subtitle = models.CharField(max_length=200, default='I was so ready for you to say no 😂')
    yay_button = models.CharField(max_length=50, default='okay okay! →')
    yay_image = models.ImageField(upload_to='site/', blank=True, null=True)
    food_title = models.CharField(max_length=200, default='What are we feeling? 🍜✨')
    food_button = models.CharField(max_length=50, default='this one! →')
    schedule_title = models.CharField(max_length=200, default='So... when are you free?')
    schedule_date_label = models.CharField(max_length=100, default='Pick a Day ✨')
    schedule_time_label = models.CharField(max_length=100, default='Pick a Time ✨')
    schedule_button = models.CharField(max_length=50, default='set the date! 💌')
    final_title = models.CharField(
        max_length=300,
        default="glad you didn't say no. be ready by {time}, I'm coming to get you 🚗",
    )
    final_note = models.TextField(
        default='P.S. normal people text. I made a website. during lunch. for you. no big deal.',
    )
    final_profile_image = models.ImageField(upload_to='site/', blank=True, null=True)
    final_video = models.FileField(upload_to='site/videos/', blank=True, null=True)
    final_video_url = models.URLField(blank=True, default='')
    final_video_poster = models.ImageField(upload_to='site/', blank=True, null=True)

    class Meta:
        verbose_name = 'Site content'
        verbose_name_plural = 'Site content'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ContentMixin:
    """Shared page helpers — used by each person's InviteContent."""

    def final_title_display(self, time_slot='6:00 PM'):
        return self.final_title.replace('{time}', time_slot)

    def ask_title_display(self, name):
        if name:
            return self.ask_title.replace('{name}', name)
        return self.ask_title.replace('{name}', '').replace('  ', ' ').strip()

    def no_runaway_messages_list(self, name):
        default = 'please {name}...\n{name} wait 🥺\npretty please {name}?\nplease say yes 💗'
        raw = self.no_runaway_messages.strip() or default
        return [
            format_name_line(line.strip(), name)
            for line in raw.splitlines()
            if line.strip()
        ]

    def final_video_source(self):
        if self.final_video:
            return self.final_video.url
        return self.final_video_url.strip()

    def has_final_video(self):
        return bool(self.final_video or self.final_video_url.strip())

    def ask_card_has_video(self):
        return bool(self.ask_gift_video)


class InviteContent(ContentMixin, models.Model):
    """All page text and media for one person — completely separate from others."""

    invite = models.OneToOneField('Invite', on_delete=models.CASCADE, related_name='content')
    ask_title = models.CharField(max_length=200, default='🌸 Will you go on a date with me? 🌸')
    ask_yes_button = models.CharField(max_length=50, default='YES 💗')
    ask_no_button = models.CharField(max_length=50, default='no... 🙈')
    ask_gift_video = models.FileField(upload_to='invites/gift/', blank=True, null=True)
    background_image = models.ImageField(upload_to='invites/backgrounds/', blank=True, null=True)
    no_runaway_messages = models.TextField(
        blank=True,
        default='please {name}...\n{name} wait 🥺\npretty please {name}?\nplease say yes 💗',
    )
    yay_title = models.CharField(max_length=200, default='WAIT YOU ACTUALLY SAID YES?? 😭')
    yay_subtitle = models.CharField(max_length=200, default='I was so ready for you to say no 😂')
    yay_button = models.CharField(max_length=50, default='okay okay! →')
    yay_image = models.ImageField(upload_to='invites/yay/', blank=True, null=True)
    food_title = models.CharField(max_length=200, default='What are we feeling? 🍜✨')
    food_button = models.CharField(max_length=50, default='this one! →')
    schedule_title = models.CharField(max_length=200, default='So... when are you free?')
    schedule_date_label = models.CharField(max_length=100, default='Pick a Day ✨')
    schedule_time_label = models.CharField(max_length=100, default='Pick a Time ✨')
    schedule_button = models.CharField(max_length=50, default='set the date! 💌')
    final_title = models.CharField(
        max_length=300,
        default="glad you didn't say no. be ready by {time}, I'm coming to get you 🚗",
    )
    final_note = models.TextField(
        default='P.S. normal people text. I made a website. during lunch. for you. no big deal.',
    )
    final_profile_image = models.ImageField(upload_to='invites/profile/', blank=True, null=True)
    final_video = models.FileField(upload_to='invites/videos/', blank=True, null=True)
    final_video_url = models.URLField(blank=True, default='')
    final_video_poster = models.ImageField(upload_to='invites/posters/', blank=True, null=True)

    def __str__(self):
        return f'Content for {self.invite.name}'


class Invite(models.Model):
    token = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = generate_invite_token()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('invite_ask', kwargs={'token': self.token})

    @property
    def latest_proposal(self):
        return self.proposals.order_by('-updated_at').first()

    @property
    def status_label(self):
        proposal = self.latest_proposal
        if not proposal:
            return 'Page not opened yet'
        return proposal.status_label


class FoodOption(models.Model):
    invite = models.ForeignKey(
        Invite,
        on_delete=models.CASCADE,
        related_name='food_options',
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=50)
    label = models.CharField(max_length=50)
    emoji = models.CharField(max_length=10, blank=True)
    image = models.ImageField(upload_to='invites/food/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'label']
        unique_together = [['invite', 'slug']]

    def __str__(self):
        return self.label


class TimeSlot(models.Model):
    invite = models.ForeignKey(
        Invite,
        on_delete=models.CASCADE,
        related_name='time_slots',
        null=True,
        blank=True,
    )
    label = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'label']

    def __str__(self):
        return self.label


class DateProposal(models.Model):
    invite = models.ForeignKey(
        Invite,
        on_delete=models.CASCADE,
        related_name='proposals',
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    said_yes = models.BooleanField(default=False)
    said_yes_at = models.DateTimeField(null=True, blank=True)
    food_choice = models.CharField(max_length=50, blank=True)
    food_chosen_at = models.DateTimeField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    time_slot = models.CharField(max_length=50, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    @property
    def status_label(self):
        if self.completed:
            return 'Scheduled 💌'
        if self.food_choice:
            return 'Picked food 🍽️'
        if self.said_yes:
            return 'Said yes 💗'
        return 'Started'

    def mark_yes(self):
        if not self.said_yes:
            self.said_yes = True
            self.said_yes_at = timezone.now()
            self.save(update_fields=['said_yes', 'said_yes_at', 'updated_at'])

    def mark_food(self, food_label):
        self.food_choice = food_label
        self.food_chosen_at = timezone.now()
        self.save(update_fields=['food_choice', 'food_chosen_at', 'updated_at'])

    def mark_scheduled(self, date, time_slot):
        self.date = date
        self.time_slot = time_slot
        self.scheduled_at = timezone.now()
        self.completed = True
        self.save(update_fields=['date', 'time_slot', 'scheduled_at', 'completed', 'updated_at'])


class AskClick(models.Model):
    YES = 'yes'
    NO = 'no'
    CHOICES = [(YES, 'Yes'), (NO, 'No')]

    invite = models.ForeignKey(
        Invite,
        on_delete=models.CASCADE,
        related_name='clicks',
        null=True,
        blank=True,
    )
    choice = models.CharField(max_length=3, choices=CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
