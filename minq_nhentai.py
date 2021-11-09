#!/usr/bin/env python3

import requests
import bs4 # sudo pacman -S --needed python-beautifulsoup4
import argparse


BASE_URL = 'https://nhentai.net/'
URL_TAG_PAGE = BASE_URL + '/tag/{}/?page={}'

#REQUIRED_TAGS = ['/tag/drugs', 'cross']
#REQUIRED_TAGS = ['/tag/drugs']


MAX_RESPONSE_RETRIES = 20
def raw_response(url):
    for _ in range(MAX_RESPONSE_RETRIES):
        page = requests.get(url)
        if page.ok:
            return page.content
    assert 0, 'wtf'

def decoded_response(url):
    return raw_response(url).decode()


def scrape_hentai_links(tag, page):

    url = URL_TAG_PAGE.format(tag, page)
    data = decoded_response(url)
    page += 1

    soup = bs4.BeautifulSoup(data, "lxml")

    hentai_container = soup.find(class_='container index-container')
    hentais = hentai_container.find_all(class_='cover')
    hentai_urls = [BASE_URL + item['href'] for item in hentais]

    return page, hentai_urls


def scrape_hentai_tags(link):

    data = decoded_response(link)

    soup = bs4.BeautifulSoup(data, "lxml")

    tags_container = soup.find(id='tags')
    for cont in tags_container:
        if 'Tags:' in cont.text:
            tags_container = cont
            break
    else:
        tags_container = []

    tags_html = list(tags_container)[1]
    tags = [tag['href'] for tag in tags_html]

    return tags


def main_loop(main_tag, additional_tags):

    page = 1

    while True:

        found_any_hentai = False

        print(f'{page=}')
        page, candidates = scrape_hentai_links(main_tag, page)

        cands_left = []
        
        for cand in candidates:

            tags = scrape_hentai_tags(cand)

            for req_tag in additional_tags:
                for tag in tags:
                    if req_tag in tag:
                        break
                else:
                    break
            else:
                print(f'HHH {cand}')
                found_any_hentai = True

        if found_any_hentai:
            input('>>> Press enter to scrape next page')


def main():
    parser = argparse.ArgumentParser(description="A tool to search nhentai by tags. NOTE: When searching for say 3 tags, you are searching for a hentai with ALL 3 of them, and not ANY.")
    parser.add_argument('tag', type=str, help="The first tag desired. This has to be a legitemate tag. IE {URL_TAG_PAGE.format(YOUR_TAG, 1)} has to exist.")
    parser.add_argument('additional_tags', nargs='*', help="Additional tags. Has to only be in the name. IE 'dress' will count as both 'chinese dress' as well as 'crossdressing'.")
    args = parser.parse_args()
    
    tag = args.tag
    if(additional_tags := args.additional_tags) == None:
        additional_tags = []
    main_loop(tag, additional_tags)


if __name__ == '__main__':
    main()
