from rest_framework import serializers

from .models import ApiRequestTemplate, ApiRunLog, LoadTestRun, LoadTestScenario


class ApiRequestTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiRequestTemplate
        fields = [
            'id',
            'name',
            'method',
            'url',
            'headers',
            'query_params',
            'body',
            'body_type',
            'timeout_seconds',
            'environment',
            'created_at',
            'updated_at',
        ]


class ApiRunLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiRunLog
        fields = [
            'id',
            'request_template',
            'method',
            'url',
            'response_status',
            'response_time_ms',
            'response_headers',
            'response_body',
            'success',
            'error_message',
            'created_at',
        ]


class LoadTestScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoadTestScenario
        fields = [
            'id',
            'name',
            'request_template',
            'environment',
            'method',
            'url',
            'headers',
            'query_params',
            'body',
            'body_type',
            'timeout_seconds',
            'total_requests',
            'concurrency',
            'mode',
            'delay_ms',
            'created_at',
            'updated_at',
        ]


class LoadTestRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoadTestRun
        fields = [
            'id',
            'scenario',
            'request_template',
            'environment',
            'status',
            'task_id',
            'request_snapshot',
            'total_requests',
            'concurrency',
            'mode',
            'delay_ms',
            'success_count',
            'failure_count',
            'min_ms',
            'max_ms',
            'avg_ms',
            'p95_ms',
            'p99_ms',
            'total_duration_ms',
            'requests_per_second',
            'error_summary',
            'results',
            'started_at',
            'finished_at',
        ]


class SendApiRequestSerializer(serializers.Serializer):
    template_id = serializers.IntegerField(required=False)
    method = serializers.ChoiceField(choices=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], required=False)
    url = serializers.URLField(required=False)
    headers = serializers.DictField(required=False)
    query_params = serializers.DictField(required=False)
    body = serializers.CharField(required=False, allow_blank=True)
    body_type = serializers.ChoiceField(choices=['json', 'xml', 'raw'], required=False)
    timeout_seconds = serializers.IntegerField(required=False, min_value=1, max_value=300)
    environment_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if not attrs.get('template_id') and not (attrs.get('method') and attrs.get('url')):
            raise serializers.ValidationError('Provide template_id or both method and url.')
        return attrs


class RunLoadTestSerializer(serializers.Serializer):
    scenario_id = serializers.IntegerField(required=False)
    template_id = serializers.IntegerField(required=False)
    method = serializers.ChoiceField(choices=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], required=False)
    url = serializers.URLField(required=False)
    headers = serializers.DictField(required=False)
    query_params = serializers.DictField(required=False)
    body = serializers.CharField(required=False, allow_blank=True)
    body_type = serializers.ChoiceField(choices=['json', 'xml', 'raw'], required=False)
    timeout_seconds = serializers.IntegerField(required=False, min_value=1, max_value=300)
    environment_id = serializers.IntegerField(required=False)
    total_requests = serializers.IntegerField(required=False, min_value=1, max_value=5000)
    concurrency = serializers.IntegerField(required=False, min_value=1, max_value=300)
    mode = serializers.ChoiceField(choices=['single', 'multi'], required=False)
    delay_ms = serializers.IntegerField(required=False, min_value=0, max_value=60000)

    def validate(self, attrs):
        has_scenario = attrs.get('scenario_id') is not None
        has_template = attrs.get('template_id') is not None
        has_adhoc = attrs.get('method') and attrs.get('url')

        if not has_scenario and not has_template and not has_adhoc:
            raise serializers.ValidationError(
                'Provide scenario_id, template_id, or both method and url for ad-hoc run.'
            )

        return attrs
