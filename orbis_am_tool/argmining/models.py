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
            "It's created when the model is saved."
        ),
    )
    statement = models.ForeignKey(
        Statement,
        on_delete=models.CASCADE,
        help_text=("Position statement this is an Argumentative Component of"),
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
        )
    )

    def __str__(self):
        return f"{self.get_label_display()} component in {self.statement}"

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

    def save(self, *args, **kwargs):
        """
        Override save function to create an identifier from the combination of
        slugify(self.statement[self.start:self.end])+self.statement.identifier
        """
        if not self.id:
            # Only if there isn't a saved instance of the model, to avoid
            # overwriting the identifier and keep it the same
            slug = f"{slugify(self.statement.statement[self.start:self.end])}+{self.statement.identifier}"  # noqa
            self.identifier = xxhash.xxh3_64_hexdigest(slug, seed=settings.XXHASH_SEED)
        super().save(*args, **kwargs)


class ArgumentativeRelation(models.Model):
    """
    Argumentative relation model. Holds the information of two related
    argumentative components about the label (i.e., attack or support) and the
    direction (i.e. what is the argumentative component that is having the
    action of attack/support and which one is the receiving).
    This represents an edge in a directed graph.
    """

    class ArgumentativeRelationLabel(models.TextChoices):
        ATTACK = "ATT", "Attack"
        SUPPORT = "SUP", "Support"

    # Careful with the related names in these foreign keys:
    # - `ArgumentativeComponent.from_relations` are all the relations that the
    #   component is part of as the start of the edge.
    component_from = models.ForeignKey(
        ArgumentativeComponent,
        on_delete=models.CASCADE,
        help_text=(
            "The argumentative component that is the start of the relation. I.e., 'A' in 'A'->'B'."
        ),
        related_name="from_relations",
    )
    # - `ArgumentativeComponent.to_relations` are all the relations that the
    #   component is part of the end of the edge
    component_to = models.ForeignKey(
        ArgumentativeComponent,
        on_delete=models.CASCADE,
        help_text=(
            "The argumentative component that is the end of the relation. I.e., 'B' in 'A'->'B'."
        ),
        related_name="to_relations",
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
        )
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["component_from", "component_to"], name="unique_edge")
        ]

    def __str__(self):
        return f"{self.get_label_display()} relation between {self.component_from} and {self.component_to}"  # noqa

    def clean(self):
        """
        Validate that the from and to components are different.
        """
        if self.component_from == self.component_to:
            raise ValidationError("The from and to components can't be the same")
