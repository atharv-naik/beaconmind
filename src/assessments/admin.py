from django.contrib import admin

from .models import Assessment, AssessmentRecord, AssessmentResult


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'type', 'status', 'timestamp', 'completed_at']
    search_fields = ['patient__user__username', 'patient__user__email']
    list_filter = ['type', 'status', 'patient']
    ordering = ['-timestamp']


@admin.register(AssessmentRecord)
class AssessmentRecordAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'question_id',
                    'question_text', 'score', 'timestamp']
    search_fields = ['assessment__patient__user__username',
                     'assessment__patient__user__email', 'question_text']
    list_filter = ['assessment__type', 'assessment__status', 'assessment__patient']
    ordering = ['-timestamp', 'assessment']


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'score', 'timestamp']
    search_fields = ['assessment__patient__user__username',
                     'assessment__patient__user__email']
    list_filter = ['assessment__type', 'assessment__status', 'assessment__patient']
    ordering = ['assessment', '-timestamp']

