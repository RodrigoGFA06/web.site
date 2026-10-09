from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Profile, Post, Follow, Message, Like, Comment
from django.contrib.auth.models import User

def inicio(request):
    if request.user.is_authenticated:
        following_ids = request.user.following.values_list('followed_id', flat=True)
        posts = Post.objects.filter(user_id__in=list(following_ids) + [request.user.id]).order_by('-created_at')
        suggested_users = User.objects.exclude(id__in=list(following_ids) + [request.user.id])[:5]
        return render(request, "index.html", {'posts': posts, 'suggested_users': suggested_users})
    else:
        return render(request, "index.html")

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, "register.html", {'form': form})

@login_required
def profile(request):
    Profile.objects.get_or_create(user=request.user)
    return render(request, "profile.html")

@login_required
def config(request):
    return render(request, "config.html")

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

@login_required
def criar_post(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        audio = request.FILES.get('audio')
        if content or image or video or audio:
            Post.objects.create(user=request.user, content=content, image=image, video=video, audio=audio)
    return redirect('home')

@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    Follow.objects.get_or_create(follower=request.user, followed=user_to_follow)
    return redirect('home')

@login_required
def descobrir(request):
    query = request.GET.get('q', '')
    users = []
    if query:
        users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
        
    posts = Post.objects.all().order_by('?')[:20]
    return render(request, "descobrir.html", {'posts': posts, 'users': users, 'query': query})

@login_required
def mensagens(request):
    return render(request, "mensagens.html")

@login_required
def atividades(request):
    return render(request, "atividades.html")

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete() # Toggle like
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def comment_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Comment.objects.create(user=request.user, post=post, content=content)
    return redirect(request.META.get('HTTP_REFERER', 'home'))