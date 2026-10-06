import json

from django.http import JsonResponse

from backend.benchmarks.algorithms import calculate_benchmark_score


def health(request):
    """Liveness only - no DB/cache/etc. touched, so a slow dependency can't
    false-negative this. Used by k8s/backend-deployment.yaml's readiness/
    liveness probes, and the deploy workflow's post-deploy health check."""
    return JsonResponse({'status': 'ok'})

def benchmark_view(request):
    """
    API view that receives student profile and dynamic weights,
    runs the benchmark algorithm, and returns the result.
    """
    if request.method == 'POST':
        try:
            # Safely handle incoming data whether it's sent as JSON or Form data
            if request.body:
                data = json.loads(request.body)
            else:
                data = request.POST

            student_profile = data.get('student_profile', {})
            dynamic_weights = data.get('dynamic_weights', {})

            # If the frontend passes them as stringified JSON, parse them safely
            if isinstance(student_profile, str):
                student_profile = json.loads(student_profile)
            if isinstance(dynamic_weights, str):
                dynamic_weights = json.loads(dynamic_weights)

            # Call your classmate's algorithm function
            result = calculate_benchmark_score(student_profile, dynamic_weights)

            return JsonResponse({
                'status': 'success',
                'data': result
            }, status=200)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Only POST requests are allowed.'
    }, status=405)
