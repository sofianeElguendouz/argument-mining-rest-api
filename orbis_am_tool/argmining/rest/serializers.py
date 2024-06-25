from rest_framework import serializers

from argmining.models import ArgumentativeComponent, ArgumentativeRelation


class ArgumentativeRelationSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_label_display")
    source_component_identifier = serializers.HyperlinkedRelatedField(
        view_name="argumentativecomponent-detail",
        read_only=True,
        lookup_field="identifier",
        source="source",
    )
    target_component_identifier = serializers.HyperlinkedRelatedField(
        view_name="argumentativecomponent-detail",
        read_only=True,
        lookup_field="identifier",
        source="target",
    )

    class Meta:
        model = ArgumentativeRelation
        exclude = ["id"]


class ArgumentativeComponentSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="argumentativecomponent-detail", read_only=True, lookup_field="identifier"
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
        exclude = ["identifier"]
