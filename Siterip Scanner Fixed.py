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
# Append Plex scanner paths (adjust as needed)
sys.path.append("/Users/josh/Library/Application Support/Plex Media Server/Scanners/Series")
sys.path.append("/Applications/Plex Media Server.app/Contents/Resources/Plug-ins-12f6b8c83/Scanners.bundle/Contents/Resources/Common/")
import re, os, os.path, datetime
import json

# Load persistent season mapping
MAPPING_FILE = os.path.join(os.path.dirname(__file__), 'season_map.json')
try:
    with open(MAPPING_FILE, 'r') as f:
        SEASON_MAP = json.load(f)
except Exception:
    SEASON_MAP = {}
try:
    import Media, VideoFiles, Stack, Utils
    from mp4file import mp4file, atomsearch
except ImportError:
    # Local testing stubs for Plex modules
    import types
    Media = types.ModuleType('Media')
    VideoFiles = types.ModuleType('VideoFiles')
    Stack = types.ModuleType('Stack')
    Utils = types.ModuleType('Utils')
    _mp4 = types.ModuleType('mp4file')
    _mp4.mp4file = None
    _mp4.atomsearch = None
    # Ensure stub modules are available if re-imported
    sys.modules['Media'] = Media
    sys.modules['VideoFiles'] = VideoFiles
    sys.modules['Stack'] = Stack
    sys.modules['Utils'] = Utils
    sys.modules['mp4file'] = _mp4
import logging, logging.handlers
import inspect
import time

os.system("logger -p user.error starting siterip")

try:
    # Initialize logging to console if file not writable
    logging.basicConfig(level=logging.DEBUG)
except Exception:
    # Fallback: basic configuration without file output
    logging.basicConfig()

logging.info("Siterip scanner starting")

class Section:
    """Represents a section."""
    title = "Root of a section"
    path = ""
    def __init__(self):
        # Initialize shows mapping for this section instance
        self.shows = {}
        self.path = ""

    def findOrCreateShow(self, path):
        if path in self.shows:
            return self.shows[path]

        self.shows[path] = Show()
        show = self.shows[path]
        show.title = path
        show.path = os.path.join(self.path, path)

        # Seed existing seasons from persistent mapping
        mapping = SEASON_MAP.get(path, {})
        if mapping:
            max_season = max(mapping.values())
            show.seasonCount = max_season + 1
            for season_name, season_num in mapping.items():
                if season_name == "Unsorted":
                    continue
                season = Season()
                season.title = season_name
                season.path = os.path.join(show.path, season_name)
                season.season = season_num
                show.seasons[season_name] = season

        return show

rootSection = Section()

class Show:
    """Represents a TV show"""
    title = "Untitled"

    seasonCount = 1
    showNumber = 0
    path = ""
    seasons = {}
    
    def __init__(self):
        # body of the constructor
        self.seasons = {}
        # Initialize an "Unsorted" season for files directly in the show folder (season 10000)
        unsorted = Season()
        unsorted.title = "Unsorted"
        unsorted.episodeCount = 0
        unsorted.season = 10000
        self.seasons["Unsorted"] = unsorted
        # Next created seasons will start from 1
        self.seasonCount = 1

    def findOrCreateSeason(self, path):
        if path in self.seasons:
            return self.seasons[path]

        # Determine season number using persistent mapping
        show_name = self.title
        mapping = SEASON_MAP.setdefault(show_name, {})
        
        if path in mapping:
            # Always use existing mapping if available
            season_num = mapping[path]
        else:
            # This is a new season that needs to be assigned a season number
            # based on alphabetical order (case insensitive)
            
            # First get all season names (including those with saved mapping and those
            # that were just created in this session)
            all_season_names = list(self.seasons.keys())
            for sname in mapping.keys():
                if sname not in all_season_names and sname != "Unsorted":
                    all_season_names.append(sname)
                    
            # Sort all season names alphabetically (case insensitive)
            # Exclude "Unsorted" which is always special
            sorted_seasons = sorted([s for s in all_season_names if s != "Unsorted"], 
                                   key=lambda x: x.lower())
            
            # Find position of this season in the sorted list
            try:
                position = sorted_seasons.index(path)
            except ValueError:
                # Should not happen, but add it to the end if it does
                sorted_seasons.append(path)
                position = len(sorted_seasons) - 1
                
            # Assign season numbers sequentially based on alphabetical position
            # Starting with 1 for the first season
            new_numbers = {}
            for i, season_name in enumerate(sorted_seasons):
                # If season already has a mapping, preserve it
                if season_name in mapping:
                    new_numbers[season_name] = mapping[season_name]
                else:
                    # Find the next available season number
                    next_num = 1
                    while next_num in new_numbers.values():
                        next_num += 1
                    new_numbers[season_name] = next_num
            
            # Use the newly assigned season number
            season_num = new_numbers[path]
            
            # Update all mappings at once
            mapping.update(new_numbers)
            # Persist updated mapping
            try:
                with open(MAPPING_FILE, 'w') as f:
                    json.dump(SEASON_MAP, f, indent=4, sort_keys=True)
            except Exception as e:
                logging.warning("Failed to write season map: %s", e)

        season = Season()
        season.title = path
        season.path = os.path.join(self.path, path)
        season.season = season_num
        self.seasons[path] = season
        return season

class Season:
    """Represents a TV season"""
    episodeCount = 0
    episodes = {}
    path = ""
    title = "Untitled"
    season = 0  # Fix: Add default season number

class Episode:
    """Represents a TV episode"""
    episodeNumber = 0
    path = ""
    title = "Untitled"

class SiteripDirectory:
    """Handles directory structure parsing for siterips"""

    def __init__(self):
        self.shows = {}

    def _get_path_components(self, root, path):
        """Extract normalized path components relative to root"""
        # Get the common prefix
        common_prefix = os.path.commonprefix([root, path])
        # Strip the root path
        clean_path = path[len(common_prefix):]
        # Normalize path (handle different separators)
        clean_path = os.path.normpath(clean_path)
        # Split into components and filter empty strings
        components = [comp for comp in clean_path.split(os.sep) if comp]
        
        return components

    def registerPath(self, root, path):
        """Register a directory path in the structure"""
        logging.debug("registerPath: %s", path)
        # Ignore empty paths
        if not path:
            return rootSection
        # Extract path components relative to root
        components = self._get_path_components(root, path)
        if not components:
            return rootSection
        # First component is always the show name
        logging.debug("registerPath components: %s", components)
        show = rootSection.findOrCreateShow(components[0])
        # If this is the show folder itself
        if len(components) == 1:
            return show
        # If this is a direct subfolder under the show, register as its own season
        if len(components) == 2:
            return show.findOrCreateSeason(components[1])
        # Deeper nested folders are ignored (flattened into show)
        return show

    def registerFile(self, root, path):
        """Register a file in the structure and return appropriate Media object"""
        logging.debug("registerFile: %s", path)
        # Extract path components relative to root
        components = self._get_path_components(root, path)
        if not components:
            logging.warning("No components found for file: %s", path)
            return None
        # First component is always the show name
        show = rootSection.findOrCreateShow(components[0])
        logging.debug("registerFile components: %s", components)
        # Determine directory depth before the file (exclude the file name)
        dirs = components[:-1]
        # Assign season based on directory depth: use first subfolder as season for any depth >=2
        if len(dirs) >= 2:
            # Any nested file under a season folder belongs to that season
            season = show.findOrCreateSeason(dirs[1])
        else:
            # File directly in the show folder -> Unsorted season
            season = show.seasons.get("Unsorted")
        
        # Increment episode count for this season
        season.episodeCount += 1
        
        # Get the base filename for the episode title
        name = os.path.basename(path)
        
        # Create the Media.Episode object for Plex
        media = Media.Episode(show.title, season.season, season.episodeCount, name, None)
        media.parts.append(path)
        
        return media

def Scan(path, files, mediaList, subdirs, language=None, root=None, **kwargs):
    """Main scanner function called by Plex"""
    logging.info("SCANNING-----------------------------------------------------------------")
    logging.info("Path: %s", path)
    logging.info("Files: %s", files)
    logging.info("Subdirs: %s", subdirs)
    logging.info("Root: %s", root)
    # Debug: optionally capture input parameters for later analysis
    if os.getenv('SITERIP_CAPTURE_PARAMS', '0') == '1':
        try:
            record = {
                'timestamp': datetime.datetime.now().isoformat(),
                'path': path,
                'files': files,
                'subdirs': subdirs,
                'root': root,
                'language': language,
                'extras': kwargs
            }
            with open('/tmp/siterip_scan_params.txt', 'a') as dbg:
                dbg.write(json.dumps(record) + '\n')
        except Exception:
            logging.exception('Failed to write debug scan parameters')

    # Register the current path in our structure
    siterip.registerPath(root, path)

    # Register all subdirectories
    for subdir in subdirs:
        siterip.registerPath(root, subdir)

    # Let the VideoFiles helper process these files
    # (this will filter out non-video files)
    VideoFiles.Scan(path, files, mediaList, subdirs, root)

    # Process each video file
    for file in files:
        media = siterip.registerFile(root, file)
        if media:
            mediaList.append(media)
    
    logging.info("Media found: %s", mediaList)

# Initialize the global siterip directory handler
siterip = SiteripDirectory()

if __name__ == '__main__':
    # Clear persistent mapping for tests
    try:
        os.remove(MAPPING_FILE)
    except Exception:
        pass
    SEASON_MAP.clear()
    # ---- Dummy stubs for testing without Plex dependencies ----
    # Simple Episode stub matching Media.Episode signature
    class DummyEpisode:
        def __init__(self, show, season, epnum, name, _):
            self.show = show
            self.season = season
            self.episode = epnum
            self.name = name
            self.parts = []
        def __repr__(self):
            return '<Episode show=%r season=%r ep=%r name=%r parts=%r>' % (
                self.show, self.season, self.episode, self.name, self.parts)
    # Monkey-patch Media.Episode and VideoFiles.Scan for local tests
    Media.Episode = DummyEpisode
    VideoFiles.Scan = lambda path, files, mediaList, subdirs, root: None

    # Define test scenarios
    tests = [
        {
            'name': 'Test1: register show only',
            'root': '/root',
            'path': '',
            'files': [],
            'subdirs': ['/root/Show1'],
        },
        {
            'name': 'Test2: file in top-level show folder',
            'root': '/root',
            'path': 'Show1',
            'files': ['/root/Show1/test.mp4'],
            'subdirs': ['/root/Show1/SeasonA'],
        },
        {
            'name': 'Test3: files in season and nested subfolder',
            'root': '/root',
            'path': 'Show2',
            'files': ['/root/Show2/Season1/ep1.mp4', '/root/Show2/Season1/Sub/ep2.mp4'],
            'subdirs': ['/root/Show2/Season1', '/root/Show2/Season1/Sub'],
        },
        {
            'name': 'Test4: new folder earlier in alphabet assigned new season',
            'root': '/root',
            'path': 'Show2',
            'files': ['/root/Show2/Season1/ep1.mp4', '/root/Show2/A-New-Season/epA.mp4'],
            'subdirs': ['/root/Show2/A-New-Season', '/root/Show2/Season1'],
        },
        {
            'name': 'Test5: alphabetical ordering test with multiple new folders',
            'root': '/root',
            'path': 'Show3',
            'files': ['/root/Show3/C-Middle/ep1.mp4', '/root/Show3/A-First/ep2.mp4', '/root/Show3/z-Last/ep3.mp4', '/root/Show3/B-Second/ep4.mp4'],
            'subdirs': ['/root/Show3/C-Middle', '/root/Show3/A-First', '/root/Show3/z-Last', '/root/Show3/B-Second'],
        },
        {
            'name': 'Test6: case insensitive alphabetical ordering',
            'root': '/root',
            'path': 'Show4',
            'files': ['/root/Show4/FIRST/ep1.mp4', '/root/Show4/second/ep2.mp4', '/root/Show4/Third/ep3.mp4'],
            'subdirs': ['/root/Show4/FIRST', '/root/Show4/second', '/root/Show4/Third'],
        },
        {
            'name': 'Test7: preserves existing mappings while adding new seasons alphabetically',
            'root': '/root',
            'path': 'Show5',
            'files': [],
            'subdirs': ['/root/Show5/B-Second', '/root/Show5/D-Fourth'],
            'setup': {
                'show': 'Show5',
                'seasons': {
                    'B-Second': 2,  # Already mapped
                    'C-Third': 3,   # Already mapped but folder not present
                }
            }
        },
        {
            'name': 'Test8: adding a season in middle of alphabet',
            'root': '/root',
            'path': 'Show5',
            'files': [
                '/root/Show5/B-Second/file1.mp4',
                '/root/Show5/C-Third/file2.mp4',
                '/root/Show5/D-Fourth/file3.mp4',
                '/root/Show5/A-First/file4.mp4'
            ],
            'subdirs': ['/root/Show5/B-Second', '/root/Show5/C-Third', '/root/Show5/D-Fourth', '/root/Show5/A-First'],
        },
        {
            'name': 'Test9: inserting a season at beginning of alphabet',
            'root': '/root',
            'path': 'Show6',
            'files': [
                '/root/Show6/C-Third/file1.mp4',
                '/root/Show6/D-Fourth/file2.mp4'
            ],
            'subdirs': ['/root/Show6/C-Third', '/root/Show6/D-Fourth'],
            'setup': {
                'show': 'Show6',
                'seasons': {
                    'C-Third': 1,
                    'D-Fourth': 2
                }
            }
        },
        {
            'name': 'Test10: add files to season that alphabetically comes first',
            'root': '/root',
            'path': 'Show6',
            'files': [
                '/root/Show6/C-Third/file1.mp4',
                '/root/Show6/D-Fourth/file2.mp4',
                '/root/Show6/A-First/newfile.mp4'
            ],
            'subdirs': ['/root/Show6/C-Third', '/root/Show6/D-Fourth', '/root/Show6/A-First'],
        },
    ]
    # Run tests
    for t in tests:
        # Reset global structure for each test
        rootSection = Section()
        siterip = SiteripDirectory()
        media = []
        
        # Setup existing mappings if provided
        if 'setup' in t:
            setup = t['setup']
            show_name = setup.get('show')
            seasons = setup.get('seasons', {})
            if show_name and seasons:
                SEASON_MAP[show_name] = seasons.copy()
        
        # Run the scan
        Scan(t['path'], t.get('files', []), media, t.get('subdirs', []), None, t['root'])
        
        # Display test result
        print('%s -> %s' % (t['name'], media))
        
        # If there are seasons in this test, print their mappings for verification
        if media and t['path'] and 'Show' in t['path']:
            show_name = t['path'].split('/')[0]
            if show_name in SEASON_MAP:
                print('  Season mappings for %s: %s' % (show_name, SEASON_MAP[show_name]))
