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
from torch import device

from utils.pipelines import (
    arguments_components_model,
    arguments_relations_model,
    statements_classification_model,
    statements_relations_model,
)

#from captum.attr import visualization as viz
from captum.attr import IntegratedGradients, LayerIntegratedGradients
#from captum.attr import configure_interpretable_embedding_layer, remove_interpretable_embedding_layer

import torch
import torch.nn as nn
import json
import numpy as np

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize


# ********************************************* For XAI purposes *********************************************************

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
#logits = ''

# Forward function used by LayerIntegratedGradients
def forward_func_arg_comp(inputs, token_type_ids=None, position_ids=None, attention_mask=None):
    #global logits # to store the logits for further visualization
    pred = arguments_components_model.model.deberta(
        input_ids=inputs,
        token_type_ids=token_type_ids,
        position_ids=position_ids,
        attention_mask=attention_mask
    )
    mean_pooled_output = pred.last_hidden_state.mean(dim=1)  # [batch_size, hidden_size]
    return mean_pooled_output

def forward_func_sta_class(inputs, token_type_ids=None, position_ids=None, attention_mask=None):
    #global logits # to store the logits for further visualization
    pred = statements_classification_model.model.deberta(
        input_ids=inputs,
        token_type_ids=token_type_ids,
        position_ids=position_ids,
        attention_mask=attention_mask
    )
    mean_pooled_output = pred.last_hidden_state.mean(dim=1)  # [batch_size, hidden_size]
    return mean_pooled_output

# Construct input and reference pairs
def construct_input_ref_pair(text, ref_token_id, sep_token_id, cls_token_id):
    input_ids = arguments_components_model.tokenizer.encode(text, add_special_tokens=True)
    ref_input_ids = [cls_token_id] + [ref_token_id] * len(input_ids[1:-1]) + [sep_token_id]
    return torch.tensor([input_ids], device=device), torch.tensor([ref_input_ids], device=device)

# Token type and reference pairs
def construct_input_ref_token_type_pair(input_ids):
    seq_len = input_ids.size(1)
    token_type_ids = torch.tensor([[0] * seq_len], device=device)
    ref_token_type_ids = torch.zeros_like(token_type_ids, device=device)
    return token_type_ids, ref_token_type_ids

# Attention mask
def construct_attention_mask(input_ids):
    return torch.ones_like(input_ids)

# Construct embeddings
def construct_embeddings(input_ids, ref_input_ids, token_type_ids=None, ref_token_type_ids=None):
    input_embeddings = arguments_components_model.model.deberta.embeddings(
        input_ids=input_ids,
        token_type_ids=token_type_ids
    )
    ref_input_embeddings = arguments_components_model.model.deberta.embeddings(
        input_ids=ref_input_ids,
        token_type_ids=ref_token_type_ids
    )
    return input_embeddings, ref_input_embeddings

# Summarize attributions across embedding dimensions
def summarize_attributions(attributions):
    attributions = attributions.sum(dim=-1).squeeze(0)
    attributions = attributions / torch.norm(attributions)
    return attributions

# Get tokenizer tokens
ref_token_id = arguments_components_model.tokenizer.pad_token_id  # Reference token (e.g., padding)
sep_token_id = arguments_components_model.tokenizer.sep_token_id  # Separator token
cls_token_id = arguments_components_model.tokenizer.cls_token_id  # CLS token for start

# Use LayerIntegratedGradients to compute attributions
lig_arg_comp = LayerIntegratedGradients(forward_func_arg_comp, arguments_components_model.model.deberta.embeddings)
lig_sta_class = LayerIntegratedGradients(forward_func_sta_class, statements_classification_model.model.deberta.embeddings)

label2id_arg_comp = {"Claim": 0, "Premise":1}
label2id_sta_class = {"Position": 0, "Attack":1, "Support":2}

# ******************************************************************************************************

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

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="xai",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description=(
                "If `true` then generate explanations alongside argumentation predictions."
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
        xai = request.query_params.get("xai", "").lower() in {"true", "1"}

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
        cpt_statements = 0
        for statement_data in pipeline_data.validated_data["statements"]:
            # print(f"------------------------------------------- Statement {cpt_statements} ----------------------------------------")
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

                #print("Nothing to do, don't override existing!")
                continue
            # Run the component detection model
            components = []
            cpt_statements += 1
            for i, component in enumerate(arguments_components_model(statement.statement)):
                #print(f'***** Component {i} ****** : {component}\n')
                # Only consider components above certain threshold
                if component["score"] < settings.MINIMUM_COMPONENT_SCORE:
                    continue
                # print(f'***** Component {i} Not Ignored ******')

                # ******************************************** Generate explanation attributions for component classification ************************************************************
                component_attributions = []
                if xai:
                    # Create input tensors for model and explanation
                    input_ids, ref_input_ids = construct_input_ref_pair(statement.statement, ref_token_id, sep_token_id, cls_token_id)
                    token_type_ids, ref_token_type_ids = construct_input_ref_token_type_pair(input_ids)
                    attention_mask = construct_attention_mask(input_ids)
                    # Convert input IDs to tokens for later visualization
                    indices = input_ids[0].detach().tolist()
                    all_tokens = arguments_components_model.tokenizer.convert_ids_to_tokens(indices)
                    # Remove '▁' and re-join subwords
                    filtered_tokens = [token for token in all_tokens if token not in ['[CLS]', '[SEP]']]
                    relevant_tokens = [token[1:] for token in filtered_tokens]
                    #cleaned_tokens = []
                    #for token in filtered_tokens:
                        #if token.startswith('▁'):
                            #cleaned_tokens.append(token[1:])
                        #else:
                            #cleaned_tokens[-1] += token  # Append subword to the last token
                    #all_tokens = cleaned_tokens

                    # Compute attributions
                    target = label2id_arg_comp[component['entity_group']] #map the label to a target id to be used by lig
                    component_attributions, delta = lig_arg_comp.attribute(
                        inputs=input_ids,
                        baselines=ref_input_ids,
                        additional_forward_args=(token_type_ids, attention_mask),
                        return_convergence_delta=True,
                        target=target,
                    )

                    # Summarize attributions
                    component_attributions_sum = summarize_attributions(component_attributions)
                    component_attributions = component_attributions_sum[1:-1]# delete attributions for [CLS] and [SEP] special tokens
                    component_attributions = (component_attributions * 10 ** 4).round() / (10 ** 4) # round them to 4 decimals
                    component_attributions = component_attributions.numpy()

                    # Uncomment to generate visualizations of the attributions
                    """
                    # Set up the color map (using a colormap like 'coolwarm')
                    component_attributions_normalized = (component_attributions - np.min(component_attributions)) / (np.max(component_attributions) - np.min(component_attributions))
                    cmap = cm.get_cmap('coolwarm')
                    norm = Normalize(vmin=0, vmax=1)  # Normalization for color map
                    # Create a new figure
                    plt.figure(figsize=(10, 1))
                    ax = plt.gca()
                    ax.axis('off')  # Turn off the axis
                    # Add colored text for each token
                    for i, (token, score) in enumerate(zip(relevant_tokens, component_attributions_normalized)):
                        color = cmap(norm(score))  # Get color for the token based on the score
                        ax.text(0.1 * i, 0.5, token, fontsize=12, ha='center', va='center', bbox=dict(facecolor=color, edgecolor='none', boxstyle='round,pad=0.3'))
                    # Adjust the layout and save the figure
                    plt.subplots_adjust(left=0.05, right=0.95, top=0.8, bottom=0.2)
                    plt.savefig(f"~/orbis-argument-mining-tool/orbis_am_tool/visuals/comp_attr_vis_highlighted_sent_{target}.png", bbox_inches='tight')
                    """
                    component_attributions = component_attributions.tolist()

                # ********************************************************************************************************

                component_attributions_json = json.dumps(component_attributions)  # to store it in db and return in request response
                component = ArgumentativeComponent(
                    statement=statement,
                    start=component["start"],
                    end=component["end"],
                    label=component["entity_group"],
                    score=component["score"],
                    component_attributions=component_attributions_json,
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

                # Check the component fragment has a minimum length (e.g., to avoid components with only single words)
                if len(component.statement_fragment) < settings.MINIMUM_COMPONENT_LENGTH:
                    continue

                component_identifier = component.build_identifier()
                if ArgumentativeComponent.objects.filter(identifier=component_identifier).exists():
                    component = ArgumentativeComponent.objects.get(identifier=component_identifier)
                else:
                    component.save()
                components.append(component) # for further use in relation class i guess

            # =====================================================================================================================================================================
            # ====================================================================  COMP  REL CLASS   =============================================================================
            # =====================================================================================================================================================================

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
                if (relation["label"] != "noRel" and relation["score"] >= settings.MINIMUM_RELATION_SCORE):
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

            # =====================================================================================================================================================================
            # ======================================================================    STA CLASS   ===============================================================================
            # =====================================================================================================================================================================


            # After building the internal argumentative structure, we
            # automatically classify the statement, that is if it hasn't been
            # manually annotated
            if not statement.has_manual_annotation:
                statement_classification = statements_classification_model(statement.statement)[0]
                #print(f'***** Statement {i} ****** : {statement_classification}\n')
                
                # *********************************************************************************************************
                
                statement_attributions = []
                if xai:
                    # Create input tensors for model and explanation
                    input_ids, ref_input_ids = construct_input_ref_pair(statement.statement, ref_token_id, sep_token_id, cls_token_id)
                    token_type_ids, ref_token_type_ids = construct_input_ref_token_type_pair(input_ids)
                    attention_mask = construct_attention_mask(input_ids)

                    # Compute attributions
                    target = label2id_sta_class[statement_classification['label']]
                    statement_attributions, delta = lig_sta_class.attribute(
                        inputs=input_ids,
                        baselines=ref_input_ids,
                        additional_forward_args=(token_type_ids, attention_mask),
                        return_convergence_delta=True,
                        target=target,
                    )

                    # Summarize attributions
                    statement_attributions_sum = summarize_attributions(statement_attributions)
                    statement_attributions = statement_attributions_sum[1:-1]  # delete attributions for [CLS] and [SEP] special tokens
                    statement_attributions = (statement_attributions * 10 ** 4).round() / (10 ** 4)  # round them to 4 decimals
                    statement_attributions = statement_attributions.numpy()
                    
                    # Uncomment to generate visualizations of the attributions
                    """
                    # Convert input IDs to tokens for visualization
                    indices = input_ids[0].detach().tolist()
                    all_tokens = statements_classification_model.tokenizer.convert_ids_to_tokens(indices)
                    filtered_tokens = [token for token in all_tokens if token not in ['[CLS]', '[SEP]']]  # REMOVE SPECIAL TOKENS
                    # Remove '▁' and re-join subwords
                    relevant_tokens = [token[1:] for token in filtered_tokens]
                    statement_attributions_normalized = (statement_attributions - np.min(statement_attributions)) / (np.max(statement_attributions) - np.min(statement_attributions))
                    cmap = cm.get_cmap('coolwarm')
                    norm = Normalize(vmin=0, vmax=1)  # Normalization for color map
                    # Create a new figure
                    plt.figure(figsize=(10, 1))
                    ax = plt.gca()
                    ax.axis('off')  # Turn off the axis
                    # Add colored text for each token
                    for i, (token, score) in enumerate(zip(relevant_tokens, statement_attributions_normalized)):
                        color = cmap(norm(score))  # Get color for the token based on the score
                        ax.text(0.1 * i, 0.5, token, fontsize=12, ha='center', va='center', bbox=dict(facecolor=color, edgecolor='none', boxstyle='round,pad=0.3'))
                    # Adjust the layout and save the figure
                    plt.subplots_adjust(left=0.05, right=0.95, top=0.8, bottom=0.2)
                    plt.savefig(f"~/orbis-argument-mining-tool/orbis_am_tool/visuals/sta_attr_vis_highlighted_sent_{target}.png", bbox_inches='tight')
                    """
                    statement_attributions = statement_attributions.tolist()
                    
                # ********************************************************************************************************
                
                statement_attributions = json.dumps(statement_attributions)
                # prepare the statement object
                statement.statement_type = statement_classification["label"]
                statement.statement_classification_score = statement_classification["score"]
                statement.statement_attributions = statement_attributions
                statement.save()

        # =====================================================================================================================================================================
        # ====================================================================    STA REL CLASS   =============================================================================
        # =====================================================================================================================================================================

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
            elif (
                source_statement.related_to or source_statement.statement_relation_score == 0
            ) and not override:
                # If the source statement has already the related class or if it
                # was assigned the relation score of 0, even if it's not related
                # to any other statement, we avoid to run it again unless
                # specified by override
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
            source_statement = statements_pairs[rid]["source"]
            target_statement = statements_pairs[rid]["target"]
            if (
                relation["label"] == statements_pairs[rid]["source"].statement_type
                and relation["score"] >= settings.MINIMUM_STATEMENT_RELATION_SCORE
            ):
                source_statement.related_to = target_statement
                source_statement.statement_relation_score = relation["score"]

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
            else:
                # If not, we will set the source statement relation score to 0 as a way
                # to cache the source statement and avoid running it again unless override
                # is set
                source_statement.statement_classification_score = 0
            source_statement.save()

        # =====================================================================================================================================================================
        # =======================================================    MAJOR CLAIMS REL CLASS CROSS STATEMENTS  =================================================================
        # =====================================================================================================================================================================

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
