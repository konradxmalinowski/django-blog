from rest_framework import serializers
from django.contrib.auth.models import User
from taggit.serializers import TagListSerializerField, TaggitSerializer
from apps.blog.models import Post, Category, Comment


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'color']


class CommentSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    name  = serializers.CharField(max_length=80, required=False, default='')
    email = serializers.EmailField(required=False, default='')

    class Meta:
        model = Comment
        fields = ['id', 'user', 'name', 'email', 'body', 'created']
        read_only_fields = ['id', 'created', 'user']


class PostListSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    category = CategorySerializer(read_only=True)
    author = UserMiniSerializer(read_only=True)
    reading_bar = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'author', 'category', 'tags',
                  'excerpt', 'publish', 'reading_time', 'reading_bar', 'status']

    def get_reading_bar(self, obj):
        filled = min(obj.reading_time, 10)
        return '█' * filled + '░' * (10 - filled)


class PostDetailSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    category = CategorySerializer(read_only=True)
    author = UserMiniSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    similar_posts = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'author', 'category', 'tags',
                  'body', 'excerpt', 'publish', 'reading_time', 'status',
                  'comments', 'comments_count', 'similar_posts']

    def get_comments(self, obj):
        active = obj.comments.filter(active=True)
        return CommentSerializer(active, many=True).data

    def get_comments_count(self, obj):
        return obj.comments.filter(active=True).count()

    def get_similar_posts(self, obj):
        from django.db.models import Count
        ids = obj.tags.values_list('id', flat=True)
        similar = (
            Post.published.filter(tags__in=ids)
            .exclude(id=obj.id)
            .annotate(same_tags=Count('tags'))
            .order_by('-same_tags', '-publish')[:4]
        )
        return PostListSerializer(similar, many=True).data


class PostWriteSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField(required=False)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category',
        allow_null=True, required=False,
    )

    class Meta:
        model = Post
        fields = ['title', 'body', 'excerpt', 'category_id', 'tags', 'publish', 'status']

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        post = Post.objects.create(**validated_data)
        post.tags.set(tags)
        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance
