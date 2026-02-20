from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import SignupForm


def signup_view(request):
    """User registration; redirects to event list after signup."""
    if request.user.is_authenticated:
        return redirect('event_list')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('event_list')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})
