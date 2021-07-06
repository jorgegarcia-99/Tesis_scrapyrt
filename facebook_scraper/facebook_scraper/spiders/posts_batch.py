import scrapy
import json
import os
import pandas as pd
from ..items import PostItem
from datetime import datetime
from lxml import etree
from urllib.parse import urljoin

XPATH_ID_PUBLICATION = '((//div[@data-ft])[1]/@data-ft)|//div[contains(@id,"actions")]/@id'
XPATH_TEXT_PUBLICATION = '(//div[@data-ft and @data-gt])[1]//text()'
XPATH_DATE_PUBLICATION = '(//a/abbr)[1]/text()'
XPATH_REACTIONS = '//a[contains(@href,"ufi/reaction") and child::div]/@href'
XPATH_SHARES = '(//a[contains(@href,"shares")]/span/text())|//div[contains(@id,"mobile_injected")]//span[contains(@data-sigil,"share")]/text()'
XPATH_TYPE_VIDEO = 'boolean(//div[@class="story_body_container"]//div[contains(@data-store,"video")])'
XPATH_ID_USER = '(//div[contains(@data-sigil,"feed_story_ring")])[1]/@data-sigil'

def lista_posts():
    df_posts = pd.read_csv('publicacion.csv',usecols=['post_url'])
    df_posts = df_posts.astype({'post_url':'str'})
    return df_posts['post_url'].tolist()

def extraer_cookies():
    list_cookies = []
    list_dir = os.listdir('cookies')

    for carpeta in list_dir:
        with open(f'cookies/{carpeta}') as f:
            contents = f.read()
            list_cookies.append(json.loads(contents))
    
    return list_cookies

class SpiderPost(scrapy.Spider):
    name = 'spider_post_batch'
    start_urls = lista_posts()
    custom_settings = {'FEED_URI': 'post_batch.json',
                       'FEED_FORMAT': 'json',                       
                       'AUTOTHROTTLE_START_DELAY':5,
                       'AUTOTHROTTLE_MAX_DELAY':8,
                       'AUTOTHROTTLE_DEBUG': True}
    handle_httpstatus_list = [200]

    def __init__(self):
        pass

    def start_requests(self):
        j = 0
        list_cookies = extraer_cookies()
        for i, url in enumerate(self.start_urls):
            
            if 'facebook' in url:
                url = f'https://m.{url[url.find("facebook"):]}'
            
            yield scrapy.Request(url=url, callback=self.parse, meta={'cookiejar': i},cookies=list_cookies[j])

            if j + 1 == len(list_cookies):
                j = 0
            else:
                j += 1

    def parse(self, response):
        
        if 'watch' in response.url: return

        post_object = PostItem()

        element_xml = response.xpath('//comment()').getall()
        element_xml = map(lambda x: str(x).replace("<!-- ","").replace(" -->",""),element_xml)
        element_xml = ''.join(list(element_xml)).strip('')
        element_xml = f'<html><head></head><body>{element_xml}</body></html>'.replace("&nbsp;","")
        element_xml = etree.fromstring(element_xml)

        identifier = element_xml.xpath(XPATH_ID_PUBLICATION)
        text = element_xml.xpath(XPATH_TEXT_PUBLICATION)
        date = element_xml.xpath(XPATH_DATE_PUBLICATION)
        link_reactions = element_xml.xpath(XPATH_REACTIONS)
        shares = element_xml.xpath(XPATH_SHARES)
        type_video = element_xml.xpath(XPATH_TYPE_VIDEO)
        id_user = element_xml.xpath(XPATH_ID_USER)
        id_red_social = '1'
        url = response.url
        fetch_datatime = datetime.now()
        
        if identifier:
            identifier = identifier[0]
            if 'mf_story_key' in identifier:            
                identifier = json.loads(identifier)['mf_story_key']
            
            else:
                identifier = identifier.replace("actions_","")
        else:
            identifier = None

        text = ''.join(text).strip(' ')

        if date: date = date[0] 
        else: date = None
        if shares: shares = shares[0].split()[0]
        else: shares = 0
        if id_user: id_user = id_user[0].replace("feed_story_ring","")
        else: id_user = None

        post_object["identifier"] = identifier
        post_object["text"] = text
        post_object["date"] = date
        post_object["shares"] = shares
        post_object["id_red_social"] = id_red_social
        post_object["type_video"] = type_video
        post_object["url"] = url
        post_object["id_user"] = id_user
        post_object["fetch_datetime"] = fetch_datatime

        if link_reactions:
            yield scrapy.Request(url=urljoin(response.url, link_reactions[0]), callback=self.parseReaction,cb_kwargs={**post_object},meta={'cookiejar': response.meta['cookiejar']})

        else:
            post_object["reactions"] = None
            yield post_object

    def parseReaction(self, response, **kwargs):
        post_object = PostItem()

        reactions = response.xpath('//span[@data-store]/@data-store').getall()
        list_type_reaction = [reaction_type[reaction_type.find(
                    ":")+1:-1] for reaction_type in reactions]
        dict_reaction = dict(
            zip(list(list_type_reaction), response.xpath('//span[@data-store]//span/text()').getall()))
    
        if '"all"' in dict_reaction.keys():
            dict_reaction['all'] = dict_reaction['"all"'].replace(
                "Todas (", "").replace(")", "")
            del(dict_reaction['"all"'])
        else:
            dict_reaction['all'] = dict_reaction[list(
                dict_reaction.keys())[0]]
        
        post_object["identifier"] = kwargs["identifier"]
        post_object["text"] = kwargs["text"]
        post_object["date"] = kwargs["date"]
        post_object["shares"] = kwargs["shares"]
        post_object["id_red_social"] = kwargs["id_red_social"]
        post_object["type_video"] = kwargs["type_video"]
        post_object["url"] = kwargs["url"]
        post_object["id_user"] = kwargs["id_user"]
        post_object["fetch_datetime"] = kwargs["fetch_datetime"]
        post_object['reactions'] = dict(dict_reaction)

        yield post_object
