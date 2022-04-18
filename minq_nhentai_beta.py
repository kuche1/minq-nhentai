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
import minq_caching_thing; mct = minq_caching_thing.Minq_caching_thing() # paru -S python-minq-caching-thing-git
import tempfile

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

SETTINGS_DIR = os.path.expanduser('~/.config/minq-nhentai/settings/')
BLACKLIST_DIR = os.path.join(SETTINGS_DIR, 'blacklisted')

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
        
        s.page_urls = [None] * pages
        
    def __eq__(s, other):
        if type(s) != type(other):
            return False
        return s.id_ == other.id_

    def image_path(s, url):
        return mct.get_url(url, return_path=True)

    def image_cache(s, img_url, silent=False, allow_cached=True):
        receive_raw(img_url, silent=silent, allow_cached=allow_cached)

    def show(s):
        print(f'Title: {s.title}')
        print(f'Pages: {s.pages}')
        print(s.link)
        for t in s.tags: print(t)
        for a in s.artists: print(a)
        for l in s.languages: print(l)
        s.print_thumb()

    def print_thumb(s):
        path = receive(s.thumb_url, silent=True, allow_cached=True, return_path=True)
        image_print(path)

    def contains_artist(s, artist):
        if len(s.tags) == 0:
            return True
        for a in s.artists:
            if artist == a.name:
                return True
        return False

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
    
    def is_blacklisted(s):
        id_ = str(s.id_)
        for dir_,fols,fils in os.walk(BLACKLIST_DIR):
            return id_ in fils
    
    def set_blacklisted(s, yes):
        id_ = str(s.id_)
        path = os.path.join(BLACKLIST_DIR, id_)
        if yes: # move to blacklist
            if not os.path.isdir(BLACKLIST_DIR):
                os.makedirs(BLACKLIST_DIR)
            with open(path, 'w') as f:
                pass
        else: # remove from blacklist
            os.remove(path)

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

    get_page_image_url_tlock = threading.Lock()
    def get_page_image_url(s, page_num):
        s.get_page_image_url_tlock.acquire()
        try:
            cached = s.page_urls[page_num-1]
            if cached != None:
                return cached
    
            url = URL_READ.format(id=s.id_, page=page_num)
            data = receive(url, silent=True)
    
            soup = bs4.BeautifulSoup(data, SOUP_PARSER)
            link = soup.find(id='image-container').img['src']
            s.page_urls[page_num-1] = link
            return link
        finally:
            s.get_page_image_url_tlock.release()

    def reading_loop(s):

        s.download_in_background()

        CMDS = []
        CMDS.append(CMD_QUIT := ['quit', 'q', 'exit', 'e'])
        CMDS.append(CMD_NEXT := ['next page', 'next', 'n', ''])
        CMDS.append(CMD_PREV := ['prevoius page', 'prev', 'p', 'back', 'b'])
        CMDS.append(CMD_PAGE := ['go to page', 'page', 'go to', 'goto', 'go', 'g'])

        page_num = 1
        while page_num <= s.pages and page_num >= 1:

            image_link = s.get_page_image_url(page_num)

            if (image_path := s.image_path(image_link)) == None:
                print_tmp('Downloading...')
                try:
                    while (image_path := s.image_path(image_link)) == None:
                        time.sleep(WAIT_FOR_PAGE_DOWNLOAD_SLEEP)
                except KeyboardInterrupt:
                    break

            print(f'Page: {page_num} / {s.pages}')
            image_print(image_path)

            c = input('>> ', 'q')

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

def image_print(path):
    cmd = shlex.join(['viu', path])
    output = subprocess.run(cmd, shell=True, check=True, capture_output=False)

def alert(msg=''):
    print(msg)
    input('PRESS ENTER TO CONITNUE', -1)

def receive_raw(url, silent=False, allow_cached=False, return_path=False):
    try:
        if allow_cached:
            cont = mct.get_url(url, read_mode='b', return_path=return_path)
            if cont != None:
                return cont
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0'}
        page = requests.get(url, headers=headers)
        if page.ok:
            cont = page.content
            mct.cache_url(url, cont)
            if return_path:
                with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                    f.write(cont)
                    return f.name.encode()
            else:
                return cont
    except requests.exceptions.ConnectionError: # no internet (or TODO)
        cont = mct.get_url(url, read_mode='b', return_path=return_path) # TODO please no duplicates
        if cont == None:
            assert False, 'no internet connection'
        else:
            return cont

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

def get_page_tag_count(url):
    try:
        cont = receive(url)
    except Exception_net_page_not_found:
        return 0
    soup = bs4.BeautifulSoup(cont, SOUP_PARSER)
    count = soup.find(class_='count').text
    count = count.lower()
    if count.endswith('m'):
        count = count[:-1] + '0'*6
    elif count.endswith('k'):
        count = count[:-1] + '0'*3

    try:
        count = int(count)
    except ValueError:
        print('THIS IS A BUG, PLEASE REPORT TO THE DEVELOPER')
        print(f'debug info: count is {count}')
        input('PRESS ENTER TO CONTINUE', 0)
        count = 1
    return count

def scrape_tag_container(container):

    meta = container.text.strip().replace('\n','').replace('\t','')

    tag_counts = container.find(class_='tags').find_all(class_='count')
    tags = [t.parent for t in tag_counts]
    assert len(tag_counts) == len(tags)
    tag_names = [t.find(class_='name').text for t in tags]
    tag_counts = [t.find(class_='count').text for t in tags]

    tag_links = []
    tag_link_names = []
    for t in tags:
        link = t['href']
        if link.startswith('/'): link = link[1:]
        link = URL_INDEX + link
        tag_links.append(link)

        link_name = link.split('/')[-2]
        tag_link_names.append(link_name)

    assert len(tags) == len(tag_names) == len(tag_counts) == len(tag_links) == len(tag_link_names)
    # we are returning the tag link name instead of the real name
    return meta, [tag_link_names, tag_names][0], tag_links, tag_counts

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
    CMDS.append(CMD_QUIT := ['quit', 'q', 'exit'])
    CMDS.append(CMD_NEXT := ['next hentai', 'next', 'n', ''])
    CMDS.append(CMD_PREV := ['previous hentai', 'previous', 'prev', 'p'])
    CMDS.append(CMD_DOWNLOAD := ['download hentai', 'download', 'd'])
    CMDS.append(CMD_READ := ['read hentai', 'read', 'r', 'enjoy', 'cum', 'wank', 'sex'])
    CMDS.append(CMD_IGNORE := ['ignore hentai', 'ignore', 'ign', 'block hentai', 'block', 'blk'])

    assert type(required_tags) in (list, tuple)
    assert type(required_language) in (str, type(None))

    ## filtering

    url_page = None
    url_page_tag_count = float('inf')

    # search

    if search_term != None:
        assert url_page == None
        url_page = URL_SEARCH.format(search=search_term)
        url_page_tag_count = -1

    # artist

    if required_artist != None:
        c = get_page_tag_count(URL_ARTIST.format(artist=required_artist))
        if c == 0:
            print(f"Artist doesn't exist: {required_artist}")
            sys.exit(1)
        elif c < url_page_tag_count:
            url_page_tag_count = c
            url_page = URL_ARTIST.format(artist=required_artist)

    # tags

    for tag in required_tags:
        c = get_page_tag_count(URL_TAG.format(tag=tag))
        if c == 0:
            print(f"Tag doesn't exist: {tag}")
            sys.exit(1)
        elif c < url_page_tag_count:
            url_page_tag_count = c
            url_page = URL_TAG.format(tag=tag)

    # lang

    if required_language != None:
        c = get_page_tag_count(URL_LANG.format(lang=required_language))
        if c == 0:
            print(f"Language doesn't exist: {required_language}")
            sys.exit(1)
        elif c < url_page_tag_count:
            url_page_tag_count = c
            url_page = URL_LANG.format(lang=required_language)

    # if no filters

    if url_page == None:
        url_page = URL_INDEX
    else:
        print(f'DEBUG: selected url "{url_page}" with count "{url_page_tag_count}"')

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

            for _ in range(1):

                for h in hentais:
                    if h == hentai:
                        find_new_hentai = 'duplicate'
                        break
                if find_new_hentai:
                    break

                if required_artist != None:
                    if not hentai.contains_artist(required_artist): # TODO this doesn't exist
                        find_new_hentai = f'missing artist: {required_artist}'
                        break
    
                for tag in required_tags:
                    if not hentai.contains_tag(tag):
                        find_new_hentai = f'missing tag: {tag}'
                        break
                if find_new_hentai:
                    break

                if required_language != None:
                    if not hentai.contains_language(required_language):
                        find_new_hentai = f'missing langiage: {required_language}'
                        break
    
                if hentai.is_blacklisted():
                    find_new_hentai = 'blacklisted'
                    break

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
            elif c in CMD_IGNORE:
                hentai.set_blacklisted(True)
                del hentais[ind]
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
