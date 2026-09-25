from django.contrib import admin

from .models import (
    Assessment,
    AssessmentAnswer,
    ChecklistCriterion,
    ChecklistLevel,
    ChecklistOption,
    ChecklistSection,
    ChecklistTemplate,
)


class ChecklistSectionInline(admin.TabularInline):
    model = ChecklistSection
    extra = 0


class ChecklistLevelInline(admin.TabularInline):
    model = ChecklistLevel
    extra = 0


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "max_score",
        "is_active",
    )

    inlines = (
        ChecklistSectionInline,
        ChecklistLevelInline,
    )


class ChecklistOptionInline(admin.TabularInline):
    model = ChecklistOption
    extra = 0


@admin.register(ChecklistCriterion)
class ChecklistCriterionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "section",
        "order",
        "max_score",
    )

    list_filter = (
        "section__template",
        "section",
    )

    search_fields = (
        "title",
    )

    inlines = (
        ChecklistOptionInline,
    )


@admin.register(ChecklistSection)
class ChecklistSectionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "template",
        "order",
    )


class AssessmentAnswerInline(admin.TabularInline):
    model = AssessmentAnswer
    extra = 0


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "visit",
        "template",
        "status",
        "score",
        "updated_at",
    )

    list_filter = (
        "template",
        "status",
    )

    inlines = (
        AssessmentAnswerInline,
    )

    @admin.display(description="Балл")
    def score(self, obj):
        return obj.total_score
