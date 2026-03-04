import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from apps.core.models import Environment


_PLACEHOLDER_PATTERN = re.compile(r'\{\{\s*([A-Za-z0-9_\-]+)\s*\}\}')


def _replace_placeholders(value, variables):
    if isinstance(value, str):
        def repl(match):
            key = match.group(1)
            return str(variables.get(key, match.group(0)))

        return _PLACEHOLDER_PATTERN.sub(repl, value)

    if isinstance(value, dict):
        return {k: _replace_placeholders(v, variables) for k, v in value.items()}

    if isinstance(value, list):
        return [_replace_placeholders(item, variables) for item in value]

    return value


def resolve_environment(environment_id):
    if not environment_id:
        return {}

    env = Environment.objects.prefetch_related('variables').filter(id=environment_id).first()
    if not env:
        return {}

    return {item.key: item.value for item in env.variables.all()}


def execute_request(config, variables):
    method = config['method']
    url = _replace_placeholders(config['url'], variables)
    headers = _replace_placeholders(config.get('headers', {}), variables)
    params = _replace_placeholders(config.get('query_params', {}), variables)
    body = _replace_placeholders(config.get('body', ''), variables)
    body_type = config.get('body_type', 'json')
    timeout_seconds = config.get('timeout_seconds', 30)

    req_kwargs = {
        'method': method,
        'url': url,
        'headers': headers,
        'params': params,
        'timeout': timeout_seconds,
    }

    if body:
        if body_type == 'json':
            req_kwargs['json'] = json.loads(body)
        elif body_type == 'xml':
            req_kwargs['content'] = body.encode('utf-8')
            req_kwargs['headers'] = {**headers, 'Content-Type': 'application/xml'}
        else:
            req_kwargs['content'] = body.encode('utf-8')

    start = time.perf_counter()
    response = httpx.request(**req_kwargs)
    duration_ms = (time.perf_counter() - start) * 1000

    return response, duration_ms, {'method': method, 'url': url}


def _percentile(values, p):
    if not values:
        return None

    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    k = (len(sorted_values) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)

    if f == c:
        return sorted_values[f]

    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


def _build_stats(results, total_duration_ms):
    durations = [item['duration_ms'] for item in results if item.get('duration_ms') is not None]
    successes = sum(1 for item in results if item.get('success'))
    failures = len(results) - successes
    errors = [item.get('error', '') for item in results if item.get('error')]
    error_summary = dict(Counter(errors))

    if durations:
        min_ms = min(durations)
        max_ms = max(durations)
        avg_ms = sum(durations) / len(durations)
        p95_ms = _percentile(durations, 95)
        p99_ms = _percentile(durations, 99)
    else:
        min_ms = max_ms = avg_ms = p95_ms = p99_ms = None

    rps = (len(results) / (total_duration_ms / 1000)) if total_duration_ms > 0 else None

    return {
        'success_count': successes,
        'failure_count': failures,
        'min_ms': round(min_ms, 2) if min_ms is not None else None,
        'max_ms': round(max_ms, 2) if max_ms is not None else None,
        'avg_ms': round(avg_ms, 2) if avg_ms is not None else None,
        'p95_ms': round(p95_ms, 2) if p95_ms is not None else None,
        'p99_ms': round(p99_ms, 2) if p99_ms is not None else None,
        'total_duration_ms': round(total_duration_ms, 2),
        'requests_per_second': round(rps, 2) if rps is not None else None,
        'error_summary': error_summary,
    }


def run_load_test(config, variables, total_requests, concurrency, mode, delay_ms):
    def execute_one(sequence):
        if delay_ms > 0:
            time.sleep(delay_ms / 1000)

        try:
            response, duration_ms, _ = execute_request(config, variables)
            return {
                'sequence': sequence,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
                'success': response.is_success,
                'error': '',
            }
        except Exception as exc:
            return {
                'sequence': sequence,
                'status_code': None,
                'duration_ms': None,
                'success': False,
                'error': str(exc),
            }

    started = time.perf_counter()
    results = []

    if mode == 'single':
        for i in range(total_requests):
            results.append(execute_one(i + 1))
    else:
        worker_count = min(concurrency, total_requests)
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(execute_one, i + 1) for i in range(total_requests)]
            for future in as_completed(futures):
                results.append(future.result())

    total_duration_ms = (time.perf_counter() - started) * 1000
    results.sort(key=lambda item: item['sequence'])

    stats = _build_stats(results, total_duration_ms)
    stats['results'] = results

    return stats


def build_postman_collection_from_config(config, name='qa-tools request', identifier='custom'):
    headers = [{'key': str(k), 'value': str(v)} for k, v in (config.get('headers') or {}).items()]
    url_query = [{'key': str(k), 'value': str(v)} for k, v in (config.get('query_params') or {}).items()]

    item = {
        'name': name,
        'request': {
            'method': config.get('method', 'GET'),
            'header': headers,
            'url': {
                'raw': config.get('url', ''),
                'host': [config.get('url', '')],
                'query': url_query,
            },
            'body': {
                'mode': 'raw',
                'raw': config.get('body', ''),
                'options': {
                    'raw': {
                        'language': 'json' if config.get('body_type', 'json') == 'json' else 'text'
                    }
                },
            },
        },
        'response': [],
    }

    return {
        'info': {
            'name': f'qa-tools::{name}',
            '_postman_id': str(identifier),
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
        },
        'item': [item],
    }


def build_postman_collection(template):
    config = {
        'method': template.method,
        'url': template.url,
        'headers': template.headers,
        'query_params': template.query_params,
        'body': template.body,
        'body_type': template.body_type,
    }
    return build_postman_collection_from_config(config, name=template.name, identifier=template.id)
