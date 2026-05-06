from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from .models import (
    StudyPlan, Module, Topic, Resource, DailyLog, 
    Quiz, QuizAttempt, StudySession, UserProfile
)
from .forms import (
    StudyPlanForm, ModuleForm, TopicForm, ResourceForm,
    DailyLogForm, QuizAttemptForm
)
from .ai_service import NVIDIAStudyPlanGenerator
import json


def index(request):
    """Landing page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')


def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')


@login_required
def dashboard(request):
    """Main dashboard"""
    study_plans = StudyPlan.objects.filter(user=request.user, is_active=True)
    
    # Get statistics
    total_plans = study_plans.count()
    total_topics = Topic.objects.filter(module__study_plan__user=request.user).count()
    completed_topics = Topic.objects.filter(
        module__study_plan__user=request.user,
        is_completed=True
    ).count()
    
    total_hours = Topic.objects.filter(
        module__study_plan__user=request.user
    ).aggregate(total=Sum('time_spent_minutes'))['total'] or 0
    total_hours = round(total_hours / 60, 1)
    
    # Recent activity
    recent_logs = DailyLog.objects.filter(user=request.user)[:7]
    
    # Current streak
    streak = calculate_study_streak(request.user)
    
    context = {
        'study_plans': study_plans,
        'total_plans': total_plans,
        'total_topics': total_topics,
        'completed_topics': completed_topics,
        'total_hours': total_hours,
        'recent_logs': recent_logs,
        'streak': streak,
    }
    
    return render(request, 'planner/dashboard.html', context)


@login_required
def create_plan(request):
    """Create new study plan with AI"""
    if request.method == 'POST':
        form = StudyPlanForm(request.POST)
        if form.is_valid():
            study_plan = form.save(commit=False)
            study_plan.user = request.user
            study_plan.save()
            
            # Generate AI plan
            ai_generator = NVIDIAStudyPlanGenerator()
            duration_weeks = request.POST.get('duration_weeks', 12)
            hours_per_week = request.POST.get('hours_per_week', 10)
            
            ai_plan = ai_generator.generate_study_plan(
                domain=study_plan.domain,
                title=study_plan.title,
                description=study_plan.description,
                duration_weeks=int(duration_weeks),
                hours_per_week=int(hours_per_week)
            )
            
            study_plan.ai_generated_plan = ai_plan
            study_plan.save()
            
            # Create modules and topics from AI plan
            create_modules_from_ai_plan(study_plan, ai_plan)
            
            messages.success(request, 'Study plan created successfully!')
            return redirect('plan_detail', pk=study_plan.pk)
    else:
        form = StudyPlanForm()
    
    return render(request, 'planner/create_plan.html', {'form': form})


@login_required
def plan_detail(request, pk):
    """View study plan details"""
    study_plan = get_object_or_404(StudyPlan, pk=pk, user=request.user)
    modules = study_plan.modules.all().prefetch_related('topics')
    
    completion_percentage = study_plan.get_completion_percentage()
    total_time = study_plan.get_total_time_spent()
    
    context = {
        'study_plan': study_plan,
        'modules': modules,
        'completion_percentage': completion_percentage,
        'total_time': total_time,
    }
    
    return render(request, 'planner/plan_detail.html', context)


@login_required
def toggle_topic_complete(request, topic_id):
    """Toggle topic completion status"""
    topic = get_object_or_404(Topic, pk=topic_id, module__study_plan__user=request.user)
    
    if topic.is_completed:
        topic.mark_incomplete()
    else:
        topic.mark_complete()
    
    return JsonResponse({
        'success': True,
        'is_completed': topic.is_completed,
        'completion_percentage': topic.module.study_plan.get_completion_percentage()
    })


@login_required
def add_resource(request, topic_id):
    """Add resource to topic"""
    topic = get_object_or_404(Topic, pk=topic_id, module__study_plan__user=request.user)
    
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.topic = topic
            resource.save()
            messages.success(request, 'Resource added successfully!')
            return redirect('plan_detail', pk=topic.module.study_plan.pk)
    else:
        form = ResourceForm()
    
    return render(request, 'planner/add_resource.html', {'form': form, 'topic': topic})


@login_required
def analytics(request):
    """Analytics and visualizations"""
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Daily study time
    daily_logs = DailyLog.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Study time by domain
    domain_stats = StudyPlan.objects.filter(user=request.user).values('domain').annotate(
        total_time=Sum('modules__topics__time_spent_minutes'),
        completion=Avg('modules__topics__is_completed')
    )
    
    # Weekly progress
    weekly_data = []
    for i in range(days // 7):
        week_start = end_date - timedelta(days=(i+1)*7)
        week_end = end_date - timedelta(days=i*7)
        
        week_topics = Topic.objects.filter(
            module__study_plan__user=request.user,
            completed_at__date__gte=week_start,
            completed_at__date__lte=week_end
        ).count()
        
        weekly_data.append({
            'week': f'Week {i+1}',
            'topics': week_topics
        })
    
    context = {
        'daily_logs': daily_logs,
        'domain_stats': domain_stats,
        'weekly_data': weekly_data,
    }
    
    return render(request, 'planner/analytics.html', context)


@login_required
def calendar_view(request):
    """Calendar view of study schedule"""
    study_plans = StudyPlan.objects.filter(user=request.user, is_active=True)
    daily_logs = DailyLog.objects.filter(user=request.user)
    
    context = {
        'study_plans': study_plans,
        'daily_logs': daily_logs,
    }
    
    return render(request, 'planner/calendar.html', context)


@login_required
def start_study_session(request, topic_id):
    """Start a study session"""
    topic = get_object_or_404(Topic, pk=topic_id, module__study_plan__user=request.user)
    
    session = StudySession.objects.create(
        user=request.user,
        topic=topic,
        start_time=timezone.now()
    )
    
    return JsonResponse({
        'success': True,
        'session_id': session.id
    })


@login_required
def end_study_session(request, session_id):
    """End a study session"""
    session = get_object_or_404(StudySession, pk=session_id, user=request.user)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        session.notes = notes
        session.complete_session()
        
        return JsonResponse({
            'success': True,
            'duration': session.duration_minutes
        })
    
    return JsonResponse({'success': False})


@login_required
def generate_quiz(request, topic_id):
    """Generate AI quiz for topic"""
    topic = get_object_or_404(Topic, pk=topic_id, module__study_plan__user=request.user)
    
    # Check if quiz already exists
    existing_quiz = Quiz.objects.filter(topic=topic).first()
    if existing_quiz:
        return redirect('take_quiz', quiz_id=existing_quiz.id)
    
    # Generate new quiz
    ai_generator = NVIDIAStudyPlanGenerator()
    questions = ai_generator.generate_quiz_questions(
        topic_title=topic.title,
        topic_description=topic.description,
        difficulty='medium',
        num_questions=5
    )
    
    if questions:
        quiz = Quiz.objects.create(
            topic=topic,
            title=f"Quiz: {topic.title}",
            questions=questions
        )
        messages.success(request, 'Quiz generated successfully!')
        return redirect('take_quiz', quiz_id=quiz.id)
    else:
        messages.error(request, 'Failed to generate quiz. Please try again.')
        return redirect('plan_detail', pk=topic.module.study_plan.pk)


@login_required
def take_quiz(request, quiz_id):
    """Take a quiz"""
    quiz = get_object_or_404(Quiz, pk=quiz_id, topic__module__study_plan__user=request.user)
    
    if request.method == 'POST':
        answers = {}
        score = 0
        
        for i, question in enumerate(quiz.questions):
            user_answer = request.POST.get(f'question_{i}')
            correct_answer = question.get('correct_answer')
            
            answers[f'question_{i}'] = user_answer
            if user_answer == correct_answer:
                score += 1
        
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            total_questions=len(quiz.questions),
            answers=answers
        )
        
        return redirect('quiz_results', attempt_id=attempt.id)
    
    return render(request, 'planner/take_quiz.html', {'quiz': quiz})


@login_required
def quiz_results(request, attempt_id):
    """View quiz results"""
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user)
    
    context = {
        'attempt': attempt,
        'percentage': attempt.get_percentage(),
    }
    
    return render(request, 'planner/quiz_results.html', context)


# Helper functions

def create_modules_from_ai_plan(study_plan, ai_plan):
    """Create modules and topics from AI generated plan"""
    modules_data = ai_plan.get('modules', [])
    
    for idx, module_data in enumerate(modules_data):
        module = Module.objects.create(
            study_plan=study_plan,
            title=module_data.get('title', f'Module {idx+1}'),
            description=module_data.get('description', ''),
            order=idx,
            estimated_hours=module_data.get('estimated_hours', 10)
        )
        
        topics_data = module_data.get('topics', [])
        for topic_idx, topic_data in enumerate(topics_data):
            Topic.objects.create(
                module=module,
                title=topic_data.get('title', f'Topic {topic_idx+1}'),
                description=topic_data.get('description', ''),
                order=topic_idx,
                estimated_minutes=topic_data.get('estimated_minutes', 60)
            )


def calculate_study_streak(user):
    """Calculate current study streak"""
    logs = DailyLog.objects.filter(user=user).order_by('-date')
    
    if not logs.exists():
        return 0
    
    streak = 0
    current_date = timezone.now().date()
    
    for log in logs:
        if log.date == current_date or log.date == current_date - timedelta(days=streak):
            streak += 1
            current_date = log.date
        else:
            break
    
    return streak