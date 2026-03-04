from django.contrib import admin

from .models import Environment, EnvironmentVariable


class EnvironmentVariableInline(admin.TabularInline):
    model = EnvironmentVariable
    extra = 1


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'updated_at')
    search_fields = ('name',)
    inlines = [EnvironmentVariableInline]


@admin.register(EnvironmentVariable)
class EnvironmentVariableAdmin(admin.ModelAdmin):
    list_display = ('id', 'environment', 'key', 'is_secret', 'updated_at')
    list_filter = ('environment', 'is_secret')
    search_fields = ('key', 'value')
