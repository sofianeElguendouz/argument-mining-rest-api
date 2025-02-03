import xxhash

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from debate.models import Statement
from utils.django import AbstractIdentifierModel


class ArgumentativeComponent(AbstractIdentifierModel):
    """
    Argumentative component model for a statement. It holds information about
    the label of the argumentative component (i.e., claim or premise), and the
    start and the end it spans in the statement text.
    """

    class ArgumentativeComponentLabel(models.TextChoices):
        CLAIM = "Claim"
        PREMISE = "Premise"

    identifier = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        help_text=(
            "An identifier that is a hash of: "
            "`slugify(self.statement.statement[self.start:self.end])+self.start:self.end+self.statement.identifier`. "  # noqa
            "It's created when the model is saved. "
            "It's useful to avoid exposing the internal PK to the public."
        ),
    )
    statement = models.ForeignKey(
        Statement,
        on_delete=models.CASCADE,
        help_text=("Position statement this is an Argumentative Component of"),
        related_name="argumentative_components",
    )
    start = models.PositiveIntegerField(
        help_text=("The start of the argumentative component in the statement")
    )
    end = models.PositiveIntegerField(
        help_text=("The end of the argumentative component in the statement")
    )
    label = models.CharField(
        max_length=10,
        choices=ArgumentativeComponentLabel,
        help_text="The label for this argumentative component.",
    )
    score = models.FloatField(
        blank=True,
        null=True,
        help_text=(
            "Score (between 0 and 1) given by an automatic model to the classification label. "
            "It's useful to get a general idea how certain is the model about a prediction."
        ),
    )
    has_manual_annotation = models.BooleanField(
        default=False,
        help_text="Boolean value to denote that the component was annotated manually",
    )
    # -----------------------------------------------------------------------------------------------------------
    # New field to store attributions
    component_attributions = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="A JSON field to store the XAI attribution scores reflecting the importance of each token for the classification of the argumentative component."
    )
    # -----------------------------------------------------------------------------------------------------------
    def __str__(self):
        return f"{self.get_label_display()} component in {self.statement}"

    @property
    def statement_fragment(self) -> str:
        """
        Returns the fragment text of the statement that has been marked as an
        argumentative component

        Returns
        -------
        str
            The statement's fragment of annotated text.
        """
        return self.statement.statement[self.start : self.end]

    def clean(self):
        """
        Check that the ``start`` and the ``end`` have some length, are ordered,
        and are inside the statement.
        """
        if self.start >= self.end:
            raise ValidationError(
                "The start of an argumentative component can't be larger or equal to the end"
            )
        if self.end > len(self.statement.statement):
            raise ValidationError(
                "The end of the argumentative component can't be larger than the length of the "
                "statement."
            )
        super().clean()

    def build_identifier(self) -> str:
        """
        Helper function to build an identifier.

        I use a helper function because in some occasions is useful to have the
        identifier prior to saving the model.

        The identifier is a combination of:
        slugify(self.statement[self.start:self.end])+self.start:self.end+self.statement.identifier

        We require to have both the fraction of text of the statement and the
        start and end values because some fractions of text might be duplicated
        (i.e., have the same word), and we want to guarantee it being unique.

        Returns
        -------
        str
            The identifier.
        """
        slug = (
            slugify(self.statement.statement[self.start : self.end])
            + f"+{self.start}:{self.end}+"
            + self.statement.identifier
        )
        return xxhash.xxh3_64_hexdigest(slug, seed=settings.XXHASH_SEED)


class ArgumentativeRelation(models.Model):
    """
    Argumentative relation model. Holds the information of two related
    argumentative components about the label (i.e., attack or support) and the
    direction (i.e. what is the source argumentative component in the relation
    and what is the target component).
    This represents an edge in a directed graph.
    """

    class ArgumentativeRelationLabel(models.TextChoices):
        ATTACK = "Attack"
        SUPPORT = "Support"

    # Careful with the related names in these foreign keys:
    # - `ArgumentativeComponent.relations_as_source` are all the relations that
    #   the component is part of as the start of the edge.
    source = models.ForeignKey(
        ArgumentativeComponent,
        on_delete=models.CASCADE,
        help_text=(
            "The argumentative component that is the source of the relation. I.e., 'A' in 'A'->'B'."
        ),
        related_name="relations_as_source",
    )
    # - `ArgumentativeComponent.relations_as_target` are all the relations that
    #   the component is part of the end of the edge
    target = models.ForeignKey(
        ArgumentativeComponent,
        on_delete=models.CASCADE,
        help_text=(
            "The argumentative component that is the target of the relation. I.e., 'B' in 'A'->'B'."
        ),
        related_name="relations_as_target",
    )
    label = models.CharField(
        max_length=10,
        choices=ArgumentativeRelationLabel,
        help_text="The type of relation between the components.",
    )
    # -----------------------------------------------------------------------------------------------------------
    relation_attributions = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="A JSON field to store the XAI attribution scores reflecting the importance of each token, in both source and target components, for the classification of the relation."
    )
    # -----------------------------------------------------------------------------------------------------------
    score = models.FloatField(
        blank=True,
        null=True,
        help_text=(
            "Score (between 0 and 1) given by an automatic model to the classification label. "
            "It's useful to get a general idea how certain is the model about a prediction."
        ),
    )
    has_manual_annotation = models.BooleanField(
        default=False,
        help_text="Boolean value to denote that the relation was annotated manually",
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "target"], name="unique_edge")]

    def __str__(self):
        return f"{self.get_label_display()} relation between {self.source} and {self.target}"

    def clean(self):
        """
        Validate that the from and to components are different.
        """
        if self.source == self.target:
            raise ValidationError("The source and target components can't be the same")

    def save(self, *args, **kwargs):
        """
        Override save function

        Run the full clean before saving
        """
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_cross_statement(self) -> bool:
        """
        Returns if a relation is cross statement (i.e., the source and target
        argumentative components come from different statements).
        """
        return self.source.statement != self.target.statement
