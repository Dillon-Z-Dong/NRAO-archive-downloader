# NRAO-archive-downloader
Automatable searches and downloads from the NRAO archive which at the moment has no official API. 

- Currently using Selenium (https://www.selenium.dev/) to directly interact with javascript elements in the archive website. archive_downloader.py can be used to download a ms if you know the project code and SB/EB code.

- Programatic searches through RESTful API (https://restfulapi.net/) with restful_api_interface.py. 

Todo:
- Replace Selenium downloads with RESTful API calls