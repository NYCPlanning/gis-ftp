# FTP Upload

*******************************

FTP Upload script is used for uploading nyc zoning features, MIH polygon, tax lot polygon, and other requisite files to FTP server so that Data Engineering may utilize them for data set generation.

### Prerequisites

An installation of Python 2 with the following packages is required to run. Additionally, credentials for accessing the FTP are required. 

##### FTP_Upload.py

```
ftplib, os, shutil, arcpy, datetime, zipfile, traceback, sys, ConfigParser
```

### Instructions for running

##### FTP_Upload.py

1. Open the config.ini file and ensure that all data paths and user credentials are up-to-date.

2. Open the script in any integrated development environment (PyCharm is suggested)

3. Run the script. It will pull the following datasets from DCP local network file-system: [Condos, Shoreline Polygon, Tax Lot Polygon, MIH]. All files will be brought into the export sub-directory within the script’s root directory. Files within the export directory will be packaged in either exports or zips directories. After zipping, the files are uploaded to the requisite directory on the FTP. 

