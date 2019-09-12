'''
This script should be run with Python 2.
Modify ini file in script main directory to change any modified data paths or to alter user and password credentials
for FTP Access
'''

from ftplib import FTP
import os, arcpy, shutil, datetime, zipfile, ConfigParser, traceback, sys
from slackclient import SlackClient


try:
    # Set today variable with appropriate format

    today = datetime.datetime.today().strftime('%Y-%m-%d')

    # Set configuration file path

    config = ConfigParser.ConfigParser()
    config.read(r'ftp_config_sample.ini')

    # Set log path

    log_path = config.get('PATHS', 'Log')
    log = open(log_path, "a")

    # Set start-time variable for logging run-times

    StartTime = datetime.datetime.now().replace(microsecond=0)

    # Collect paths for desired DOF files in prep for FTP upload

    dof_dir = {}
    dof_files = []

    dof_path = config.get('PATHS', 'DOF_Path')
    arcpy.env.workspace = dof_path
    exports = arcpy.ListWorkspaces(None, 'FileGDB')

    for workspace in exports:
        workspace_date = workspace.split("_")[3][:-4]
        workspace_date_time = datetime.datetime.strptime(workspace_date, '%Y%m%d')
        dof_dir[workspace_date_time] = workspace

    newest = max(dof_dir)
    print("Most recent DOF export " + str(newest))
    arcpy.env.workspace = dof_dir[newest]

    for table in arcpy.ListTables():
        if table == "Condo":
            print("Adding Condo table to array of desired FTP files")
            dof_files.append(os.path.join(dof_dir[workspace_date_time], table))
        else:
            continue

    datasets = arcpy.ListDatasets()

    for dataset in datasets:
        arcpy.env.workspace = os.path.join(dof_dir[workspace_date_time], dataset)
        fcList = arcpy.ListFeatureClasses()
        for fc in fcList:
            if fc == "Tax_Lot_Polygon" or fc == "Shoreline_Polygon":
                print("Adding Tax Lot Polygon to array of desired FTP files")
                dof_files.append(os.path.join(dof_dir[workspace_date_time], dataset, fc))
            else:
                continue

    # Extract desired DOF files from SDE.

    export_path = config.get('PATHS', 'Export_Path')
    prev_export_files = os.listdir(export_path)

    if not prev_export_files:
        print("Directory is ready for export files")
    else:
        print("Please wait, directory not ready")
        shutil.rmtree(export_path)
        os.makedirs(export_path)
        print("Directory is ready for export files")

    print("The following files will be uploaded to DOF FTP: ")
    print(dof_files)

    for f in dof_files:
        if "Shoreline" in f or "Tax_Lot" in f:
            print("Copying {} to exports directory".format(f))
            arcpy.FeatureClassToShapefile_conversion(f, export_path)
            arcpy.RepairGeometry_management(os.path.join(export_path, f.split('\\')[-1] + '.shp'), True)
        else:
            print("Copying Condo.csv to exports directory")
            arcpy.TableToTable_conversion(f, export_path, "Condo.csv")

    print("DOF files successfully exported to exports folder.")

    # Compress extracted SDE files to a new directory in AutoFTP Project directory called zips

    z_path = config.get('PATHS', 'Z_Path')


    def zip_shapes(path, out_path):
        arcpy.env.workspace = path
        shapes = arcpy.ListFeatureClasses()

        # Zip list of shapefiles
        for shape in shapes:
            name = os.path.splitext(shape)[0]
            print("Zipping the following dataset {}".format(name))
            zip_path = os.path.join(out_path, name + '.zip')
            zip = zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED)
            zip.write(os.path.join(path, shape), shape)
            for f in arcpy.ListFiles('%s*' %name):
                if not f.endswith('.shp'):
                    print("Writing {} to the zip dataset".format(f))
                    zip.write(os.path.join(path, f), f)
            zip.close()


    zip_shapes(export_path, z_path)

    # Check the ftp upload directory prior to uploading to FTP for old files and remove them.
    # Subsequently move in new files

    ftp_read_path = config.get('PATHS', 'FTP_Ready_Path')
    prev_zip_files = os.listdir(ftp_read_path)

    if not prev_zip_files:
        print("Directory is ready for export")
    else:
        print("Please wait, directory not ready")
        shutil.rmtree(ftp_read_path)
        os.makedirs(ftp_read_path)
        print("Directory is ready for export")

    print("Moving Condo table from export directory to ftp ready directory")
    shutil.move(os.path.join(export_path, 'Condo.csv'),
                os.path.join(ftp_read_path, 'Condo.csv'))
    print("Moving Shoreline Polygon FC from export directory to ftp ready directory")
    shutil.move(os.path.join(z_path, 'Shoreline_Polygon.zip'),
                os.path.join(ftp_read_path, 'Shoreline_Polygon.zip'))
    print("Moving Tax Lot Polygon FC from export directory to ftp ready directory")
    shutil.move(os.path.join(z_path, 'Tax_Lot_Polygon.zip'),
                os.path.join(ftp_read_path, 'Tax_Lot_Polygon.zip'))

    # Collect paths for desired DCP zoning files in prep for FTP upload

    dcp_zoning_dir = {}
    dcp_zoning_files = []

    dcp_path = config.get('PATHS', 'DCP_Path')

    directoryList = os.listdir(dcp_path)

    directory_year_list = []

    print("Parsing Zoning folder for most up-to-date directory")
    for directory in directoryList:
        directory_year = datetime.datetime.strptime(directory, '%Y').year
        directory_year_list.append(directory_year)

    for dir_year in directory_year_list:
        max_year = max(directory_year_list)
    print("Most up-to-date directory is {}".format(max_year))

    max_datetime = []

    for directory in directoryList:
        if directory == str(max_year):
            dcp_path_recent_year = os.path.join(dcp_path, directory)
            print("Most recent year folder = " + dcp_path_recent_year)
            for export_dir in os.listdir(dcp_path_recent_year):
                export_dir_target = export_dir[:4] + "20" + export_dir[4:]
                export_dir_time = datetime.datetime.strptime(export_dir_target, '%m%d%Y')
                max_datetime.append(export_dir_time)
                target_dir = max(max_datetime)
                dcp_zoning_dir[target_dir] = export_dir
        else:
            print("Skipping {} because it is not the most recent year".format(directory))

    newest = max(dcp_zoning_dir)
    print("Most recent DCP zoning export " + str(newest))
    zoning_shp_dir = os.path.join(dcp_path_recent_year, dcp_zoning_dir[newest], 'shp')
    print(zoning_shp_dir)

    zip_shp_path = os.path.join(export_path, 'nycgiszoningfeatures_shp.zip')
    zip = zipfile.ZipFile(zip_shp_path, 'w', compression=zipfile.ZIP_DEFLATED)
    for file in os.listdir(zoning_shp_dir):
        if 'nysidewalkcafe' not in file:
            os.chdir(zoning_shp_dir)
            if file.endswith('.shp'):
                arcpy.RepairGeometry_management(os.path.join(zoning_shp_dir, file), True)
            zip.write(file)
            dcp_zoning_files.append(os.path.join(zoning_shp_dir, file))
        else:
            continue
    zip.close()

    print("The following files will be uploaded to DCP FTP: ")
    print(dcp_zoning_files)

    # Collect paths for desired DCP mih files in prep for FTP upload

    dcp_mih_dir = {}
    dcp_mih_files = []

    mih_path = config.get('PATHS', 'MIH_Path')

    directoryList = os.listdir(mih_path)

    directory_year_list = []

    print("Parsing MIH folder for most up-to-date directory")
    for directory in directoryList:
        if len(directory) == 4:
            directory_year = datetime.datetime.strptime(directory, '%Y').year
            directory_year_list.append(directory_year)

    for dir_year in directory_year_list:
        max_year = max(directory_year_list)
    print("Most up-to-date directory is {}".format(max_year))

    max_datetime = []

    for directory in directoryList:
        if directory == str(max_year):
            mih_path_recent_year = os.path.join(mih_path, directory)
            print("Most recent year folder = " + mih_path_recent_year)
            for export_dir in os.listdir(mih_path_recent_year):
                export_dir_time = datetime.datetime.strptime(export_dir, '%Y%m%d')
                max_datetime.append(export_dir_time)
                target_dir = max(max_datetime)
                dcp_mih_dir[target_dir] = export_dir
        else:
            print("Skipping {} because it is not the most recent year".format(directory))

    newest = max(dcp_mih_dir)
    print("Most recent DCP MIH export " + str(newest))
    mih_shp_dir = os.path.join(mih_path_recent_year, dcp_mih_dir[newest], 'shp')
    print(os.path.join(mih_path_recent_year, dcp_mih_dir[newest], 'shp'))

    zip_shp_path = os.path.join(export_path, 'MIH.zip')
    zip = zipfile.ZipFile(zip_shp_path, 'w', compression=zipfile.ZIP_DEFLATED)
    for file in os.listdir(mih_shp_dir):
        print("Repairing and zipping the following file - {}".format(file))
        os.chdir(mih_shp_dir)
        if file.endswith('.shp'):
            arcpy.RepairGeometry_management(os.path.join(mih_shp_dir, file), True)
        zip.write(file)
        dcp_mih_files.append(os.path.join(mih_shp_dir, file))
    zip.close()

    print("The following files will be uploaded to DCP FTP: ")
    print(dcp_mih_files)

    # Connect to FTP with user credentials. Can include credentials in locked text file for added security.

    host_proxy = config.get('PROXY_CREDS', 'Host_Proxy')
    user_proxy = config.get('PROXY_CREDS', 'User_Proxy')
    pass_proxy = config.get('PROXY_CREDS', 'Pass_Proxy')

    user = config.get('FTP_CREDS', 'User')
    password = config.get('FTP_CREDS', 'Password')
    host = config.get('FTP_CREDS', 'Host')

    u = "{user}@{host} {user_prox}".format(user=user, host=host, user_prox=user_proxy)

    ftp = FTP(host_proxy, u, password, pass_proxy)
    print("Connected to FTP server")

    # Upload zoning feature file to FTP.

    ftp.cwd("agencysourcedata/dcp")
    os.chdir(export_path)
    for f in os.listdir(export_path):
        if f.endswith('.zip') and 'nycgiszoningfeatures' in f:
            myfile = open(f, 'rb')
    ftp.storbinary('STOR ' + 'nycgiszoningfeatures_shp.zip', myfile)
    myfile.close()

    # Upload MIH feature file to FTP.

    os.chdir(export_path)
    for f in os.listdir(export_path):
        if f.endswith('.zip') and 'MIH' in f:
            myfile = open(f, 'rb')
    print("Uploading MIH.zip")
    ftp.storbinary('STOR ' + 'MIH.zip', myfile)
    print("MIH.zip upload complete.")
    myfile.close()

    # Upload tax map files to FTP.

    ftp.cwd("../..")
    ftp.cwd("agencysourcedata/dof")
    os.chdir(config.get('PATHS', 'FTP_Ready_Path'))
    ftp_ready_list = os.listdir(ftp_read_path)

    for file in ftp_ready_list:
        print("Uploading " + file)
        myfile = open(file, 'rb')
        ftp.storbinary('STOR ' + file, myfile)
        print(file + " upload complete.")
        myfile.close()

    ftp.close()

    # Variables required for slack connection

    ftp_message = 'Greetings, nyc zoning, condo, shoreline, MIH, and tax lot files have been pushed to FTP ' \
                  'and are currently available for download. Thank you!'

    def send_slack_msg(text_content, credential_section, channel_reference):
        slack_token = config.get(credential_section, 'slack_token')
        icon_url = config.get('RESOURCES', 'icon_url')
        username = config.get('RESOURCES', 'username')
        channel = config.get(credential_section, channel_reference)
        sc = SlackClient(slack_token)
        sc.api_call(
            "chat.postMessage",
            channel=channel,
            username=username,
            text=text_content
        )


    send_slack_msg(ftp_message, "CREDENTIALS", "test_channel_key")

    EndTime = datetime.datetime.now().replace(microsecond=0)
    print("Script runtime: {}".format(EndTime - StartTime))
    log.write(str(StartTime) + "\t" + str(EndTime) + "\t" + str(EndTime - StartTime) + "\n")
    log.close()

except:
    print("error")
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages() + "\n"

    print(pymsg)
    print(msgs)

    log.write("" + pymsg + "\n")
    log.write("" + msgs + "")
    log.write("\n")
    log.close()
