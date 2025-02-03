import xxhash

from django.apps import apps
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from typing import Optional

from utils.django import AbstractIdentifierModel


class AbstractNameModel(AbstractIdentifierModel):
    """
    An abstract model that has an identifier and a name. It uses the identifier
    for internal manipulation (to avoid displaying the DB identifier).  When the
    model is saved, if the instance doesn't exists in the DB, it will create the
    identifier from a hash of a slugified version of the name
    """

    identifier = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        help_text=(
            "An identifier that is a hash of the name. "
            "It's created from the slug of the name when the model is saved. "
            "It's useful to avoid exposing the internal PK to the public."
        ),
    )
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="The name of the model. Must be unique.",
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def build_identifier(self) -> str:
        """
        Helper function to build the identifier

        The identifier is created as the hash of the slug of the model's name
        field.

        Returns
        -------
        str
            The identifier
        """
        return xxhash.xxh3_64_hexdigest(slugify(self.name), seed=settings.XXHASH_SEED)


class Source(AbstractNameModel):
    """
    Source for debates.

    It can be the BCause app, an ORBIS Pilot event, a dataset. It only makes
    sense for internal purposes.
    """

    # Override `name` to add help_text
    name = models.CharField(
        max_length=200, unique=True, help_text="Name of the source. Must be unique."
    )
    description = models.TextField(blank=True, help_text="Description of the source")


class Debate(AbstractNameModel):
    """
    Debate model.

    Has information on the general debate that is being discussed.  A single
    debate can have multiple different statements that are related with each
    other.
    """

    # Override `name` to add help_text
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text=(
            "The title of the debate. It should give a general idea what the debates is about. "
            "Must be unique."
        ),
    )
    summary = models.TextField(
        blank=True,
        help_text=(
            "A summary of the topic of the debate. "
            "It's useful if the title isn't expressive enough."
        ),
    )
    source = models.ForeignKey(
        Source,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debates",
        help_text="A source for the debate, in case it has one.",
    )


class Author(AbstractNameModel):
    """
    The author of an Statement.

    It's usually identified by a unique anonymous ID.  Is useful to keep track
    of authors across different debates.
    """

    # Override `name` to add help_text
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text=(
            "The name of the author. It doesn't have to be a real name, but something that "
            "is useful to identify the author (e.g. a combination of the name and other things)."
        ),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user associated with the author, if the author isn't anonymous",
    )


class Statement(AbstractIdentifierModel):
    """
    A statement is done by someone (an author), and is part of a Debate.

    The statement can have different types: a position, an argument, etc.  It's
    the argumentative text that informs the stance of a single person regarding
    the debate it's referring to.
    """

    class StatementType(models.TextChoices):
        POSITION = "Position"  # Position over the debate
        ATTACK = "Attack"  # Argument against a position
        SUPPORT = "Support"  # Argument in favor of a position

    identifier = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        help_text=(
            "An identifier that is a hash of: "
            "`slugify(self.statement)+self.debate.identifier+self.author.identifier`. "
            "It's created when the model is saved. "
            "It's useful to avoid exposing the internal PK to the public."
        ),
    )
    statement = models.TextField(help_text="The argumentative statement done.")
    debate = models.ForeignKey(
        Debate,
        on_delete=models.CASCADE,
        help_text="The debate this statement is part of.",
        related_name="statements",
    )
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        help_text="The author of the statement",
        related_name="statements",
    )
    statement_type = models.CharField(
        choices=StatementType,
        max_length=10,
        blank=True,
        help_text="The type of statement being made.",
    )
    statement_classification_score = models.FloatField(
        blank=True,
        null=True,
        help_text=(
            "Score (between 0 and 1) given by an automatic model for statement classification. "
            "It's useful to get a general idea how certain is the model about a prediction."
        ),
    )
    related_to = models.ForeignKey(
        "Statement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=(
            "Another statement that this statement is related to. "
            "It only makes sense for statements of type SUPPORTING_ARGUMENT or ATTACKING_ARGUMENT."
        ),
        related_name="related_statements",
    )
    statement_relation_score = models.FloatField(
        blank=True,
        null=True,
        help_text=(
            "Score (between 0 and 1) given by an automatic model for statement relation. "
            "It's useful to get a general idea how certain is the model about a prediction."
        ),
    )
    has_manual_annotation = models.BooleanField(
        default=False,
        help_text="Boolean value to denote that the statement was annotated manually",
    )
    #-----------------------------------------------------------------------------------------------------------
    # New field to store attributions
    statement_attributions = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="A JSON field to store the XAI attribution scores reflecting the importance of each token in the statement classification process."
    )

    # New field to store attributions
    statement_relation_attributions = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="A JSON field to store the XAI attribution scores reflecting the importance of each token in the statement relation classification process."
    )
    # -----------------------------------------------------------------------------------------------------------
    def __str__(self):
        return (
            f'{self.get_statement_type_display()} statement over "{self.debate}" by {self.author}'
        )

    def build_identifier(self) -> str:
        """
        Helper function to build an identifier.

        I use a helper function because in some occasions is useful to have the
        identifier prior to saving the model.

        The identifier is a combination of:
        slugify(self.statement)+self.debate.identifier+self.author.identifier

        Returns
        -------
        str
            The identifier.
        """
        slug = f"{slugify(self.statement)}+{self.debate.identifier}+{self.author.identifier}"
        return xxhash.xxh3_64_hexdigest(slug, seed=settings.XXHASH_SEED)

    def get_major_claim(self) -> Optional["argmining.models.ArgumentativeComponent"]:  # noqa
        """
        Ad-Hoc function to get the most important claim from a statement

        To be able to build cross-statements argumentative component relations,
        while avoiding an explosion in the relationship graph complexity, we
        need to limit in some way the comparison of argumentative components
        across different statements. There are many ways to do so, ideally, we
        would use a model that correctly classifies those "major claims" among
        the different statements and use only those major claims to check for
        relationships. However, at the time there's no dataset to build such
        model, in the future this heuristics function could be replaced by a
        proper model in charge of doing so, for now this will have to suffice.

        The heuristics of this function is based on 3 principles, these
        principles are used to select the major claim. This heuristics is flawed
        however, and should be only temporal:
            - Claims with the maximum number of inbound relations (i.e., that
              are target of most of the relations among components within a
              statement) are the major claims.
            - Claims with the minimum number of outbound relations (i.e., that
              are source of the less relations than other claims).
            - Claim with maximum scores.

        Returns
        -------
        argmining.models.ArgumentativeComponent | None
            The ArgumentativeComponent marked as the major claim, or None if no
            argumentative component is found.
        """
        # Required to be loaded like this to avoid circular importing
        return (
            self.argumentative_components.filter(
                # We filter only claims. It's required to be this way to avoid
                # circular import
                label=apps.get_model(
                    "argmining", "ArgumentativeComponent"
                ).ArgumentativeComponentLabel.CLAIM
            )
            .annotate(
                # Get the number of relations of the claims as a target and as a source
                relations_as_target_count=models.Count("relations_as_target"),
                relations_as_source_count=models.Count("relations_as_source"),
            )
            .order_by(
                # Order by the claim with the most amount of relations as a target (inbound)
                "-relations_as_target_count",
                # Then by the claim with the least amount of relations as a source (outbound)
                "relations_as_source_count",
                # Finally by the highest score
                "-score",
            )
            .first()  # Return the first claim
        )
