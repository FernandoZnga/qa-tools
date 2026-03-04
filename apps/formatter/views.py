import json
import difflib
from xml.dom import minidom
import xml.etree.ElementTree as ET

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class FormatPayloadView(APIView):
    def post(self, request):
        payload = request.data.get('input', '')
        format_type = request.data.get('format', 'json').lower()
        action = request.data.get('action', 'pretty').lower()

        if format_type not in {'json', 'xml'}:
            return Response(
                {'detail': 'format must be one of: json, xml'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action not in {'pretty', 'minify'}:
            return Response(
                {'detail': 'action must be one of: pretty, minify'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if format_type == 'json':
                parsed = json.loads(payload)
                formatted = (
                    json.dumps(parsed, indent=2, ensure_ascii=False)
                    if action == 'pretty'
                    else json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
                )
            else:
                root = ET.fromstring(payload)
                xml_bytes = ET.tostring(root, encoding='utf-8')
                if action == 'pretty':
                    formatted = minidom.parseString(xml_bytes).toprettyxml(indent='  ')
                else:
                    formatted = xml_bytes.decode('utf-8')

            return Response({'valid': True, 'output': formatted})

        except Exception as exc:
            return Response(
                {
                    'valid': False,
                    'error': str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class DiffPayloadView(APIView):
    def post(self, request):
        text_a = request.data.get('text_a', '')
        text_b = request.data.get('text_b', '')

        file_a = request.FILES.get('file_a')
        file_b = request.FILES.get('file_b')
        from_name = request.data.get('from_name') or 'a'
        to_name = request.data.get('to_name') or 'b'
        ignore_whitespace = str(request.data.get('ignore_whitespace', 'false')).lower() == 'true'

        if file_a:
            text_a = file_a.read().decode('utf-8', errors='replace')
            from_name = file_a.name
        if file_b:
            text_b = file_b.read().decode('utf-8', errors='replace')
            to_name = file_b.name

        if not text_a and not text_b:
            return Response(
                {'detail': 'Provide text_a/text_b or upload file_a/file_b.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)
        if ignore_whitespace:
            lines_a = [line.strip() + '\n' for line in lines_a]
            lines_b = [line.strip() + '\n' for line in lines_b]

        diff_output = ''.join(
            difflib.unified_diff(
                lines_a,
                lines_b,
                fromfile=from_name,
                tofile=to_name,
                lineterm='\n',
            )
        )

        return Response(
            {
                'has_diff': bool(diff_output),
                'diff': diff_output,
                'from_name': from_name,
                'to_name': to_name,
            }
        )
