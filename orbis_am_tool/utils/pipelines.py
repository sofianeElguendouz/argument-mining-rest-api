"""
Hugging Face Pipelines to load the models.
"""

from django.conf import settings
from transformers import AutoTokenizer, pipeline


arguments_components_model = pipeline(
    task="token-classification",
    model=settings.ARGUMENTS_COMPONENTS_MODEL,
    tokenizer=AutoTokenizer.from_pretrained(
        settings.ARGUMENTS_COMPONENTS_MODEL,
        model_max_length=settings.ARGUMENTS_COMPONENT_MODEL_MAX_LENGTH,
    ),
    aggregation_strategy=settings.ARGUMENTS_COMPONENT_MODEL_STRATEGY,
    stride=settings.ARGUMENTS_COMPONENT_MODEL_STRIDE,
)

arguments_relations_model = pipeline(
    task="text-classification",
    model=settings.ARGUMENTS_RELATIONS_MODEL,
    tokenizer=AutoTokenizer.from_pretrained(
        settings.ARGUMENTS_RELATIONS_MODEL,
        model_max_length=settings.ARGUMENTS_RELATION_MODEL_MAX_LENGTH,
    ),
)
