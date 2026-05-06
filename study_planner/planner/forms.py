from django import forms
from .models import StudyPlan, Module, Topic, Resource, DailyLog, QuizAttempt

class StudyPlanForm(forms.ModelForm):
    duration_weeks = forms.IntegerField(
        initial=12,
        min_value=1,
        max_value=52,
        help_text="How many weeks to complete this plan?"
    )
    hours_per_week = forms.IntegerField(
        initial=10,
        min_value=1,
        max_value=40,
        help_text="How many hours per week can you study?"
    )
    
    class Meta:
        model = StudyPlan
        fields = ['title', 'domain', 'description', 'start_date', 'target_end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'target_end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'estimated_hours']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['title', 'description', 'estimated_minutes', 'notes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['title', 'resource_type', 'url', 'file', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class DailyLogForm(forms.ModelForm):
    class Meta:
        model = DailyLog
        fields = ['hours_studied', 'notes', 'mood']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'mood': forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
        }


class QuizAttemptForm(forms.ModelForm):
    class Meta:
        model = QuizAttempt
        fields = []