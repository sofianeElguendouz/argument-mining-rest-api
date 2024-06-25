import xxhash

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from debate.models import Statement


class ArgumentativeComponent(models.Model):
    """
    Argumentative component model for a statement. It holds information about
    the label of the argumentative component (i.e., claim or premise), and the
    start and the end it spans in the statement text.
    """

    class ArgumentativeComponentLabel(models.TextChoices):
        CLAIM = "CL", "Claim"
        PREMISE = "PR", "Premise"

    identifier = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        help_text=(
            "An identifier that is a hash of: "
            "``slugify(self.statement.statement[self.start:self.end])+self.statement.identifier. "
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
        max_length=2,
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

    def __str__(self):
        return f"{self.get_label_display()} component in {self.statement}"

    def clean(self):
        """
        Check that the ``start`` and the ``end`` have some length, are ordered,
        and are inside the statement.

        If it's valid, and it hasn't been saved yet, create an identifier from
        the combination of:
        slugify(self.statement[self.start:self.end])+self.statement.identifier
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

        if not self.id:
            # Only if there isn't a saved instance of the model, to avoid
            # overwriting the identifier and keep it the same
            slug = f"{slugify(self.statement.statement[self.start:self.end])}+{self.statement.identifier}"  # noqa
            self.identifier = xxhash.xxh3_64_hexdigest(slug, seed=settings.XXHASH_SEED)


class ArgumentativeRelation(models.Model):
    """
    Argumentative relation model. Holds the information of two related
    argumentative components about the label (i.e., attack or support) and the
    direction (i.e. what is the source argumentative component in the relation
    and what is the target component).
    This represents an edge in a directed graph.
    """

    class ArgumentativeRelationLabel(models.TextChoices):
        ATTACK = "ATT", "Attack"
        SUPPORT = "SUP", "Support"

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
        max_length=3,
        choices=ArgumentativeRelationLabel,
        help_text="The type of relation between the components.",
    )
    score = models.FloatField(
        blank=True,
        null=True,
        help_text=(
            "Score (between 0 and 1) given by an automatic model to the classification label. "
            "It's useful to get a general idea how certain is the model about a prediction."
        ),
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
