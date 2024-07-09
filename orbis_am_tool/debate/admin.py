from django.contrib import admin

from debate.models import Source, Debate, Author, Statement


class StatementInline(admin.StackedInline):
    readonly_fields = ("identifier",)
    model = Statement
    extra = 0


class AbstractNameModelAdmin(admin.ModelAdmin):
    readonly_fields = ("identifier",)


class SourceAdmin(AbstractNameModelAdmin):
    pass


class AuthorAdmin(AbstractNameModelAdmin):
    pass


class DebateAdmin(AbstractNameModelAdmin):
    inlines = [StatementInline]


admin.site.register(Source, SourceAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Debate, DebateAdmin)
