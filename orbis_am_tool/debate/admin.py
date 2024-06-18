from django.contrib import admin

from debate.models import Source, Debate, Author, Statement


class StatementInline(admin.StackedInline):
    model = Statement
    extra = 0


class SlugModelAdmin(admin.ModelAdmin):
    readonly_fields = ("identifier", "slug")


class SourceAdmin(SlugModelAdmin):
    pass


class AuthoAdmin(SlugModelAdmin):
    pass


class DebateAdmin(SlugModelAdmin):
    inlines = [StatementInline]


admin.site.register(Source, SourceAdmin)
admin.site.register(Author, AuthoAdmin)
admin.site.register(Debate, DebateAdmin)
