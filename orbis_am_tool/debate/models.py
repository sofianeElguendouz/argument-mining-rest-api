import xxhash

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class AbstractSlugModel(models.Model):
    """
    An abstract model that has an identifier, name and slug. It uses the
    identifier for internal manipulation (to avoid displaying the DB identifier)
    and the slug as a way to represent the name in a URL friendly way for REST
    APIs. When the model is saved, if the instance doesn't exists in the DB, it
    will create the slug from the name and the identifier from a hash of the
    slug.
    """

    identifier = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        help_text=(
            "An identifier that is a hash of the slug, for internal use. "
            "It's created from the slug when the model is saved."
        ),
    )
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="The name of the model. Must be unique.",
    )
    slug = models.SlugField(
        max_length=200,
        blank=True,
        unique=True,
        editable=False,
        help_text=(
            "A slug representation of the name of the model. "
            "It's created from the name of the source when the model is saved."
        ),
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def clean(self):
        """
        During clean, create a slug from the name of the model and an identifier
        from the slug if the model hasn't been saved into the DB yet.
        """
        if not self.id:
            # Only if there isn't a saved instance of the model, to avoid
            # overwriting the slug/identifier and keep it the same
            self.slug = slugify(self.name)
            self.identifier = xxhash.xxh3_64_hexdigest(self.slug, seed=settings.XXHASH_SEED)


class Source(AbstractSlugModel):
    """
    Source for debates. It can be the BCause app, an ORBIS Pilot event, a
    dataset.
    """

    # Override `name` to add help_text
    name = models.CharField(
        max_length=200, unique=True, help_text="Name of the source. Must be unique."
    )
    description = models.TextField(blank=True, help_text="Description of the source")


class Debate(AbstractSlugModel):
    """
    Debate model. Has information on the general debate that is being discussed.
    A single debate can have multiple different arguments that are related with
    each other.
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


class Author(AbstractSlugModel):
    """
    The author of an statement. It's usually identified by a unique anonymous ID.
    Is useful to keep track of authors across different debates.
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


class Statement(models.Model):
    """
    A statement is done by someone (an author), and is part of a Debate.  The
    statement can have different types: a position, an argument, etc.
    """

    class StatementType(models.TextChoices):
        POSITION = "POS", "Position"  # Position over the debate
        ATTACKING_ARGUMENT = "ATT", "Attacking Argument"  # Argument against a position
        SUPPORTING_ARGUMENT = "SUP", "Supporting Argument"  # Argument in favor of a position

    identifier = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        help_text=(
            "An identifier that is a hash of: "
            "`slugify(self.statement)+self.debate.identifier+self.author.identifier`. "
            "It's created when the model is saved."
        ),
    )
    statement = models.TextField(help_text="The argumentative statement done.")
    debate = models.ForeignKey(
        Debate, on_delete=models.CASCADE, help_text="The debate this statement is part of."
    )
    author = models.ForeignKey(
        Author, on_delete=models.CASCADE, help_text="The author of the statement"
    )
    statement_type = models.CharField(
        choices=StatementType, max_length=3, blank=True,
        help_text="The type of statement being made."
    )
    related_to = models.ForeignKey(
        "Statement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=(
            "Another statement that this statement is related to. "
            "It only makes sense for statements of type SUPPORTING_ARGUMENT or ATTACKING_ARGUMENT. "
        ),
        related_name="related_statements",
    )

    def __str__(self):
        return (
            f'{self.get_statement_type_display()} statement over "{self.debate}" by {self.author}'
        )

    def clean(self):
        """
        During clean create an identifier from the combination of
        slugify(self.statement)+self.debate.identifier+self.author.identifier
        """
        if not self.id:
            # Only if there isn't a saved instance of the model, to avoid
            # overwriting the identifier and keep it the same
            slug = f"{slugify(self.statement)}+{self.debate.identifier}+{self.author.identifier}"
            self.identifier = xxhash.xxh3_64_hexdigest(slug, seed=settings.XXHASH_SEED)
