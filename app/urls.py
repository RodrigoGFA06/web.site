from django.contrib import admin
from django.urls import path
from .views import (
    inicio, profile, config, editar_perfil, editar_capa,
    criar_post, follow_user, descobrir, mensagens, atividades,
    like_post, comment_post, register
)

urlpatterns = [
    path("", inicio, name="home"),
    path("profile", profile, name="url_profile"),
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
]
