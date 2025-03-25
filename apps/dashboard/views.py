import json
import requests
from decouple import config
from django.views.generic import TemplateView
from apps.data.about_data import AboutData
from datetime import datetime, timedelta

def fetch_github_activity():
    username = "ridwaanhall"
    access_token = config("ACCESS_TOKEN")
    api_url = "https://api.github.com/graphql"

    query = """
      query {
        user(login: "%s") {
          contributionsCollection {
            contributionCalendar {
              totalContributions
              months {
                firstDay
                name
                totalWeeks
              }
              weeks {
                firstDay
                contributionDays {
                  contributionCount
                  date
                }
              }
            }
          }
        }
      }
    """ % username

    headers = {
        "Authorization": "Bearer %s" % access_token,
        "Content-Type": "application/json",
    }
    data = json.dumps({"query": query})

    response = requests.post(api_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
def calculate_github_stats(contribution_weeks, total_contributions):
    """Calculate GitHub contribution statistics."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    day_of_week = today.weekday()
    first_day_of_current_week = today - timedelta(days=(day_of_week + 1) % 7)
    
    this_week_contributions = 0
    best_day_count = 0
    total_days_with_contributions = 0
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    all_days = []
    for week in contribution_weeks:
        for day in week['contributionDays']:
            date = datetime.fromisoformat(day['date'])
            count = day['contributionCount']
            
            all_days.append({'date': date, 'count': count})
            
            if count > best_day_count:
                best_day_count = count
            
            if first_day_of_current_week <= date <= today:
                this_week_contributions += count
            
            if count > 0:
                total_days_with_contributions += 1
    
    all_days.sort(key=lambda x: x['date'])
    
    for day_data in all_days:
        if day_data['count'] > 0:
            temp_streak += 1
            
            day_diff = (today - day_data['date']).days
            if day_diff <= 1:
                current_streak = temp_streak
        else:
            if temp_streak > longest_streak:
                longest_streak = temp_streak
            temp_streak = 0
    
    if temp_streak > longest_streak:
        longest_streak = temp_streak
    
    if all_days:
        last_day = all_days[-1]
        days_since_last_contribution = (today - last_day['date']).days
        if days_since_last_contribution > 1 or last_day['count'] == 0:
            current_streak = 0
    
    total_days = len(all_days)
    average_contributions = round(total_contributions / total_days, 1) if total_days > 0 else 0
    
    return {
        'this_week': this_week_contributions,
        'best_day': best_day_count,
        'average': f"{average_contributions}",
        'longest_streak': longest_streak,
        'current_streak': current_streak
    }

def fetch_wakatime_activity():
    wakatime_api_key = config("WAKATIME_API_KEY")
    last_7_days_api = "https://wakatime.com/api/v1/users/current/stats/last_7_days?api_key=%s" % wakatime_api_key
    all_time_since_today_api = "https://wakatime.com/api/v1/users/current/all_time_since_today?api_key=%s" % wakatime_api_key
    
    last_7_days_response = requests.get(last_7_days_api)
    all_time_response = requests.get(all_time_since_today_api)
    
    if last_7_days_response.status_code == 200 and all_time_response.status_code == 200:
        return {
            'last_7_days': last_7_days_response.json(),
            'all_time': all_time_response.json()
        }
    else:
        return None

def calculate_wakatime_stats(data):
    """Calculate Wakatime statistics."""
    if not data:
        return None
    
    last_7_days = data['last_7_days']['data']
    all_time = data['all_time']['data']
    
    # Format time durations
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} hrs {minutes} mins"
    
    # Extract required data
    # Calculate the time difference for "X hours ago"
    end_date = datetime.fromisoformat(last_7_days['end'].replace('Z', '+00:00'))
    now = datetime.now().astimezone() # Get current time with timezone
    time_diff = now - end_date
    hours_ago = int(time_diff.total_seconds() / 3600)
    last_update = f"{hours_ago} hours ago"
    
    waka_stats = {
        'start_date': datetime.fromisoformat(last_7_days['start'].replace('Z', '+00:00')).strftime('%B %d, %Y'),
        'end_date': datetime.fromisoformat(last_7_days['end'].replace('Z', '+00:00')).strftime('%B %d, %Y'),
        'daily_average': format_time(last_7_days['daily_average']),
        'this_week_coding': format_time(last_7_days['total_seconds']),
        'best_day_date': datetime.fromisoformat(last_7_days['best_day']['date']).strftime('%B %d, %Y'),
        'best_day_coding': last_7_days['best_day']['text'],
        'all_time_coding': all_time['text'],
        'all_time_start': datetime.fromisoformat(all_time['range']['start'].replace('Z', '+00:00')).strftime('%B %d, %Y'),
        'all_time_end': datetime.fromisoformat(all_time['range']['end'].replace('Z', '+00:00')).strftime('%B %d, %Y'),
        'last_update_time': last_update
    }
    
    return waka_stats

class DashboardView(TemplateView):
    template_name = 'dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        about = AboutData.get_about_data()
        context['about'] = about[0]
        
        seo = {
            'title': f"Developer Dashboard | {about[0]['name']} - Coding Activity",
            'description': f"Track {about[0]['name']}'s coding activity, GitHub contributions, and development metrics. See real-time stats and productivity measures.",
            'keywords': f"{about[0]['name']}, developer dashboard, github contributions, coding metrics, programming activity, wakatime stats",
            'og_image': about[0].get('image_url', ''),
            'og_type': 'website',
            'twitter_card': 'summary_large_image',
        }
        context['seo'] = seo
        
        # GitHub data
        github_activity = fetch_github_activity()
        context['github_activity'] = github_activity
        
        if github_activity:
            calendar_data = github_activity['data']['user']['contributionsCollection']['contributionCalendar']
            contribution_weeks = calendar_data['weeks']
            total_contributions = calendar_data['totalContributions']
            
            github_stats = calculate_github_stats(contribution_weeks, total_contributions)
            
            context['total_contributions'] = total_contributions
            context['this_week'] = github_stats['this_week']
            context['best_day'] = github_stats['best_day']
            context['average'] = f"{github_stats['average']} / day"
            context['longest_streak'] = github_stats['longest_streak']
            context['current_streak'] = github_stats['current_streak']
            context['github_last_update'] = datetime.now().strftime('%B %d, %Y %I:%M %p')
        
        # WakaTime data
        wakatime_activity = fetch_wakatime_activity()
        if wakatime_activity:
            wakatime_stats = calculate_wakatime_stats(wakatime_activity)
            context['wakatime_stats'] = wakatime_stats
        
        return context