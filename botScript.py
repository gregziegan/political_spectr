#!/usr/local/bin/python2.7
import twitter
import random
import re
import os
import shutil
from pyquery import PyQuery
from time import sleep
import requests

victimList = []
politicalData = {}

def getVictimIds():
    ''' Retrieves the ids of posters we've
    already replied to '''

    stats = open('stats.txt').read()
    ids = re.findall(r'\d{6,}', stats)
    return ids


def api_connect():
    ''' Reads in Oauth keys from a separate txt file and returns
    the twitter api
    '''

    keys = open('validationKeys.txt').read().split()
    api = twitter.Api(keys[0], keys[1], keys[2], keys[3])
    return api


def delayActivity():
    ''' Delays posts and other activity for the bot,
    it will post between 10 minutes and 2 hours with a step
    size of 12 minutes
    '''

    sleep(random.randrange(600, 7200, 720))


def grabHTML(url):
    ''' Grabs the html from the url passed in
    (Used to be more verbose with urllib2 but had to use requests instead)
    '''

    html = requests.get(url).text
    return html


def getFriedmanQuotes():

    html = grabHTML('http://en.wikiquote.org/wiki/Milton_Friedman')
    pq = PyQuery(html)
    q = pq('li').find('b').filter(lambda e: 16 < len(PyQuery(this).text()) < 137)
    quotes = []
    for quote in q:
        quotes.append(quote.text)

    return quotes


def getSocialistSongs():
    ''' Gets socialist songs from a wikipedia page and returns
    a dictionary of the titles and their wikipedia urls
    '''

    songs = {}

    url = 'http://en.wikipedia.org/wiki/List_of_socialist_songs'

    html = grabHTML(url)

    m = re.search(r'"Socialist_.*?(<ul>.*?</ul>)', html, re.DOTALL)
    ul = m.group(1)
    pq = PyQuery(ul)
    items = pq('ul').children()

    for item in items:
        txt = pq(item).text()
        m = re.search(r'[^-^"]+', txt)
        title = m.group(0).rstrip()

        ref = pq(item).find('a').attr('href')
        if ref[6:9] != title[:3]:  # hack to determine legit urls
            continue

        link = 'http://en.wikipedia.org' + pq(item).find('a').attr('href')
        songs[title] = link

    return songs


def getSongLyrics(song_url):
    ''' Gets the lyrics of songs from each wikipedia url
        and returns them as a list of strings for each meaningful line
    '''

    lyrics = []

    html = grabHTML(song_url)
    m = re.search(r'("Lyrics|[^<]+_Lyrics).*?</h2>', html, re.DOTALL)
    pq = PyQuery(m.group(0))

    edit = pq('span').filter(lambda i: PyQuery(this).hasClass('mw-editsection'))

    edit_url = 'http://en.wikipedia.org' + edit.children().attr('href')

    html = grabHTML(edit_url)

    pq = PyQuery(html)

    txt = pq('textarea')[0].text
    txt = txt.splitlines()

    not_text = re.compile(r'([<>:\[\]\{\}|=&!]|\\)')

    for line in txt:
        line = line.strip()
        if len(line) < 14 or len(line) > 55:
            continue
        elif not_text.search(line):
            if (line.find('|') != -1 or line.find('{') != -1 or
                    line.find('=') != -1 or line.find('&') != -1 or
                    line.find(r'\\') != -1 or line.lower().find('lyrics') != -1):
                continue
            line = line.replace('[[', '').replace(']]', '').replace(':', '')
            if line.find('<') != -1:
                line = line[:line.find('<')]

        lyrics.append(line.strip())

    return lyrics


def pickLines(songs):
    ''' Returns two random lines from
    socialist song lyrics'''

    # Could have grabbed from web but there was no standard format on pages to read authors
    authors = {'The Internationale': 'Eugene Pottier',
               'Solidarity Forever': 'Ralph Chaplin',
               'The Red Flag': 'Jim Connell',
               'Bella ciao': 'Unknown Socialist'}

    rand = random.choice(songs.keys())
    lyrics = songs[rand]
    author = authors[rand]
    rand = random.randrange(0, len(lyrics) - 1)
    if lyrics[rand + 1][-1] == ',':
        lyric2 = lyrics[rand + 1][:-1]
    else:
        lyric2 = lyrics[rand + 1]

    lines = ' "' + lyrics[rand] + '\n\r' + lyric2 + '" ~ ' + author

    return lines


def conservative_buzzwords():
    ''' Grabs conservative buzzwords and returns a list of them
    Quotes inside are included so Twitter knows to search for those words together
    '''

    buzzwords = ['"states\' rights"', '"activist judges"', '"job killing"',
                 '"welfare mothers"', '"anchor babies"', '"socialist agenda"', '"tax cuts"', '"muslim obama"',
                 '"Barack Hussein Obama"', '"founding fathers"', '"family values"',
                 '"welfare state"', '"unborn baby"', '"socialized medicine"', 'marxism', 'marxist',
                 '"legalized perversion"', '"premarital sex"']

    return buzzwords


def liberal_buzzwords():

    buzzwords = ['fascist', '"economic fairness"', '"corporate pigs"', '"bible thumping"',
                 '"gun toting"', '"american imperialism"', '"working families"',
                 '"economic justice"', '"big oil"', '"hippie culture"']

    return buzzwords


def getVictim(api, buzzwords, ids):
    ''' Searches Twitter for a victim using
    the buzzwords passed in '''

    buzzword = random.choice(buzzwords).lower()

    results = api.GetSearch(buzzword, per_page=50)
    if results:
        victim = random.choice(results)
        if victim.id not in ids and victim.id not in politicalData:
            ids.append(victim.id)
            print 'Searched for %s' % buzzword
            return victim

    getVictim(api, buzzwords, ids)


def makePosts(songs, buzzwords, api, ids):
    ''' Makes a post on Twitter with two lines
        returns id of tweet for data purposes
    '''
    if isinstance(songs, list):
        quote = random.choice(songs)
    else:
        quote = pickLines(songs)

    victim = getVictim(api, buzzwords, ids)
    print '%s said: \n%s' % (victim.user.screen_name, victim.text)
    print '-' * 20 + '\n'
    api.PostUpdate('@' + victim.user.screen_name + ' ' + quote, victim.id)
    print "Posted: %s\n" % quote
    print '-' * 20 + '\n' + '-' * 20 + '\n\n'
    return victim.id


def main():

    if os.path.exists('stats.txt'):
        victimIds = getVictimIds()
    else:
        victimIds = []

    api = api_connect()
    quotes = getFriedmanQuotes()
    buzzwords = conservative_buzzwords()
    songs = getSocialistSongs()

    # Hack for a page that doesn't have a 'Lyrics' section
    del songs['Bandiera Rossa']

    for title, url in songs.items():
        songs[title] = getSongLyrics(url)

    try:
        i = 2

        while True:
            if i % 2 == 0:
                buzzwords = conservative_buzzwords()
                conservative = True
            else:
                buzzwords = liberal_buzzwords()
                conservative = False

            if conservative:
                tweet = makePosts(songs, buzzwords, api, victimIds)
                politicalData['conservative  _offset: ' + str(i)] = tweet
            else:
                tweet = makePosts(quotes, buzzwords, api, victimIds)
                politicalData['liberal  _offset: ' + str(i)] = tweet
            delayActivity()
            i += 1

    except KeyboardInterrupt:

        if os.path.exists('stats.txt'):
            shutil.copy('stats.txt', os.path.join(os.getcwd(), 'oldstats.txt'))

        f = open('stats.txt', 'w')

        for party, tweet in politicalData.items():
            f.write('%s\n' % party + '-' * 20 + '\n%s\n' % tweet + '-' * 20 + '\n')

        f.close()

if __name__ == "__main__":
    main()
