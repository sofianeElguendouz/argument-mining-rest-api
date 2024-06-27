"""
Hugging Face Pipelines to load the models.
"""

from django.conf import settings
from transformers import pipeline


arguments_components_model = pipeline(
    task="token-classification",
    model=settings.ARGUMENTS_COMPONENTS_MODEL,
    aggregation_strategy="first",
)

arguments_relations_model = pipeline(
    task="text-classification",
    model=settings.ARGUMENTS_RELATIONS_MODEL,
)
