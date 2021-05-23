# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CommentItem(scrapy.Item):
    # define the fields for your item here like:
    identifier = scrapy.Field()
    text = scrapy.Field()
    date = scrapy.Field()
    flag_profile = scrapy.Field()
    link_reaction = scrapy.Field()
    comment_dad = scrapy.Field()
    id_publication = scrapy.Field()
    fetch_datetime = scrapy.Field()

class PostItem(scrapy.Item):
    # define the fields for your item here like:
    identifier = scrapy.Field()
    text = scrapy.Field()
    date = scrapy.Field()
    reactions = scrapy.Field()
    shares = scrapy.Field()
    id_red_social = scrapy.Field()
    type_video = scrapy.Field()
    url = scrapy.Field()
    id_user = scrapy.Field()
    fetch_datetime = scrapy.Field()