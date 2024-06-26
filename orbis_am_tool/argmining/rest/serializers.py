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
        view_name="component-detail", read_only=True, lookup_field="identifier"
    )
    label = serializers.CharField(source="get_label_display")
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
            "relations_as_source",
            "relations_as_target",
        ]
