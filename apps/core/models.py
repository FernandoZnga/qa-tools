from django.db import models


class Environment(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class EnvironmentVariable(models.Model):
    environment = models.ForeignKey(
        Environment,
        related_name='variables',
        on_delete=models.CASCADE,
    )
    key = models.CharField(max_length=120)
    value = models.TextField()
    is_secret = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('environment', 'key')
        ordering = ['key']

    def __str__(self):
        return f'{self.environment.name}:{self.key}'
