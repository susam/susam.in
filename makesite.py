#!/usr/bin/env python3

# Copyright (c) 2018-2020 Susam Pal
# Licensed under the terms of the MIT License.

# This software is a derivative of the original makesite.py.
# The license text of the original makesite.py is included below.

# The MIT License (MIT)
#
# Copyright (c) 2018 Sunaina Pai
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


"""Make static website/blog with Python."""


import os
import shutil
import re
import glob
import sys
import json
import datetime
import collections


def fread(filename):
    """Read file and close the file."""
    with open(filename, 'r') as f:
        return f.read()


def fwrite(filename, text):
    """Write content to file and close the file."""
    basedir = os.path.dirname(filename)
    if not os.path.isdir(basedir):
        os.makedirs(basedir)

    with open(filename, 'w') as f:
        f.write(text)


def log(msg, *args):
    """Log message with specified arguments."""
    sys.stderr.write(msg.format(*args) + '\n')


def truncate(text, words=25):
    """Remove tags and truncate text to the specified number of words."""
    text = re.sub(r'(?s)<h[1-6].*?>(.*?)</h[1-6]>', '', text)
    text = re.sub(r'(?s)\\\(|\\\)|\\[|\\]|\\begin{.*?}|\\end{.*?}', '', text)
    text = re.sub(r'(?s)<.*?>', '', text)
    text = re.sub(r'(?s)\\[a-z]*?{(.*?)}', r'\1', text)
    text = ' '.join(text.split()[:words])
    return text


# Regular expressions to parse headers in post and comment files.
_HEADER_RE = r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*'
_HEADER_TEXT_RE = _HEADER_RE + '|.+'
_HEADER_RE = re.compile(_HEADER_RE)
_HEADER_TEXT_RE = re.compile(_HEADER_TEXT_RE)


def read_headers(text, pos=0):
    """Parse headers in text and yield (key, value, end-index) tuples."""
    for match in _HEADER_TEXT_RE.finditer(text, pos):
        if not match.group(1):
            break
        yield match.group(1), match.group(2), match.end()


def rfc_2822_format(date_str):
    """Convert yyyy-mm-dd date string to RFC 2822 format date string."""
    d = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    return d.strftime('%a, %d %b %Y %H:%M:%S +0000')


def simple_date(date_str):
    """Convert yyyy-mm-dd date string to simple date string."""
    try:
        d = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return d.strftime('%d %b %Y')
    except ValueError:
        d = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
        d = d.astimezone(tz=datetime.timezone.utc)
        return d.strftime('%d %b %Y %I:%M %p GMT')


def read_content(filename):
    """Read content and metadata from file into a dictionary."""
    # Read file content.
    text = fread(filename)

    # Read metadata and save it in a dictionary.
    date_slug = os.path.basename(filename).split('.')[0]
    match = re.search('^(?:(\d\d\d\d-\d\d-\d\d)-)?(.+)$', date_slug)
    content = {
        'date': match.group(1) or '1970-01-01',
        'slug': match.group(2),
    }

    # Read headers.
    end = 0
    for key, val, end in read_headers(text):
        content[key] = val

    # Separate content from headers.
    text = text[end:]

    # Convert Markdown content to HTML.
    if filename.endswith(('.md', '.mkd', '.mkdn', '.mdown', '.markdown')):
        try:
            if _test == 'ImportError':
                raise ImportError('Error forced by test')
            import CommonMark
            text = CommonMark.commonmark(text)
        except ImportError as e:
            log('WARNING: Cannot render Markdown in {}: {}', filename, str(e))

    # Update the dictionary with content and RFC 2822 date.
    content.update({
        'content': text,
        'rfc_2822_date': rfc_2822_format(content['date']),
        'simple_date': simple_date(content['date'])
    })

    return content


def read_files(src):
    """Read all posts into a list."""
    items = []
    for src_path in glob.glob(src):
        content = read_content(src_path)
        content['basename'] = os.path.basename(src_path)
        content['title'] = content['content'].splitlines()[0]
        items.append(content)
    return items


def render(template, **params):
    """Replace placeholders in template with values from params."""
    return re.sub(r'{{\s*([^}\s]+)\s*}}',
                  lambda match: str(params.get(match.group(1), match.group(0))),
                  template)


def head_content(import_header, root):
    tokens = [x.strip() for x in import_header.split()]
    imports = []
    for token in tokens:
        if token.endswith('.js'):
            code = ('  <script src="{}js/{}"></script>'
                    .format(root, token))
        elif token.endswith('.css'):
            code = ('  <link rel="stylesheet" href="{}css/{}">'
                    .format(root, token))
        else:
            raise ValueError('Unknown import type {!r} in {!r}'
                             .format(token, import_header))
        imports.append(code)
    return '\n' + '\n'.join(imports)


def set_canonical_url(params, dst_path):
    clean_path = dst_path.replace('_site/', '').replace('index.html', '')
    params['canonical_url'] = params['site_url'] + clean_path


def make_pages(src, dst, layout, **params):
    """Generate pages from page content."""
    items = []

    for src_path in glob.glob(src):
        content = read_content(src_path)

        # Invoke callback if registered.
        if 'callback' in params:
            params['callback'](content)

        page_params = dict(params, **content)

        # Populate placeholders in content if content-rendering is enabled.
        if page_params.get('render') == 'yes':
            rendered_content = render(page_params['content'], **page_params)
            page_params['content'] = rendered_content
            content['content'] = rendered_content

        # Add imports if importing is requested.
        if 'import' in page_params:
            page_params['imports'] = head_content(page_params['import'],
                                                  page_params['root'])

        items.append(content)

        dst_path = render(dst, **page_params)
        set_canonical_url(page_params, dst_path)
        output = render(layout, **page_params)

        log('Rendering {} => {} ...', content['slug'], dst_path)
        fwrite(dst_path, output)

    return sorted(items, key=lambda x: x['date'], reverse=True)


def make_list(posts, dst, list_layout, item_layout, **params):
    """Generate list page for a blog."""
    items = []
    for post in posts:
        # Invoke callback if registered.
        if 'callback' in params:
            params['callback'](post)
        item_params = dict(params, **post)
        item_params['summary'] = truncate(post['content'])
        item = render(item_layout, **item_params)
        items.append(item)

    count = len(posts)
    params['content'] = ''.join(items)
    params['count'] = count
    params['post_label'] = 'post' if count == 1 else 'posts'
    if 'import' in params:
        params['imports'] = head_content(params['import'], params['root'])

    dst_path = render(dst, **params)
    set_canonical_url(params, dst_path)
    output = render(list_layout, **params)

    log('Rendering list => {} ...', dst_path)
    fwrite(dst_path, output)


def make_tags(posts, dst,
              tags_layout, tagh_layout, tagl_layout,
              item_layout, **params):
    """Generate tags page for a blog."""
    tag_map = collections.defaultdict(list)
    for post in posts:
        item_params = dict(params, **post)
        item = render(item_layout, **item_params)
        tag = post['tag']
        tag_map[tag].append(item)

    tag_tuples = []
    for tag, items in tag_map.items():
        tag_tuples.append((len(items), tag, items))
    tag_tuples.sort(reverse=True)

    header = []
    content = []
    for count, tag, items in tag_tuples:
        params['content'] = ''.join(items)
        params['tag'] = tag
        params['count'] = count
        params['post_label'] = 'post' if count == 1 else 'posts'
        params['tag_title'] = tag.title()
        dst_path = render(dst, **params)
        header.append(render(tagh_layout, **params))
        content.append(render(tagl_layout, **params))

    params['header'] = ''.join(header)
    params['content'] = ''.join(content)
    set_canonical_url(params, dst_path)

    log('Rendering list => {} ...', dst_path)
    fwrite(dst_path, render(tags_layout, **params))


def make_blog(src, page_layout, **params):
    """Generate blog."""
    post_layout = fread('layout/blog/post.html')
    list_layout = fread('layout/blog/list.html')
    tags_layout = fread('layout/blog/tags.html')
    tagh_layout = fread('layout/blog/tagh.html')
    tagl_layout = fread('layout/blog/tagl.html')
    item_layout = fread('layout/blog/item.html')
    feed_xml = fread('layout/blog/feed.xml')
    item_xml = fread('layout/blog/item.xml')

    blog_root = params['root']
    post_root = blog_root + '../'

    # Combine layouts to form final layouts.
    post_layout = render(page_layout, content=post_layout)
    list_layout = render(page_layout, content=list_layout)
    tags_layout = render(page_layout, content=tags_layout)

    # Read all posts.
    params['root'] = post_root
    posts = make_pages(src, '_site/blog/{{ slug }}/index.html',
                       post_layout, blog='blog', render='yes', **params)
    listed_posts = [post for post in posts if post.get('list') != 'no']

    # Create blog list page as the home page.
    params['root'] = './'
    make_list(listed_posts, '_site/index.html',
              list_layout, item_layout,
              blog='blog', title="Susam's Blog", **params)

    # Create tag list page as the blog page.
    params['root'] = blog_root
    make_tags(listed_posts, '_site/blog/index.html',
              tags_layout, tagh_layout, tagl_layout, item_layout,
              blog='blog', title="Susam's Blog", **params)

    # Create RSS feeds.
    make_list(listed_posts, '_site/blog/rss.xml',
              feed_xml, item_xml,
              blog='blog', title="Susam's Blog", **params)

    return posts


# Comments
# ========
def read_comment(text, pos):
    """Read a single comment from a comment file."""
    content = {}

    # Read headers.
    end = pos
    for key, val, end in read_headers(text, pos):
        content[key] = val

    # Select content until next header (if any).
    match = _HEADER_RE.search(text, end)
    if match:
        next_pos = match.start()
        text = text[end:next_pos]
    else:
        next_pos = -1
        text = text[end:]

    # Determine commenter and commenter type.
    commenter = content['name']
    if 'url' in content:
        commenter = '<a href="{}">{}</a>'.format(content['url'], commenter)
    commenter_type = 'author' if content['name'] == 'Susam Pal' else 'guest'

    # Update dictionary with content.
    content.update({
        'commenter': commenter,
        'commenter_type': commenter_type,
        'content': text,
        'simple_date': simple_date(content['date'])
    })
    return content, next_pos


def read_post_comments(filename):
    """Read a list of comments from a comment file."""
    # Read file content.
    text = fread(filename)

    # Read metadata and save it in a dictionary.
    date_slug = os.path.basename(filename).split('.')[0]
    match = re.search('^(?:(\d\d\d\d-\d\d-\d\d)-)?(.+)$', date_slug)
    post_comments = []

    next_pos = 0
    while next_pos != -1:
        comment, next_pos = read_comment(text, next_pos)
        post_comments.append(comment)

    slug = match.group(2)
    return slug, sorted(post_comments, key=lambda x: x['date'])


def make_comment_list(post, comments, dst,
                      list_layout, item_layout, **params):
    """Generate a comment page with a list of rendered comments."""
    slug = post['slug']

    count = len(comments)

    items = []
    for index, comment in enumerate(comments, 1):
        item_params = dict(params, index=index, **comment)
        item_params['count'] = count
        item_params['comment_label'] = 'comment' if count == 1 else 'comments'
        item_params['retrieved'] = ''
        source_url = item_params.get('source')
        if source_url is not None:
            item_params['retrieved'] = (
                '<div class="meta">(Retrieved from <a href="{}">{}</a>)</div>'
                .format(source_url, source_url)
            )
        item = render(item_layout, **item_params)
        items.append(item)

    title = 'Comments on ' + post['title']
    params['content'] = ''.join(items)
    params['slug'] = slug
    params['title'] = title
    params['post_title'] = post['title']
    dst_path = render(dst, **params)
    set_canonical_url(params, dst_path)

    # Inherit imports from post.
    import_value = 'comment.css ' + post.get('import', '')
    params['imports'] = head_content(import_value, params['root'])

    log('Rendering {} => {} ...', slug, dst_path)
    output = render(list_layout, **params)
    fwrite(dst_path, output)


def make_comments_none(post, dst, none_layout, **params):
    """Generate a comment page with no comments."""
    slug = post['slug']
    title = 'Comments on ' + post['title']

    params['slug'] = slug
    params['title'] = title
    params['post_title'] = post['title']

    dst_path = render(dst, **params)
    set_canonical_url(params, dst_path)

    log('Rendering {} => {} ...', slug, dst_path)
    output = render(none_layout, **params)
    fwrite(dst_path, output)


def make_comments(src, posts, page_layout, **params):
    """Generate comment list pages."""
    none_layout = fread('layout/comments/none.html')
    list_layout = fread('layout/comments/list.html')
    item_layout = fread('layout/comments/item.html')
    none_layout = render(page_layout, content=none_layout)
    list_layout = render(page_layout, content=list_layout)
    dst = '_site/{{ blog }}/{{ slug }}/comments/index.html'

    # Read all comments.
    comment_map = {}
    for src_path in glob.glob(src):
        slug, post_comments = read_post_comments(src_path)
        comment_map[slug] = post_comments

    # For each post, render comment list page or no comments page.
    for post in posts:
        slug = post['slug']
        if slug in comment_map:
            make_comment_list(post, comment_map[slug], dst,
                              list_layout, item_layout, blog='blog', **params)
        else:
            make_comments_none(post, dst, none_layout, blog='blog', **params)



_SECTION_RE = re.compile('\s*<!--\s*(note|quote)\s*-->\s*')


def set_parsed_reading_content(post):
    """Parse reading content into quotes and notes."""
    begin = -1
    for match in _SECTION_RE.finditer(post['content']):
        end = match.start()
        if begin != -1:
            if kind not in post:
                post[kind] = []
            post[kind].append(post['content'][begin:end] + '\n')
        kind = match.group(1)
        begin = match.end()

    if begin != -1:
        if kind not in post:
            post[kind] = []
        post[kind].append(post['content'][begin:])


def set_reading_extra_meta(post):
    """Populate extra meta data to be rendered for reading posts."""
    key_attrs = collections.OrderedDict({
        'pdf': 'PDF',
        'url': 'url',
    })
    extra = []
    for key, key_label in key_attrs.items():
        url = post.get(key)
        if url is not None:
            extra.append(' [<a href="{}" class="basic">{}</a>]'
                         .format(url, key_label))
    post['extra'] = ''.join(extra)


def make_reading(src, page_layout, **params):
    """Generate reading listing."""
    tag_attrs = collections.OrderedDict({
        # tag: (title, singular_label, plural_label)
        'non-fiction': ('Non-Fiction', 'book', 'books'),
        'technical': ('Technical', 'book', 'books'),
        'textbook': ('Textbooks', 'book', 'books'),
        'paper': ('Papers', 'paper', 'papers'),
        'fiction': ('Fiction', 'book', 'books'),
    })
    # Read file content.
    read_layout = fread('layout/reading/read.html')
    tagl_layout = fread('layout/reading/tagl.html')
    item_layout = fread('layout/reading/tagi.html')
    tocl_layout = fread('layout/reading/tocl.html')
    toci_layout = fread('layout/reading/toci.html')
    read_layout = render(page_layout, content=read_layout)

    tag_map = collections.defaultdict(list)
    for src_path in glob.glob(src):
        post = read_content(src_path)
        set_parsed_reading_content(post)
        set_reading_extra_meta(post)
        tag = post['tag']
        if tag not in tag_attrs:
            msg = 'Unknown tag {!r} in {}'.format(tag, src_path)
            raise ValueError(msg)
        tag_map[tag].append(post)

    toc_list = []
    tag_list = []

    for tag, (tag_title, singular_label, plural_label) in tag_attrs.items():
        # Ignore tags with no posts.
        count = len(tag_map[tag])
        if count == 0:
            continue

        tag_params = dict(params)
        tag_params['tag'] = tag
        tag_params['tag_title'] = tag.title()
        tag_params['count'] = count
        tag_params['tag_label'] = (singular_label if count == 1 else
                                   plural_label)

        toc_items = []
        tag_items = []

        posts = tag_map[tag]
        posts = sorted(posts, key=lambda x: x['date'], reverse=True)

        for post in posts:
            item_params = dict(params, **post)
            quotes = ['<blockquote>\n{}</blockquote>\n'.format(quote)
                      for quote in post['quote']]
            item_params['quotes'] = ''.join(quotes)
            item_params['notes'] = ''.join(post['note'])
            item_params['quote_title'] = ('An Excerpt' if len(quotes) == 1 else
                                          'Some Excerpts')
            tag_items.append(render(item_layout, **item_params))
            toc_items.append(render(toci_layout, **item_params))

        toc_list.append(render(tocl_layout, content=''.join(toc_items), **tag_params))
        tag_list.append(render(tagl_layout, content=''.join(tag_items), **tag_params))

    read_params = dict(params)
    read_params['content'] = ''.join(tag_list)
    read_params['toc'] = ''.join(toc_list)
    read_params['imports'] = head_content('reading.css tex.js', params['root'])

    dst_path = '_site/reading/index.html'
    set_canonical_url(read_params, dst_path)
    output = render(read_layout, title='My Reading Log', **read_params)
    fwrite(dst_path, output)


# Other Sections
# ==============
def make_text_dir(src, page_layout, **params):
    """Generate directory listing."""
    path = '/'.join(src.split('/')[1:-1]) # static/dir/topic/*.txt => dir/topic
    topic = path.split('/')[-1] # dir/topic => topic
    list_layout = fread('layout/textdir/list.html')
    item_layout = fread('layout/textdir/item.html')
    list_layout = render(page_layout, content=list_layout)
    file_list = read_files(src)
    file_list = sorted(file_list, key=lambda x: x['basename'], reverse=True)
    title = topic.title() + ' Files'
    dir_params = dict(params)
    dir_params['import'] = 'extra.css'
    make_list(file_list, '_site/' + path + '/index.html',
              list_layout, item_layout, title=title, dirname=path,
              **dir_params)


def make_music(src, page_layout, **params):
    """Generate music listing."""
    list_layout = fread('layout/music/list.html')
    post_layout = fread('layout/music/post.html')
    item_layout = fread('layout/music/item.html')
    widget_layout = fread('layout/music/widget.html')
    list_layout = render(page_layout, content=list_layout)
    post_layout = render(page_layout, content=post_layout)

    def make_widget(content):
        widget_params = dict(music_params, **content)
        widget = render(widget_layout, **widget_params)
        content['widget'] = widget

    music_params = dict(params)
    music_params['import'] = 'music.css'
    music_params['root'] = params['root'] + '../'
    posts = make_pages(src,
                       '_site/music/{{ slug }}/index.html',
                       post_layout, blog='music', render='yes',
                       callback=make_widget, **music_params)

    music_params['root'] = params['root']
    make_list(posts, '_site/music/index.html',
              list_layout, item_layout, blog='music', title='Music',
              **music_params, callback=make_widget)


def main():
    """Generate website."""
    # Create a new _site directory from scratch.
    if os.path.isdir('_site'):
        shutil.rmtree('_site')
    shutil.copytree('static', '_site')

    # Default parameters.
    params = {
        'base_path': '',
        'subtitle': ' - Susam Pal',
        'author': 'Susam Pal',
        'site_url': 'https://susam.in/',
        'current_year': datetime.datetime.now().year,
        'imports': '',
        'index': '',
    }

    # If params.json exists, load it.
    if os.path.isfile('params.json'):
        params.update(json.loads(fread('params.json')))

    page_layout = fread('layout/page.html')

    params['root'] = '../'
    make_pages('content/[!_]*.html', '_site/{{ slug }}/index.html',
               page_layout, render='yes', **params)

    # Blog.
    params['root'] = '../'
    posts = make_blog('content/blog/*.html', page_layout, **params)

    # Comments.
    params['root'] = '../../../'
    make_comments('content/comments/*.html', posts, page_layout, **params)

    # Music.
    params['root'] = '../'
    make_music('content/music/*.html', page_layout, **params)

    # Reading.
    params['root'] = '../'
    make_reading('content/reading/*.html', page_layout, **params)

    # Special directories.
    params['root'] = '../'
    make_text_dir('static/security/*.txt', page_layout, **params)
    make_text_dir('static/poetry/*.txt', page_layout, **params)

    #make_licenses('content/licenses/*.html', page_layout, **params)


# Test parameter to be set temporarily by unit tests.
_test = None


def checks():
    """Perform sanity checks."""
    log('Checking comment files ...')
    posts = glob.glob('content/blog/*.html')
    comments = glob.glob('content/comments/*.html')

    posts = set(os.path.basename(x) for x in posts)
    comments = set(os.path.basename(x) for x in comments)

    # For each comment file, there must exist a post file.
    for comment in comments:
        if comment not in posts:
            msg = 'Cannot find post for comment file ' + comment
            raise LookupError(msg)


if __name__ == '__main__':
    checks()
    main()
