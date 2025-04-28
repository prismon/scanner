#!/usr/bin/env python

#     Copyright (C) 2013  Casey Duquette
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.


import sys
sys.path.append("/Users/josh/Library/Application Support/Plex Media Server/Scanners/Series")
sys.path.append("/Applications/Plex Media Server.app/Contents/Resources/Plug-ins-12f6b8c83/Scanners.bundle/Contents/Resources/Common/");

import re, os, os.path
import sys
import re, os, os.path, datetime
import Media, VideoFiles, Stack, Utils
from mp4file import mp4file, atomsearch
import logging, logging.handlers
import inspect
import time

os.system("logger -p user.error starting siterip")

logging.basicConfig(filename='/tmp/scan.log',level=logging.DEBUG)

logging.info("Siterip scanner starting")

class Section:
    """Represents a section."""
    title = "Root of a section"
    shows = {}
    path = ""

    def findOrCreateShow(self , path):
        if path in self.shows:
            return self.shows[path]
        
        self.shows[path] = Show()
        self.shows[path].title = path
        self.shows[path].path = os.path.join(self.path, path)

        return self.shows[path]



rootSection = Section()

class Show:
    """A simple example class"""
    title = "Untitled"

    seasonCount = 1
    showNumber = 0
    path = ""
    seasons = {}
    def __init__(self):
        # body of the constructor
        self.seasons["Unsorted"] = Season()
        self.seasons["Unsorted"].title = "Unsorted"
        self.seasons["Unsorted"].episodeCount = 0
        self.seasons["Unsorted"].season = 1000000
        self.seasonCount=1

    def findOrCreateSeason(self , path):
        if path in self.seasons:
            return self.seasons[path]
        
        self.seasons[path] = Season()
        self.seasons[path].title = path
        self.seasons[path].path = os.path.join(self.path, path)
        self.seasons[path].season = self.seasonCount
        self.seasonCount +=1
        

        return self.seasons[path]



class Season:
    """A simple example class"""
    episodeCount = 0
    episodes = {}
    path = ""

    title = "Untitled"

    def f(self):
        return 'hello world'

class Episode:
    episodeNumber = 0
    path = ""
    title = "Untitled"

class SiteripDirectory:
    """A simple example class"""

    shows = {}
    seasonCount = 0

    def registerPath(self, root, path):

        if path is None or len(path) == 0:
            return rootSection

        # Strip the root out of the path:
        paths = os.path.split(path)
        common_prefix = os.path.commonprefix([root, path])
        cleanPath = path[len(common_prefix):]

        cleanPaths = os.path.normpath(cleanPath)
        components = cleanPaths.split(os.sep)

  
        while("" in components) :
            components.remove("")

        # we have a show to handle. First see if we have a pre-existing show definition. 
        logging.debug("Found a show ")
        logging.debug(components)
        show = rootSection.findOrCreateShow(components[0])
    
        if len(components) == 1:   
            return show

        # Now we have to find the second. We do that on the next component. Note that we fall back to season 0 for anything in the show directory. 

        season = show.findOrCreateSeason(components[1])
        return season

    def registerFile(self, root, path):

            # Strip the root out of the path:
            paths = os.path.split(path)
            common_prefix = os.path.commonprefix([root, path])
            cleanPath = path[len(common_prefix):]

            cleanPaths = os.path.normpath(cleanPath)
            components = cleanPaths.split(os.sep)
  
            while("" in components) :
                components.remove("")

            show = rootSection.findOrCreateShow(components[0])
            logging.debug("Found a show")
            logging.debug(components)

            season = {}

            # FIXME - What about root behavior?
            if len(components) >2 :
                season = show.findOrCreateSeason(components[1])
            else:
                season = show.findOrCreateSeason("Unsorted")


            season.episodeCount+=1; 
            name = os.path.basename(path)

            media = Media.Episode(show.title, season.season, season.episodeCount, name, None)
            media.parts.append(path)
            return media






def Scan(path, files, mediaList, subdirs, language=None, root=None, **kwargs):
    logging.info("SCANNING-----------------------------------------------------------------")
    logging.info("Path:")
    logging.info (path)
    logging.info("Files:")
    logging.info (files)
    logging.info("Media List:")
    logging.info (mediaList)
    logging.info("Subdirs:")
    logging.info (subdirs)
    logging.info("Language:")
    logging.info (language)
    logging.info("Root:")
    logging.info (root)


    siterip.registerPath(root, path)


    for subdir in subdirs:
        siterip.registerPath(root, subdir)
    

    VideoFiles.Scan(path, files, mediaList, subdirs, root)

    for file in files:

        media=siterip.registerFile(root, file)
        mediaList.append(media)

        #me#dia = Media.Episode(show.title, season.season, season.episodeCount, None, year)
        #media.parts.append(file)
        #mediaList.append(media)
        #logging.info ("---season ")
        #logging.info( season.season)
        #logging.info ("---title ")
        #logging.info( show.title)
        #logging.info ("---episode ")
        #logging.info( episode)

        #logging.info("appended ")
        #logging.info(file)

    logging.info(files)
    
siterip = SiteripDirectory()

   
if __name__ == '__main__':  #command line
  
  path  = ""
  files = []
  subdirs = ['/Volumes/vol/scan/Ellery Corin/']
  media = []
  root = "/Volumes/vol/scan"
  Scan(path, files, media, subdirs, [], root)

  logging.info(media)

  path  = "Ellery Corin"
  files = ["/Volumes/vol/scan/Ellery Corin/test.mp4"]
  subdirs = ['/Volumes/vol/scan/Ellery Corin/01 - FTV - Mindy - Come in My Place', '/Volumes/vol/scan/Ellery Corin/02 - FTV - Mindy - I Can be Extreme Too'];
  media = []
  root = "/Volumes/vol/scan"
  Scan(path, files, media, subdirs, [], root)

  logging.info(media)

  path  = "Ellery Corin/01 - FTV - Mindy - Come in My Place"
  files = ['/Volumes/vol/scan/Ellery Corin/01 - FTV - Mindy - Come in My Place/mindy-00006607-01-1080p.mp4', '/Volumes/vol/scan/Ellery Corin/01 - FTV - Mindy - Come in My Place/mindy-00006607-02-1080p.mp4', '/Volumes/vol/scan/Ellery Corin/01 - FTV - Mindy - Come in My Place/mindy-00006607-03-1080p.mp4', '/Volumes/vol/scan/Ellery Corin/01 - FTV - Mindy - Come in My Place/mindy-00006607-04-1080p.mp4', '/Volumes/vol/scan/Ellery Corin/01 - FTV - Mindy - Come in My Place/mindy-00006607-05-1080p.mp4']
  media = []
  root = "/Volumes/vol/scan"
  Scan(path, files, media, [], [], root)

  logging.info(media)

#if __name__ == '__main__':  #command line
#  path  = ""
#  files = ["/Volumes/vol/scan/Exhibitionism/My Girlfriend's Mother on the Beach.mp4"]
#  media = []
#  Scan(path[1:], files, media, [], [], "/Volumes/vol/scan")
