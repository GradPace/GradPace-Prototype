from django.http import JsonResponse
from .algorithms import calculate_benchmark_score, normalize_skills

def run_benchmark_view(request):
    # Example test data to ensure it works
    sample_profile = {'skills': 80.0, 'experience': 70.0, 'networking': 50.0}
    sample_weights = {'skills': 0.40, 'experience': 0.40, 'networking': 0.20}
    
    results = calculate_benchmark_score(sample_profile, sample_weights)
    return JsonResponse({'success': True, 'data': results})