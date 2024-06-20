from rest_framework import viewsets

from debate.models import Author, Debate, Source, Statement
from debate.rest import serializers


class AuthorView(viewsets.ReadOnlyModelViewSet):
    queryset = Author.objects.all()
    serializer_class = serializers.AuthorSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"


class DebateView(viewsets.ReadOnlyModelViewSet):
    queryset = Debate.objects.all()
    serializer_class = serializers.DebateSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"


class SourceView(viewsets.ReadOnlyModelViewSet):
    queryset = Source.objects.all()
    serializer_class = serializers.SourceSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"


class StatementView(viewsets.ReadOnlyModelViewSet):
    queryset = Statement.objects.all()
    serializer_class = serializers.StatementSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"
