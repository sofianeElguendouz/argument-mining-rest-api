from django.contrib import admin

from argmining.models import ArgumentativeComponent, ArgumentativeRelation


class ArgumentativeComponentAdmin(admin.ModelAdmin):
    readonly_fields = (
        "identifier",
        "statement_fragment",
    )


admin.site.register(ArgumentativeComponent, ArgumentativeComponentAdmin)
admin.site.register(ArgumentativeRelation)
