from rest_framework import serializers

from argmining.rest.serializers import ArgumentativeComponentSerializer
from debate.models import Author, Debate, Source, Statement


class SourceSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="source-detail",
        read_only=True,
        lookup_field="identifier",
    )

    class Meta:
        model = Source
        exclude = ["identifier"]


class DebateSerializer(serializers.HyperlinkedModelSerializer):
    source = serializers.HyperlinkedRelatedField(
        view_name="source-detail",
        read_only=True,
        lookup_field="identifier",
    )
    url = serializers.HyperlinkedIdentityField(
        view_name="debate-detail",
        read_only=True,
        lookup_field="identifier",
    )
    statements = serializers.HyperlinkedRelatedField(
        many=True,
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
    )

    class Meta:
        model = Debate
        exclude = ["identifier"]


class AuthorSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="author-detail", read_only=True, lookup_field="identifier"
    )

    class Meta:
        model = Author
        exclude = ["identifier"]


class StatementSerializer(serializers.HyperlinkedModelSerializer):
    debate = serializers.HyperlinkedRelatedField(
        view_name="debate-detail",
        read_only=True,
        lookup_field="identifier",
    )
    url = serializers.HyperlinkedIdentityField(
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
    )
    author = serializers.HyperlinkedRelatedField(
        view_name="author-detail",
        read_only=True,
        lookup_field="identifier",
    )
    statement_type = serializers.CharField(source="get_statement_type_display")
    related_to = serializers.HyperlinkedRelatedField(
        view_name="statement-detail", read_only=True, lookup_field="identifier"
    )
    related_statements = serializers.HyperlinkedRelatedField(
        many=True,
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
    )
    argumentative_components = ArgumentativeComponentSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Statement
        exclude = ["identifier"]
