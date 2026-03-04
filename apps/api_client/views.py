from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Environment

from .models import ApiRequestTemplate, ApiRunLog, LoadTestRun, LoadTestScenario
from .serializers import (
    ApiRequestTemplateSerializer,
    ApiRunLogSerializer,
    LoadTestRunSerializer,
    LoadTestScenarioSerializer,
    RunLoadTestSerializer,
    SendApiRequestSerializer,
)
from .services import (
    build_postman_collection,
    build_postman_collection_from_config,
    execute_request,
    resolve_environment,
    run_load_test,
)
from .tasks import execute_load_test_task


def _build_request_config(payload, template=None, scenario=None):
    if scenario:
        config = {
            'method': scenario.method,
            'url': scenario.url,
            'headers': scenario.headers,
            'query_params': scenario.query_params,
            'body': scenario.body,
            'body_type': scenario.body_type,
            'timeout_seconds': scenario.timeout_seconds,
        }
        if scenario.request_template:
            template = scenario.request_template
            config = {
                'method': template.method,
                'url': template.url,
                'headers': template.headers,
                'query_params': template.query_params,
                'body': template.body,
                'body_type': template.body_type,
                'timeout_seconds': template.timeout_seconds,
            }

        config = {
            'method': scenario.method or config['method'],
            'url': scenario.url or config['url'],
            'headers': scenario.headers or config['headers'],
            'query_params': scenario.query_params or config['query_params'],
            'body': scenario.body if scenario.body else config['body'],
            'body_type': scenario.body_type or config['body_type'],
            'timeout_seconds': scenario.timeout_seconds or config['timeout_seconds'],
        }
    elif template:
        config = {
            'method': template.method,
            'url': template.url,
            'headers': template.headers,
            'query_params': template.query_params,
            'body': template.body,
            'body_type': template.body_type,
            'timeout_seconds': template.timeout_seconds,
        }
    else:
        config = {
            'method': payload.get('method'),
            'url': payload.get('url'),
            'headers': {},
            'query_params': {},
            'body': '',
            'body_type': 'json',
            'timeout_seconds': 30,
        }

    return {
        'method': payload.get('method', config.get('method')),
        'url': payload.get('url', config.get('url')),
        'headers': payload.get('headers', config.get('headers', {})),
        'query_params': payload.get('query_params', config.get('query_params', {})),
        'body': payload.get('body', config.get('body', '')),
        'body_type': payload.get('body_type', config.get('body_type', 'json')),
        'timeout_seconds': payload.get('timeout_seconds', config.get('timeout_seconds', 30)),
    }


def _resolve_load_execution(data):
    scenario = None
    template = None

    if data.get('scenario_id'):
        scenario = LoadTestScenario.objects.select_related('request_template', 'environment').filter(
            id=data['scenario_id']
        ).first()
        if not scenario:
            return None, None, None, {'detail': 'scenario not found'}
        template = scenario.request_template

    if data.get('template_id'):
        template = ApiRequestTemplate.objects.filter(id=data['template_id']).first()
        if not template:
            return None, None, None, {'detail': 'template not found'}

    config = _build_request_config(data, template=template, scenario=scenario)
    if not config.get('method') or not config.get('url'):
        return None, None, None, {'detail': 'missing method/url after scenario/template resolution'}

    if scenario:
        total_requests = data.get('total_requests', scenario.total_requests)
        concurrency = data.get('concurrency', scenario.concurrency)
        mode = data.get('mode', scenario.mode)
        delay_ms = data.get('delay_ms', scenario.delay_ms)
        environment_id = data.get('environment_id') or (
            scenario.environment_id or (template.environment_id if template else None)
        )
    else:
        total_requests = data.get('total_requests', 10)
        concurrency = data.get('concurrency', 1)
        mode = data.get('mode', 'single')
        delay_ms = data.get('delay_ms', 0)
        environment_id = data.get('environment_id') or (
            template.environment_id if template and template.environment_id else None
        )

    if mode == 'single':
        concurrency = 1

    if environment_id and not Environment.objects.filter(id=environment_id).exists():
        return None, None, None, {'detail': 'environment not found'}

    execution = {
        'config': config,
        'environment_id': environment_id,
        'total_requests': total_requests,
        'concurrency': concurrency,
        'mode': mode,
        'delay_ms': delay_ms,
    }

    return scenario, template, execution, None


class ApiRequestTemplateViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = ApiRequestTemplate.objects.select_related('environment').all()
    serializer_class = ApiRequestTemplateSerializer

    @action(detail=True, methods=['get'], url_path='export-postman')
    def export_postman(self, request, pk=None):
        template = self.get_object()
        return Response(build_postman_collection(template))


class ApiRunLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset: QuerySet = ApiRunLog.objects.select_related('request_template').all()
    serializer_class = ApiRunLogSerializer


class LoadTestScenarioViewSet(viewsets.ModelViewSet):
    queryset: QuerySet = LoadTestScenario.objects.select_related('request_template', 'environment').all()
    serializer_class = LoadTestScenarioSerializer


class LoadTestRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset: QuerySet = LoadTestRun.objects.select_related('scenario', 'request_template', 'environment').all()
    serializer_class = LoadTestRunSerializer

    @action(detail=True, methods=['get'], url_path='export-postman')
    def export_postman(self, request, pk=None):
        run = self.get_object()
        snapshot = run.request_snapshot or {}
        collection = build_postman_collection_from_config(
            snapshot,
            name=f'load-run-{run.id}',
            identifier=f'load-run-{run.id}',
        )
        return Response(collection)


class SendApiRequestView(APIView):
    def post(self, request):
        serializer = SendApiRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        template = None

        if data.get('template_id'):
            template = ApiRequestTemplate.objects.filter(id=data['template_id']).first()
            if not template:
                return Response({'detail': 'template not found'}, status=status.HTTP_404_NOT_FOUND)

        config = _build_request_config(data, template=template)
        environment_id = data.get('environment_id') or (
            template.environment_id if template and template.environment_id else None
        )

        variables = resolve_environment(environment_id)

        if environment_id and not variables:
            if not Environment.objects.filter(id=environment_id).exists():
                return Response({'detail': 'environment not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            response, duration_ms, final_req = execute_request(config, variables)
            log = ApiRunLog.objects.create(
                request_template=template,
                method=final_req['method'],
                url=final_req['url'],
                response_status=response.status_code,
                response_time_ms=round(duration_ms, 2),
                response_headers=dict(response.headers),
                response_body=response.text,
                success=response.is_success,
            )

            return Response(
                {
                    'run_log_id': log.id,
                    'status_code': response.status_code,
                    'ok': response.is_success,
                    'duration_ms': round(duration_ms, 2),
                    'response_headers': dict(response.headers),
                    'response_body': response.text,
                }
            )

        except Exception as exc:
            log = ApiRunLog.objects.create(
                request_template=template,
                method=config['method'],
                url=config['url'],
                success=False,
                error_message=str(exc),
            )
            return Response(
                {
                    'run_log_id': log.id,
                    'detail': 'request execution failed',
                    'error': str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class RunLoadTestView(APIView):
    def post(self, request):
        serializer = RunLoadTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scenario, template, execution, error = _resolve_load_execution(data)
        if error:
            code = status.HTTP_404_NOT_FOUND if error['detail'].endswith('not found') else status.HTTP_400_BAD_REQUEST
            return Response(error, status=code)

        variables = resolve_environment(execution['environment_id'])
        run = LoadTestRun.objects.create(
            scenario=scenario,
            request_template=template,
            environment_id=execution['environment_id'],
            status='running',
            request_snapshot=execution['config'],
            total_requests=execution['total_requests'],
            concurrency=execution['concurrency'],
            mode=execution['mode'],
            delay_ms=execution['delay_ms'],
        )

        try:
            output = run_load_test(
                config=execution['config'],
                variables=variables,
                total_requests=execution['total_requests'],
                concurrency=execution['concurrency'],
                mode=execution['mode'],
                delay_ms=execution['delay_ms'],
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

            return Response(
                {
                    'load_run_id': run.id,
                    'status': run.status,
                    'total_requests': run.total_requests,
                    'concurrency': run.concurrency,
                    'mode': run.mode,
                    'success_count': run.success_count,
                    'failure_count': run.failure_count,
                    'min_ms': run.min_ms,
                    'max_ms': run.max_ms,
                    'avg_ms': run.avg_ms,
                    'p95_ms': run.p95_ms,
                    'p99_ms': run.p99_ms,
                    'total_duration_ms': run.total_duration_ms,
                    'requests_per_second': run.requests_per_second,
                    'error_summary': run.error_summary,
                }
            )
        except Exception as exc:
            run.status = 'failed'
            run.finished_at = timezone.now()
            run.error_summary = {'fatal': str(exc)}
            run.save()
            return Response(
                {
                    'load_run_id': run.id,
                    'status': run.status,
                    'detail': 'load test execution failed',
                    'error': str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class RunLoadTestAsyncView(APIView):
    def post(self, request):
        serializer = RunLoadTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scenario, template, execution, error = _resolve_load_execution(data)
        if error:
            code = status.HTTP_404_NOT_FOUND if error['detail'].endswith('not found') else status.HTTP_400_BAD_REQUEST
            return Response(error, status=code)

        run = LoadTestRun.objects.create(
            scenario=scenario,
            request_template=template,
            environment_id=execution['environment_id'],
            status='queued',
            request_snapshot=execution['config'],
            total_requests=execution['total_requests'],
            concurrency=execution['concurrency'],
            mode=execution['mode'],
            delay_ms=execution['delay_ms'],
        )

        task = execute_load_test_task.delay(run.id)
        run.task_id = task.id
        run.save(update_fields=['task_id'])

        return Response(
            {
                'load_run_id': run.id,
                'task_id': task.id,
                'status': run.status,
                'detail': 'load test queued',
            },
            status=status.HTTP_202_ACCEPTED,
        )
