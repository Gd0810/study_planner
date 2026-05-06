from django.contrib import admin
from .models import (
    UserProfile, StudyPlan, Module, Topic, Resource,
    DailyLog, Quiz, QuizAttempt, StudySession
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'timezone', 'daily_study_goal', 'notifications_enabled']
    search_fields = ['user__username']


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'domain', 'is_active', 'created_at']
    list_filter = ['domain', 'is_active', 'created_at']
    search_fields = ['title', 'user__username']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'study_plan', 'order', 'estimated_hours']
    list_filter = ['study_plan']


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'is_completed', 'time_spent_minutes']
    list_filter = ['is_completed', 'module__study_plan']


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'topic', 'resource_type', 'is_completed']
    list_filter = ['resource_type', 'is_completed']


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'study_plan', 'date', 'hours_studied', 'mood']
    list_filter = ['date', 'user']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'topic', 'difficulty', 'created_at']
    list_filter = ['difficulty']


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'score', 'total_questions', 'completed_at']
    list_filter = ['completed_at']


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'start_time', 'duration_minutes']
    list_filter = ['start_time']