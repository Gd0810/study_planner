from datetime import datetime, timedelta
from django.utils import timezone
from .models import DailyLog, Topic

def get_weekly_stats(user, weeks=4):
    """Get study statistics for the past N weeks"""
    stats = []
    end_date = timezone.now().date()
    
    for i in range(weeks):
        week_start = end_date - timedelta(days=(i+1)*7)
        week_end = end_date - timedelta(days=i*7)
        
        logs = DailyLog.objects.filter(
            user=user,
            date__gte=week_start,
            date__lte=week_end
        )
        
        total_hours = sum([log.hours_studied for log in logs])
        days_studied = logs.count()
        
        stats.append({
            'week': f'Week {weeks-i}',
            'total_hours': total_hours,
            'days_studied': days_studied,
            'start_date': week_start,
            'end_date': week_end
        })
    
    return list(reversed(stats))


def get_domain_distribution(user):
    """Get study time distribution by domain"""
    from django.db.models import Sum
    from .models import StudyPlan
    
    domains = StudyPlan.objects.filter(user=user).values('domain').annotate(
        total_minutes=Sum('modules__topics__time_spent_minutes')
    )
    
    return [
        {
            'domain': d['domain'],
            'hours': round((d['total_minutes'] or 0) / 60, 1)
        }
        for d in domains
    ]


def predict_completion_date(study_plan):
    """Predict when a study plan will be completed"""
    total_topics = Topic.objects.filter(module__study_plan=study_plan).count()
    completed_topics = Topic.objects.filter(
        module__study_plan=study_plan,
        is_completed=True
    ).count()
    
    if completed_topics == 0:
        return None
    
    # Calculate average completion rate
    days_since_start = (timezone.now().date() - study_plan.start_date).days
    if days_since_start == 0:
        return None
    
    topics_per_day = completed_topics / days_since_start
    remaining_topics = total_topics - completed_topics
    
    if topics_per_day == 0:
        return None
    
    days_remaining = remaining_topics / topics_per_day
    predicted_date = timezone.now().date() + timedelta(days=int(days_remaining))
    
    return predicted_date