from django.urls import path

from . import views
from .feeds import CategoryFeed, LatestPostsFeed

app_name = 'blog'

urlpatterns = [
    path('', views.PostListView.as_view(), name='post_list'),
    path('search/', views.post_search, name='post_search'),
    path('tag/<slug:tag_slug>/', views.post_list_by_tag, name='post_list_by_tag'),
    path('category/<slug:cat_slug>/', views.CategoryPostListView.as_view(), name='post_list_by_category'),
    path('author/posts/', views.author_post_list, name='author_post_list'),
    path('author/posts/new/', views.author_post_new, name='author_post_new'),
    path('author/posts/<slug:slug>/edit/', views.author_post_edit, name='author_post_edit'),
    path('author/posts/<slug:slug>/delete/', views.author_post_delete, name='author_post_delete'),
    path('author/<str:username>/', views.AuthorPostListView.as_view(), name='post_list_by_author'),
    path(
        '<int:year>/<int:month>/<int:day>/<slug:post>/',
        views.post_detail,
        name='post_detail',
    ),
    path('<int:post_id>/share/', views.post_share, name='post_share'),
    path('posts/<int:post_id>/react/', views.toggle_reaction, name='toggle_reaction'),
    path('posts/<int:post_id>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('bookmarks/', views.bookmark_list, name='bookmark_list'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/confirm/<uuid:token>/', views.newsletter_confirm, name='newsletter_confirm'),
    path('newsletter/unsubscribe/<uuid:token>/', views.newsletter_unsubscribe, name='newsletter_unsubscribe'),
    path('feed/', LatestPostsFeed(), name='post_feed'),
    path('feed/category/<slug:cat_slug>/', CategoryFeed(), name='category_feed'),
]
