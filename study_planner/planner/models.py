from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    timezone = models.CharField(max_length=50, default='UTC')
    daily_study_goal = models.IntegerField(default=2, help_text="Hours per day")
    notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class StudyPlan(models.Model):
    DOMAIN_CHOICES = [
        ('software', 'Software Development'),
        ('law', 'Law'),
        ('medicine', 'Medicine'),
        ('business', 'Business'),
        ('design', 'Design'),
        ('data_science', 'Data Science'),
        ('marketing', 'Marketing'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')
    title = models.CharField(max_length=255)
    domain = models.CharField(max_length=50, choices=DOMAIN_CHOICES)
    description = models.TextField(blank=True)
    ai_generated_plan = models.JSONField(default=dict, blank=True)
    start_date = models.DateField(default=timezone.now)
    target_end_date = models.DateField(null=True, blank=True)
    estimated_hours = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def get_completion_percentage(self):
        total_topics = self.modules.aggregate(
            total=models.Count('topics')
        )['total'] or 0
        
        if total_topics == 0:
            return 0
        
        completed_topics = Topic.objects.filter(
            module__study_plan=self,
            is_completed=True
        ).count()
        
        return round((completed_topics / total_topics) * 100, 2)
    
    def get_total_time_spent(self):
        return Topic.objects.filter(
            module__study_plan=self
        ).aggregate(
            total=models.Sum('time_spent_minutes')
        )['total'] or 0


class Module(models.Model):
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    estimated_hours = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.title} - {self.study_plan.title}"
    
    def get_completion_percentage(self):
        total = self.topics.count()
        if total == 0:
            return 0
        completed = self.topics.filter(is_completed=True).count()
        return round((completed / total) * 100, 2)


class Topic(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    estimated_minutes = models.IntegerField(default=60)
    time_spent_minutes = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.title}"
    
    def mark_complete(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()
    
    def mark_incomplete(self):
        self.is_completed = False
        self.completed_at = None
        self.save()


class Resource(models.Model):
    RESOURCE_TYPES = [
        ('video', 'Video'),
        ('article', 'Article'),
        ('pdf', 'PDF Document'),
        ('book', 'Book'),
        ('course', 'Online Course'),
        ('other', 'Other'),
    ]
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    url = models.URLField(blank=True)
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.topic.title}"


class DailyLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_logs')
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='daily_logs')
    date = models.DateField(default=timezone.now)
    topics_completed = models.ManyToManyField(Topic, blank=True)
    hours_studied = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    mood = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="1-5 rating"
    )
    
    class Meta:
        unique_together = ['user', 'study_plan', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class Quiz(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    questions = models.JSONField(default=list)  # Store questions as JSON
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Quiz: {self.title}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    answers = models.JSONField(default=dict)
    completed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.score}/{self.total_questions}"
    
    def get_percentage(self):
        if self.total_questions == 0:
            return 0
        return round((self.score / self.total_questions) * 100, 2)


class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_sessions')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.topic.title} - {self.start_time}"
    
    def complete_session(self):
        self.end_time = timezone.now()
        self.duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)
        self.save()
        
        # Update topic time spent
        self.topic.time_spent_minutes += self.duration_minutes
        self.topic.save()