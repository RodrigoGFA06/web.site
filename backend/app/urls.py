from django.urls import path
from .views import (
    inicio, profile, config, editar_perfil, editar_capa,
    criar_post, follow_user, descobrir, mensagens, atividades,
    like_post, comment_post, register
)
from .api_views import (
    api_me, api_login, api_register, api_logout,
    api_feed, api_create_post, api_like_post, api_comment_post,
    api_follow_user, api_discover, api_messages, api_activities, api_profile
)

urlpatterns = [
    path("", inicio, name="home"),
    path("profile", profile, name="url_profile"),
    path("profile/<str:username>/", profile, name="profile_user"),
    path("config", config, name="uel_inicio"),
    path("editar-perfil", editar_perfil, name="editar_perfil"),
    path("editar-capa", editar_capa, name="editar_capa"),
    path("criar-post", criar_post, name="criar_post"),
    path("follow/<int:user_id>/", follow_user, name="follow_user"),
    path("descobrir", descobrir, name="descobrir"),
    path("mensagens", mensagens, name="mensagens"),
    path("atividades", atividades, name="atividades"),
    path("like/<int:post_id>/", like_post, name="like_post"),
    path("comment/<int:post_id>/", comment_post, name="comment_post"),
    path("register", register, name="register"),

    # JSON API para o frontend React
    path("api/me/", api_me, name="api_me"),
    path("api/auth/login/", api_login, name="api_login"),
    path("api/auth/register/", api_register, name="api_register"),
    path("api/auth/logout/", api_logout, name="api_logout"),
    path("api/feed/", api_feed, name="api_feed"),
    path("api/posts/create/", api_create_post, name="api_create_post"),
    path("api/posts/<int:post_id>/like/", api_like_post, name="api_like_post"),
    path("api/posts/<int:post_id>/comment/", api_comment_post, name="api_comment_post"),
    path("api/users/<int:user_id>/follow/", api_follow_user, name="api_follow_user"),
    path("api/discover/", api_discover, name="api_discover"),
    path("api/messages/", api_messages, name="api_messages"),
    path("api/activities/", api_activities, name="api_activities"),
    path("api/profile/", api_profile, name="api_profile"),
    path("api/profile/<str:username>/", api_profile, name="api_profile_user"),
]