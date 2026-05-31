from django.contrib import admin

from .models import AskClick, DateProposal, FoodOption, Invite, InviteContent, SiteContent, TimeSlot


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteContent.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ('name', 'token', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'token')


@admin.register(InviteContent)
class InviteContentAdmin(admin.ModelAdmin):
    list_display = ('invite', 'ask_title')
    search_fields = ('invite__name',)


@admin.register(FoodOption)
class FoodOptionAdmin(admin.ModelAdmin):
    list_display = ('label', 'emoji', 'slug', 'invite', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('invite',)
    prepopulated_fields = {'slug': ('label',)}


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('label', 'invite', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('invite',)


@admin.register(DateProposal)
class DateProposalAdmin(admin.ModelAdmin):
    list_display = ('invite', 'status_label', 'food_choice', 'date', 'time_slot', 'said_yes', 'completed', 'updated_at')
    list_filter = ('completed', 'said_yes', 'date', 'invite')
    readonly_fields = ('created_at', 'updated_at', 'said_yes_at', 'food_chosen_at', 'scheduled_at')


@admin.register(AskClick)
class AskClickAdmin(admin.ModelAdmin):
    list_display = ('invite', 'choice', 'created_at')
    list_filter = ('choice', 'invite')
    readonly_fields = ('choice', 'created_at')
