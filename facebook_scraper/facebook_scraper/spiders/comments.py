import scrapy
import json
import pandas as pd
import os
import re
from datetime import datetime
from ..items import CommentItem
from urllib.parse import urljoin

# XPATH_PATH = '//div[@id="root"]/div[@id="m_story_permalink_view"]'
XPATH_PATH = ''
XPATH_HELP = '//div[not (@style)]/a[contains(@href,"/help/")]'
XPATH_PROFILE_UNIV = f'({XPATH_PATH}//h3[@class]//a/text())|//div[@data-ft]//strong/text()'
XPATH_COMMENTS_X_PAGE = f'{XPATH_PATH}//h3[not (@class)]/../../@id'
XPATH_SUBCOMMENTS_X_PAGE = '//h3[not (@class)]/../../../div/div[not (contains(@id,"comment"))]/@id'
XPATH_VIDEO_X_PAGE = '//div[contains(@id,"mobile_injected")]//a[contains(@href,"action_list")]/@href'
XPATH_SEE_PREV_SUBCOMMENT_X_PAGE = '//div[contains(@id,"comment_replies_more_1")]/a/@href'
XPATH_SEE_NEXT_SUBCOMMENT_X_PAGE = '//div[contains(@id,"comment_replies_more_2")]/a/@href'
XPATH_SEE_PREV_COMMENT_X_PAGE = f'{XPATH_PATH}//div[@class and contains(@id,"see_prev")]/a/@href'
XPATH_SEE_NEXT_COMMENT_X_PAGE = f'{XPATH_PATH}//div[@class and contains(@id,"see_next")]/a/@href'
XPATH_ID_PUBLICATION = f'(({XPATH_PATH}//div[@data-ft])[1]/@data-ft)|//div[contains(@id,"actions")]/@id'

def extraer_cookies():
    list_cookies = []
    list_dir = os.listdir('cookies')

    for carpeta in list_dir:
        with open(f'cookies/{carpeta}') as f:
            contents = f.read()
            list_cookies.append(json.loads(contents))
    
    return list_cookies

class SpiderComment(scrapy.Spider):
    name = 'spider_comment'

    custom_settings = {'FEED_URI': 'comment.json',
                       'FEED_FORMAT': 'json',
                       'AUTOTHROTTLE_START_DELAY':25,
                       'AUTOTHROTTLE_MAX_DELAY':35,
                       'AUTOTHROTTLE_DEBUG': True}
    handle_httpstatus_list = [200]

    def __init__(self, url):
        self.start_urls = [url]

    def start_requests(self):
        j = 0
        list_cookies = extraer_cookies()
        for i, url in enumerate(self.start_urls):
            
            if 'facebook' in url:
                url = f'https://mbasic.{url[url.find("facebook"):]}'
            
            yield scrapy.Request(url=url, callback=self.parse, meta={'cookiejar': i},cookies=list_cookies[j])

            if j + 1 == len(list_cookies):
                j = 0
            else:
                j += 1

    def parse(self, response, **kwargs):
        direction = kwargs.get('direction',True)
        num = kwargs.get('num', 0)

        if direction == True and num == 0:
            page_prev = response.xpath(XPATH_SEE_PREV_COMMENT_X_PAGE).get()
            page_next = response.xpath(XPATH_SEE_NEXT_COMMENT_X_PAGE).get()
        elif direction == False:
            page_prev = response.xpath(XPATH_SEE_PREV_COMMENT_X_PAGE).get()
            page_next = None
        else:
            page_prev = None
            page_next = response.xpath(XPATH_SEE_NEXT_COMMENT_X_PAGE).get()

        comments = response.xpath(XPATH_COMMENTS_X_PAGE).getall()

        for comment in comments:
            obj_comment = CommentItem()

            xpath_text_comment = f'//div[@id="{str(comment)}"]/div/div[1]//text()'
            xpath_person_tag = f'//div[@id="{str(comment)}"]/div/div[1]//a[count(@*)<=1]/text()'
            xpath_date_comment = f'//div[@id="{str(comment)}"]/div/div[contains(@class," ")]/abbr/text()'
            xpath_flag_profile = f'//div[@id="{str(comment)}"]/div/h3/a/text()="{response.xpath(XPATH_PROFILE_UNIV).get()}"'
            xpath_subcomment = f'(//div[@id="{str(comment)}"]/div/div/div[contains(@id,"comment")]//a/@href)[last()]'
            xpath_link_reaction = f'//div[@id="{str(comment)}"]/div/div[contains(@class," ")]/span[1]/span[1]/a[@class]/@href'

            identifier = str(comment)
        
            text_comment = response.xpath(xpath_text_comment).getall()
            text_comment = ''.join(text_comment).strip(' ')
            person_tag = response.xpath(xpath_person_tag).getall()
            date_comment = response.xpath(xpath_date_comment).get()
            flag_profile = response.xpath(xpath_flag_profile).get()
            link_subcomment = response.xpath(xpath_subcomment).get()
            link_reaction = response.xpath(xpath_link_reaction).get()
            comment_dad = None
            id_publication = response.xpath(XPATH_ID_PUBLICATION).get()

            if 'mf_story_key' in id_publication:            
                id_publication = json.loads(id_publication)['mf_story_key']
            
            else:
                id_publication = id_publication.replace("actions_","")

            if link_reaction:
                link_reaction = f'https://m.facebook.com/ufi/reaction/profile/browser/?ft_ent_identifier={id_publication}_{identifier}&refid=52&__tn__=R'

            if link_subcomment:
                yield scrapy.Request(url=urljoin(response.url, link_subcomment), callback=self.parse_subcomment, cb_kwargs={'comment_dad': identifier, 'univ': response.xpath(XPATH_PROFILE_UNIV).get(),'id_publication':id_publication}, meta={'cookiejar': response.meta['cookiejar']})

            for word in person_tag:
                text_comment = text_comment.replace(word, f'[{word}]')

            texto_encontrado = re.findall(r"(([a-zA-ZÀ-ÿ\u00f1\u00d1\d-]+\[[a-zA-ZÀ-ÿ\u00f1\u00d1(\ )\d-]+\][a-zA-ZÀ-ÿ\u00f1\u00d1\d-]*)|(\[[a-zA-ZÀ-ÿ\u00f1\u00d1(\ )\d-]+\][a-zA-ZÀ-ÿ\u00f1\u00d1\d-]+))",text_comment)

            texto_encontrado = [sentence[0] for sentence in texto_encontrado]

            for sentence in texto_encontrado:
                text_comment = text_comment.replace(sentence,sentence.replace("[","").replace("]",""))

            obj_comment['identifier'] = identifier
            obj_comment['text'] = text_comment
            obj_comment['date'] = date_comment
            obj_comment['flag_profile'] = flag_profile
            obj_comment['link_reaction'] = link_reaction
            obj_comment['comment_dad'] = comment_dad
            obj_comment['id_publication'] = id_publication
            obj_comment['fetch_datetime'] = datetime.now()

            yield obj_comment

        num += 1

        if page_next:
            yield scrapy.Request(url=urljoin(response.url, page_next),callback=self.parse,cb_kwargs={'direction':True, 'num': num}, meta={'cookiejar': response.meta['cookiejar']})
          
        if page_prev:
            yield scrapy.Request(url=urljoin(response.url, page_prev),callback=self.parse,cb_kwargs={'direction':False, 'num': num}, meta={'cookiejar': response.meta['cookiejar']})

    def parse_subcomment(self, response, **kwargs):
        direction = kwargs.get('direction',True)
        num = kwargs.get('num', 0)

        if direction == True and num == 0:
            page_prev = response.xpath(XPATH_SEE_PREV_SUBCOMMENT_X_PAGE).get()
            page_next = response.xpath(XPATH_SEE_NEXT_SUBCOMMENT_X_PAGE).get()
        elif direction == False:
            page_prev = response.xpath(XPATH_SEE_PREV_SUBCOMMENT_X_PAGE).get()
            page_next = None
        else:
            page_prev = None
            page_next = response.xpath(XPATH_SEE_NEXT_SUBCOMMENT_X_PAGE).get()

        comments = response.xpath(XPATH_SUBCOMMENTS_X_PAGE).getall()

        for comment in comments:
            obj_comment = CommentItem()

            xpath_text_comment = f'//div[@id="{str(comment)}"]/div/div[1]//text()'
            xpath_person_tag = f'//div[@id="{str(comment)}"]/div/div[1]//a[count(@*)<=1]/text()'
            xpath_date_comment = f'//div[@id="{str(comment)}"]/div/div[contains(@class," ")]/abbr/text()'
            xpath_flag_profile = f'//div[@id="{str(comment)}"]/div/h3/a/text()="{kwargs["univ"]}"'
            xpath_subcomment = f'(//div[@id="{str(comment)}"]/div/div/div[contains(@id,"comment")]//a/@href)[last()]'
            xpath_link_reaction = f'//div[@id="{str(comment)}"]/div/div[contains(@class," ")]/span[1]/span[1]/a[@class]/@href'
            
            identifier = str(comment)
        
            text_comment = response.xpath(xpath_text_comment).getall()
            text_comment = ''.join(text_comment).strip(' ')
            person_tag = response.xpath(xpath_person_tag).getall()
            date_comment = response.xpath(xpath_date_comment).get()
            flag_profile = response.xpath(xpath_flag_profile).get()
            link_subcomment = response.xpath(xpath_subcomment).get()
            link_reaction = response.xpath(xpath_link_reaction).get()
            comment_dad = kwargs['comment_dad']
            id_publication = kwargs['id_publication']

            if link_reaction:
                link_reaction = f'https://m.facebook.com/ufi/reaction/profile/browser/?ft_ent_identifier={id_publication}_{identifier}&refid=52&__tn__=R'

            if link_subcomment:
                yield scrapy.Request(url=urljoin(response.url, link_subcomment), callback=self.parse_subcomment, cb_kwargs={'comment_dad': identifier, 'univ': kwargs["univ"], 'id_publication':id_publication}, meta={'cookiejar': response.meta['cookiejar']})

            for word in person_tag:
                text_comment = text_comment.replace(word, f'[{word}]')

            obj_comment['identifier'] = identifier
            obj_comment['text'] = text_comment
            obj_comment['date'] = date_comment
            obj_comment['flag_profile'] = flag_profile
            obj_comment['link_reaction'] = link_reaction
            obj_comment['comment_dad'] = comment_dad
            obj_comment['id_publication'] = id_publication
            obj_comment['fetch_datetime'] = datetime.now()

            yield obj_comment

        num += 1

        if page_next:
            yield scrapy.Request(url=urljoin(response.url, page_next),callback=self.parse,cb_kwargs={'direction':True, 'num': num, 'comment_dad': comment_dad, 'univ':kwargs["univ"], 'id_publication':id_publication}, meta={'cookiejar': response.meta['cookiejar']})
          
        if page_prev:
            yield scrapy.Request(url=urljoin(response.url, page_prev),callback=self.parse,cb_kwargs={'direction':False, 'num': num, 'comment_dad': comment_dad, 'univ':kwargs["univ"], 'id_publication':id_publication}, meta={'cookiejar': response.meta['cookiejar']})