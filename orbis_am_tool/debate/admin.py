from django.contrib import admin

from debate.models import Source, Debate, Author, Statement


class StatementInline(admin.StackedInline):
    readonly_fields = ("identifier",)
    model = Statement
    extra = 0


class AbstractSlugModelAdmin(admin.ModelAdmin):
    readonly_fields = ("identifier", "slug")


class SourceAdmin(AbstractSlugModelAdmin):
    pass


class AuthoAdmin(AbstractSlugModelAdmin):
    pass


class DebateAdmin(AbstractSlugModelAdmin):
    inlines = [StatementInline]


admin.site.register(Source, SourceAdmin)
admin.site.register(Author, AuthoAdmin)
admin.site.register(Debate, DebateAdmin)
