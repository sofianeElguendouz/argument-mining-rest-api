from rest_framework import serializers

from argmining.rest.serializers import ArgumentativeComponentSerializer
from debate.models import Author, Debate, Source, Statement


class SourceSerializer(serializers.ModelSerializer):
    """
    Serializer for a Debate's ``source`` model.
    """

    class Meta:
        model = Source
        exclude = ["id"]


class DebateSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for a Debate.

    It lists the source (if any) and the statements associated to it, all of
    them via their ``identifier`` field.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="debate-detail",
        read_only=True,
        lookup_field="identifier",
        help_text="The URL that identifies this debate resource.",
    )
    source = SourceSerializer(
        read_only=True,
        required=False,
        help_text="The Source of this debate.",
    )
    statements = serializers.HyperlinkedRelatedField(
        many=True,
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
        help_text=(
            "The list of URLs that identifies the statements resources that are part of this debate"
        ),
    )

    class Meta:
        model = Debate
        fields = [
            "url",
            "name",
            "summary",
            "source",
            "statements",
        ]  # The identifier is already part of the URL


class AuthorSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for an Author

    It overrides the ``url`` parameter so it looks via the ``identifier`` field.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="author-detail",
        read_only=True,
        lookup_field="identifier",
        help_text="The URL that identifies this author resource",
    )
    statements = serializers.HyperlinkedRelatedField(
        many=True,
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
        help_text="The list of URLs that identifies the statements this resource is an author of.",
    )

    class Meta:
        model = Author
        fields = [
            "url",
            "name",
            "statements",
        ]  # Don't provide the real user and the identifier is already in the ULR


class StatementSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer of a Statement.

    It has pointers to the debate and the author it belongs to, using their
    corresponding ``identifier`` field.

    It displays the ``statement_type`` via the ``get_FOO_display`` function to
    show the "human readable" version of it.

    It has an hyperlink to the related statement, if there's one, and a list of
    all the statements that are related to it. In both cases it uses the
    ``identifier`` as the lookup field.

    Finally, it has a list of all the argumentative components that are
    associated to it, with the same representation these components have in
    their API, thus having indirect access to the relationships.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
        help_text="The URL that identifies this statement resource.",
    )
    debate = serializers.HyperlinkedRelatedField(
        view_name="debate-detail",
        read_only=True,
        lookup_field="identifier",
        help_text="The URL that identifies the debate resource of this statement.",
    )
    author = serializers.HyperlinkedRelatedField(
        view_name="author-detail",
        read_only=True,
        lookup_field="identifier",
        help_text="The URL that identifies the author resource of this statement.",
    )
    statement_type = serializers.CharField(
        read_only=True,
        source="get_statement_type_display",
        help_text=(
            "The type of this statement (if it has any): "
            "position, attacking argument or supporting argument"
        ),
    )
    argumentative_components = ArgumentativeComponentSerializer(
        many=True,
        read_only=True,
        help_text="The list of argumentative components that are part of this statement.",
    )
    related_to = serializers.HyperlinkedRelatedField(
        view_name="statement-detail",
        lookup_field="identifier",
        read_only=True,
        help_text=(
            "The URL that identifies the statement resource with "
            "which this statement is related to."
        ),
    )
    related_statements = serializers.HyperlinkedRelatedField(
        many=True,
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
        help_text=(
            "The list of URLs that identifies the statements resources with "
            "which are related to this statement."
        ),
    )

    class Meta:
        model = Statement
        fields = [
            "url",
            "debate",
            "author",
            "statement_type",
            "statement",
            "argumentative_components",
            "related_to",
            "related_statements",
        ]  # The identifier is already part of the URL
