from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profile, Post

def inicio (request):
    return render(request,"index.html")

@login_required
def profile(request):
    # Ensure profile exists
    Profile.objects.get_or_create(user=request.user)
    return render(request,"profile.html")

@login_required
def config(request):
    return render(request,"config.html")

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile.bio = request.POST.get('bio', '')
        profile.location = request.POST.get('location', '')
        profile.website = request.POST.get('website', '')
        
        birth_date = request.POST.get('birth_date')
        if birth_date:
            profile.birth_date = birth_date
            
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            
        profile.save()
        
    return redirect('url_profile')

@login_required
def editar_capa(request):
    if request.method == 'POST':
        profile, created = Profile.objects.get_or_create(user=request.user)
        if 'cover' in request.FILES:
            profile.cover = request.FILES['cover']
            profile.save()
            
    return redirect('url_profile')