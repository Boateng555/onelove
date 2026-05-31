from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from .invite_setup import setup_invite
from .invite_utils import get_invite_session, set_invite_session
from .media_utils import video_mime_type
from .models import AskClick, DateProposal, FoodOption, Invite, TimeSlot


def _active_food_options(invite):
    return FoodOption.objects.filter(invite=invite, is_active=True)


def _active_time_slots(invite):
    return [(slot.label, slot.label) for slot in TimeSlot.objects.filter(invite=invite, is_active=True)]


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _resolve_invite(token):
    invite = get_object_or_404(Invite, token=token, is_active=True)
    if not hasattr(invite, 'content'):
        setup_invite(invite)
    return invite


def _person_site(invite):
    return invite.content


def _get_active_proposal(request, invite):
    session_key = _ensure_session_key(request)
    proposal = (
        DateProposal.objects.filter(
            invite=invite,
            session_key=session_key,
            completed=False,
        )
        .order_by('-created_at')
        .first()
    )
    if proposal:
        return proposal
    return DateProposal.objects.create(session_key=session_key, invite=invite)


@ensure_csrf_cookie
def ask(request, token):
    invite = _resolve_invite(token)
    site = _person_site(invite)
    request.session['invite_token'] = token
    return render(request, 'proposal/ask.html', {
        'invite': invite,
        'site': site,
        'ask_title': site.ask_title_display(invite.name),
        'no_messages': site.no_runaway_messages_list(invite.name),
        'ask_gift_video_type': video_mime_type(site.ask_gift_video),
    })


def home(request):
    return render(request, 'proposal/home.html')


def yay(request, token):
    invite = _resolve_invite(token)
    _get_active_proposal(request, invite).mark_yes()
    return render(request, 'proposal/yay.html', {
        'invite': invite,
        'site': _person_site(invite),
    })


@require_http_methods(['GET', 'POST'])
def food(request, token):
    invite = _resolve_invite(token)
    food_options = _active_food_options(invite)
    proposal = _get_active_proposal(request, invite)

    if request.method == 'POST':
        choice = request.POST.get('food_choice', '')
        food_obj = food_options.filter(slug=choice).first()
        if food_obj:
            proposal.mark_food(food_obj.label)
            set_invite_session(request, invite, 'food_choice', choice)
            set_invite_session(request, invite, 'proposal_id', proposal.id)
            return redirect('invite_schedule', token=token)

    return render(request, 'proposal/food.html', {
        'invite': invite,
        'site': _person_site(invite),
        'food_options': food_options,
    })


@require_http_methods(['GET', 'POST'])
def schedule(request, token):
    invite = _resolve_invite(token)
    if not get_invite_session(request, invite, 'food_choice'):
        return redirect('invite_food', token=token)

    time_slots = _active_time_slots(invite)
    proposal_id = get_invite_session(request, invite, 'proposal_id')
    proposal = DateProposal.objects.filter(id=proposal_id, invite=invite).first()
    if not proposal:
        proposal = _get_active_proposal(request, invite)

    if request.method == 'POST':
        date = request.POST.get('date')
        time_slot = request.POST.get('time_slot')
        if date and time_slot:
            proposal.mark_scheduled(date, time_slot)
            set_invite_session(request, invite, 'date', date)
            set_invite_session(request, invite, 'time_slot', time_slot)
            return redirect('invite_final', token=token)

    return render(request, 'proposal/schedule.html', {
        'invite': invite,
        'site': _person_site(invite),
        'time_slots': time_slots,
    })


def final(request, token):
    invite = _resolve_invite(token)
    if not get_invite_session(request, invite, 'food_choice'):
        return redirect('invite_food', token=token)

    site = _person_site(invite)
    time_slot = get_invite_session(request, invite, 'time_slot', '6:00 PM')

    return render(request, 'proposal/final.html', {
        'invite': invite,
        'site': site,
        'food_choice': get_invite_session(request, invite, 'food_choice', ''),
        'date': get_invite_session(request, invite, 'date', ''),
        'time_slot': time_slot,
        'final_title': site.final_title_display(time_slot),
        'final_note': site.final_note,
        'final_video_type': video_mime_type(site.final_video, site.final_video_url),
    })


@require_POST
def track_click(request):
    token = request.session.get('invite_token')
    if not token:
        return JsonResponse({'ok': False, 'error': 'no_invite'}, status=400)

    invite = Invite.objects.filter(token=token, is_active=True).first()
    if not invite:
        return JsonResponse({'ok': False, 'error': 'invalid_invite'}, status=400)

    choice = request.POST.get('choice', '')
    if choice not in (AskClick.YES, AskClick.NO):
        return JsonResponse({'ok': False}, status=400)

    click = AskClick.objects.create(choice=choice, invite=invite)

    if choice == AskClick.YES:
        _get_active_proposal(request, invite).mark_yes()

    return JsonResponse({'ok': True, 'id': click.id})


def _staff_preview_required(request):
    return request.user.is_authenticated and request.user.is_staff


def _preview_invite(request):
    invite_id = request.GET.get('person') or request.session.get('preview_person_id')
    if not invite_id:
        return None
    invite = Invite.objects.filter(pk=invite_id).select_related('content').first()
    if invite:
        request.session['preview_person_id'] = invite.id
    return invite


@login_required(login_url='dashboard_login')
def preview_ask(request):
    if not _staff_preview_required(request):
        return redirect('home')
    invite = _preview_invite(request)
    if not invite:
        return redirect('dashboard')
    site = invite.content
    return render(request, 'proposal/ask.html', {
        'site': site,
        'invite': invite,
        'ask_title': site.ask_title_display(invite.name),
        'no_messages': site.no_runaway_messages_list(invite.name),
        'ask_gift_video_type': video_mime_type(site.ask_gift_video),
        'is_preview': True,
    })


@login_required(login_url='dashboard_login')
def preview_yay(request):
    if not _staff_preview_required(request):
        return redirect('home')
    invite = _preview_invite(request)
    if not invite:
        return redirect('dashboard')
    return render(request, 'proposal/yay.html', {
        'invite': invite,
        'site': invite.content,
        'is_preview': True,
    })


@login_required(login_url='dashboard_login')
@require_http_methods(['GET', 'POST'])
def preview_food(request):
    if not _staff_preview_required(request):
        return redirect('home')
    invite = _preview_invite(request)
    if not invite:
        return redirect('dashboard')
    if request.method == 'POST':
        return redirect(f'/preview/schedule/?person={invite.id}')
    return render(request, 'proposal/food.html', {
        'invite': invite,
        'site': invite.content,
        'food_options': _active_food_options(invite),
        'is_preview': True,
    })


@login_required(login_url='dashboard_login')
@require_http_methods(['GET', 'POST'])
def preview_schedule(request):
    if not _staff_preview_required(request):
        return redirect('home')
    invite = _preview_invite(request)
    if not invite:
        return redirect('dashboard')
    if request.method == 'POST':
        return redirect(f'/preview/final/?person={invite.id}')
    return render(request, 'proposal/schedule.html', {
        'invite': invite,
        'site': invite.content,
        'time_slots': _active_time_slots(invite),
        'is_preview': True,
    })


@login_required(login_url='dashboard_login')
def preview_final(request):
    if not _staff_preview_required(request):
        return redirect('home')
    invite = _preview_invite(request)
    if not invite:
        return redirect('dashboard')
    site = invite.content
    return render(request, 'proposal/final.html', {
        'invite': invite,
        'site': site,
        'food_choice': 'preview',
        'date': '',
        'time_slot': '6:00 PM',
        'final_title': site.final_title_display('6:00 PM'),
        'final_note': site.final_note,
        'final_video_type': video_mime_type(site.final_video, site.final_video_url),
        'is_preview': True,
    })


def serve_media(request, path):
    import re

    from .models import StoredMedia

    try:
        obj = StoredMedia.objects.get(name=path)
    except StoredMedia.DoesNotExist as exc:
        raise Http404('Media not found') from exc

    data = bytes(obj.data)
    size = len(data)
    content_type = obj.content_type or 'application/octet-stream'

    range_header = request.META.get('HTTP_RANGE', '').strip()
    if range_header:
        match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else size - 1
            end = min(end, size - 1)
            if start >= size or start > end:
                response = HttpResponse(status=416)
                response['Content-Range'] = f'bytes */{size}'
                return response

            chunk = data[start:end + 1]
            response = HttpResponse(chunk, status=206, content_type=content_type)
            response['Content-Range'] = f'bytes {start}-{end}/{size}'
            response['Content-Length'] = str(len(chunk))
            response['Accept-Ranges'] = 'bytes'
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response

    response = HttpResponse(data, content_type=content_type)
    response['Content-Length'] = str(size)
    response['Accept-Ranges'] = 'bytes'
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response
