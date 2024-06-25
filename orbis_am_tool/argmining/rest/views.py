from rest_framework import viewsets

from argmining.models import ArgumentativeComponent
from argmining.rest import serializers


class ArgumentativeComponentView(viewsets.ReadOnlyModelViewSet):
    queryset = ArgumentativeComponent.objects.all()
    serializer_class = serializers.ArgumentativeComponentSerializer
    lookup_field = "identifier"
    lookup_value_regex = "[0-9a-f]{16}"
