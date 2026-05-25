import logging

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import validate_email
from django.db import models as db_models
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django_ratelimit.decorators import ratelimit

from taggit.models import Tag

from apps.blog.forms import CommentForm, EmailPostForm, PostForm, SearchForm

logger = logging.getLogger(__name__)
from apps.blog.models import Bookmark, Comment, Category, Post, PostReaction, Subscriber


class PostListView(ListView):
    queryset = Post.published.all()
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 3

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = 'blog'
        return context


def post_list_by_tag(request, tag_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)
    posts = Post.published.filter(tags__in=[tag])

    paginator = Paginator(posts, django_settings.BLOG_POSTS_PER_PAGE)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return _render_post_list(
        request,
        page_obj,
        tag=tag,
        section='blog',
    )


def _render_post_list(request, page_obj, tag=None, category=None, author=None, section='blog'):
    return render(request, 'blog/post_list.html', {
        'posts': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'tag': tag,
        'category': category,
        'author': author,
        'section': section,
    })


class CategoryPostListView(ListView):
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 3

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['cat_slug'])
        return Post.published.filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['section'] = 'blog'
        return context


class AuthorPostListView(ListView):
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 3

    def get_queryset(self):
        self.author = get_object_or_404(User, username=self.kwargs['username'])
        return Post.published.filter(author=self.author)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['author'] = self.author
        context['section'] = 'blog'
        return context


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def post_detail(request, year, month, day, post):
    post_obj = get_object_or_404(
        Post,
        status='published',
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )

    all_comments = post_obj.comments.filter(active=True)
    comment_paginator = Paginator(all_comments, 10)
    comment_page = request.GET.get('comment_page', 1)
    try:
        comments = comment_paginator.page(comment_page)
    except (EmptyPage, PageNotAnInteger):
        comments = comment_paginator.page(1)

    new_comment = None

    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post_obj
            if request.user.is_authenticated:
                new_comment.user = request.user
                new_comment.name = request.user.get_full_name() or request.user.username
                new_comment.email = request.user.email
            new_comment.save()
            _notify_author_new_comment(post_obj, new_comment)
            messages.success(request, 'Komentarz dodany — czeka na moderację.')
            return redirect(post_obj.get_absolute_url())
    else:
        comment_form = CommentForm()

    post_tags_ids = post_obj.tags.values_list('id', flat=True)
    similar_posts = (
        Post.published
        .filter(tags__in=post_tags_ids)
        .exclude(id=post_obj.id)
        .annotate(same_tags=Count('tags'))
        .order_by('-same_tags', '-publish')[:4]
    )

    session_key = f'viewed_post_{post_obj.id}'
    if not request.session.get(session_key):
        Post.objects.filter(id=post_obj.id).update(views_count=db_models.F('views_count') + 1)
        request.session[session_key] = True
        post_obj.views_count += 1

    user_liked = post_obj.reactions.filter(user=request.user).exists() if request.user.is_authenticated else False
    user_bookmarked = post_obj.bookmarks.filter(user=request.user).exists() if request.user.is_authenticated else False

    return render(request, 'blog/post_detail.html', {
        'post': post_obj,
        'comments': comments,
        'new_comment': new_comment,
        'comment_form': comment_form,
        'similar_posts': similar_posts,
        'section': 'blog',
        'user_liked': user_liked,
        'user_bookmarked': user_bookmarked,
    })


def _notify_author_new_comment(post, comment):
    if getattr(django_settings, 'DEMO_MODE', False):
        return
    try:
        author = post.author
        if not author.email:
            return
        profile = getattr(author, 'profile', None)
        if profile and not getattr(profile, 'notify_comments', True):
            return
        subject = f'Nowy komentarz do: {post.title}'
        message = (
            f'Hej {author.get_full_name() or author.username},\n\n'
            f'{comment.name} skomentował(a) Twój post "{post.title}":\n\n'
            f'{comment.body}\n\n'
            f'Przejdź do posta:\n{getattr(django_settings, "SITE_URL", "").rstrip("/")}{post.get_absolute_url()}'
        )
        send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [author.email], fail_silently=True)
    except Exception:
        pass


def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            if getattr(django_settings, 'DEMO_MODE', False):
                messages.info(request, 'Tryb demo — wysyłanie emaili jest wyłączone.')
                return render(request, 'blog/post_share.html', {
                    'post': post, 'form': form, 'sent': False, 'section': 'blog',
                })
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f'{cd["name"]} ({cd["email"]}) poleca: "{post.title}"'
            message = (
                f'Przeczytaj post "{post.title}" na:\n{post_url}\n\n'
                f'Komentarz od {cd["name"]}:\n{cd["comments"]}'
            )
            try:
                send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [cd['to']])
                sent = True
            except Exception:
                messages.error(request, 'Nie udało się wysłać e-maila. Spróbuj ponownie później.')
    else:
        form = EmailPostForm()

    return render(request, 'blog/post_share.html', {
        'post': post,
        'form': form,
        'sent': sent,
        'section': 'blog',
    })


def post_search(request):
    form = SearchForm()
    results = []
    query = None

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.published.filter(
                Q(title__icontains=query)
                | Q(body__icontains=query)
                | Q(excerpt__icontains=query)
            ).distinct()

    return render(request, 'blog/post_search.html', {
        'form': form,
        'query': query,
        'results': results,
        'section': 'search',
    })


@login_required
@require_POST
def toggle_reaction(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    reaction, created = PostReaction.objects.get_or_create(post=post, user=request.user)
    if not created:
        reaction.delete()
        liked = False
    else:
        liked = True
    count = post.reactions.count()
    return JsonResponse({'liked': liked, 'count': count})


@login_required
@require_POST
def toggle_bookmark(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
    if not created:
        bookmark.delete()
        saved = False
    else:
        saved = True
    return JsonResponse({'saved': saved})


@login_required
def bookmark_list(request):
    bookmarks = Bookmark.objects.filter(user=request.user).select_related('post', 'post__author', 'post__category')
    return render(request, 'blog/bookmark_list.html', {'bookmarks': bookmarks, 'section': 'bookmarks'})


@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def newsletter_subscribe(request):
    if request.method == 'POST':
        if getattr(django_settings, 'DEMO_MODE', False):
            messages.info(request, 'Tryb demo — wysyłanie emaili jest wyłączone.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        email = request.POST.get('email', '').strip()
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Nieprawidłowy adres e-mail.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        sub, created = Subscriber.objects.get_or_create(email=email)
        if created or not sub.confirmed:
            _send_newsletter_confirm(request, sub)
            messages.success(request, 'Sprawdź skrzynkę i potwierdź subskrypcję.')
        else:
            messages.info(request, 'Ten adres jest już zapisany.')
        return redirect(request.META.get('HTTP_REFERER', '/'))
    return redirect('blog:post_list')


def newsletter_confirm(request, token):
    sub = get_object_or_404(Subscriber, token=token)
    sub.confirmed = True
    sub.save()
    messages.success(request, 'Subskrypcja potwierdzona!')
    return redirect('blog:post_list')


def newsletter_unsubscribe(request, token):
    sub = get_object_or_404(Subscriber, token=token)
    sub.delete()
    messages.success(request, 'Wypisano z newslettera.')
    return redirect('blog:post_list')


def _send_newsletter_confirm(request, subscriber):
    site_url = getattr(django_settings, 'SITE_URL', '').rstrip('/')
    confirm_url = f'{site_url}{reverse("blog:newsletter_confirm", args=[subscriber.token])}'
    try:
        send_mail(
            'Potwierdź subskrypcję DevLog',
            f'Kliknij link, by potwierdzić:\n{confirm_url}',
            django_settings.DEFAULT_FROM_EMAIL,
            [subscriber.email],
        )
        logger.info('Newsletter confirm sent to %s', subscriber.email)
    except Exception as exc:
        logger.error('Newsletter confirm failed for %s: %s', subscriber.email, exc)


@login_required
def author_post_list(request):
    if request.user.is_staff:
        posts = Post.objects.all().order_by('-publish')
    else:
        posts = Post.objects.filter(author=request.user).order_by('-publish')
    return render(request, 'blog/author_post_list.html', {
        'posts': posts, 'section': 'blog', 'is_moderator': request.user.is_staff,
    })


@login_required
def author_post_new(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()
            messages.success(request, 'Post zapisany.')
            return redirect('blog:author_post_list')
    else:
        form = PostForm()
    return render(request, 'blog/author_post_form.html', {'form': form, 'action': 'Nowy post'})


@login_required
def author_post_edit(request, slug):
    if request.user.is_staff:
        post = get_object_or_404(Post, slug=slug)
    else:
        post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post zaktualizowany.')
            return redirect('blog:author_post_list')
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/author_post_form.html', {'form': form, 'post': post, 'action': 'Edytuj post'})


@login_required
def author_post_delete(request, slug):
    if request.user.is_staff:
        post = get_object_or_404(Post, slug=slug)
    else:
        post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post usunięty.')
        return redirect('blog:author_post_list')
    return render(request, 'blog/author_post_confirm_delete.html', {'post': post})
