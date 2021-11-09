#!/usr/bin/env python3

import requests
import bs4


MAX_RESPONSE_RETRIES = 20
def raw_response(url):
    for _ in range(MAX_RESPONSE_RETRIES):
        page = requests.get(url)
        if page.ok:
            return page.content
    assert 0, 'wtf'

def decoded_response(url):
    return raw_response(url).decode()


BASE_URL = 'https://nhentai.net/'
PAGE_URL = BASE_URL + '?page={}'

REQUIRED_TAGS = ['/tag/drugs', 'cross']

def scrape_hentai_links(page):

    data = decoded_response(PAGE_URL.format(page) + REQUIRED_TAGS[0] + '/')
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


def main():

    page = 1
    hentais = []
    hentai_idx = 0

    while True:

        while hentai_idx >= len(hentais):
            print(f'{page=}')
            page, candidates = scrape_hentai_links(page)

            cands_left = []
            
            for cand in candidates:

                tags = scrape_hentai_tags(cand)

                for req_tag in REQUIRED_TAGS:
                    for tag in tags:
                        if req_tag in tag:
                            break
                    else:
                        break
                else:
                    cands_left.append(cand)

            # todo: check for repeats
            hentais.extend(cands_left)

        inp = input('>')
        print(hentais[hentai_idx])
        hentai_idx += 1


if __name__ == '__main__':
    main()
    exit(0)





    pizzas = soup.find_all(class_='product-detail-more')

    for pizza_ind, pizza in enumerate(pizzas):
        name = pizza.find(class_='product-name').text.strip()
        
        ings = pizza.find_all(class_='product-ingredients')
        for ind, ing in reversed(list(enumerate(ings))):
            ing = ing.text.strip()
            if ing == '':
                del ings[ind]
            else:
                ing = ing.split(', ')
                ings[ind] = ing
        
        l = len(ings)
        if l == 0:
            ings = ['NO_DESC']
        elif l == 1:
            ings = ings[0]
        else:
            ings = sum(ings, [])

        for ind,_ing in enumerate(ings):
            ings[ind] = _ing.replace('\n', ' ; ')


        weight, size, price = pizza.find_all(class_='row product-unit')[-1].text.split('\n')[1:4]

        postfix1 = ' гр.'
        postfix2 = ' бр.'
        assert weight.endswith(postfix1) or weight.endswith(postfix2)
        assert len(postfix1) == len(postfix2)
        weight = weight[:-len(postfix1)]
        assert float(weight) == int(weight)
        weight = int(weight)

        postfix = ' лв.'
        assert price.endswith(postfix)
        price = price[:-len(postfix)]
        price = float(price)

        image = pictures = soup.find(class_='img-responsive', title=name)
        if image == None:
            #image_link = 'error'
            image = pictures = soup.find(class_='img-responsive', title=' '+name)
        image = image['src']
        image_link = BASE_URL + image
        
        pizzas[pizza_ind] = Pizza(name, ings, weight, size, price, image_link)


for ind, pizza in reversed(list(enumerate(pizzas))):
    for ing in filter_ing:
        if pizza.contains(ing):
            break
    else:
        continue

    del pizzas[ind]

pizzas.sort(reverse=True, key=lambda p:p.value)

for pizza in pizzas:
    pizza.show_info()
    pizza.show_image()
    input()



