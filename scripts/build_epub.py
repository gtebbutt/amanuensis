import argparse
import uuid
import json
import hashlib
import time
import requests
import os.path
import dateutil.parser
import tidy_html
from slugify import slugify
from bs4 import BeautifulSoup

CACHE_PATH_PREFIX = 'cache/'
HTML_PARSER = 'html.parser'
XML_PARSER = 'xml'

def get_cached(url):
    url_hash = hashlib.md5(url).hexdigest()
    file_path = os.path.abspath(u''.join([CACHE_PATH_PREFIX, url_hash]))

    try:
        # Try opening file to see if it exists
        with open(file_path, 'r') as f:
            # Parse with BeautifulSoup if so
            return BeautifulSoup(f.read().decode('utf8'), HTML_PARSER)
    except IOError:
        print 'No cached version found, downloading [{}]...'.format(url_hash)
        # Fetch from web, save
        page = requests.get(url, headers={'User-agent': 'amanuensis/0.0.1'})

        with open(file_path, 'w') as f:
            f.write(page.text.encode('utf8')) # Note that 'text' is the HTML, without headers

        # Rate limiter
        time.sleep(3)

        # Recursive call to actually return object
        return get_cached(url)

def process_item(item):
    print 'Processing URL: ' + item['url']

    parsed_html = get_cached(item['url'])
    
    tagline = parsed_html.select('#siteTable .tagline')[0]
    author = tagline.find(class_='author').text
    timestamp = dateutil.parser.parse(tagline.find('time')['datetime'])
    main_body = parsed_html.select('#siteTable div.md')[0].decode_contents(formatter="html")
    comments = parsed_html.select('div.commentarea .entry')

    item['author'] = author
    item['timestamp'] = timestamp
    item['main_body'] = main_body
    item['comment_body'] = []

    for comment in comments:
        try:
            comment_author = comment.select('a.author')[0].text
            if comment_author == author:
                comment_body = comment.select('div.md')[0]
                if len(comment_body.text.split()) > 100:
                    item['comment_body'].append(comment_body.decode_contents(formatter="html"))
        except IndexError:
            print 'Empty comment found, continuing'

    return item

def item_to_html(item):
    html = None
    with open('epub/template/OEBPS/chapter_template.xhtml', 'r') as f:
        html = BeautifulSoup(f.read().decode('utf8'), HTML_PARSER)

    html.find('title').string = item['title']
    html.find('h1').string = item['title']
    html.find(class_='author').string = u''.join(['By ', item['author']])

    main_body = html.find(id='main-body')
    main_body.append(BeautifulSoup(item['main_body'], HTML_PARSER))    
    for comment in item['comment_body']:
        main_body.append(BeautifulSoup(comment, HTML_PARSER))

    return unicode(html)

def create_filename(item):
    return u''.join([item['timestamp'].strftime('%Y-%m-%d'), '_', slugify(item['title']), '.xhtml'])

def save_item_html(item, path_prefix):
    f = open(u''.join([path_prefix, create_filename(item)]), 'w')
    f.write(tidy_html.process(item_to_html(item)).encode('utf8'))
    f.close()

def create_id(item):
    return slugify(item['title'])

def create_opf(contents, path_prefix, book_title, book_uid):
    opf_open = u'<?xml version="1.0"?>\
                <package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">\
                 \
                  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">\
                    <dc:title>{}</dc:title>\
                    <dc:language>en</dc:language>\
                    <dc:identifier id="BookId" opf:scheme="UUID">{}</dc:identifier>\
                    <dc:creator opf:file-as="Various Authors" opf:role="aut">Various Authors</dc:creator>\
                  </metadata>\
                 \
                  <manifest>\
                    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />'.format(book_title, book_uid)

    manifest_content = u''.join([u'<item id="{}" href="{}" media-type="application/xhtml+xml" />'.format(create_id(x), create_filename(x)) for x in contents])

    manifest_spine = u'</manifest><spine toc="ncx">'

    spine_content = u''.join([u'<itemref idref="{}" />'.format(create_id(x)) for x in contents])

    opf_close = u'</spine></package>'

    opf = u''.join([opf_open, manifest_content, manifest_spine, spine_content, opf_close])

    with open(u''.join([path_prefix, 'content.opf']), 'w') as f:
        f.write(opf.encode('utf8'))

def create_ncx(contents, path_prefix, book_title, book_uid):
    ncx = None
    with open('epub/template/OEBPS/toc_template.ncx', 'r') as f:
        ncx = BeautifulSoup(f.read().decode('utf8'), XML_PARSER)

    ncx.find('meta', attrs={'name': 'dtb:uid'})['content'] = book_uid
    ncx.find('docTitle').find('text').string = book_title

    nav_map = ncx.find('navMap')

    for i, x in enumerate(contents):
        nav_point = ncx.new_tag('navPoint', id=create_id(x), playOrder=i)
        nav_label = ncx.new_tag('navLabel')
        nav_text = ncx.new_tag('text')
        nav_text.string = x['title']
        nav_label.append(nav_text)
        nav_point.append(nav_label)
        nav_point.append(ncx.new_tag('content', src=create_filename(x)))
        nav_map.append(nav_point)

    with open(u''.join([path_prefix, 'toc.ncx']), 'w') as f:
        f.write(ncx.prettify().encode('utf8'))

def build_epub(contents, path_prefix, book_title, book_uid):
    print 'Building ePub'
    for item in contents:
        save_item_html(item, path_prefix)
    create_opf(contents, path_prefix, book_title, book_uid)
    create_ncx(contents, path_prefix, book_title, book_uid)
    print 'Successfully built ePub'

def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to JSON file containing book title, chapter titles, chapter URLs")
    parser.add_argument("--override_order", help="Forces the chapters to be sorted by publication date, ignoring the JSON file ordering.", action="store_true")
    return parser.parse_args()

def get_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def run():
    args = arguments()

    book_info = get_json(args.input)
    book_uid = uuid.uuid4()
    book_title = book_info['title']
    contents = book_info['contents']
    
    # Process everything, downloading individual pages
    for item in contents:
        process_item(item)

    if contents:
        if args.override_order:
            contents.sort(key=lambda x: x['timestamp'])
        build_epub(contents, u'out/', book_title, book_uid)

run()
