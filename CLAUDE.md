# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run script: `python "Siterip Scanner.py"`

## Code Style Guidelines
- **Python Version**: Python 2
- **Imports**: Group imports by standard lib, third-party, and local modules
- **Formatting**: Use 4 spaces for indentation
- **Naming**: 
  - Classes: PascalCase
  - Functions/Methods: snake_case
  - Variables: snake_case
- **Documentation**: Docstrings for classes and functions
- **Error Handling**: Use try/except blocks with specific exceptions
- **Logging**: Use the logging module as configured in the code
- **File Structure**: Maintain the existing structure for Plex compatibility

This is a legacy Plex Media Server scanner plugin for organizing media files from siterips into a structured format for the Plex library. It relies on Plex's Python 2 environment and specific imports from the Plex Media Server codebase.