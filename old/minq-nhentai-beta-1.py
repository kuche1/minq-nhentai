#! /usr/bin/env python3

# TODO
# include recommended hentai
# typo check in menus
# add most popular
# allow running multiple instances
# add hentai blacklist
# TODO MBY
# implement normal menu mechanism
# fetch tags from https://nhentai.net/tags/

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
ms = __import__('minq-storage')

DEBUG = False
if DEBUG:
    sys.path.insert(0, '../minq-storage/minq-storage')
    ms = __import__('__init__')
    del sys.path[0]

NET_TOO_MANY_REQUESTS_SLEEP = 3
WAIT_FOR_PAGE_DOWNLOAD_SLEEP = 0.2

URL_PAGE_POSTFIX = r'page={page}'
URL_INDEX = r'https://nhentai.net/'
URL_SEARCH = URL_INDEX + r'search/?q={search}'
URL_READ = URL_INDEX + r'g/{id}/{page}/'
URL_TAG = URL_INDEX + r'tag/{tag}/'
URL_LANG = URL_INDEX + r'language/{lang}/'
URL_ARTIST = URL_INDEX + r'artist/{artist}/'

SOUP_PARSER = 'lxml'

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

        s.stop_downloading_in_background()

    def __eq__(s, other):
        if type(s) != type(other):
            return False
        return s.id_ == other.id_

    def image_cached(s, url):
        return ms.net_cached(url)

    def image_cache(s, img_url, silent=False, allow_cached=True):
        receive_raw(img_url, silent=silent, allow_cached=allow_cached)

    def image_print(s, url):
        assert s.image_cached(url)
        path = ms.net_cached_path(url)
        cmd = shlex.join(['viu', path])
        output = subprocess.run(cmd, shell=True, check=True, capture_output=False)

    def show(s):
        print(f'Title: {s.title}')
        print(f'Pages: {s.pages}')
        print(s.link)
        for t in s.tags: print(t)
        for a in s.artists: print(a)
        for l in s.languages: print(l)
        s.print_thumb()

    def print_thumb(s):
        ms.net_cache(s.thumb_url, fresh=False)
        s.image_print(s.thumb_url)

    def contains_tag(s, tag):
        if len(s.tags) == 0:
            return True
        for t in s.tags:
            if tag == t.name:
                return True
        return False

    def contains_language(s, lang):
        if len(s.languages) == 0:
            return True
        for l in s.languages:
            if lang == l.name:
                return True
        return False

    download_in_background_tlock = threading.Lock()
    def download_in_background(s):

        if s.download_in_background_tlock.acquire(False) == False:
            print('Warning: Pages are already being downloaded in the backgroudn. Either this is a bug or you fucked around too much')
            return

        def download_all_pages():
            nonlocal s
            try:
                for page_num in range(1, s.pages+1):
                    if s.download_in_background_tlock.locked() == False:
                        break
                    s.image_cache(s.get_page_image_url(page_num))
            finally:
                if s.download_in_background_tlock.locked():
                    s.download_in_background_tlock.release()

        threading.Thread(target=download_all_pages).start()

    def stop_downloading_in_background(s):
        if s.download_in_background_tlock.locked():
            s.download_in_background_tlock.release()

    def get_page_image_url(s, page_num):
        url = URL_READ.format(id=s.id_, page=page_num)
        data = receive(url, silent=True)

        soup = bs4.BeautifulSoup(data, SOUP_PARSER)
        link = soup.find(id='image-container').img['src']
        return link

    def reading_loop(s):

        s.download_in_background()

        CMDS = []
        CMDS.append(CMD_QUIT := ['quit', 'q', 'exit', 'e'])
        CMDS.append(CMD_NEXT := ['next page', 'next', 'n'])
        CMDS.append(CMD_PREV := ['prevoius page', 'prev', 'p', 'back', 'b'])
        CMDS.append(CMD_PAGE := ['go to page', 'page', 'go to', 'goto', 'go', 'g'])

        page_num = 1
        while page_num <= s.pages and page_num >= 1:

            image_link = s.get_page_image_url(page_num)

            if not s.image_cached(image_link):
                print_tmp('Downloading...')
                try:
                    while not s.image_cached(image_link):
                        time.sleep(WAIT_FOR_PAGE_DOWNLOAD_SLEEP)
                except KeyboardInterrupt:
                    break

            print(f'Page: {page_num} / {s.pages}')
            s.image_print(image_link)

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

        s.stop_downloading_in_background()

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

def receive_raw(url, silent=False, allow_cached=False):

    try:
        return ms.net_read(url, fresh=not allow_cached)
    except ms.Exception_net_page_not_ok as err:
        page = err.page

    match (page.status_code, page.reason):
        case (404, 'Not Found'):
            raise Exception_net_page_not_found()
        case (429, 'Too Many Requests'):
            if not silent: print_tmp(f'Too many requests, server refused connection, retrying in {NET_TOO_MANY_REQUESTS_SLEEP} seconds')
            time.sleep(NET_TOO_MANY_REQUESTS_SLEEP)
            return receive_raw(url, silent, allow_cached)
        case _:
            raise Exception_net_unknown(f'{url} {page.status_code} {page.reason}')

    assert False

def receive(*a, **kw):
    return receive_raw(*a, **kw).decode()

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
        hentais_in_container = container.find_all(class_='cover')
        if len(hentais_in_container) == 0:
            while True: yield

        for hentai in hentais_in_container:
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

def interactive_hentai_enjoyment(search_term=None, required_tags=None, required_language=None, required_artist=None):

    CMDS = []
    CMDS.append(CMD_QUIT := ['quit', 'q', 'exit', 'e'])
    CMDS.append(CMD_NEXT := ['next hentai', 'next', 'n'])
    CMDS.append(CMD_PREV := ['previous hentai', 'previous', 'prev', 'p'])
    CMDS.append(CMD_READ := ['read hentai', 'read', 'r', 'enjoy', 'cum', 'wank', 'sex'])
    CMDS.append(CMD_DOWNLOAD := ['download hentai', 'download', 'd'])

    assert type(required_tags) in (list, tuple)
    assert type(required_language) in (str, type(None))

    ## filtering

    url_page = None

    # search

    if search_term != None:
        assert url_page == None
        url_page = URL_SEARCH.format(search=search_term)

    # artist

    if required_artist != None:
        if not does_page_exist(URL_ARTIST.format(artist=required_artist)):
            print(f"Artist doesn't exist: {required_artist}")
            sys.exit(1)

        if url_page == None:
            url_page = URL_ARTIST.format(artist=required_artist)
            required_artist = None

    # tags

    for tag in required_tags:
        if not does_page_exist(URL_TAG.format(tag=tag)):
            print(f"Tag doesn't exist: {tag}")
            sys.exit(1)

    if url_page == None:
        if len(required_tags) != 0:
            # TODO select the tag with the least popularity
            url_page = URL_TAG.format(tag=required_tags[0])
            required_tags = required_tags[1:]

    # lang

    if required_language != None:
        if not does_page_exist(URL_LANG.format(lang=required_language)):
            print(f"Language doesn't exist: {required_language}")
            sys.exit(1)

        if url_page == None:
            url_page = URL_LANG.format(lang=required_language)
            required_language = None

    # if no filters

    if url_page == None:
        url_page = URL_INDEX

    # TODO this is not perfect
    if '?' in url_page: url_page += '&'
    else: url_page += '?'

    url_page += URL_PAGE_POSTFIX

    ## else

    running = True
    hentais = []
    ind = 0

    # TODO
    # what if ctrl+c is pressed here
    # download hentai metadata in background
    for hentai in scrape_hentais(url_page):

        if hentai == None:
            if len(hentais) == 0:
                alert('No hentais with the specified parameters')
                break
            else:
                alert('This was the last hentai')
            ind = len(hentais)-1
        else:

            find_new_hentai = False

            for h in hentais:
                if h == hentai:
                    find_new_hentai = 'duplicate'
                    break

            if required_artist != None:
                if not hentai.contains_artist(required_artist): # TODO this doesn't exist
                    find_new_hentai = f'missing artist: {required_artist}'

            for tag in required_tags:
                if not hentai.contains_tag(tag):
                    find_new_hentai = f'missing tag: {tag}'
                    break

            if required_language != None:
                if not hentai.contains_language(required_language):
                    find_new_hentai = f'missing langiage: {required_language}'

            if find_new_hentai:
                print_tmp(f'Hentai rejected (reason: {find_new_hentai}), searching for another one...')
                continue

            hentais.append(hentai)

        while running:

            if ind >= len(hentais):
                break
            if ind < 0:
                ind = 0
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
            elif c in CMD_DOWNLOAD:
                hentai.download_in_background()

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
    parser.add_argument('--search', help='String to search for')
    parser.add_argument('--tags', nargs='+', help='Tags required for the hentai', default=[])
    parser.add_argument('--language', help='Language required for the hentai')
    parser.add_argument('--artist', help='Artist required for the hentai')
    args = parser.parse_args()

    call_args = []
    call_args.append(args.search)
    call_args.append(args.tags)
    call_args.append(args.language)
    call_args.append(args.artist)

    interactive_hentai_enjoyment(*call_args)

if __name__ == '__main__':
    main()
