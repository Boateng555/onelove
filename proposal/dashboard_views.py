from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_http_methods

from .forms import (
    AskPageForm,
    DashboardLoginForm,
    FoodOptionFormSet,
    OtherPagesForm,
    TimeSlotFormSet,
)
from .models import AskClick, DateProposal, FoodOption, SiteContent, TimeSlot


def staff_required(view):
    return user_passes_test(lambda u: u.is_active and u.is_staff, login_url='dashboard_login')(view)


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
    site = SiteContent.load()

    ask_form = AskPageForm(instance=site)
    pages_form = OtherPagesForm(instance=site)
    food_formset = FoodOptionFormSet(queryset=FoodOption.objects.all())
    time_formset = TimeSlotFormSet(queryset=TimeSlot.objects.all())
    active_tab = request.GET.get('tab', '')

    if request.method == 'POST':
        section = request.POST.get('section', 'ask')

        if section == 'ask':
            ask_form = AskPageForm(request.POST, request.FILES, instance=site)
            if ask_form.is_valid():
                ask_form.save()
                messages.success(request, 'Ask page saved!')
                return redirect('/dashboard/?tab=ask#ask')
            messages.error(request, 'Could not save — check the fields below.')
            active_tab = 'ask'

        elif section == 'pages':
            pages_form = OtherPagesForm(request.POST, request.FILES, instance=site)
            if pages_form.is_valid():
                pages_form.save()
                messages.success(request, 'Other pages saved!')
                return redirect('/dashboard/?tab=pages#pages')
            messages.error(request, 'Could not save — check the fields below.')
            active_tab = 'pages'

        elif section == 'food':
            food_formset = FoodOptionFormSet(request.POST, request.FILES, queryset=FoodOption.objects.all())
            if food_formset.is_valid():
                food_formset.save()
                messages.success(request, 'Food options saved!')
                return redirect('/dashboard/?tab=food#food')
            messages.error(request, 'Could not save food options.')
            active_tab = 'food'

        elif section == 'times':
            time_formset = TimeSlotFormSet(request.POST, queryset=TimeSlot.objects.all())
            if time_formset.is_valid():
                time_formset.save()
                messages.success(request, 'Time slots saved!')
                return redirect('/dashboard/?tab=times#times')
            messages.error(request, 'Could not save time slots.')
            active_tab = 'times'

    submissions = DateProposal.objects.exclude(
        said_yes=False,
        food_choice='',
        completed=False,
    )[:30]
    preview_messages = site.no_runaway_messages_list()

    return render(request, 'proposal/dashboard/index.html', {
        'site': site,
        'ask_form': ask_form,
        'pages_form': pages_form,
        'food_formset': food_formset,
        'time_formset': time_formset,
        'submissions': submissions,
        'preview_messages': preview_messages,
        'preview_title': site.ask_title_display(),
        'active_tab': active_tab,
    })


def _serialize_click(click):
    return {
        'id': click.id,
        'type': 'click',
        'choice': click.choice,
        'label': 'YES 💗' if click.choice == AskClick.YES else 'NO 🙈',
        'time': timezone.localtime(click.created_at).strftime('%I:%M:%S %p'),
        'iso': click.created_at.isoformat(),
    }


def _serialize_proposal(proposal):
    return {
        'id': proposal.id,
        'type': 'proposal',
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
    if proposal.completed:
        return f"Scheduled! {proposal.food_choice} · {proposal.date} · {proposal.time_slot}"
    if proposal.food_choice:
        return f"Picked {proposal.food_choice} 🍽️"
    if proposal.said_yes:
        return 'She said YES 💗'
    return 'New visit'


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

    since_proposal_time = request.GET.get('since_proposal_time', '')
    parsed_since = parse_datetime(since_proposal_time) if since_proposal_time else None
    if parsed_since and timezone.is_naive(parsed_since):
        parsed_since = timezone.make_aware(parsed_since, timezone.get_current_timezone())

    proposal_filter = DateProposal.objects.exclude(
        said_yes=False,
        food_choice='',
        completed=False,
    )
    proposals = proposal_filter[:30]

    new_proposals_qs = proposal_filter
    if parsed_since:
        new_proposals_qs = new_proposals_qs.filter(updated_at__gt=parsed_since)
    else:
        new_proposals_qs = new_proposals_qs.filter(id__gt=since_proposal)
    new_proposals = new_proposals_qs.order_by('updated_at')

    latest_proposal_id = DateProposal.objects.order_by('-id').values_list('id', flat=True).first() or 0

    completed_count = DateProposal.objects.filter(completed=True).count()

    today = timezone.localdate()
    yes_today = AskClick.objects.filter(choice=AskClick.YES, created_at__date=today).count()
    no_today = AskClick.objects.filter(choice=AskClick.NO, created_at__date=today).count()

    new_clicks = AskClick.objects.filter(id__gt=since_id).order_by('id')
    recent_clicks = AskClick.objects.all()[:40]
    latest_click_id = AskClick.objects.order_by('-id').values_list('id', flat=True).first() or 0

    return JsonResponse({
        'stats': {
            'yes_today': yes_today,
            'no_today': no_today,
            'yes_total': AskClick.objects.filter(choice=AskClick.YES).count(),
            'no_total': AskClick.objects.filter(choice=AskClick.NO).count(),
            'scheduled_total': completed_count,
        },
        'new_events': [_serialize_click(c) for c in new_clicks],
        'events': [_serialize_click(c) for c in recent_clicks],
        'latest_id': latest_click_id,
        'proposals': [_serialize_proposal(p) for p in proposals],
        'new_proposals': [_serialize_proposal(p) for p in new_proposals],
        'latest_proposal_id': latest_proposal_id,
    })
