from drf_spectacular.openapi import OpenApiParameter, OpenApiResponse, OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status

from debate.models import Author, Debate, Source, Statement
from debate.rest import serializers


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="identifier",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="The unique identifier of the author to retrieve.",
        )
    ],
    responses={
        status.HTTP_200_OK: serializers.AuthorSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(description="The author was not found."),
    },
)
class AuthorView(generics.RetrieveAPIView):
    """
    Author View

    It's a read only view of the specific author, obtained via the identifier.
    """

    queryset = Author.objects.all()
    serializer_class = serializers.AuthorSerializer
    lookup_field = "identifier"


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="identifier",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="The unique identifier of the debate to retrieve.",
        )
    ],
    responses={
        status.HTTP_200_OK: serializers.DebateSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(description="The debate was not found."),
    },
)
class DebateView(generics.RetrieveAPIView):
    """
    Debate View

    It's a read only view of the specific debate, obtained via the identifier.
    """

    queryset = Debate.objects.all()
    serializer_class = serializers.DebateSerializer
    lookup_field = "identifier"


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="identifier",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="The unique identifier of the source to retrieve.",
        )
    ],
    responses={
        status.HTTP_200_OK: serializers.SourceSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(description="The source was not found."),
    },
)
class SourceView(generics.RetrieveAPIView):
    """
    Source View

    It's a read only view of the specific source, obtained via the identifier.
    """

    queryset = Source.objects.all()
    serializer_class = serializers.SourceSerializer
    lookup_field = "identifier"


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="identifier",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="The unique identifier of the statement to retrieve.",
        )
    ],
    responses={
        status.HTTP_200_OK: serializers.SourceSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(description="The statement was not found."),
    },
)
class StatementView(generics.RetrieveAPIView):
    """
    Statement View

    It's a read only view of the specific statement, obtained via the
    identifier.
    """

    queryset = Statement.objects.all()
    serializer_class = serializers.StatementSerializer
    lookup_field = "identifier"
