from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin
from .models import Post, Category, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    fields = ('name', 'slug', 'description', 'color', 'meta_description')


@admin.register(Post)
class PostAdmin(MarkdownxModelAdmin):
    list_display = ('title', 'slug', 'category', 'author', 'publish', 'status', 'reading_time')
    list_filter = ('status', 'category', 'created', 'publish', 'author')
    search_fields = ('title', 'body', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    date_hierarchy = 'publish'
    ordering = ('status', 'publish')
    fieldsets = (
        ('Treść', {'fields': ('title', 'slug', 'author', 'category', 'body', 'excerpt', 'cover_image', 'cover_image_alt', 'tags', 'status', 'publish')}),
        ('SEO', {'fields': ('meta_description', 'meta_keywords', 'canonical_url'), 'classes': ('collapse',)}),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'post', 'created', 'active')
    list_filter = ('active', 'created', 'updated')
    search_fields = ('name', 'email', 'body')
