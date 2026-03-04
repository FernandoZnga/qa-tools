from celery import shared_task
from django.utils import timezone

from .models import LoadTestRun
from .services import resolve_environment, run_load_test


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 2})
def execute_load_test_task(self, load_run_id):
    run = LoadTestRun.objects.select_related('environment').filter(id=load_run_id).first()
    if not run:
        return {'detail': f'load run {load_run_id} not found'}

    run.status = 'running'
    run.task_id = self.request.id or run.task_id
    run.save(update_fields=['status', 'task_id'])

    try:
        output = run_load_test(
            config=run.request_snapshot,
            variables=resolve_environment(run.environment_id),
            total_requests=run.total_requests,
            concurrency=run.concurrency,
            mode=run.mode,
            delay_ms=run.delay_ms,
        )

        run.status = 'completed'
        run.success_count = output['success_count']
        run.failure_count = output['failure_count']
        run.min_ms = output['min_ms']
        run.max_ms = output['max_ms']
        run.avg_ms = output['avg_ms']
        run.p95_ms = output['p95_ms']
        run.p99_ms = output['p99_ms']
        run.total_duration_ms = output['total_duration_ms']
        run.requests_per_second = output['requests_per_second']
        run.error_summary = output['error_summary']
        run.results = output['results']
        run.finished_at = timezone.now()
        run.save()
    except Exception as exc:
        run.status = 'failed'
        run.error_summary = {'fatal': str(exc)}
        run.finished_at = timezone.now()
        run.save(update_fields=['status', 'error_summary', 'finished_at'])
        raise

    return {
        'load_run_id': run.id,
        'status': run.status,
        'success_count': run.success_count,
        'failure_count': run.failure_count,
    }
