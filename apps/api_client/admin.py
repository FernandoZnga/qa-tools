from django.contrib import admin

from .models import ApiRequestTemplate, ApiRunLog, LoadTestRun, LoadTestScenario


@admin.register(ApiRequestTemplate)
class ApiRequestTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'method', 'url', 'environment', 'updated_at')
    list_filter = ('method', 'environment', 'body_type')
    search_fields = ('name', 'url')


@admin.register(ApiRunLog)
class ApiRunLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'method', 'url', 'response_status', 'response_time_ms', 'success', 'created_at')
    list_filter = ('success', 'method', 'response_status')
    search_fields = ('url', 'error_message')
    readonly_fields = ('created_at',)


@admin.register(LoadTestScenario)
class LoadTestScenarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'request_template', 'mode', 'total_requests', 'concurrency', 'updated_at')
    list_filter = ('mode', 'request_template', 'environment')
    search_fields = ('name', 'url')


@admin.register(LoadTestRun)
class LoadTestRunAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'scenario',
        'status',
        'task_id',
        'mode',
        'total_requests',
        'success_count',
        'failure_count',
        'requests_per_second',
        'started_at',
    )
    list_filter = ('status', 'mode', 'scenario')
    search_fields = ('id', 'task_id')
    readonly_fields = ('started_at', 'finished_at')
