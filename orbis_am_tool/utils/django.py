"""
Utility module for Django related things.
"""

from django.core.exceptions import ValidationError
from django.db import models


class AbstractIdentifierModel(models.Model):
    """
    An abstract class that serves for models that deal with an identifier.
    """

    class Meta:
        abstract = True

    def build_identifier(self) -> str:
        """
        Abstract class for building the identifier.

        It varies from model to model.

        Returns
        -------
        str
            The identifier
        """
        raise NotImplementedError()

    def clean(self):
        """
        Override clean method

        We need to check if there is an object with the identifier and raise
        """
        if self.__class__.objects.filter(identifier=self.build_identifier()).exists():
            raise ValidationError("The identifier isn't unique")

    def save(self, *args, **kwargs):
        """
        Override save method.

        Check if the model is in the DB, if not, build the identifier and assign
        it to the model.
        Run a full clean before saving.
        """
        if not self.id:
            # Only if there isn't a saved instance of the model, to avoid
            # overwriting the identifier and keep it the same
            self.identifier = self.build_identifier()
        self.full_clean()
        super().save(*args, **kwargs)
