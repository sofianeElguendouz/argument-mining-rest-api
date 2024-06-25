from django.contrib import admin

from debate.models import Source, Debate, Author, Statement


class StatementInline(admin.StackedInline):
    readonly_fields = ("identifier",)
    model = Statement
    extra = 0


class AbstractModelAdmin(admin.ModelAdmin):
    readonly_fields = ("identifier",)


class SourceAdmin(AbstractModelAdmin):
    pass


class AuthorAdmin(AbstractModelAdmin):
    pass


class DebateAdmin(AbstractModelAdmin):
    inlines = [StatementInline]


admin.site.register(Source, SourceAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Debate, DebateAdmin)
