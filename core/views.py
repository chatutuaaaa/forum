from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from markdown import markdown

from .forms import CommentForm, PostForm, RegisterForm
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

    context = {
        'posts': posts,
        'categories': categories,
        'tags': tags,
        'hot_posts': hot_posts,
        'daily_quote': daily_quote,
        'live_weather': live_weather,
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

