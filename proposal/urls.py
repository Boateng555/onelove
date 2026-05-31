from django.urls import path

from . import dashboard_views, views

urlpatterns = [
    path('', views.home, name='home'),
    path('for/<slug:token>/', views.ask, name='invite_ask'),
    path('for/<slug:token>/yay/', views.yay, name='invite_yay'),
    path('for/<slug:token>/food/', views.food, name='invite_food'),
    path('for/<slug:token>/schedule/', views.schedule, name='invite_schedule'),
    path('for/<slug:token>/final/', views.final, name='invite_final'),
    path('api/track-click/', views.track_click, name='track_click'),
    path('preview/ask/', views.preview_ask, name='preview_ask'),
    path('preview/yay/', views.preview_yay, name='preview_yay'),
    path('preview/food/', views.preview_food, name='preview_food'),
    path('preview/schedule/', views.preview_schedule, name='preview_schedule'),
    path('preview/final/', views.preview_final, name='preview_final'),
    path('dashboard/login/', dashboard_views.dashboard_login, name='dashboard_login'),
    path('dashboard/logout/', dashboard_views.dashboard_logout, name='dashboard_logout'),
    path('dashboard/api/live/', dashboard_views.live_activity, name='live_activity'),
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),
]
