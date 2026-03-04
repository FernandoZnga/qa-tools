import ast
import random
import re
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Environment, EnvironmentVariable
from .serializers import EnvironmentSerializer, EnvironmentVariableSerializer


FIRST_NAMES = ['Alex', 'Jordan', 'Taylor', 'Casey', 'Morgan', 'Riley', 'Avery', 'Reese']
LAST_NAMES = ['Smith', 'Johnson', 'Brown', 'Williams', 'Davis', 'Miller', 'Wilson', 'Moore']
DOMAINS = ['example.com', 'testmail.dev', 'qa.local']
_PROVIDER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


class EnvironmentViewSet(viewsets.ModelViewSet):
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer


class EnvironmentVariableViewSet(viewsets.ModelViewSet):
    queryset = EnvironmentVariable.objects.select_related('environment').all()
    serializer_class = EnvironmentVariableSerializer


class RandomDataView(APIView):
    def get(self, request):
        count = min(int(request.query_params.get('count', 1)), 50)
        rows = [self._one() for _ in range(count)]
        return Response({'count': count, 'results': rows})

    def _one(self):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f'{first_name} {last_name}'
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 99)}@{random.choice(DOMAINS)}"
        phone = f'+1{random.randint(2000000000, 9999999999)}'
        now = datetime.now(timezone.utc)

        return {
            'uuid': str(uuid.uuid4()),
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'boolean': random.choice([True, False]),
            'integer': random.randint(1, 100000),
            'timestamp_utc': now.isoformat(),
            'future_date_utc': (now + timedelta(days=random.randint(1, 365))).date().isoformat(),
        }


class RandomDataProvidersView(APIView):
    def get(self, request):
        locale = request.query_params.get('locale', 'en_US')
        fake = Faker(locale)
        providers = []
        for name in dir(fake):
            if name.startswith('_'):
                continue
            if not _PROVIDER_RE.match(name):
                continue
            if name == 'seed':
                continue
            try:
                attr = getattr(fake, name)
            except Exception:
                continue
            if callable(attr):
                providers.append(name)

        providers.sort()
        return Response({'locale': locale, 'provider_count': len(providers), 'providers': providers})


class RandomDataGenerateView(APIView):
    def post(self, request):
        count = min(max(int(request.data.get('count', 1)), 1), 500)
        locale = request.data.get('locale', 'en_US')
        seed = request.data.get('seed')
        schema = request.data.get('schema', {})
        commands = request.data.get('commands', '')

        fake = Faker(locale)
        if seed is not None and str(seed).strip() != '':
            fake.seed_instance(int(seed))

        if schema and not isinstance(schema, dict):
            return Response({'detail': 'schema must be a JSON object'}, status=status.HTTP_400_BAD_REQUEST)

        command_specs = []
        if commands:
            if not isinstance(commands, str):
                return Response({'detail': 'commands must be a string'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                command_specs = self._parse_commands(commands)
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not schema and not command_specs:
            schema = {
                'uuid': 'uuid4',
                'name': 'name',
                'email': 'email',
                'phone': 'phone_number',
                'address': 'address',
                'company': 'company',
                'date': 'date',
            }

        try:
            results = [self._generate_row(fake, schema, command_specs) for _ in range(count)]
        except Exception as exc:
            return Response({'detail': f'generation failed: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'count': count,
                'locale': locale,
                'seed': seed,
                'schema_keys': list(schema.keys()) if isinstance(schema, dict) else [],
                'command_count': len(command_specs),
                'results': results,
            }
        )

    def _generate_row(self, fake, schema, command_specs):
        row = {}

        for key, spec in schema.items():
            if isinstance(spec, str):
                row[key] = self._call_provider(fake, spec, [], {})
            elif isinstance(spec, dict):
                provider = spec.get('provider')
                args = spec.get('args', [])
                kwargs = spec.get('kwargs', {})
                row[key] = self._call_provider(fake, provider, args, kwargs)
            else:
                raise ValueError(f'invalid schema for key {key}: use string or object')

        for cmd in command_specs:
            row[cmd['var_name']] = self._call_provider(fake, cmd['provider'], cmd['args'], cmd['kwargs'])

        return row

    def _call_provider(self, fake, provider, args, kwargs):
        if not isinstance(provider, str) or not _PROVIDER_RE.match(provider):
            raise ValueError(f'invalid provider name: {provider}')

        fn = getattr(fake, provider, None)
        if not callable(fn):
            raise ValueError(f'unknown Faker provider: {provider}')

        if not isinstance(args, list):
            raise ValueError('args must be a list')
        if not isinstance(kwargs, dict):
            raise ValueError('kwargs must be an object')

        return fn(*args, **kwargs)

    def _parse_commands(self, commands_text):
        specs = []
        lines = commands_text.splitlines()

        for idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue

            try:
                parsed = ast.parse(line, mode='exec')
            except SyntaxError as exc:
                raise ValueError(f'Invalid command syntax on line {idx}: {exc.msg}') from exc

            if len(parsed.body) != 1 or not isinstance(parsed.body[0], ast.Assign):
                raise ValueError(f'Line {idx} must be assignment like: var_name = provider(args)')

            assign = parsed.body[0]
            if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
                raise ValueError(f'Line {idx} must assign to a single variable name')

            var_name = assign.targets[0].id
            if not _PROVIDER_RE.match(var_name):
                raise ValueError(f'Invalid variable name on line {idx}: {var_name}')

            if not isinstance(assign.value, ast.Call) or not isinstance(assign.value.func, ast.Name):
                raise ValueError(f'Line {idx} right side must be a provider call, e.g. email()')

            provider = assign.value.func.id
            if not _PROVIDER_RE.match(provider):
                raise ValueError(f'Invalid provider name on line {idx}: {provider}')

            args = []
            kwargs = {}
            for arg_node in assign.value.args:
                args.append(ast.literal_eval(arg_node))
            for kw in assign.value.keywords:
                if kw.arg is None:
                    raise ValueError(f'Line {idx} does not support **kwargs expansion')
                kwargs[kw.arg] = ast.literal_eval(kw.value)

            specs.append({'var_name': var_name, 'provider': provider, 'args': args, 'kwargs': kwargs})

        return specs
