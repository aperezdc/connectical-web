#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# vim:fenc=utf-8:

"""This module generate contents for planet page, feeding with the blogs
definitions."""

from hashlib import md5
from HTMLParser import HTMLParser
import PyRSS2Gen
import datetime
import feedparser
import cache
import utils

Site.CONTEXT.planet = AttrDict()
Site.CONTEXT.planet.blog = AttrDict()
Site.CONTEXT.planet.blog.post = []
Site.CONTEXT.planet.blog.feed = []
Site.CONTEXT.planet.blog.tags = set()

config_fields = "rss"
config_avatar = "avatar"
default_avatar = "/img/avatar.png"

atom_feed = PyRSS2Gen.RSS2(
        title = "Connectical Blog Feed",
        link  = "http://connectical.com/blog",
        description = "Blog for Connectical staff and collaborators",
        lastBuildDate = datetime.datetime.utcnow(),
        items = []
)


class MLStripper(HTMLParser):

    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


try:

    for person in Site.CONTEXT.config.staff.sections():

        feed = Site.CONTEXT.config.staff.get(person, config_fields)

        cache_key = os.path.join(
            Site.CONTEXT.config.cache.get("cache","cache_dir"),
            md5(feed).hexdigest())

        blog = cache.get(cache_key,
                expires=Site.CONTEXT.config.cache.get("cache","expires"))

        if not blog:
            blog = feedparser.parse(feed)
            if not blog.has_key("status") or int(blog["status"]) != 200:
                print "warning:planet_blog:feed %s returns a non valid status" % feed
                continue
            cache.set(cache_key, blog)

        if len(blog.feed) == 0:
            print "warning:planet_blog:feed %s is not available" % feed
            continue

        # Remove appeded title for category based feeds in wordpress
        if blog.feed.title.find(u"»") != -1:
            blog.feed.title = blog.feed.title.split(u"»")[0]

        Site.CONTEXT.planet.blog.feed.append(AttrDict(
            title = blog.feed.title,
            link = blog.feed.link,
           author = unicode(person,"utf-8") ))

        for e in blog.entries:
            try:
                content = e.content[0].value
            except AttributeError:
                content = e.summary_detail.value
            atom_feed.items.append(PyRSS2Gen.RSSItem(
                title = e.title,
                link  = e.link,
                author = unicode(person,"utf-8"),
                description = content,
                pubDate = e.updated
            ))

            if Site.CONTEXT.config.staff.has_option(person, config_avatar):
                _avatar = Site.CONTEXT.config.staff.get(person, config_avatar)
            else:
                _avatar = default_avatar

            img = utils.get_img(content)

            Site.CONTEXT.planet.blog.post.append(AttrDict(
                title = e.title,
                author = unicode(person,"utf-8"),
                author_url = blog.feed.link,
                author_avatar = _avatar,
                updated = e.updated_parsed,
                updated_str = e.updated,
                img = img,
                url = e.link,
                content = content,
                tags = map(lambda d:d.term,e.tags) if getattr(e,"tags",False) else [],
                comments = e.slash_comments if getattr(e,"slash_comments",False) else 0,
                text_content = strip_tags(content)))

    Site.CONTEXT.planet.blog.post.sort( cmp = lambda x,y: cmp(y.updated,x.updated) )
    Site.CONTEXT.planet.blog.post = Site.CONTEXT.planet.blog.post[0:10]

    for obj in Site.CONTEXT.planet.blog.post:
        if obj.tags:
            Site.CONTEXT.planet.blog.tags = Site.CONTEXT.planet.blog.tags.union(set(obj.tags))

    atom_feed.write_xml(open("live/feed/index.xml", "w"))

except Exception, e:
    if Site.CONTEXT.config.debug.getboolean('debug','enabled') == True:
        raise
    else:
        print "error:planet_blog: %s" % e

