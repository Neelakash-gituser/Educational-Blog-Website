from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = "user"
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "writer")
    list_select_related = ("profile",)

    @admin.display(boolean=True, description="Can write")
    def writer(self, obj):
        return bool(getattr(obj, "profile", None) and obj.profile.is_author)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "can_write", "location")
    list_filter = ("can_write",)
    search_fields = ("display_name", "user__username", "user__email", "headline")
