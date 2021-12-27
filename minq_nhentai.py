#! /usr/bin/env python3

# TODO
# include recommended hentai
# automatically download hole hentai
# cache metadata
# typo check in menus
# add most popular
# add search by name
# add search by author
# TODO MBY
# implement normal menu mechanism
# fetch tags from https://nhentai.net/tags/
# check for internet connection

import argparse
import requests
import bs4 # sudo pacman -S --needed python-beautifulsoup4
import shlex
import subprocess
import os
import sys
import io
import time
import threading

CACHE_DIR = os.path.expanduser(r'~/.cache/minq_nhentai/')
SETTINGS_DIR = os.path.expanduser(r'~/.config/minq_nhentai/')
HENTAIS_DIR = CACHE_DIR + r'hentai_sources/'

NET_TOO_MANY_REQUESTS_SLEEP = 3
WAIT_FOR_PAGE_DOWNLOAD_SLEEP = 0.2

URL_PAGE_POSTFIX = r'?page={page}'
URL_INDEX = r'https://nhentai.net/'
URL_PAGE = URL_INDEX + r'?page={page}'
URL_READ = URL_INDEX + r'g/{id}/{page}/'
URL_TAG = URL_INDEX + r'tag/{tag}/'
URL_LANG = URL_INDEX + r'language/{lang}/'

SOUP_PARSER = 'lxml'

THUMB_NAME = 'thumb'
DONE_POSTFIX = '.done'

class PageNotFoundException(Exception): pass

class Exception_net_page_not_found(Exception): pass
class Exception_net_unknown(Exception): pass

class Hentai:
    def __init__(s, id_, title, link, thumb, tags, languages, categories, pages, uploaded, parodies, characters, artists, groups):
        s.id_ = id_
        s.title = title
        s.link = link
        s.thumb_url = thumb
        s.tags = tags
        s.languages = languages
        s.categories = categories
        s.pages = pages
        s.uploaded = uploaded
        s.parodies = parodies
        s.characters = characters
        s.artists = artists
        s.groups = groups

        s.stop_downloading_pages_in_background()

    def __eq__(s, other):
        return s.id_ == other.id_

    def image_path(s, img):
        path = HENTAIS_DIR + str(s.id_) + '/' + img
        dir_ = os.path.dirname(path)
        if not os.path.isdir(dir_):
            os.makedirs(dir_)
        return path

    def image_cached(s, img):
        path = s.image_path(img)
        done = path + DONE_POSTFIX
        return os.path.isfile(done)

    def image_set_cached(s, img):
        path = s.image_path(img)
        done = path + DONE_POSTFIX
        with open(done, 'w'): pass

    def image_unset_cached(s, img):
        path = s.image_path(img)
        done = path + DONE_POSTFIX
        if os.path.isfile(done):
            os.remove(done)

    def image_cache(s, url, img):
        s.image_unset_cached(img)
        data = receive_raw(url)
        with open(s.image_path(img), 'wb') as f: f.write(data)
        s.image_set_cached(img)

    def image_print(s, img):
        assert s.image_cached(img)
        path = s.image_path(img)
        cmd = shlex.join(['viu', path])
        output = subprocess.run(cmd, shell=True, check=True, capture_output=False)

    def image_print_cache(s, url, img):
        if not s.image_cached(img):
            s.image_cache(url, img)
        s.image_print(img)

    def show(s):
        print(f'Title: {s.title}')
        print(f'Pages: {s.pages}')
        print(s.link)
        for t in s.tags: print(t)
        for a in s.artists: print(a)
        for l in s.languages: print(l)
        s.print_thumb()

    def print_thumb(s):
        if not s.image_cached(THUMB_NAME):
            s.image_cache(s.thumb_url, THUMB_NAME)
        s.image_print(THUMB_NAME)

    def contains_tag(s, tag):
        for t in s.tags:
            if tag == t.name:
                return True
        return False

    def contains_language(s, lang):
        for l in s.languages:
            if lang == l.name:
                return True
        return False

    def start_downloading_pages_in_background(s):

        def download_all_pages():
            nonlocal s
            for page_num in range(1, s.pages+1):
                if s.downloading_pages_in_background == False:
                    break

                url = URL_READ.format(id=s.id_, page=page_num)
                data = receive(url)

                soup = bs4.BeautifulSoup(data, SOUP_PARSER)
                link = soup.find(id='image-container').img['src']
                s.image_cache(link, str(page_num))
            s.downloading_pages_in_background = False

        assert s.downloading_pages_in_background == False
        s.downloading_pages_in_background = True
        threading.Thread(target=download_all_pages).start()

    def stop_downloading_pages_in_background(s):
        s.downloading_pages_in_background = False

    def reading_loop(s):

        s.start_downloading_pages_in_background()

        CMDS = []
        CMDS.append(CMD_QUIT := ['quit', 'q', 'exit', 'e', 'back', 'b'])
        CMDS.append(CMD_NEXT := ['next page', 'next', 'n'])
        CMDS.append(CMD_PREV := ['prevoius page', 'prev', 'p'])
        CMDS.append(CMD_PAGE := ['go to page', 'page', 'go to', 'goto', 'go', 'g'])

        page_num = 1
        while page_num <= s.pages and page_num >= 1:

            if not s.image_cached(str(page_num)):
                print_tmp('Downloading...')
                try:
                    while not s.image_cached(str(page_num)):
                        time.sleep(WAIT_FOR_PAGE_DOWNLOAD_SLEEP)
                except KeyboardInterrupt:
                    break

            print(f'Page: {page_num} / {s.pages}')
            s.image_print(str(page_num))

            c = input('>> ', 'q')
            if c == '':
                c = CMD_NEXT[0]

            if c in CMD_QUIT:
                break
            elif c in CMD_NEXT:
                page_num += 1
            elif c in CMD_PREV:
                if page_num == 1:
                    alert("This is the first page")
                else:
                    page_num -= 1
            elif c in CMD_PAGE:
                page = input('Enter page number>> ', -1)
                if page == -1:
                    continue
                try:
                    page = int(page)
                except ValueError:
                    alert(f'Not a valid number: {page}')
                    continue
                if page < 1 or page > s.pages:
                    alert(f'Invalid page: {page} (must be between 0 and {s.pages})')
                    continue
                page_num = page
            else:
                print(f'Unknown command: {c}')
                print('List of available commands:')
                for item in CMDS:
                    print(f'->{item}')
                alert()

        s.stop_downloading_pages_in_background()

class Tag:
    prefix = 'Tag'
    def __init__(s, name, link, count):
        s.name = name
        s.link = link
        s.count = count
    def __repr__(s):
        return f'-> {s.prefix}: {s.name} ({s.count}) {s.link}'
class Language(Tag): prefix = 'Language'
class Category(Tag): prefix = 'Category'
class Parody(Tag): prefix = 'Parody'
class Character(Tag): prefix = 'Character'
class Artist(Tag): prefix = 'Artist'
class Group(Tag): prefix = 'Group'

_input = input
def input(msg, if_interrupted):
    try:
        return _input(msg)
    except KeyboardInterrupt:
        return if_interrupted

_print = print
_print_tmp_last_msg = ''
_print_tmp_last_count = 1
_print_tmp_last_len = 0
_print_tmp_lock = threading.Lock()
def print(*a, **kw):
    _print_tmp_lock.acquire()
    global _print_tmp_last_msg
    global _print_tmp_last_count
    global _print_tmp_last_len
    fake_stdout = io.StringIO()
    file_bak = kw['file'] if 'file' in kw else None
    _print(*a, **kw, file=fake_stdout)
    if file_bak != None: kw['file'] = file_bak
    out = fake_stdout.getvalue()
    l = len(out.split('\n')[0])
    if l < _print_tmp_last_len:
        _print(' '*_print_tmp_last_len, end='\r')
    _print_tmp_last_msg = ''
    _print_tmp_last_count = 1
    _print_tmp_last_len = 0
    _print(*a, **kw)
    _print_tmp_lock.release()
def print_tmp(msg):
    _print_tmp_lock.acquire()
    global _print_tmp_last_msg
    global _print_tmp_last_count
    global _print_tmp_last_len
    assert not '\n' in msg

    last_len = _print_tmp_last_len
    _print_tmp_last_len = len(msg)

    if msg == _print_tmp_last_msg:
        _print_tmp_last_count += 1
        _print(f'({_print_tmp_last_count}) ', end='')
        _print_tmp_last_len += 3 + len(str(_print_tmp_last_count))
    else:
        _print_tmp_last_count = 1

    _print_tmp_last_msg = msg

    _print(msg, end='')
    l = len(msg)
    if last_len > l:
        diff = last_len - l
        _print(' '*diff, end='')
    _print('\r', end='', flush=True)

    _print_tmp_lock.release()

def alert(msg=''):
    print(msg)
    input('PRESS ENTER TO CONITNUE', -1)

def image_cache(url, id_, img_name):
    data = receive_raw(url)
    path = HENTAIS_DIR + str(id_) + '/' + img_name, 'w'
    with open(path) as f: f.write(data)
    with open(path + DONE_POSTFIX, 'w'): pass

def receive_raw(url):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0'}
    page = requests.get(url, headers=headers)

    if page.ok:
        return page.content

    match (page.status_code, page.reason):
        case (404, 'Not Found'):
            raise Exception_net_page_not_found()
        case (429, 'Too Many Requests'):
            print_tmp(f'Too many requests, server refused connection, retrying in {NET_TOO_MANY_REQUESTS_SLEEP} seconds')
            time.sleep(NET_TOO_MANY_REQUESTS_SLEEP)
            return receive_raw(url)
        case _:
            raise Exception_net_unknown(f'{url} {page.status_code} {page.reason}')

    assert False

def receive(url):
    return receive_raw(url).decode()

def does_page_exist(url):
    try:
        receive(url)
    except Exception_net_page_not_found:
        return False
    return True

def scrape_tag_container(container):

    meta = container.text.strip().replace('\n','').replace('\t','')

    tag_counts = container.find(class_='tags').find_all(class_='count')
    tags = [t.parent for t in tag_counts]
    assert len(tag_counts) == len(tags)
    tag_names = [t.find(class_='name').text for t in tags]
    tag_counts = [t.find(class_='count').text for t in tags]

    tag_links = []
    for t in tags:
        link = t['href']
        if link.startswith('/'): link = link[1:]
        link = URL_INDEX + link
        tag_links.append(link)

    assert len(tags) == len(tag_names) == len(tag_counts) == len(tag_links)
    return meta, tag_names, tag_links, tag_counts

def scrape_hentais(url_page):
    page_num = 0
    while True:
        page_num += 1

        url = url_page.format(page=page_num)
        data = receive(url)

        soup = bs4.BeautifulSoup(data, SOUP_PARSER)

        container = soup.find(class_='container index-container')

        for hentai in container.find_all(class_='cover'):
            link = hentai['href']
            if link.endswith('/'): link = link[1:]
            link = URL_INDEX + link

            thumb_smol = hentai.find(class_='lazyload')['data-src']
            title = hentai.find(class_='caption').text

            id_ = link.split('/')[-2]
            id_ = int(id_)

            data = receive(link)
            soup = bs4.BeautifulSoup(data, SOUP_PARSER)

            thumb = soup.find(class_='lazyload')['data-src']

            more_like_this = soup.find(id='related-container') # TODO unfinished

            containers = soup.find_all(class_='tag-container field-name') + soup.find_all(class_='tag-container field-name hidden')
            tags = []
            languages = []
            categories = []
            parodies = []
            characters = []
            artists = []
            groups = []
            pages = None
            uploaded = None
            for container in containers:
                meta, n,l,c = scrape_tag_container(container)

                if meta.startswith('Pages:'):
                    pages = meta[len('Pages:'):]
                    pages = int(pages)
                elif meta.startswith('Uploaded:'): # TODO fix this
                    uploaded = meta[len('Uploaded:'):] + ' (this time is currently bugged)'
                else:

                    for n,l,c in zip(n,l,c):
                        if meta.startswith('Tags:'):
                            tags.append(Tag(n,l,c))
                        elif meta.startswith('Languages:'):
                            languages.append(Language(n,l,c))
                        elif meta.startswith('Categories:'):
                            categories.append(Category(n,l,c))
                        elif meta.startswith('Parodies:'):
                            parodies.append(Parody(n,l,c))
                        elif meta.startswith('Characters:'):
                            characters.append(Character(n,l,c))
                        elif meta.startswith('Artists:'):
                            artists.append(Artist(n,l,c))
                        elif meta.startswith('Groups:'):
                            groups.append(Group(n,l,c))
                        else:
                            assert False

            yield Hentai(id_, title, link, thumb, tags, languages, categories, pages, uploaded, parodies, characters, artists, groups)

def interactive_hentai_enjoyment(required_tags, required_language=None):

    CMDS = []
    CMDS.append(CMD_QUIT := ['quit', 'q', 'exit', 'e'])
    CMDS.append(CMD_NEXT := ['next hentai', 'next', 'n'])
    CMDS.append(CMD_PREV := ['previous hentai', 'previous', 'prev', 'p'])
    CMDS.append(CMD_READ := ['read hentai', 'read', 'r', 'enjoy', 'cum', 'wank', 'sex'])

    assert type(required_tags) in (list, tuple)
    assert type(required_language) in (str, type(None))

    for tag in required_tags:
        if not does_page_exist(URL_TAG.format(tag=tag)):
            print(f"Tag doesn't exist: {tag}")
            sys.exit(1)

    if len(required_tags) == 0:
        url_page = URL_INDEX
    else:
        url_page = URL_TAG.format(tag=required_tags[0]) + URL_PAGE_POSTFIX
        required_tags = required_tags[1:]

    if required_language != None:
        if not does_page_exist(URL_LANG.format(lang=required_language)):
            print(f"Language doesn't exist: {required_language}")
            sys.exit(1)

    running = True
    hentais = []
    ind = 0

    for hentai in scrape_hentais(url_page): # TODO what if ctrl+c is pressed here

        find_new_hentai = False

        for h in hentais:
            if h == hentai:
                find_new_hentai = 'duplicate'
                break

        for tag in required_tags:
            if not hentai.contains_tag(tag):
                find_new_hentai = f'missing tag: {tag}'
                break

        if required_language != None and not hentai.contains_language(required_language):
            find_new_hentai = 'missing langiage: {required_language}'

        if find_new_hentai:
            print_tmp(f'Hentai rejected (reason: {find_new_hentai}), searching for another one...')
            continue

        hentais.append(hentai)

        while running:

            if ind >= len(hentais):
                break
            hentai = hentais[ind]

            hentai.show()

        
            c = input('> ', CMD_QUIT[0])

            if c == '':
                c = CMD_NEXT[0]

            if c in CMD_QUIT:
                running = False
            elif c in CMD_NEXT:
                ind += 1
            elif c in CMD_PREV:
                ind -= 1
            elif c in CMD_READ:
                hentai.reading_loop()
            
            else:
                print(f'Unknown command: {c}')
                print('List of available commands:')
                for cmd in CMDS:
                    print(f'-> {cmd}')
                alert()

        else:
            break
            
def main():
    parser = argparse.ArgumentParser(description='Command line port of nhentai')
    parser.add_argument('--tags', nargs='+', help='Tags required for the hentai', default=[])
    parser.add_argument('--language', help='Tags required for the hentai')
    args = parser.parse_args()

    call_args = []

    call_args.append(args.tags)
    if args.language != None:
        call_args.append(args.language)

    interactive_hentai_enjoyment(*call_args)

if __name__ == '__main__':
    main()
