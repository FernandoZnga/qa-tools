from django.db import models

from apps.core.models import Environment


class ApiRequestTemplate(models.Model):
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ]

    BODY_TYPE_CHOICES = [
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('raw', 'RAW'),
    ]

    name = models.CharField(max_length=150, unique=True)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    url = models.URLField(max_length=2048)
    headers = models.JSONField(default=dict, blank=True)
    query_params = models.JSONField(default=dict, blank=True)
    body = models.TextField(blank=True)
    body_type = models.CharField(max_length=10, choices=BODY_TYPE_CHOICES, default='json')
    timeout_seconds = models.PositiveIntegerField(default=30)
    environment = models.ForeignKey(
        Environment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ApiRunLog(models.Model):
    request_template = models.ForeignKey(
        ApiRequestTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='run_logs',
    )
    method = models.CharField(max_length=10)
    url = models.URLField(max_length=2048)
    response_status = models.IntegerField(null=True, blank=True)
    response_time_ms = models.FloatField(null=True, blank=True)
    response_headers = models.JSONField(default=dict, blank=True)
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = self.response_status if self.response_status is not None else 'ERR'
        return f'{self.method} {self.url} -> {status}'


class LoadTestScenario(models.Model):
    MODE_CHOICES = [
        ('single', 'Single Thread'),
        ('multi', 'Multi Thread'),
    ]

    name = models.CharField(max_length=150, unique=True)
    request_template = models.ForeignKey(
        ApiRequestTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='load_scenarios',
    )
    environment = models.ForeignKey(
        Environment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='load_scenarios',
    )
    method = models.CharField(max_length=10, choices=ApiRequestTemplate.METHOD_CHOICES, blank=True)
    url = models.URLField(max_length=2048, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    query_params = models.JSONField(default=dict, blank=True)
    body = models.TextField(blank=True)
    body_type = models.CharField(max_length=10, choices=ApiRequestTemplate.BODY_TYPE_CHOICES, default='json')
    timeout_seconds = models.PositiveIntegerField(default=30)
    total_requests = models.PositiveIntegerField(default=10)
    concurrency = models.PositiveIntegerField(default=1)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='single')
    delay_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LoadTestRun(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    scenario = models.ForeignKey(
        LoadTestScenario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='runs',
    )
    request_template = models.ForeignKey(
        ApiRequestTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='load_runs',
    )
    environment = models.ForeignKey(
        Environment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='load_runs',
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='running')
    task_id = models.CharField(max_length=100, blank=True)
    request_snapshot = models.JSONField(default=dict, blank=True)
    total_requests = models.PositiveIntegerField(default=0)
    concurrency = models.PositiveIntegerField(default=1)
    mode = models.CharField(max_length=10, choices=LoadTestScenario.MODE_CHOICES, default='single')
    delay_ms = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    min_ms = models.FloatField(null=True, blank=True)
    max_ms = models.FloatField(null=True, blank=True)
    avg_ms = models.FloatField(null=True, blank=True)
    p95_ms = models.FloatField(null=True, blank=True)
    p99_ms = models.FloatField(null=True, blank=True)
    total_duration_ms = models.FloatField(null=True, blank=True)
    requests_per_second = models.FloatField(null=True, blank=True)
    error_summary = models.JSONField(default=dict, blank=True)
    results = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'load-run:{self.id} ({self.status})'
