from rest_framework import generics

from debate.models import Author, Debate, Source, Statement
from debate.rest import serializers


class AuthorView(generics.RetrieveAPIView):
    """
    Author View

    It's a read only view of the specific author, obtained via the identifier,
    as a way to difficult the access to the whole database.
    """

    queryset = Author.objects.all()
    serializer_class = serializers.AuthorSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"


class DebateView(generics.RetrieveAPIView):
    """
    Debate View

    It's a read only view of the specific debate, obtained via the identifier,
    as a way to difficult the access to the whole database.
    """

    queryset = Debate.objects.all()
    serializer_class = serializers.DebateSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"


class SourceView(generics.RetrieveAPIView):
    """
    Source View

    It's a read only view of the specific source, obtained via the identifier,
    as a way to difficult the access to the whole database.
    """

    queryset = Source.objects.all()
    serializer_class = serializers.SourceSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"


class StatementView(generics.RetrieveAPIView):
    """
    Statement View

    It's a read only view of the specific statement, obtained via the
    identifier, as a way to difficult the access to the whole database.
    """

    queryset = Statement.objects.all()
    serializer_class = serializers.StatementSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"
