# Standard library
import os
import sys
import shutil
import csv
import re
from datetime import date
from datetime import datetime
import subprocess  # Shamefully not cross-platform, for permissions

# Get from Pip please
import yaml

# NOTES:
#       - Things TPA cannot do:
#           - Skip files without an extension
#           - Skip individual files
#       - A lot of reliance is placed on the calculated file list,
#         if things change after the calculation, things could go screwy.


class BackupJob:
    def __init__(self):
        # Options to be set by user
        self.pathSource = False
        self.lstPathDest = []
        self.dicOpts = {
            'Delete after': False,
            'Check sizes after': False,
            'Reset permissions': True,
            'Skip empty folders': True,
            'Copy invisible files': False,
            'Keep only most recent videos': True
        }
        self.lstFilters = []
        self.lstDirsToSkip = []
        self.strLogFileName = False

        # Will sort out all the files and folders into these lists:
        self.lstDirsVis = []
        self.lstDirsInvis = []
        self.lstFilesVis = []
        self.lstFilesInvis = []
        self.lstFilesWillSkip = []
        self.lstVidsToCopy = []
        self.lstVidsWillSkip = []

        self.countFiles = 0
        self.sizeFiles = 0

        # Stuff to use during copy
        self.progCount = 0
        self.progSize = 0

    def set_source(self, src: str):
        """
        Setter for source
        :param src:
        :return: exception if failure or True if success
        """
        if os.path.isdir(src) or src == False:
            self.pathSource = src
            self.sizeFiles = 0
            self.countFiles = 0
        else:
            raise NotADirectoryError

    def get_source(self) -> str:
        """
        Getter for source
        :return: source as string
        """
        return self.pathSource

    def add_destination(self, dest: str):
        """
        Adds a destination to the list
        :param dest:
        :return: exception if failure or True if success
        """
        if not os.path.isdir(dest):
            raise NotADirectoryError
        elif dest in self.lstPathDest:
            raise ValueError(f"{dest} is already in the list of copy destinations")
        else:
            self.lstPathDest.append(dest)

    def remove_destinations(self, folders):
        """
        Removes destinations from the list
        :param folders: a list of paths or one path as a string
        """
        lstFolders = []
        if isinstance(folders, str):
            lstFolders.append(folders)
        else:
            lstFolders = folders

        for folder in lstFolders:
            if not os.path.isdir(folder):
                raise NotADirectoryError
            elif folder not in self.lstPathDest:
                raise ValueError(f"{folder} is not in the list of copy destinatons.")
            else:
                self.lstPathDest.remove(folder)

    def get_destinations(self) -> list:
        """
        Getter for destinations
        :return: list of folder paths as strings
        """
        return self.lstPathDest

    def set_options(self, dicOpts):
        """
        Setter for options dictionary
        :param dicOpts: a dictionary of options
        """
        # Check the keys in the dict of options given matches the internal dict
        newOpts = set(dicOpts)
        oldOpts = set(self.dicOpts)
        if newOpts == oldOpts:
            self.dicOpts = dicOpts
        else:
            raise ValueError(f"Unexpected/missing option parameters:{max((oldOpts - newOpts, newOpts - oldOpts))}")

    def get_options(self) -> dict:
        """
        Getter for options dictionary
        :return: a dictionary of options
        """
        return self.dicOpts

    def add_dirs_to_skip(self, folders):
        """
        Adds a folder to exclude from the copy.
        """
        # TO DO: Test this with GUI
        lstFolders = []
        if isinstance(folders, str):
            lstFolders.append(folders)
        else:
            lstFolders = folders

        for folder in lstFolders:
            if not os.path.isdir(folder):
                raise NotADirectoryError
            elif folder in self.lstDirsToSkip:
                raise ValueError(f"{folder} is already in the list of folders to exclude from the copy.")
            else:
                self.lstDirsToSkip.append(folder)

    def reset_dirs_to_skip(self):
        """
        Clears list of folders to exclude from the copy
        """
        self.lstDirsToSkip = []

    def remove_dirs_to_skip(self, folders):
        """
        Removes a folder from the list of folders to exclude from the copy
        :param folders: folder (string) or list of folders
        """
        lstFolders = []
        if isinstance(folders, str):
            lstFolders.append(folders)
        else:
            lstFolders = folders

        for folder in lstFolders:
            if not os.path.isdir(folder):
                raise NotADirectoryError
            elif folder not in self.lstDirsToSkip:
                raise ValueError(f"{folder} is not in the list of folders to exclude.")
            else:
                self.lstDirsToSkip.remove(folder)

    def get_dirs_to_skip(self) -> list:
        """
        Getter for list of folders to exclude from the copy
        :return: list of folder paths as strings
        """
        return self.lstDirsToSkip

    def add_filter(self, filters):
        """
        Setter for the list of file types to filter
        Required format: '.ext'
        :param lstFilters: list of filetypes in globbable format to filter
        """
        lstFilters = []
        if isinstance(filters, str):
            lstFilters.append(filters)
        else:
            lstFilters = filters

        # Check list of file types are in globbable format
        goodFormat = re.compile(r'^\.\w+$')
        for extension in lstFilters:
            if goodFormat.match(extension) is not None:
                self.lstFilters.append(extension)
            else:
                raise ValueError(f"{extension} is not a valid file extension. Please use the format '.ext'")

    def get_filters(self) -> list:
        """
        Getter for the list of file types to filter
        :return: list of filetypes
        """
        return self.lstFilters

    def remove_filters(self, filters):
        """
        Remove items from the list of file types to filter
        :param lstFilters: List of filters to be removed (in globbable format)
        """
        lstFilters = []
        if isinstance(filters, str):
            lstFilters.append(filters)
        else:
            lstFilters = filters

        goodFormat = re.compile(r'^\.\w+$')
        for extension in lstFilters:
            if goodFormat.match(extension) is None:
                raise ValueError(f"{extension} is not a valid file extension. Please use the format '.ext'")
            elif extension not in self.lstFilters:
                raise IndexError(f"{extension} is not in the list of file types to exclude.")
            else:
                self.lstFilters.remove(extension)

    @staticmethod
    def extension(filePath: str) -> str:
        """
        Returns the extension of the given file
        :param filePath: file name or path
        :return: str
        """
        return os.path.splitext(filePath)[1].lower()

    @staticmethod
    def choose_files(lstFiles: list) -> tuple:
        """
        Chooses the most recent files from a list of file paths.
        :param lstFiles: a list of file paths
        :return: a tuple containing (list of files to keep, list of files to lose]
        """
        if len(lstFiles) == 1:  # If only one file, return it.
            return(lstFiles[0])

        # Sort the files by date modifed
        lstDateModified = [date.fromtimestamp(os.path.getmtime(x)) for x in lstFiles]
        sorted(lstDateModified, reverse=True)
        sorted(lstFiles, key=os.path.getmtime, reverse=True)
        mostRecentDate = max(lstDateModified)
        lstFilesToKeep = []
        lstFilesToLose = []

        for file in lstFiles:
            if date.fromtimestamp(os.path.getmtime(file)) == mostRecentDate:
                lstFilesToKeep.append(file)
            else:
                lstFilesToLose.append(file)

        return lstFilesToKeep, lstFilesToLose

    @staticmethod
    def human_readable(noOfBytes: int) -> str:
        """
        Translates an int of bytes into a human-readable string
        """
        # 2 **10 = 1024
        power = 2**10
        n = 0
        labels = {
            0: 'B',
            1: 'KB',
            2: 'MB',
            3: 'GB',
            4: 'TB'
        }
        while noOfBytes > power:
            noOfBytes /= power
            n += 1
        noOfBytes = round(noOfBytes, 2)
        return f"{noOfBytes} {labels[n]}"

    def get_file_list(self, recalculate: bool = False) -> list:
        """
        Calculates/returns the list of file paths to be copied.
        Populates the following properties of the BackupJob class:
            self.lstDirsVis
            self.lstDirsInvis
            self.lstFilesVis
            self.lstFilesInvis
            self.lstFilesWillSkip
            self.lstVidsToCopy
            self.lstVidsWillSkip
            self.countFiles
            self.sizeFiles
        :param recalculate: pass if you want to repopulate the list
        :return: list of files to copy
        """

        # return False if no source
        if not self.pathSource:
            return self.pathSource

        # Quick return if applicable
        if not recalculate and (self.lstFilesVis or self.lstFilesInvis):
            if self.dicOpts['Copy invisible files']:
                return self.lstFilesVis + self.lstFilesInvis
            else:
                return self.lstFilesVis
        else:
            # Reset all lists/counters ready to populate anew
            self.lstDirsVis = []
            self.lstDirsInvis = []
            self.lstFilesVis = []
            self.lstFilesInvis = []
            self.lstFilesWillSkip = []
            self.lstVidsToCopy = []
            self.lstVidsWillSkip = []
            self.countFiles = 0
            self.sizeFiles = 0

        # The big walk to populate the lists
        for srcPath, dirs, files in os.walk(self.pathSource):
            # Exclude directories
            if self.dicOpts['Skip empty folders']:
                dirs[:] = [d for d in dirs
                           if os.path.join(srcPath, d) not in self.lstDirsToSkip
                           and self.extension(d) not in self.lstFilters
                           and os.listdir(os.path.join(srcPath, d))]
            else:
                dirs[:] = [d for d in dirs
                           if os.path.join(srcPath, d) not in self.lstDirsToSkip
                           and self.extension(d) not in self.lstFilters]

            # Sort remaining directories into visible and invisible
            for directory in dirs:
                if directory[0] != '.':
                    self.lstDirsVis.append(os.path.join(srcPath, directory))
                else:
                    self.lstDirsInvis.append(os.path.join(srcPath, directory))

            # Exclude file extensions
            self.lstFilesWillSkip += [f for f in files if self.extension(f) in self.lstFilters]
            files[:] = [f for f in files if self.extension(f) not in self.lstFilters]

            # Sort videos into most recent and old
            lstVids = [os.path.join(srcPath, x) for x in files if self.extension(x) in ('.mov', '.mp4')]
            if lstVids:
                if 'VFX' not in srcPath and self.dicOpts['Keep only most recent videos']:
                    tupVids = self.choose_files(lstVids)
                    self.lstVidsToCopy += tupVids[0]
                    self.lstVidsWillSkip += tupVids[1]
                    # Remove old vids from file list
                    files[:] = [f for f in files if os.path.join(srcPath, f) not in tupVids[1]]
                else:
                    # Keep all videos
                    self.lstVidsToCopy += lstVids

            # Sort remaining files into visible and invisible and calculate size
            for file in files:
                if file[0] != '.':
                    self.lstFilesVis.append(os.path.join(srcPath, file))
                    self.sizeFiles += os.path.getsize(os.path.join(srcPath, file))
                else:
                    self.lstFilesInvis.append(os.path.join(srcPath, file))
                    if self.dicOpts['Copy invisible files']:
                        self.sizeFiles += os.path.getsize(os.path.join(srcPath, file))

        lstFiles = self.lstFilesVis + self.lstFilesInvis

        self.countFiles = len(lstFiles)

        return lstFiles

    def get_files_count(self, recalculate: bool = False) -> int:
        """
        Calculate/return the number of files in the list.
        To recalculate, please clear the file count first
        :param recalculate: Pass True to recount the files, default False
        :return: integer count of files in the to-copy list.
        """
        if recalculate:
            self.countFiles = len(self.get_file_list(recalculate=True))
        return self.countFiles

    def get_files_size(self, recalculate: bool = False) -> str:
        """
        Calculate total size of the source files.
        :param recalculate: Pass True to recalculate the file size, default False
        :return: string of human readable file size
        """
        if recalculate:
            self.sizeFiles = sum([os.path.getsize(x) for x in self.get_file_list(recalculate=True)])
        return self.human_readable(self.sizeFiles)

    def save_file_lists(self, directory: str):
        """
        Export CSVs of files to be copied.
        :param directory: the folder to save the csvs
        """
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"{directory} is not a directory!")

        if not os.access(directory, os.W_OK):
            raise PermissionError(f"Cannot write to folder {directory}")

        directory.rstrip('/')
        now = datetime.now()
        filePrefix = f"{directory}/{os.path.basename(self.get_source())} {now.strftime('%Y-%m-%d')} {now.strftime('%H-%M')} "

        fpDirsVis      = filePrefix + 'Directories visible.csv'
        fpDirsInvis    = filePrefix + 'Directories invisible.csv'
        fpFilesVis     = filePrefix + 'Files visible.csv'
        fpFilesInvis   = filePrefix + 'Files invisible.csv'
        fpFilesWillSkip= filePrefix + 'Files to skip.csv'
        fpVidsToCopy   = filePrefix + 'Videos to copy.csv'
        fpVidsWillSkip = filePrefix + 'Videos to skip.csv'

        self.get_file_list()

        with open(fpDirsVis, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i in self.lstDirsVis:
                writer.writerow([i])

        with open(fpDirsInvis, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i in self.lstDirsInvis:
                writer.writerow([i])

        with open(fpFilesVis, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i in self.lstFilesVis:
                writer.writerow([i])

        with open(fpFilesInvis, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i in self.lstFilesInvis:
                writer.writerow([i])

        with open(fpFilesWillSkip, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i in self.lstFilesWillSkip:
                writer.writerow([i])

        with open(fpVidsToCopy, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i in self.lstVidsToCopy:
                writer.writerow([i])

        with open(fpVidsWillSkip, mode='w') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for i in self.lstVidsWillSkip:
                writer.writerow([i])

    def reproduce_folder_structure(self, destPath):
        """
        Creates the necessary folders in the destinations, preserving date modifieds.
        If destPath does not exist, it will be created.
        Will call get_file_list first, in order to be able to function.
        """

        if not self.pathSource:
            return False

        if not self.get_file_list():
            return False

        if self.dicOpts['Copy invisible files']:
            lstDirs = self.lstDirsVis + self.lstDirsInvis
        else:
            lstDirs = self.lstDirsVis

        # Must work from bottom-up to avoid resetting the date-modifieds.
        # If you go top-down, you change the parent folder's date modified to now every time
        # you change the child folder's date modified
        for srcPath, dirs, files in os.walk(self.pathSource, topdown=False):
            # Exclude directories
            dirs[:] = [d for d in dirs if os.path.join(srcPath, d) not in self.lstDirsToSkip]
            if srcPath not in lstDirs:
                continue
            dirToMake = os.path.join(destPath, os.path.relpath(srcPath, self.pathSource))
            if not os.path.isdir(dirToMake):
                try:
                    os.makedirs(dirToMake)
                    self.write_log(srcPath, dirToMake, "Create folder")
                except Exception as e:
                    self.write_log(srcPath, dirToMake, "Create folder", e)
            srcDirStats = os.stat(srcPath)
            destDirStats = os.stat(dirToMake)
            if not (srcDirStats.st_atime, srcDirStats.st_mtime) == (destDirStats.st_atime, destDirStats.st_mtime):
                try:
                    os.utime(dirToMake, (srcDirStats.st_atime, srcDirStats.st_mtime))
                    self.write_log(srcPath, dirToMake, "Set date modified")
                except Exception as e:
                    self.write_log(srcPath, dirToMake, "Set date modified", e)

    def check_folder_permissions(self) -> bool:
        """
        Make sure we have write permissions in all the necessary destination folders
        """
        return all([os.access(dest, os.F_OK | os.W_OK) for dest in self.lstPathDest])

    def check_space_on_drive(self) -> list:
        """
        Make sure we have enough space on the drive to do the copy
        """
        if self.sizeFiles == 0:
            raise ValueError("Please calculate size of copy before checking drive space.")

        return [[x, False] if self.sizeFiles > shutil.disk_usage(x).free else [x, True] for x in self.lstPathDest]

    def copy_files(self, progress=None, index=None):
        """
        Copy the files from the source to the destinations
        progress and index are used for communicating the progress as a multiprocessing child
        """

        drivesWithoutEnoughSpace = [x[0] for x in self.check_space_on_drive() if not x[1]]
        if drivesWithoutEnoughSpace:
            raise IOError(f"Not enough space on the following destinations: {drivesWithoutEnoughSpace[0]}")

        for pathDest in self.lstPathDest:
            self.create_log(pathDest)
            self.reproduce_folder_structure(pathDest)
            self.save_file_lists(pathDest + '/Backup logs')
            for src in self.get_file_list():
                file = os.path.relpath(src, self.pathSource)
                dest = os.path.join(pathDest, file)
                try:
                    shutil.copy2(src, dest)
                    self.write_log(src, dest, "Copy")
                except Exception as e:
                    self.write_log(src, dest, "Copy", e)
                self.progSize += os.path.getsize(src)
                self.progCount += 1
                if progress:
                    progress[index] = self.progSize
            if self.dicOpts['Reset permissions']:
                self.reset_permissions()

        if self.dicOpts['Check sizes after']:
            okayToDelete = self.check_metadata()

        if self.dicOpts['Delete after'] and okayToDelete:
            self.delete_source_files()

    def check_metadata(self):
        """
        Check the file sizes between the source and the destinations after the copy
        """
        allFileSizesMatch = True
        for pathDest in self.lstPathDest:
            for src in self.get_file_list():
                file = os.path.relpath(src, self.pathSource)
                dest = os.path.join(pathDest, file)
                try:
                    if os.path.getsize(src) == os.path.getsize(dest):
                        self.write_log(src, dest, "File sizes match.")
                    else:
                        allFileSizesMatch = False
                        self.write_log(src, dest, "File sizes do not match")
                except Exception as e:
                    self.write_log(src, dest, "Check if file sizes match", e)

        return allFileSizesMatch

    def reset_permissions(self):
        """
        Reset the permissions for the transferred files.
        Currently UNIX only. Please contact developer if you need Windows support.
        """
        if sys.platform == 'darwin':
            for destPath in self.lstPathDest:
                try:
                    subprocess.run(['chmod', '-RN', destPath], check=True)
                    self.write_log("-", destPath, "Recursively cleared all permissions")
                except Exception as e:
                    self.write_log("-", destPath, "Recursively cleared all permissions", e)
        if os.name == 'posix':
            for destPath in self.lstPathDest:
                try:
                    subprocess.run(['chmod', '-R', '777', destPath], check=True)
                    self.write_log("-", destPath, "Recursively set all permissions to read/write")
                except Exception as e:
                    self.write_log("-", destPath, "Recursively set all permissions to read/write", e)

        else:
            return False

        # for destPath in self.lstPathDest:
        #     for path, dirs, files in os.walk(destPath):
        #         for d in dirs:
        #             try:
        #                 os.chmod(path + d, 0o777)
        #                 self.write_log("-", path + d, "Set permissions to read/write")
        #             except Exception as e:
        #                 self.write_log("-", path + d, "Set permissions to read/write", e)
        #         for f in files:
        #             try:
        #                 os.chmod(path + f, 0o777)
        #                 self.write_log("-", path + f, "Set permissions to read/write")
        #             except Exception as e:
        #                 self.write_log("-", path + f, "Set permissions to read/write", e)

    def delete_source_files(self):
        """
        Delete the original sources (preferably once the backups have been verified)
        """
        for srcPath, dirs, files in os.walk(self.pathSource, topdown=False):
            for f in files:
                try:
                    src = os.path.join(srcPath, f)
                    self.write_log(src, '', "Deleting")
                    os.remove(src)
                except Exception as e:
                    self.write_log(src, '', "Deleting", e)
            for d in dirs:
                try:
                    src = os.path.join(srcPath, d)
                    self.write_log(src, '', "Deleting")
                    os.rmdir(src)
                except Exception as e:
                    self.write_log(src, '', "Deleting", e)

    def create_log(self, copyDest: str):
        """
        Writes the first line in the log file (write mode).
        File will be overwritten if it exists
        :param copyDest: the root destination path for the current copy
        """

        today = str(date.today())

        self.strLogFileName = f"{copyDest}/Backup logs/{os.path.basename(self.get_source())} {today} main.csv"
        os.makedirs(os.path.dirname(self.strLogFileName), exist_ok=True)

        with open(self.strLogFileName, 'w', encoding='UTF-8') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerows([
                ["---Job Summary---"],
                [""],
                ["Source:", self.get_source()],
                ["Destinations:"]
            ])
            for i in self.get_destinations():
                writer.writerow(["", i])
            writer.writerow(["Options:"])
            for option, value in self.get_options().items():
                writer.writerow(["", option, value])
            writer.writerow(["Directories to skip:"])
            for i in self.get_dirs_to_skip():
                writer.writerow(["", i])
            writer.writerow(["File types to skip:"])
            for i in self.get_filters():
                writer.writerow(["", i])
            writer.writerows([
                ["Files to copy:", self.get_files_count()],
                ["Total file size:", self.get_files_size()],
                [""],
                ["---Begin log of file operations---"],
                [""]
            ])
            writer.writerow(["Date", "Time", "Source", "Destination", "Action", "Errors"])
            now = datetime.now()
            writer.writerow(
                [now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "-", f"{self.strLogFileName}", "Log file created"],
            )

    def write_log(self, source: str, dest: str, action: str, error: str = ""):
        """
        Writes the actions to a log (append mode).
        :param source: source file path
        :param dest: destination file path
        :param action: the intended operation
        :param error: any error received (optional)
        """
        with open(self.strLogFileName, 'a', encoding='UTF-8') as file:
            writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            now = datetime.now()
            writer.writerow(
                [now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), source, dest, action, error]
            )

    def make_job_dict(self) -> dict:
        """
        Makes a dictionary summary of the job for use by the queue to make a yaml file for saving.
        To be used in conjunction with save_job_yaml function
        :return: dictionary
        """
        dicJob = {
            'Source': self.pathSource,
            'Destinations': self.lstPathDest,
            'Options': self.dicOpts,
            'Folders to skip': self.lstDirsToSkip,
            'File types to filter': self.lstFilters,
            'Number of files to copy': self.countFiles,
            'Total file size': self.sizeFiles
        }

        return dicJob

    def create_from_dict(self, dicJob: dict):
        """
        Configures the job from a dictionary
        :param dicJob:
        """
        self.set_source(dicJob['Source'])
        for i in dicJob['Destinations']:
            self.add_destination(i)
        self.set_options(dicJob['Options'])
        self.add_dirs_to_skip(dicJob['Folders to skip'])
        self.add_filter(dicJob['File types to filter'])
        try:
            self.countFiles = dicJob['Number of files to copy']
        except KeyError:
            pass
        try:
            self.sizeFiles = dicJob['Total file size']
        except KeyError:
            pass


class QueueToBackup:
    def __init__(self, queueFile=None):
        self.lstJobs = []
        self.add_job()

    def get_jobs(self) -> list:
        """
        Getter for the list of jobs.
        :return: The list of BackupJob objects
        """
        return self.lstJobs

    def add_job(self) -> BackupJob:
        # TO DO: error checking here please
        self.lstJobs.append(BackupJob())
        return self.get_jobs()[-1]

    def remove_job(self, indices):
        """
        Removes a job from the queue
        :param indices: the index number of the job in the list
        """
        lstIndices = []
        if isinstance(indices, int):
            lstIndices.append(indices)
        else:
            lstIndices = indices
        # more error checking please
        for index in lstIndices:
            self.lstJobs.pop(index)

    def export_queue_yaml(self, filePath: str):
        """
        Saves the queue as a yaml file.
        :param filePath: the path to save, will be replaced
        """
        lstYaml = []
        for job in self.lstJobs:
            lstYaml.append(job.make_job_dict())

        if not os.access(os.path.dirname(filePath), os.W_OK):
            raise PermissionError(f"Cannot write to folder {os.path.basename(filePath)}")

        with open(filePath, 'w') as file:
            yaml.dump(lstYaml, file)

    def import_queue_yaml(self, pathYaml):
        """
        Adds jobs from a yaml file.
        """
        with open(pathYaml, 'r') as file:
            lstYaml = yaml.full_load(file)

        # If the queue is just a single blank job, get rid of it.
        jobs = self.get_jobs()
        if len(jobs) == 1 and not jobs[0].get_source() and not jobs[0].get_destinations():
            self.remove_job(0)

        for dicYaml in lstYaml:
            newJob = self.add_job()
            newJob.create_from_dict(dicYaml)

    def run_queue(self, progress=None):
        """
        Processes the list of jobs
        """
        for count, job in enumerate(self.get_jobs()):
            job.copy_files(progress, count)


def test_copy():
    job = BackupJob()
    dirPath = ''
    job.set_source(dirPath)
    dirPath = ''
    job.add_destination(dirPath)
    job.set_options(
        {
            'Delete after': False,
            'Check sizes after': False,
            'Reset permissions': True,
            'Skip empty folders': False,
            'Copy invisible files': True,
            'Keep only most recent videos': False
        }
    )
    job.add_filter(['.yaml'])
    job.get_file_list()
    job.copy_files()


if __name__ == '__main__':
    test_copy()

