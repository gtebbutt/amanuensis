#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from bs4 import BeautifulSoup

HTML_PARSER = 'html.parser'

def process(html):
    '''
    Cleanup code kindly contributed by http://www.reddit.com/user/b3iAAoLZOH9Y265cujFh and used (almost) verbatim
    '''
    # We can't use formal HTML entities. Some readers have trouble showing them
    # correctly in some contexts. Using the UTF-8 encoded unicode character 
    # equivalents works across all tested readers.
    ENT_LQUOT = '“'.decode('utf-8')
    ENT_RQUOT = '”'.decode('utf-8')
    ENT_SQUOT = '’'.decode('utf-8')
    ENT_NDASH = '–'.decode('utf-8')
    ENT_ELIPS = '⋯'.decode('utf-8')

    purge = []
    break_test = re.compile(r'[^\+.]').search
    underscore_test = re.compile(r'_+')
    parsed_html = BeautifulSoup(html, HTML_PARSER)
    body = parsed_html.find(id='main-body')

    if body:
        # Special cases
        title = parsed_html.find('h1').string
        if title == 'Run, little monster':
            purge.append(body('p')[0])
        elif title == 'Humans don’t make good pets part 7':
            ps = body('p')
            
            purge.append(ps[0])
            purge.append(ps[1])
        elif title == 'The Tigers Cub':
            ps = body('p')
            
            purge.append(ps[len(ps)-1])
        elif title == 'Deliverance':
            for e in body.find(text = '__').parent.fetchNextSiblings():
                purge.append(e)

        hrs = body('hr')
    
        if hrs:
            cruft = None
            cruft_len = 0
        
            for hr in hrs:
                c = hr.fetchPreviousSiblings()
                cl = len(str(c))
        
                if cl <= 2500: # Lower lim ~2100, upper lim ~3100
                    cruft = c
                    cruft_len = cl
    
            if cruft:
                if cruft[0].name == 'ul': # Special case: QED
                    for e in cruft:
                        if e.name == u'p':
                            t = e.text
                        
                            if t.startswith('According to the') or t.startswith('Special thanks are') or t.startswith('A complete listing'):
                                purge.append(e)
                else:
                    for e in cruft:
                        purge.append(e)
    
        hrs = body('hr')
    
        if len(hrs) > 0:
            hr = hrs[len(hrs)-1]
            cruft = hr.findNextSiblings()
            cruft_len = len(str(cruft))
        
            if cruft_len <= 300: # Actual lim: 224
                for c in cruft:
                    purge.append(c)
            else:
                if cruft[0].name == u'p' and cruft[0].text.startswith('Previous'):
                    for c in cruft:
                        purge.append(c)
        
        for e in body('hr'):
            purge.append(e)
        
        # 2014-10-16_interlude-ultimatum.xhtml, possibly others.
        for pre in body('pre'):
            code = pre.findChild('code')
            
            if code and code.text == '++':
                purge.append(pre)
        
        # Remove blank filler-paragraphs.
        for p in body('p'):
            if p.text == '&nbsp;' or not p.text.strip():
                purge.append(p)
        
        # Remove all unecessary elements.
        for e in purge:
            print('   DELETE: ' + str(e))
            e.decompose()
        
        # A wee bit of typography.
        ls = ''
        last_open = False
        
        for s in body(text=True):
            nt = ''
            
            for i in range(len(s)):
                cs = s[i]
                
                if cs == '"':
                    if not last_open or ls == ' ':
                        nt += ENT_LQUOT
                        last_open = True
                    else:
                        nt += ENT_RQUOT
                        last_open = False
                else:
                    if cs == '\'':
                        nt += ENT_SQUOT
                    elif cs == '-':
                        nt += ENT_NDASH
                    else:
                        nt += cs
                
                ls = cs
            
            nt = underscore_test.sub('', nt) # 2014-10-22_humans-dont-make-good-pets-part-16-1
            s.replaceWith(nt)
        
        # Convert all page breaks to a centered ellipsis
        # and remove any redundant pagebreaks.
        lbrk = None
        
        for brk in body('p'):
            if brk.text != '' and not bool(break_test(brk.text)):
                # Purge leading or redundant breaks
                if len(brk.findPreviousSiblings()) < 1 or brk.findPreviousSibling('p') == lbrk:
                    brk.decompose()
                else:
                    nbrk = parsed_html.new_tag('div')
                    
                    nbrk['class'] = 'pbreak'
                    nbrk.string = ENT_ELIPS
                    brk.replace_with(nbrk)
            
            lbrk = brk

    # Don't prettify the output. The introduction of additional whitespace
    # around inline tags have undesirable layout effects in some readers.
    return unicode(parsed_html)