from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404

from apps.blog.models import Category, Post


class LatestPostsFeed(Feed):
    title = "DevLog - Cykl tworzenia aplikacji webowej"
    link = "/"
    description = "Najnowsze wpisy o tworzeniu aplikacji webowych"

    def items(self):
        return Post.published.order_by('-publish')[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.body[:200]

    def item_pubdate(self, item):
        return item.publish

    def item_author_name(self, item):
        return item.author.get_full_name() or item.author.username


class CategoryFeed(Feed):
    def get_object(self, request, cat_slug):
        return get_object_or_404(Category, slug=cat_slug)

    def title(self, obj):
        return f"DevLog - kategoria: {obj.name}"

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return f"Posty w kategorii {obj.name}"

    def items(self, obj):
        return Post.published.filter(category=obj).order_by('-publish')[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.body[:200]

    def item_pubdate(self, item):
        return item.publish
