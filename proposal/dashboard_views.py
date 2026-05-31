from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_http_methods

from .forms import (
    AskPageForm,
    DashboardLoginForm,
    FoodOptionFormSet,
    InviteForm,
    OtherPagesForm,
    TimeSlotFormSet,
)
from .invite_setup import setup_invite
from .models import AskClick, DateProposal, FoodOption, Invite, TimeSlot


def staff_required(view):
    return user_passes_test(lambda u: u.is_active and u.is_staff, login_url='dashboard_login')(view)


def _get_invite(invite_id):
    invite = get_object_or_404(Invite.objects.select_related('content'), pk=invite_id)
    if not hasattr(invite, 'content'):
        setup_invite(invite)
        invite.refresh_from_db()
    return invite


def _person_dash_url(invite, tab='ask', extra=''):
    base = reverse('dashboard_person', kwargs={'invite_id': invite.id})
    query = f'tab={tab}{extra}'
    return f'{base}?{query}'


def _save_food_formset(formset, invite):
    instances = formset.save(commit=False)
    for obj in formset.deleted_objects:
        obj.delete()
    for obj in instances:
        obj.invite = invite
        obj.save()
    formset.save_m2m()


def _save_time_formset(formset, invite):
    instances = formset.save(commit=False)
    for obj in formset.deleted_objects:
        obj.delete()
    for obj in instances:
        obj.invite = invite
        obj.save()


def _person_context(invite):
    content = invite.content
    submissions = DateProposal.objects.filter(invite=invite).exclude(
        said_yes=False,
        food_choice='',
        completed=False,
    )[:30]
    return {
        'invite': invite,
        'person_content': content,
        'ask_form': AskPageForm(instance=content),
        'pages_form': OtherPagesForm(instance=content),
        'food_formset': FoodOptionFormSet(queryset=FoodOption.objects.filter(invite=invite)),
        'time_formset': TimeSlotFormSet(queryset=TimeSlot.objects.filter(invite=invite)),
        'submissions': submissions,
        'preview_messages': content.no_runaway_messages_list(invite.name),
        'preview_title': content.ask_title_display(invite.name),
        'max_video_mb': getattr(settings, 'MAX_VIDEO_SIZE_MB', 80),
        'max_gift_video_mb': getattr(settings, 'MAX_GIFT_VIDEO_MB', 2),
        'is_vercel': settings.IS_VERCEL,
    }


@require_http_methods(['GET', 'POST'])
def dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard')

    form = DashboardLoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')

    return render(request, 'proposal/dashboard/login.html', {'form': form})


@require_http_methods(['POST'])
def dashboard_logout(request):
    logout(request)
    return redirect('dashboard_login')


@login_required(login_url='dashboard_login')
@staff_required
@require_http_methods(['GET', 'POST'])
def dashboard(request):
    """Home — list all private pages and create new ones."""
    invite_form = InviteForm()
    invites = Invite.objects.prefetch_related('content', 'proposals', 'clicks').all()

    if request.method == 'POST':
        section = request.POST.get('section', 'invites')

        if section == 'invites':
            invite_form = InviteForm(request.POST)
            if invite_form.is_valid():
                invite = invite_form.save()
                setup_invite(invite)
                messages.success(
                    request,
                    f'{invite.name}\'s dashboard is ready — customize everything for her.',
                )
                return redirect(_person_dash_url(invite, 'ask', '&new=1'))
            messages.error(request, 'Could not create page — enter a name.')

        elif section == 'invite_toggle':
            invite = Invite.objects.filter(pk=request.POST.get('invite_id')).first()
            if invite:
                invite.is_active = not invite.is_active
                invite.save(update_fields=['is_active', 'updated_at'])
                state = 'enabled' if invite.is_active else 'disabled'
                messages.success(request, f'{invite.name}\'s page {state}.')
            return redirect('dashboard')

    return render(request, 'proposal/dashboard/index.html', {
        'invite_form': invite_form,
        'invites': invites,
    })


@login_required(login_url='dashboard_login')
@staff_required
@require_http_methods(['GET', 'POST'])
def person_dashboard(request, invite_id):
    """Full admin page for one person — live, ask, pages, food, times, choices."""
    invite = _get_invite(invite_id)
    active_tab = request.GET.get('tab', 'ask')
    ctx = _person_context(invite)

    if request.method == 'POST':
        section = request.POST.get('section', 'ask')

        if section == 'invite_toggle':
            invite.is_active = not invite.is_active
            invite.save(update_fields=['is_active', 'updated_at'])
            state = 'enabled' if invite.is_active else 'disabled'
            messages.success(request, f'{invite.name}\'s link {state}.')
            return redirect(_person_dash_url(invite, active_tab))

        elif section == 'ask':
            ask_form = AskPageForm(request.POST, request.FILES, instance=invite.content)
            if ask_form.is_valid():
                ask_form.save()
                messages.success(request, f'Ask page saved for {invite.name}!')
                return redirect(_person_dash_url(invite, 'ask'))
            ctx['ask_form'] = ask_form
            messages.error(request, 'Could not save — check the fields below.')
            active_tab = 'ask'

        elif section == 'pages':
            pages_form = OtherPagesForm(request.POST, request.FILES, instance=invite.content)
            if pages_form.is_valid():
                pages_form.save()
                messages.success(request, f'Other pages saved for {invite.name}!')
                return redirect(_person_dash_url(invite, 'pages'))
            ctx['pages_form'] = pages_form
            messages.error(request, 'Could not save — check the fields below.')
            active_tab = 'pages'

        elif section == 'food':
            food_formset = FoodOptionFormSet(
                request.POST,
                request.FILES,
                queryset=FoodOption.objects.filter(invite=invite),
            )
            if food_formset.is_valid():
                _save_food_formset(food_formset, invite)
                messages.success(request, f'Food options saved for {invite.name}!')
                return redirect(_person_dash_url(invite, 'food'))
            ctx['food_formset'] = food_formset
            messages.error(request, 'Could not save food options.')
            active_tab = 'food'

        elif section == 'times':
            time_formset = TimeSlotFormSet(
                request.POST,
                queryset=TimeSlot.objects.filter(invite=invite),
            )
            if time_formset.is_valid():
                _save_time_formset(time_formset, invite)
                messages.success(request, f'Time slots saved for {invite.name}!')
                return redirect(_person_dash_url(invite, 'times'))
            ctx['time_formset'] = time_formset
            messages.error(request, 'Could not save time slots.')
            active_tab = 'times'

        elif section == 'clear_activity':
            AskClick.objects.filter(invite=invite).delete()
            DateProposal.objects.filter(invite=invite).delete()
            messages.success(
                request,
                f'All activity cleared for {invite.name}. Stats and feed are fresh.',
            )
            return redirect(_person_dash_url(invite, 'live', '&cleared=1'))

    ctx['active_tab'] = active_tab
    ctx['is_new'] = request.GET.get('new') == '1'
    return render(request, 'proposal/dashboard/person.html', ctx)


def _serialize_click(click):
    name = click.invite.name if click.invite_id else 'Someone'
    choice_label = 'YES 💗' if click.choice == AskClick.YES else 'NO 🙈'
    return {
        'id': click.id,
        'type': 'click',
        'choice': click.choice,
        'person': name,
        'label': f'{name}: {choice_label}',
        'time': timezone.localtime(click.created_at).strftime('%I:%M:%S %p'),
        'iso': click.created_at.isoformat(),
    }


def _serialize_proposal(proposal):
    name = proposal.invite.name if proposal.invite_id else 'Someone'
    return {
        'id': proposal.id,
        'type': 'proposal',
        'person': name,
        'status': proposal.status_label,
        'completed': proposal.completed,
        'said_yes': proposal.said_yes,
        'food_choice': proposal.food_choice or '—',
        'date': proposal.date.strftime('%b %d, %Y') if proposal.date else '—',
        'time_slot': proposal.time_slot or '—',
        'said_yes_at': (
            timezone.localtime(proposal.said_yes_at).strftime('%b %d, %I:%M %p')
            if proposal.said_yes_at else '—'
        ),
        'updated': timezone.localtime(proposal.updated_at).strftime('%I:%M:%S %p'),
        'updated_full': timezone.localtime(proposal.updated_at).strftime('%b %d, %I:%M %p'),
        'iso': proposal.updated_at.isoformat(),
        'label': _proposal_feed_label(proposal),
    }


def _proposal_feed_label(proposal):
    name = proposal.invite.name if proposal.invite_id else 'Someone'
    if proposal.completed:
        return f'{name}: Scheduled! {proposal.food_choice} · {proposal.date} · {proposal.time_slot}'
    if proposal.food_choice:
        return f'{name}: Picked {proposal.food_choice} 🍽️'
    if proposal.said_yes:
        return f'{name}: Said YES 💗'
    return f'{name}: Opened page'


@login_required(login_url='dashboard_login')
@staff_required
@require_GET
def live_activity(request):
    try:
        since_id = int(request.GET.get('since', 0))
    except (TypeError, ValueError):
        since_id = 0

    try:
        since_proposal = int(request.GET.get('since_proposal', 0))
    except (TypeError, ValueError):
        since_proposal = 0

    invite_id = request.GET.get('person')
    invite = Invite.objects.filter(pk=invite_id).first() if invite_id else None

    since_proposal_time = request.GET.get('since_proposal_time', '')
    parsed_since = parse_datetime(since_proposal_time) if since_proposal_time else None
    if parsed_since and timezone.is_naive(parsed_since):
        parsed_since = timezone.make_aware(parsed_since, timezone.get_current_timezone())

    proposal_filter = DateProposal.objects.select_related('invite').exclude(
        said_yes=False,
        food_choice='',
        completed=False,
    )
    click_filter = AskClick.objects.select_related('invite')
    if invite:
        proposal_filter = proposal_filter.filter(invite=invite)
        click_filter = click_filter.filter(invite=invite)

    proposals = proposal_filter[:30]

    new_proposals_qs = proposal_filter
    if parsed_since:
        new_proposals_qs = new_proposals_qs.filter(updated_at__gt=parsed_since)
    else:
        new_proposals_qs = new_proposals_qs.filter(id__gt=since_proposal)
    new_proposals = new_proposals_qs.order_by('updated_at')

    latest_proposal_id = proposal_filter.order_by('-id').values_list('id', flat=True).first() or 0
    completed_count = proposal_filter.filter(completed=True).count()

    today = timezone.localdate()
    yes_today = click_filter.filter(choice=AskClick.YES, created_at__date=today).count()
    no_today = click_filter.filter(choice=AskClick.NO, created_at__date=today).count()

    new_clicks = click_filter.filter(id__gt=since_id).order_by('id')
    recent_clicks = click_filter.order_by('-id')[:40]
    latest_click_id = click_filter.order_by('-id').values_list('id', flat=True).first() or 0

    return JsonResponse({
        'stats': {
            'yes_today': yes_today,
            'no_today': no_today,
            'yes_total': click_filter.filter(choice=AskClick.YES).count(),
            'no_total': click_filter.filter(choice=AskClick.NO).count(),
            'scheduled_total': completed_count,
        },
        'new_events': [_serialize_click(c) for c in new_clicks],
        'events': [_serialize_click(c) for c in recent_clicks],
        'latest_id': latest_click_id,
        'proposals': [_serialize_proposal(p) for p in proposals],
        'new_proposals': [_serialize_proposal(p) for p in new_proposals],
        'latest_proposal_id': latest_proposal_id,
    })
