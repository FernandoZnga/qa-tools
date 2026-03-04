from rest_framework import serializers

from .models import Environment, EnvironmentVariable


class EnvironmentVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentVariable
        fields = [
            'id',
            'environment',
            'key',
            'value',
            'is_secret',
            'created_at',
            'updated_at',
        ]


class EnvironmentSerializer(serializers.ModelSerializer):
    variables = EnvironmentVariableSerializer(many=True, read_only=True)

    class Meta:
        model = Environment
        fields = ['id', 'name', 'description', 'variables', 'created_at', 'updated_at']
