from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from .media_utils import video_mime_type
from .models import AskClick, DateProposal, FoodOption, SiteContent, TimeSlot


def _active_food_options():
    return FoodOption.objects.filter(is_active=True)


def _active_time_slots():
    return [(slot.label, slot.label) for slot in TimeSlot.objects.filter(is_active=True)]


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _get_active_proposal(request):
    session_key = _ensure_session_key(request)
    proposal = (
        DateProposal.objects.filter(session_key=session_key, completed=False)
        .order_by('-created_at')
        .first()
    )
    if proposal:
        return proposal
    return DateProposal.objects.create(session_key=session_key)


@ensure_csrf_cookie
def ask(request):
    site = SiteContent.load()
    return render(request, 'proposal/ask.html', {
        'site': site,
        'ask_title': site.ask_title_display(),
        'no_messages': site.no_runaway_messages_list(),
        'ask_gift_video_type': video_mime_type(site.ask_gift_video),
    })


def yay(request):
    proposal = _get_active_proposal(request)
    proposal.mark_yes()
    return render(request, 'proposal/yay.html', {'site': SiteContent.load()})


@require_http_methods(['GET', 'POST'])
def food(request):
    food_options = _active_food_options()
    proposal = _get_active_proposal(request)

    if request.method == 'POST':
        choice = request.POST.get('food_choice', '')
        food_obj = food_options.filter(slug=choice).first()
        if food_obj:
            proposal.mark_food(food_obj.label)
            request.session['food_choice'] = choice
            request.session['proposal_id'] = proposal.id
            return redirect('schedule')

    return render(request, 'proposal/food.html', {
        'site': SiteContent.load(),
        'food_options': food_options,
    })


@require_http_methods(['GET', 'POST'])
def schedule(request):
    if not request.session.get('food_choice'):
        return redirect('food')

    time_slots = _active_time_slots()
    proposal_id = request.session.get('proposal_id')
    proposal = DateProposal.objects.filter(id=proposal_id).first() or _get_active_proposal(request)

    if request.method == 'POST':
        date = request.POST.get('date')
        time_slot = request.POST.get('time_slot')
        if date and time_slot:
            proposal.mark_scheduled(date, time_slot)
            request.session['date'] = date
            request.session['time_slot'] = time_slot
            return redirect('final')

    return render(request, 'proposal/schedule.html', {
        'site': SiteContent.load(),
        'time_slots': time_slots,
    })


def final(request):
    if not request.session.get('food_choice'):
        return redirect('food')

    site = SiteContent.load()
    time_slot = request.session.get('time_slot', '6:00 PM')

    return render(request, 'proposal/final.html', {
        'site': site,
        'food_choice': request.session.get('food_choice', ''),
        'date': request.session.get('date', ''),
        'time_slot': time_slot,
        'final_title': site.final_title_display(time_slot),
    })


@require_POST
def track_click(request):
    choice = request.POST.get('choice', '')
    if choice not in (AskClick.YES, AskClick.NO):
        return JsonResponse({'ok': False}, status=400)

    click = AskClick.objects.create(choice=choice)

    if choice == AskClick.YES:
        _get_active_proposal(request).mark_yes()

    return JsonResponse({'ok': True, 'id': click.id})


def _staff_preview_required(request):
    return request.user.is_authenticated and request.user.is_staff


@login_required(login_url='dashboard_login')
def preview_ask(request):
    if not _staff_preview_required(request):
        return redirect('ask')
    site = SiteContent.load()
    return render(request, 'proposal/ask.html', {
        'site': site,
        'ask_title': site.ask_title_display(),
        'no_messages': site.no_runaway_messages_list(),
        'ask_gift_video_type': video_mime_type(site.ask_gift_video),
        'is_preview': True,
    })


@login_required(login_url='dashboard_login')
def preview_yay(request):
    if not _staff_preview_required(request):
        return redirect('yay')
    return render(request, 'proposal/yay.html', {'site': SiteContent.load(), 'is_preview': True})


@login_required(login_url='dashboard_login')
def preview_food(request):
    if not _staff_preview_required(request):
        return redirect('food')
    return render(request, 'proposal/food.html', {
        'site': SiteContent.load(),
        'food_options': _active_food_options(),
        'is_preview': True,
    })


@login_required(login_url='dashboard_login')
def preview_schedule(request):
    if not _staff_preview_required(request):
        return redirect('schedule')
    return render(request, 'proposal/schedule.html', {
        'site': SiteContent.load(),
        'time_slots': _active_time_slots(),
        'is_preview': True,
    })


@login_required(login_url='dashboard_login')
def preview_final(request):
    if not _staff_preview_required(request):
        return redirect('final')
    site = SiteContent.load()
    return render(request, 'proposal/final.html', {
        'site': site,
        'food_choice': 'preview',
        'date': '',
        'time_slot': '6:00 PM',
        'final_title': site.final_title_display('6:00 PM'),
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
