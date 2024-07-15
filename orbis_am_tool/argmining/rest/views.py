from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.openapi import OpenApiParameter, OpenApiResponse, OpenApiTypes
from drf_spectacular.utils import extend_schema
from itertools import permutations
from rest_framework import generics, views, status
from rest_framework.response import Response

from argmining.models import ArgumentativeComponent, ArgumentativeRelation
from argmining.rest import serializers
from debate.models import Author, Debate, Source, Statement
from debate.rest.serializers import StatementSerializer

from utils.pipelines import arguments_components_model, arguments_relations_model


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="identifier",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="The unique identifier of the component to retrieve.",
        )
    ],
    responses={
        status.HTTP_200_OK: serializers.ArgumentativeComponentSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(description="The component was not found"),
    },
)
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


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="override",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description=(
                "If `true` then runs the model again on statements where it has been already run."
            ),
        )
    ],
    request=serializers.ArgumentationMiningPipelineSerializer,
    responses={
        status.HTTP_200_OK: StatementSerializer(many=True),
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            description="There was a problem while parsing the data"
        ),
    },
)
class ArgumentMiningPipelineView(views.APIView):
    """
    Argument Mining Pipeline View

    This view is in charge of running the argumentation mining pipeline given a
    debate (which is a list of statements).

    After a successful POST request it will return the list of Statements
    created with their corresponding analysis.
    """

    def post(self, request, format=None):
        pipeline_data = serializers.ArgumentationMiningPipelineSerializer(data=request.data)

        if not pipeline_data.is_valid():
            return Response(pipeline_data.errors, status=status.HTTP_400_BAD_REQUEST)

        override = request.query_params.get("override", "").lower() in {"true", "1"}

        # We try to get the Source (if it was given), if it doesn't exist we create it
        if "source" not in pipeline_data.validated_data:
            source = None
        else:
            source, _ = Source.objects.filter(
                Q(identifier=pipeline_data.validated_data["source"])
                | Q(name=pipeline_data.validated_data["source"])
            ).get_or_create(defaults={"name": pipeline_data.validated_data["source"]})

        # We try to get the Debate, if it doesn't exist we create it
        debate, _ = Debate.objects.filter(
            Q(identifier=pipeline_data.validated_data["debate"])
            | Q(name=pipeline_data.validated_data["debate"])
        ).get_or_create(defaults={"name": pipeline_data.validated_data["debate"], "source": source})

        # For each of the statements we create them and assign them to the debate
        statements = []
        for statement_data in pipeline_data.validated_data["statements"]:
            # First check if the author exists, or create it
            author, _ = Author.objects.filter(
                Q(identifier=statement_data["author"]) | Q(name=statement_data["author"])
            ).get_or_create(defaults={"name": statement_data["author"]})

            # Then we instantiate an statement, and check if it exists in the DB
            # (by identifier), if that's the case we retrieve it.
            statement, created = Statement.objects.get_or_create(
                statement=statement_data["statement"], debate=debate, author=author
            )
            statements.append(statement)

            if not created and not override:
                # Don't run the models on existing statements unless asked to do so
                continue

            # Run the component detection model
            components = []
            for component in arguments_components_model(statement.statement):
                # Only consider components above certain threshold
                if component["score"] < settings.MINIMUM_COMPONENT_SCORE:
                    continue

                component = ArgumentativeComponent(
                    statement=statement,
                    start=component["start"],
                    end=component["end"],
                    label=component["entity_group"],
                    score=component["score"],
                )

                # Clean leading and trailing spaces from the component
                leading_spaces = len(component.statement_fragment) - len(
                    component.statement_fragment.lstrip(" ")
                )
                component.start += leading_spaces

                trailing_spaces = len(component.statement_fragment) - len(
                    component.statement_fragment.rstrip(" ")
                )
                component.end -= trailing_spaces

                # Check the component fragment has a minimum length (to avoid
                # components with only single words)
                if len(component.statement_fragment) < settings.MINIMUM_COMPONENT_LENGTH:
                    continue

                component_identifier = component.build_identifier()
                if ArgumentativeComponent.objects.filter(identifier=component_identifier).exists():
                    component = ArgumentativeComponent.objects.get(identifier=component_identifier)
                else:
                    component.save()
                components.append(component)

            # Run relation classification comparing every considered component
            pairs_indices = list(permutations(range(len(components)), 2))
            relations_pairs = [
                {
                    "text": statement.statement[components[i].start : components[i].end],
                    "text_pair": statement.statement[components[j].start : components[j].end],
                }
                for i, j in pairs_indices
            ]
            for rid, relation in enumerate(arguments_relations_model(relations_pairs)):
                # Only consider Attack/Support relations, with a minimum threshold score
                if (
                    relation["label"] != "noRel"
                    and relation["score"] >= settings.MINIMUM_RELATION_SCORE
                ):
                    src, tgt = pairs_indices[rid]
                    # Try to find an existing relationship, if not create it
                    ArgumentativeRelation.objects.get_or_create(
                        source=components[src],
                        target=components[tgt],
                        defaults=dict(
                            label=relation["label"],
                            score=relation["score"],
                        ),
                    )

        statements = StatementSerializer(statements, many=True, context={"request": request})

        return Response(statements.data, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="identifier",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="The unique identifier of the debate to get the argumentative graph.",
        )
    ],
    request=serializers.ArgumentationMiningPipelineSerializer,
    responses={
        status.HTTP_200_OK: serializers.ArgumentativeGraphSerializer,
        status.HTTP_404_NOT_FOUND: OpenApiResponse(description="The debate was not found."),
    },
)
class ArgumentativeGraphView(views.APIView):
    """
    Argumentative Graph View

    Retrieves the whole argumentative graph as a list of nodes and edges of a
    given debate in the database. It provides a different, more complete and
    direct to access, view of the debate.
    """

    def get(self, request, identifier, format=None):
        debate = get_object_or_404(Debate, identifier=identifier)
        nodes = ArgumentativeComponent.objects.filter(statement__debate=debate)
        edges = ArgumentativeRelation.objects.filter(
            Q(source__statement__debate=debate) | Q(target__statement__debate=debate)
        )
        graph = serializers.ArgumentativeGraphSerializer(
            instance={
                "debate": debate,
                "statements": debate.statements.all(),
                "nodes": nodes,
                "edges": edges,
            },
            context={"request": request},
        )
        return Response(graph.data, status=status.HTTP_200_OK)
