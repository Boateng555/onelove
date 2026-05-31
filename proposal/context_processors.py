from .media_utils import video_mime_type
from .models import SiteContent


def site_content(request):
    site = SiteContent.load()
    return {
        'site': site,
        'final_video_type': video_mime_type(site.final_video, site.final_video_url),
    }