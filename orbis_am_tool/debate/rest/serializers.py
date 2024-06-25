from rest_framework import serializers

from debate.models import Author, Debate, Source, Statement


class SourceSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="source-detail", read_only=True, lookup_field="identifier"
    )

    class Meta:
        model = Source
        fields = ["url", "slug", "name", "description"]


class DebateSerializer(serializers.HyperlinkedModelSerializer):
    source = SourceSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(
        view_name="debate-detail", read_only=True, lookup_field="identifier"
    )
    statements = serializers.HyperlinkedRelatedField(
        many=True,
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
    )

    class Meta:
        model = Debate
        fields = ["url", "slug", "name", "summary", "source", "statements"]
        lookup_field = "identifier"
        lookup_url_kwarg = "identifier"


class AuthorSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="author-detail", read_only=True, lookup_field="identifier"
    )

    class Meta:
        model = Author
        fields = [
            "url",
            "slug",
            "name",
        ]


class StatementSerializer(serializers.HyperlinkedModelSerializer):
    debate = serializers.HyperlinkedRelatedField(
        view_name="debate-detail", read_only=True, lookup_field="identifier"
    )
    url = serializers.HyperlinkedIdentityField(
        view_name="statement-detail", read_only=True, lookup_field="identifier"
    )
    author = AuthorSerializer(read_only=True)
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

    class Meta:
        model = Statement
        fields = [
            "url",
            "debate",
            "author",
            "statement",
            "statement_type",
            "related_to",
            "related_statements",
        ]
        lookup_field = "identifier"
