from django.contrib import admin
from .models import Profile, Post, Follow, Message, Like, Comment

admin.site.register(Profile)
admin.site.register(Post)
admin.site.register(Follow)
admin.site.register(Message)
admin.site.register(Like)
admin.site.register(Comment)