from rest_framework import serializers

from argmining.models import ArgumentativeComponent, ArgumentativeRelation


class ArgumentativeRelationSerializer(serializers.ModelSerializer):
    """
    Serializer class for the argumentative relations.

    This is a ``ModelSerializer``, not a ``HyperlinkedModelSerializer``, as the
    only way to access the relations is through the argumentative component API,
    via the ``ArgumentativeComponentSerializer`` defined below.
    """

    label = serializers.CharField(source="get_label_display")
    source_component = serializers.HyperlinkedRelatedField(
        view_name="component-detail",
        read_only=True,
        lookup_field="identifier",
        source="source",
    )
    target_component = serializers.HyperlinkedRelatedField(
        view_name="component-detail",
        read_only=True,
        lookup_field="identifier",
        source="target",
    )

    class Meta:
        model = ArgumentativeRelation
        fields = [
            "label",
            "source_component",
            "target_component",
        ]


class ArgumentativeComponentSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer class for the argumentative components of a statement.

    This is the only model that isn't accessed through the ``/api/debate`` REST
    API, although its part of the
    ``debate.rest.serializers.StatementSerializer``.

    Unlike relations, which only make sense within the context of a pair of
    argumentative components, the components make sense to have their own REST
    API to be accessed directly, although it's debatable whether they should be
    accessed through their own REST API (i.e., the ``/api/argminin``) or if they
    can be a part of the ``/api/debate`` REST API.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="component-detail",
        read_only=True,
        lookup_field="identifier",
    )
    label = serializers.CharField(read_only=True, source="get_label_display")
    statement = serializers.HyperlinkedRelatedField(
        many=False,
        view_name="statement-detail",
        read_only=True,
        lookup_field="identifier",
    )
    relations_as_source = ArgumentativeRelationSerializer(many=True, read_only=True)
    relations_as_target = ArgumentativeRelationSerializer(many=True, read_only=True)

    class Meta:
        model = ArgumentativeComponent
        fields = [
            "url",
            "statement",
            "label",
            "start",
            "end",
            "score",
            "statement_fragment",
            "relations_as_source",
            "relations_as_target",
        ]


class PlainStatementSerializer(serializers.Serializer):
    """
    A serializer for a plain statement

    A plain statement is a statement that isn't already part of the DB, and the
    user wants to analyze. It must have an associated author. The author can be
    part or not of the database (it will try to look for it before creating it
    new).
    """

    statement = serializers.CharField(
        write_only=True,
        required=True,
        help_text="The statement done by the author. A statement is an argumentative text.",
    )
    author = serializers.CharField(
        write_only=True,
        required=True,
        help_text=(
            "An identifier (can be a name, a nickname, etc.) for an author of the statement. "
            "It can be any string that is unique for such author within a debate. "
            "It can also be the identifier of an author that is already in the DB."
        ),
    )


class ArgumentationMiningPipelineSerializer(serializers.Serializer):
    """
    Serializer for running the argumentation mining pipeline

    This expects a debate as a list of statements done by different authors.

    If an identifier is given, it will try to find the debate in the database
    and append this statements to it. Otherwise it will create a new debate.
    """

    debate = serializers.CharField(
        write_only=True,
        required=True,
        help_text=(
            "The name or identifier of a debate. It will use it to try to find the debate in the "
            "database to append the statements to it. If it doesn't find it, it will create a new "
            "debate in the database."
        ),
    )
    source = serializers.CharField(
        write_only=True,
        required=False,
        help_text=(
            "The source of the debate. It will try to find it via id or name in the database, "
            "and if it's not existing it will create a new source."
        ),
    )
    statements = PlainStatementSerializer(
        many=True,
        write_only=True,
        required=True,
        help_text="The list of statements done by the different authors.",
    )
