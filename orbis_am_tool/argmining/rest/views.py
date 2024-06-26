from rest_framework import generics

from argmining.models import ArgumentativeComponent
from argmining.rest import serializers


class ArgumentativeComponentView(generics.RetrieveAPIView):
    """
    Argumentative Component View.

    It's a read only view for the specific argumentative component, since an
    argumentive component only makes sense in the context of the statement that
    provided it, and it's not a good idea to be able to list the whole set of
    argumentative components in the DB.
    """

    queryset = ArgumentativeComponent.objects.all()
    serializer_class = serializers.ArgumentativeComponentSerializer
    lookup_field = "identifier"
