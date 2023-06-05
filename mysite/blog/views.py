from django.shortcuts import render, get_object_or_404
from taggit.models import Tag
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm, SearchForm
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.contrib.postgres.search import SearchVector

class PostlistView(ListView):
    '''Альтернативное представление списка постов'''

    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'



def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])

    # постраничная разбивка с 3 постами на страницу
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)

    try :
        posts = paginator.page(page_number)

    except EmptyPage:  #  Если page_number находится вне диапазона то выдать последнюю страницу
        posts = paginator.page(paginator.num_pages)

    except PageNotAnInteger:  # Если page_number не int то выдай 1ю стр
        posts = paginator.page(1)


    return render(request,
                 'blog/post/list.html',
                 {'posts': posts,
                  'tag': tag})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                             status=Post.Status.PUBLISHED,
                             slug=post,
                             publish__year=year,
                             publish__month=month,
                             publish__day=day,
                             )
    # Список активных комментариев к посту
    comments = post.comments.filter(active= True)
    # Форма комментирования пользователями
    form = CommentForm()

    # Список схожих постов
    post_tags_ids = post.tags.values_list('id', flat=True)  # про flat смотри стр 143
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]
    return render(request,
                  'blog/post/detail.html',
                  {'post': post,
                  'comments': comments,
                   'form': form,
                   'similar_posts': similar_posts}
                  )


def post_share(request, post_id):  # Извлечь пост по идентификатору id
    post = get_object_or_404(Post,
                             id=post_id,
                             status=Post.Status.PUBLISHED)
    sent = False
    if request.method == 'POST':  # Форма была передана на обработку
        form = EmailPostForm(request.POST)
        if form.is_valid():  # Поля формы успешно прошли валидацию
            cd = form.cleaned_data
            # print(cd)  # {'name': 'san', 'email': 'sangrits88@gmail.com', 'to': 'isanek88@gmail.com', 'comments': 'Test share post'}
            post_url = request.build_absolute_uri(post.get_absolute_url())
            # print(post_url)
            subject = f"{cd['name']} recommends you read" \
            f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n" \
            f"{cd['name']}\'s comments: {cd['comments']}"
            send_mail(subject, message, 'sangrits88@gmail.com', [cd['to']])
            sent = True
    # ... отправить электронное письмо
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post,
                                                    'form': form, 'sent': sent})


@require_POST  # этот декаратор требует чтобы метод был только POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    comment = None
    # Комментарий был отправлен
    form = CommentForm(data=request.POST)  # извлекаем из запроса PoST  его данные (имя, текст, почта)
    if form.is_valid():  #  Создать объект класса Comment, не сохраняя его в базе данных
        comment = form.save(commit=False)
        # Назначить пост комментарию
        comment.post = post
        # Сохранить комментарий в бд
        comment.save()
    return render(request, 'blog/post/comment.html',
                  {'post': post,
                   'form': form,
                   'comment': comment})


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data['query']
        results = Post.published.annotate(
            search=SearchVector('title', 'body')
        ).filter(search=query)

    return render(request,
                  'blog/post/search.html',
                  {'form': form,
                   'query': query,
                   'results': results})
