from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Profile, Post, Follow, Message, Like, Comment
from django.contrib.auth.models import User

def inicio(request):
    if request.user.is_authenticated:
        # Garante que Profile existe para o usuário (evita erros no template)
        from .models import Profile
        Profile.objects.get_or_create(user=request.user)

        following_ids = request.user.following.values_list('followed_id', flat=True)
        posts = Post.objects.filter(
            user_id__in=list(following_ids) + [request.user.id]
        ).order_by('-created_at').select_related('user', 'user__profile').prefetch_related('likes', 'comments')
        suggested_users = User.objects.exclude(id__in=list(following_ids) + [request.user.id])[:6]
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
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    posts = Post.objects.filter(user=request.user).order_by('-created_at').select_related('user', 'user__profile').prefetch_related('likes', 'comments')
    from django.db.models import Q
    media_posts = posts.filter(Q(image__gt='') | Q(video__gt='') | Q(audio__gt=''))
    return render(request, "profile.html", {
        'posts': posts,
        'media_posts': media_posts,
        'profile': profile_obj,
    })

@login_required
def config(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user = request.user
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        if email is not None:
            user.email = email
        if first_name is not None:
            user.first_name = first_name
        user.save()

        profile_obj.bio = request.POST.get('bio', profile_obj.bio)
        profile_obj.location = request.POST.get('location', profile_obj.location)
        profile_obj.website = request.POST.get('website', profile_obj.website)
        if 'avatar' in request.FILES:
            profile_obj.avatar = request.FILES['avatar']
        profile_obj.save()
        return redirect('uel_inicio')
    return render(request, "config.html", {'profile': profile_obj})

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        profile_obj, created = Profile.objects.get_or_create(user=request.user)
        profile_obj.bio = request.POST.get('bio', '')
        profile_obj.location = request.POST.get('location', '')
        profile_obj.website = request.POST.get('website', '')
        
        birth_date = request.POST.get('birth_date')
        if birth_date:
            profile_obj.birth_date = birth_date
            
        if 'avatar' in request.FILES:
            profile_obj.avatar = request.FILES['avatar']
            
        profile_obj.save()
        
    return redirect(request.META.get('HTTP_REFERER', 'url_profile'))

@login_required
def editar_capa(request):
    if request.method == 'POST':
        profile_obj, created = Profile.objects.get_or_create(user=request.user)
        if 'cover' in request.FILES:
            profile_obj.cover = request.FILES['cover']
            profile_obj.save()
        if 'avatar' in request.FILES:
            profile_obj.avatar = request.FILES['avatar']
            profile_obj.save()
            
    return redirect(request.META.get('HTTP_REFERER', 'url_profile'))

@login_required
def criar_post(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        audio = request.FILES.get('audio')
        if content or image or video or audio:
            Post.objects.create(user=request.user, content=content, image=image, video=video, audio=audio)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    follow_qs = Follow.objects.filter(follower=request.user, followed=user_to_follow)
    if follow_qs.exists():
        follow_qs.delete()
    else:
        Follow.objects.create(follower=request.user, followed=user_to_follow)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def descobrir(request):
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(username__icontains=query).exclude(id=request.user.id).select_related('profile')
    else:
        users = User.objects.exclude(id=request.user.id).select_related('profile')[:8]
        
    following_ids = set(request.user.following.values_list('followed_id', flat=True))
    posts = Post.objects.all().order_by('-created_at')[:24]
    return render(request, "descobrir.html", {
        'posts': posts,
        'users': users,
        'query': query,
        'following_ids': following_ids
    })

@login_required
def mensagens(request):
    other_users = User.objects.exclude(id=request.user.id).select_related('profile')
    selected_user_id = request.GET.get('user')
    selected_user = None
    chat_messages = []
    
    if selected_user_id:
        selected_user = User.objects.filter(id=selected_user_id).first()
    elif other_users.exists():
        selected_user = other_users.first()
        
    if request.method == 'POST' and selected_user:
        content = request.POST.get('content')
        if content:
            Message.objects.create(sender=request.user, receiver=selected_user, content=content)
            return redirect(f"{request.path}?user={selected_user.id}")

    if selected_user:
        from django.db.models import Q
        chat_messages = Message.objects.filter(
            (Q(sender=request.user, receiver=selected_user) | Q(sender=selected_user, receiver=request.user))
        ).order_by('timestamp')
        
    return render(request, "mensagens.html", {
        'other_users': other_users,
        'selected_user': selected_user,
        'chat_messages': chat_messages,
    })

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