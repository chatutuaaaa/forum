from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from markdown import markdown

from datetime import datetime

from .forms import (
    CommentForm, PostForm, RegisterForm,
    PasswordChangeForm, EmailVerificationForm, VerifyCodeForm,
)
from .models import Category, Comment, DailyQuote, Post, PostLike, Tag
from .services.amap_weather import get_live_weather, resolve_adcode_for_request


def home(request: HttpRequest) -> HttpResponse:
    category_slug = request.GET.get('category')
    tag_slug = request.GET.get('tag')
    query = request.GET.get('q', '').strip()

    posts = Post.objects.filter(is_published=True).select_related('author', 'category').prefetch_related('tags')

    if category_slug:
        posts = posts.filter(category__slug=category_slug)
    if tag_slug:
        posts = posts.filter(tags__slug=tag_slug)
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(content__icontains=query))

    posts = posts.annotate(num_likes=Count('likes'), num_comments=Count('comments'))

    categories = Category.objects.all()
    tags = Tag.objects.all()[:20]
    hot_posts = Post.objects.filter(is_published=True).annotate(
        hot_score=Count('likes') + Count('comments')
    ).order_by('-hot_score', '-created_at')[:10]
    daily_quote = DailyQuote.objects.filter(is_active=True).first()
    adcode = resolve_adcode_for_request(request)
    live_weather = get_live_weather(adcode)
    weather_location = None
    weather_date = None
    weather_icon = "img/weather/cloudy.svg"
    if live_weather:
        weather_location = " ".join([p for p in [live_weather.province, live_weather.city] if p]).strip() or None
        try:
            dt = datetime.strptime(live_weather.reporttime, "%Y-%m-%d %H:%M:%S")
            week_map = ["一", "二", "三", "四", "五", "六", "日"]
            weather_date = f"{dt.strftime('%Y年%m月%d日')} 周{week_map[dt.weekday()]}"
        except Exception:
            weather_date = live_weather.reporttime

        desc = (live_weather.weather or "").strip()
        hour = None
        try:
            if 'dt' in locals():
                hour = dt.hour
        except Exception:
            hour = None
        is_night = hour is not None and (hour >= 18 or hour < 6)

        def pick(icon: str) -> str:
            return f"img/weather/{icon}"

        if any(k in desc for k in ["雷", "雷阵雨", "雷暴"]):
            weather_icon = pick("thunderstorm.svg")
        elif any(k in desc for k in ["暴雨", "大雨", "特大暴雨"]):
            weather_icon = pick("heavy-rain.svg")
        elif "雨" in desc:
            weather_icon = pick("light-rain.svg")
        elif any(k in desc for k in ["雪", "雨夹雪"]):
            weather_icon = pick("snow.svg")
        elif any(k in desc for k in ["沙", "尘", "沙尘暴"]):
            weather_icon = pick("sandstorm.svg")
        elif any(k in desc for k in ["雾", "霾"]):
            weather_icon = pick("fog.svg")
        elif any(k in desc for k in ["大风", "狂风"]):
            weather_icon = pick("heavy-wind.svg")
        elif "风" in desc:
            weather_icon = pick("wind.svg")
        elif any(k in desc for k in ["多云", "阴"]):
            weather_icon = pick("cloudy-night.svg" if is_night else "cloudy.svg")
        elif "晴" in desc:
            weather_icon = pick("moon.svg" if is_night else "sunny.svg")
        else:
            weather_icon = pick("cloudy.svg")

    context = {
        'posts': posts,
        'categories': categories,
        'tags': tags,
        'hot_posts': hot_posts,
        'daily_quote': daily_quote,
        'live_weather': live_weather,
        'weather_location': weather_location,
        'weather_date': weather_date,
        'weather_icon': weather_icon,
        'current_category': category_slug,
        'current_tag': tag_slug,
        'query': query,
    }
    return render(request, 'core/home.html', context)


def post_detail(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post.objects.select_related('author', 'category'), pk=pk, is_published=True)
    post.views = post.views + 1
    post.save(update_fields=['views'])

    comments = Comment.objects.filter(post=post, parent__isnull=True, is_deleted=False).select_related('user')
    comment_form = CommentForm()

    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            parent_id = request.POST.get('parent_id')
            parent = Comment.objects.filter(pk=parent_id, post=post).first() if parent_id else None
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.user = request.user
            new_comment.parent = parent
            new_comment.save()
            messages.success(request, '评论成功')
            return redirect('post_detail', pk=post.pk)

    is_liked = False
    if request.user.is_authenticated:
        is_liked = PostLike.objects.filter(post=post, user=request.user).exists()

    rendered_content = markdown(post.content, extensions=['fenced_code', 'codehilite', 'tables'])

    context = {
        'post': post,
        'rendered_content': rendered_content,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': is_liked,
    }
    return render(request, 'core/post_detail.html', context)


@login_required
def like_post(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk, is_published=True)
    like, created = PostLike.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return HttpResponseRedirect(reverse('post_detail', args=[pk]))


def register(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'core/auth/register.html', {'form': form})


def user_login(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # 管理员跳转到后台管理界面
            if user.is_staff or user.is_superuser:
                return redirect('/admin/')
            return redirect('home')
        messages.error(request, '用户名或密码错误')
    return render(request, 'core/auth/login.html')


def user_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect('home')


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    posts = Post.objects.filter(author=request.user)
    form = PostForm()
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()
            messages.success(request, '发布成功')
            return redirect('dashboard')

    context = {
        'posts': posts,
        'form': form,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def password_change(request: HttpRequest) -> HttpResponse:
    """密码修改 - 使用旧密码验证"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '密码修改成功，请重新登录')
            return redirect('login')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/auth/password_change.html', {'form': form})


@login_required
def password_reset_email(request: HttpRequest) -> HttpResponse:
    """密码重置 - 发送邮箱验证码"""
    # 检查用户是否有邮箱
    if not request.user.email:
        messages.error(request, '您尚未设置邮箱，无法使用邮箱验证')
        return redirect('password_change')

    if request.method == 'POST':
        form = EmailVerificationForm(request.user, request.POST)
        if form.is_valid():
            email_sent = form.send_verification_code()
            # 存储邮箱验证状态到session
            request.session['password_reset_email_verified'] = True
            if not email_sent:
                # 开发环境：获取验证码供显示
                dev_code = cache.get(f'password_reset_dev_{request.user.pk}')
                if dev_code:
                    messages.info(request, f'[开发模式] 验证码：{dev_code}')
                else:
                    messages.warning(request, '邮件发送失败，请检查邮箱配置')
            else:
                messages.success(request, f'验证码已发送至 {request.user.email}')
            return redirect('password_reset_verify')
    else:
        form = EmailVerificationForm(request.user, initial={'email': request.user.email})
    return render(request, 'core/auth/password_reset_email.html', {'form': form})


@login_required
def password_reset_verify(request: HttpRequest) -> HttpResponse:
    """密码重置 - 验证码验证并修改密码"""
    # 检查是否已验证邮箱
    if not request.session.get('password_reset_email_verified'):
        return redirect('password_reset_email')

    if request.method == 'POST':
        form = VerifyCodeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # 清除session
            request.session.pop('password_reset_email_verified', None)
            messages.success(request, '密码修改成功，请重新登录')
            return redirect('login')
    else:
        # 开发环境：获取验证码供显示
        dev_code = cache.get(f'password_reset_dev_{request.user.pk}')
        form = VerifyCodeForm(request.user)
        if dev_code:
            messages.info(request, f'[开发模式] 验证码：{dev_code}')
    return render(request, 'core/auth/password_reset_verify.html', {'form': form})

