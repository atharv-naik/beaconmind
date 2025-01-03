from django.contrib import admin

from .models import Assessment, AssessmentRecord, AssessmentResult


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'type', 'status', 'timestamp']
    search_fields = ['patient__user__username', 'patient__user__email']
    readonly_fields = ['id', 'patient', 'timestamp', 'type', 'status']
    list_filter = ['type', 'status', 'patient']
    ordering = ['-timestamp']


@admin.register(AssessmentRecord)
class AssessmentRecordAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'question_id',
                    'question_text', 'score', 'timestamp']
    search_fields = ['assessment__patient__user__username',
                     'assessment__patient__user__email', 'question_text']
    readonly_fields = ['id', 'assessment', 'question_id',
                       'question_text', 'score', 'timestamp']
    list_filter = ['assessment__type', 'assessment__status', 'assessment__patient']
    ordering = ['-timestamp', 'assessment']


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'score', 'timestamp']
    search_fields = ['assessment__patient__user__username',
                     'assessment__patient__user__email']
    readonly_fields = ['id', 'assessment', 'score', 'timestamp']
    list_filter = ['assessment__type', 'assessment__status', 'assessment__patient']
    ordering = ['assessment', '-timestamp']

