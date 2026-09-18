from django.contrib import admin
from django.urls import path
from .views import inicio, profile, config, editar_perfil, editar_capa

urlpatterns = [
    path("",inicio,name="home"),
    path("profile",profile ,name="url_profile"),
    path("config",config,name="uel_inicio"),
    path("editar-perfil", editar_perfil, name="editar_perfil"),
    path("editar-capa", editar_capa, name="editar_capa"),
]
