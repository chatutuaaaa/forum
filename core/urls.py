from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/like/', views.like_post, name='like_post'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # 密码修改相关
    path('password/change/', views.password_change, name='password_change'),
    path('password/reset/email/', views.password_reset_email, name='password_reset_email'),
    path('password/reset/verify/', views.password_reset_verify, name='password_reset_verify'),
]

