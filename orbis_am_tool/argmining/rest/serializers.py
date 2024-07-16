from rest_framework import serializers

from argmining.models import ArgumentativeComponent, ArgumentativeRelation
from debate.models import Statement


class ArgumentativeRelationSerializer(serializers.ModelSerializer):
    """
    Serializer class for the argumentative relations.

    This is a ``ModelSerializer``, not a ``HyperlinkedModelSerializer``, as the
    only way to access the relations is through the argumentative component API,
    via the ``ArgumentativeComponentSerializer``.
    """

    label = serializers.CharField(
        read_only=True,
        source="get_label_display",
        help_text="The label (attack/support) of this relation.",
    )
    source_component = serializers.HyperlinkedRelatedField(
        view_name="argmining.rest:component-detail",
        lookup_field="identifier",
        read_only=True,
        source="source",
        help_text="The URL that identifies the source component of this relation.",
    )
    target_component = serializers.HyperlinkedRelatedField(
        view_name="argmining.rest:component-detail",
        lookup_field="identifier",
        read_only=True,
        source="target",
        help_text="The URL that identifies the target component of this relation.",
    )

    class Meta:
        model = ArgumentativeRelation
        fields = [
            "source_component",
            "target_component",
            "label",
            "score",
            "has_manual_annotation",
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
    accessed through their own REST API (i.e., the ``/api/argmining``) or if they
    can be a part of the ``/api/debate`` REST API.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="argmining.rest:component-detail",
        lookup_field="identifier",
        read_only=True,
        help_text="The URL that identifies this component resource.",
    )
    statement = serializers.HyperlinkedRelatedField(
        view_name="debate.rest:statement-detail",
        lookup_field="identifier",
        read_only=True,
        help_text="The URL that identifies this component's statement resource.",
    )
    label = serializers.CharField(
        read_only=True,
        source="get_label_display",
        help_text="The label (claim or premise) of this component.",
    )
    relations_as_source = ArgumentativeRelationSerializer(
        many=True,
        read_only=True,
        help_text="The list of relations this component is part of as a source of the relation.",
    )
    relations_as_target = ArgumentativeRelationSerializer(
        many=True,
        read_only=True,
        help_text="The list of relations this component is part of as a target of the relation.",
    )

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
            "has_manual_annotation",
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


class ArgumentativeGraphNodeSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for a node of an Argumentative Graph

    A node is an argumentative component of a statement, but it won't show the
    relations of it as they are covered by the edges in the Graph.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="argmining.rest:component-detail",
        lookup_field="identifier",
        read_only=True,
        help_text="The URL that identifies the component associated to this node.",
    )
    statement = serializers.HyperlinkedRelatedField(
        view_name="debate.rest:statement-detail",
        lookup_field="identifier",
        read_only=True,
        help_text="The URL to the statement's resource of this component.",
    )
    label = serializers.CharField(read_only=True, source="get_label_display")

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
            "has_manual_annotation",
        ]


class ArgumentativeGraphEdgeSerializer(serializers.ModelSerializer):
    """
    Serializer for an Edge of an Argumentative Graph

    The edge is the relation between two components (nodes). It's another view
    for the Argumentative Relation that has direct access to each of the
    components parts to make it easier to retrieve.
    """

    label = serializers.CharField(source="get_label_display")
    source_url = serializers.HyperlinkedRelatedField(
        view_name="argmining.rest:component-detail",
        lookup_field="identifier",
        read_only=True,
        source="source",
        help_text="The URL that identifier the component that is the source of the relation.",
    )
    source_text = serializers.CharField(
        read_only=True,
        source="source.statement_fragment",
        help_text="The text fragment of the source component.",
    )
    target_url = serializers.HyperlinkedRelatedField(
        view_name="argmining.rest:component-detail",
        lookup_field="identifier",
        read_only=True,
        source="target",
        help_text="The URL that identifier the component that is the target of the relation.",
    )
    target_text = serializers.CharField(
        read_only=True,
        source="target.statement_fragment",
        help_text="The text fragment of the target component.",
    )

    class Meta:
        model = ArgumentativeRelation
        fields = [
            "source_url",
            "target_url",
            "label",
            "score",
            "source_text",
            "target_text",
            "has_manual_annotation",
        ]


class ArgumentativeGraphStatementSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for a statement of the debate of the Argumentative Graph.

    This is useful for direct access to the statement full information, without
    the extras like the argumentative components and relations since those are
    already the edges and nodes of the Argumentative Graph.
    """

    url = serializers.HyperlinkedIdentityField(
        view_name="debate.rest:statement-detail",
        lookup_field="identifier",
        read_only=True,
        help_text="The URL that identifies the statement.",
    )
    author = serializers.HyperlinkedRelatedField(
        view_name="debate.rest:author-detail",
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
    related_to = serializers.HyperlinkedRelatedField(
        view_name="debate.rest:statement-detail",
        lookup_field="identifier",
        read_only=True,
        help_text="The URL that identifies the statement with which this statement is realted to.",
    )

    class Meta:
        model = Statement
        fields = [
            "url",
            "author",
            "statement_type",
            "statement",
            "statement_classification_score",
            "related_to",
            "statement_relation_score",
            "has_manual_annotation",
        ]


class ArgumentativeGraphSerializer(serializers.Serializer):
    """
    A serializer for the Argumentative Graph of a Debate

    This serializer builds the full argumentative graph given the relations and
    components of a given debate.
    """

    debate = serializers.HyperlinkedRelatedField(
        view_name="debate.rest:debate-detail",
        lookup_field="identifier",
        read_only=True,
        help_text="The URL that identfies the debate's resource of this graph.",
    )
    statements = ArgumentativeGraphStatementSerializer(
        many=True,
        read_only=True,
    )
    nodes = ArgumentativeGraphNodeSerializer(
        many=True,
        read_only=True,
    )
    edges = ArgumentativeGraphEdgeSerializer(
        many=True,
        read_only=True,
    )
