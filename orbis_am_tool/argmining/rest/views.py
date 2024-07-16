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

from utils.pipelines import (
    arguments_components_model,
    arguments_relations_model,
    statements_classification_model,
    statements_relations_model,
)


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

            # If the statement already existed in the database and was
            # automatically annotated (i.e., the statement type is set and is
            # not by manual annotation), ignore it unless override option is set
            if (
                not created  # Exists in the DB
                and not statement.has_manual_annotation  # | Automatically Annotated
                and statement.statement_type != ""  # |
                and not override  # Don't override
            ):
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

                # Check the component fragment has a minimum length (e.g., to
                # avoid components with only single words)
                if len(component.statement_fragment) < settings.MINIMUM_COMPONENT_LENGTH:
                    continue

                component_identifier = component.build_identifier()
                if ArgumentativeComponent.objects.filter(identifier=component_identifier).exists():
                    component = ArgumentativeComponent.objects.get(identifier=component_identifier)
                else:
                    component.save()
                components.append(component)

            # Run relation classification but only put Premises as sources
            # Claims can be sources or targets
            pairs_indices = [
                (i, j)
                for i, j in permutations(range(len(components)), 2)
                if components[j].label != ArgumentativeComponent.ArgumentativeComponentLabel.PREMISE
            ]
            relations_pairs = [
                {
                    "text": components[i].statement_fragment,
                    "text_pair": components[j].statement_fragment,
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

            # After building the internal argumentative structure, we
            # automatically classify the statement, that is if it hasn't been
            # manually annotated
            if not statement.has_manual_annotation:
                statement_classification = statements_classification_model(statement.statement)[0]
                statement.statement_type = statement_classification["label"]
                statement.statement_classification_score = statement_classification["score"]
                statement.save()

        statements_text_pairs = []
        statements_pairs = []
        for i, j in permutations(range(len(statements)), 2):
            # Check all the pairs of statements, but only try to classify
            # relations based on the statement's type. I.e., don't classify
            # statements that are marked as Positions as part of the source, or
            # statements marked as Attacking/Supporting as part of the target
            source_statement = statements[i]
            target_statement = statements[j]

            if source_statement.statement_type not in {
                Statement.StatementType.ATTACK,
                Statement.StatementType.SUPPORT,
            }:
                # A statement cannot be a source in a relation unless is an Attack/Support
                continue
            elif target_statement.statement_type != Statement.StatementType.POSITION:
                # A statement cannot be a target in a relation unless is a Position
                continue
            elif source_statement.has_manual_annotation:
                # We shouldn't run automatic annotation on a manually annotated
                # source statement (the target statement on the other hand can
                # be subject to automatic annotation because the relation
                # might not exist in that direction)
                continue
            elif source_statement.related_to and not override:
                # If the source statement has already the related class, don't
                # run it again unless override is specified
                continue
            elif (
                source_statement.statement_classification_score is not None
                and source_statement.statement_classification_score
                < settings.MINIMUM_STATEMENT_CLASSIFICATION_SCORE
            ):
                # If the source statement classification score is too low don't
                # consider it for relation classification
                continue
            elif (
                target_statement.statement_classification_score is not None
                and target_statement.statement_classification_score
                < settings.MINIMUM_STATEMENT_CLASSIFICATION_SCORE
            ):
                # If the target statement classification score is too low don't
                # consider it for relation classification
                continue
            statements_text_pairs.append(
                {"text": source_statement.statement, "text_pair": target_statement.statement}
            )
            statements_pairs.append({"source": source_statement, "target": target_statement})

        relevant_major_claims_pairs = []
        relevant_major_claims_text_pairs = []
        for rid, relation in enumerate(statements_relations_model(statements_text_pairs)):
            # Only consider Attack/Support relations, with a minimum threshold score, that
            # match the statement type of the source
            if (
                relation["label"] == statements_pairs[rid]["source"].statement_type
                and relation["score"] >= settings.MINIMUM_STATEMENT_RELATION_SCORE
            ):
                source_statement = statements_pairs[rid]["source"]
                target_statement = statements_pairs[rid]["target"]
                source_statement.related_to = target_statement
                source_statement.statement_relation_score = relation["score"]
                source_statement.save()

                # Those statements that are related are candidates for cross
                # statement argumentative components relation classification
                # thus we store the major claims, if they exists
                source_major_claim = source_statement.get_major_claim()
                target_major_claim = target_statement.get_major_claim()
                if source_major_claim is not None and target_major_claim is not None:
                    relevant_major_claims_pairs.append(
                        {"source": source_major_claim, "target": target_major_claim}
                    )
                    relevant_major_claims_text_pairs.append(
                        {
                            "text": source_major_claim.statement_fragment,
                            "text_pair": target_major_claim.statement_fragment,
                        }
                    )

        # With all the relevant major claims collected, we want to check the
        # cross statements relations between them
        for rid, relation in enumerate(arguments_relations_model(relevant_major_claims_text_pairs)):
            # Only consider Attack/Support relations, with a minimum threshold score
            if (
                relation["label"] != "noRel"
                and relation["score"] >= settings.MINIMUM_RELATION_SCORE
            ):
                # Try to find an existing relationship, if not create it
                ArgumentativeRelation.objects.get_or_create(
                    source=relevant_major_claims_pairs[rid]["source"],
                    target=relevant_major_claims_pairs[rid]["target"],
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
