import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .models import Comment, Follow, Like, Message, Post, Profile


def _user_summary(user, following_ids=None):
    profile, _ = Profile.objects.get_or_create(user=user)
    is_following = user.id in following_ids if following_ids is not None else False
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name or "",
        "display_name": user.first_name or user.username,
        "avatarUrl": profile.avatar.url if profile.avatar else "",
        "coverUrl": profile.cover.url if profile.cover else "",
        "bio": profile.bio or "",
        "location": profile.location or "",
        "website": profile.website or "",
        "followersCount": user.followers.count(),
        "followingCount": user.following.count(),
        "postsCount": user.posts.count(),
        "isFollowing": is_following,
    }


def _serialize_comment(comment):
    profile = getattr(comment.user, "profile", None)
    return {
        "id": comment.id,
        "content": comment.content,
        "createdAt": comment.created_at.isoformat(),
        "author": {
            "id": comment.user.id,
            "username": comment.user.username,
            "avatarUrl": profile.avatar.url if profile and profile.avatar else "",
        },
    }


def _serialize_post(post, current_user=None, following_ids=None):
    profile = getattr(post.user, "profile", None)
    likes = list(post.likes.all())
    comments = list(post.comments.select_related("user", "user__profile").all())
    liked_by_me = (
        any(like.user_id == current_user.id for like in likes)
        if current_user and current_user.is_authenticated
        else False
    )
    media_type = (
        "video"
        if post.video
        else "image"
        if post.image
        else "audio"
        if post.audio
        else "text"
    )
    return {
        "id": post.id,
        "content": post.content or "",
        "mediaType": media_type,
        "imageUrl": post.image.url if post.image else "",
        "videoUrl": post.video.url if post.video else "",
        "audioUrl": post.audio.url if post.audio else "",
        "createdAt": post.created_at.isoformat(),
        "likesCount": len(likes),
        "likedByMe": liked_by_me,
        "commentsCount": len(comments),
        "comments": [_serialize_comment(c) for c in comments],
        "author": {
            "id": post.user.id,
            "username": post.user.username,
            "displayName": post.user.first_name or post.user.username,
            "avatarUrl": profile.avatar.url if profile and profile.avatar else "",
            "isFollowing": post.user_id in following_ids if following_ids else False,
        },
    }


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return {}


@require_GET
def api_me(request):
    csrf_token = get_token(request)
    if not request.user.is_authenticated:
        return JsonResponse({"isAuthenticated": False, "csrfToken": csrf_token})

    following_ids = set(request.user.following.values_list("followed_id", flat=True))
    data = _user_summary(request.user, following_ids)
    data["isAuthenticated"] = True
    data["csrfToken"] = csrf_token
    data["email"] = request.user.email or ""
    return JsonResponse(data)


@require_POST
def api_login(request):
    payload = _json_body(request)
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Usuário ou senha inválidos."}, status=400)
    login(request, user)
    Profile.objects.get_or_create(user=user)
    return api_me(request)


@require_POST
def api_register(request):
    payload = _json_body(request)
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    email = (payload.get("email") or "").strip()

    if len(username) < 3:
        return JsonResponse({"error": "O nome de usuário deve ter pelo menos 3 caracteres."}, status=400)
    if len(password) < 4:
        return JsonResponse({"error": "A senha deve ter pelo menos 4 caracteres."}, status=400)
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"error": "Esse nome de usuário já está em uso."}, status=400)

    user = User.objects.create_user(username=username, password=password, email=email)
    Profile.objects.get_or_create(user=user)
    login(request, user)
    return api_me(request)


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({"ok": True, "csrfToken": get_token(request)})


@require_GET
def api_feed(request):
    tab = request.GET.get("tab", "for-you")
    following_ids = set()
    if request.user.is_authenticated:
        Profile.objects.get_or_create(user=request.user)
        following_ids = set(request.user.following.values_list("followed_id", flat=True))

    qs = Post.objects.select_related("user", "user__profile").prefetch_related(
        "likes", "comments", "comments__user", "comments__user__profile"
    )
    if tab == "following" and request.user.is_authenticated:
        qs = qs.filter(user_id__in=list(following_ids) + [request.user.id])
    elif tab == "reels":
        qs = qs.exclude(video="").exclude(video__isnull=True)

    posts = [_serialize_post(p, request.user, following_ids) for p in qs[:40]]

    exclude_ids = list(following_ids) + ([request.user.id] if request.user.is_authenticated else [])
    suggested_qs = (
        User.objects.exclude(id__in=exclude_ids)
        .select_related("profile")
        .annotate(num_followers=Count("followers"))
        .order_by("-num_followers", "-date_joined")[:8]
    )
    suggested_users = [_user_summary(u, following_ids) for u in suggested_qs]

    stories_qs = User.objects.select_related("profile").order_by("-last_login", "-date_joined")[:12]
    stories = [_user_summary(u, following_ids) for u in stories_qs]

    return JsonResponse({
        "posts": posts,
        "suggestedUsers": suggested_users,
        "stories": stories,
    })


@require_POST
def api_create_post(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Faça login para publicar."}, status=401)

    content = (request.POST.get("content") or "").strip()
    image = request.FILES.get("image")
    video = request.FILES.get("video")
    audio = request.FILES.get("audio")

    if not any([content, image, video, audio]):
        return JsonResponse({"error": "Adicione uma legenda ou mídia para publicar."}, status=400)

    post = Post.objects.create(
        user=request.user,
        content=content,
        image=image,
        video=video,
        audio=audio,
    )
    following_ids = set(request.user.following.values_list("followed_id", flat=True))
    return JsonResponse({"post": _serialize_post(post, request.user, following_ids)}, status=201)


@require_POST
def api_like_post(request, post_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Faça login para curtir."}, status=401)
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({"liked": liked, "likesCount": post.likes.count()})


@require_POST
def api_comment_post(request, post_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Faça login para comentar."}, status=401)
    post = get_object_or_404(Post, id=post_id)
    payload = _json_body(request)
    content = (payload.get("content") or request.POST.get("content") or "").strip()
    if not content:
        return JsonResponse({"error": "Comentário vazio."}, status=400)
    comment = Comment.objects.create(post=post, user=request.user, content=content)
    return JsonResponse(
        {"comment": _serialize_comment(comment), "commentsCount": post.comments.count()},
        status=201,
    )


@require_POST
def api_follow_user(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Faça login para seguir."}, status=401)
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        return JsonResponse({"error": "Você não pode seguir a si mesmo."}, status=400)

    qs = Follow.objects.filter(follower=request.user, followed=target)
    if qs.exists():
        qs.delete()
        following = False
    else:
        Follow.objects.create(follower=request.user, followed=target)
        following = True
    return JsonResponse({"following": following, "followersCount": target.followers.count()})


@require_GET
def api_discover(request):
    query = (request.GET.get("q") or "").strip()
    following_ids = (
        set(request.user.following.values_list("followed_id", flat=True))
        if request.user.is_authenticated
        else set()
    )

    users_qs = User.objects.select_related("profile")
    if request.user.is_authenticated:
        users_qs = users_qs.exclude(id=request.user.id)
    if query:
        users_qs = users_qs.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(profile__bio__icontains=query)
        )
    users = [_user_summary(u, following_ids) for u in users_qs[:15]]

    posts_qs = Post.objects.select_related("user", "user__profile").prefetch_related(
        "likes", "comments", "comments__user", "comments__user__profile"
    )
    if query:
        posts_qs = posts_qs.filter(Q(content__icontains=query) | Q(user__username__icontains=query))
    posts = [_serialize_post(p, request.user, following_ids) for p in posts_qs[:30]]

    return JsonResponse({"users": users, "posts": posts, "query": query})


def api_messages(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Faça login para acessar mensagens."}, status=401)

    other_users = User.objects.exclude(id=request.user.id).select_related("profile")
    selected_id = request.GET.get("user")
    selected_user = None
    if selected_id and selected_id.isdigit():
        selected_user = other_users.filter(id=int(selected_id)).first()
    if selected_user is None:
        selected_user = other_users.first()

    if request.method == "POST":
        payload = _json_body(request)
        target_id = payload.get("user_id") or (selected_user.id if selected_user else None)
        content = (payload.get("content") or "").strip()
        if target_id and content:
            target = get_object_or_404(User, id=target_id)
            msg = Message.objects.create(sender=request.user, receiver=target, content=content)
            return JsonResponse({
                "message": {
                    "id": msg.id,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "isMine": True,
                }
            }, status=201)
        return JsonResponse({"error": "Mensagem inválida."}, status=400)

    chat_messages = []
    if selected_user:
        msgs = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=selected_user))
            | (Q(sender=selected_user) & Q(receiver=request.user))
        ).order_by("timestamp")
        chat_messages = [
            {
                "id": m.id,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "isMine": m.sender_id == request.user.id,
            }
            for m in msgs
        ]

    following_ids = set(request.user.following.values_list("followed_id", flat=True))
    return JsonResponse({
        "users": [_user_summary(u, following_ids) for u in other_users],
        "selectedUser": _user_summary(selected_user, following_ids) if selected_user else None,
        "messages": chat_messages,
    })


@require_GET
def api_activities(request):
    if not request.user.is_authenticated:
        return JsonResponse({"activities": []})

    activities = []
    likes = Like.objects.filter(post__user=request.user).exclude(user=request.user).select_related("user", "user__profile", "post")[:15]
    for like in likes:
        activities.append({
            "id": f"like-{like.id}",
            "type": "like",
            "username": like.user.username,
            "avatarUrl": like.user.profile.avatar.url if hasattr(like.user, "profile") and like.user.profile.avatar else "",
            "text": "curtiu sua publicação",
            "postId": like.post_id,
            "createdAt": like.created_at.isoformat(),
        })

    comments = Comment.objects.filter(post__user=request.user).exclude(user=request.user).select_related("user", "user__profile", "post")[:15]
    for c in comments:
        activities.append({
            "id": f"comment-{c.id}",
            "type": "comment",
            "username": c.user.username,
            "avatarUrl": c.user.profile.avatar.url if hasattr(c.user, "profile") and c.user.profile.avatar else "",
            "text": f'comentou: "{c.content[:50]}"',
            "postId": c.post_id,
            "createdAt": c.created_at.isoformat(),
        })

    follows = Follow.objects.filter(followed=request.user).select_related("follower", "follower__profile")[:15]
    for f in follows:
        activities.append({
            "id": f"follow-{f.id}",
            "type": "follow",
            "username": f.follower.username,
            "avatarUrl": f.follower.profile.avatar.url if hasattr(f.follower, "profile") and f.follower.profile.avatar else "",
            "text": "começou a seguir você",
            "createdAt": f.created_at.isoformat(),
        })

    activities.sort(key=lambda x: x["createdAt"], reverse=True)
    return JsonResponse({"activities": activities[:30]})


def api_profile(request, username=None):
    if username:
        target_user = get_object_or_404(User, username=username)
    elif request.user.is_authenticated:
        target_user = request.user
    else:
        return JsonResponse({"error": "Faça login para ver seu perfil."}, status=401)

    profile_obj, _ = Profile.objects.get_or_create(user=target_user)

    if request.method == "POST":
        if not request.user.is_authenticated or request.user != target_user:
            return JsonResponse({"error": "Não autorizado."}, status=403)
        if request.content_type and "multipart/form-data" in request.content_type:
            target_user.first_name = request.POST.get("first_name", target_user.first_name)
            target_user.save()
            profile_obj.bio = request.POST.get("bio", profile_obj.bio or "")
            profile_obj.location = request.POST.get("location", profile_obj.location or "")
            profile_obj.website = request.POST.get("website", profile_obj.website or "")
            if "avatar" in request.FILES:
                profile_obj.avatar = request.FILES["avatar"]
            if "cover" in request.FILES:
                profile_obj.cover = request.FILES["cover"]
            profile_obj.save()
        else:
            payload = _json_body(request)
            if "first_name" in payload:
                target_user.first_name = payload["first_name"]
                target_user.save()
            for field in ("bio", "location", "website"):
                if field in payload:
                    setattr(profile_obj, field, payload[field])
            profile_obj.save()

    following_ids = (
        set(request.user.following.values_list("followed_id", flat=True))
        if request.user.is_authenticated
        else set()
    )
    posts_qs = (
        Post.objects.filter(user=target_user)
        .select_related("user", "user__profile")
        .prefetch_related("likes", "comments", "comments__user", "comments__user__profile")
    )
    posts = [_serialize_post(p, request.user, following_ids) for p in posts_qs]

    return JsonResponse({
        "profile": _user_summary(target_user, following_ids),
        "isOwnProfile": request.user.is_authenticated and request.user == target_user,
        "posts": posts,
    })

