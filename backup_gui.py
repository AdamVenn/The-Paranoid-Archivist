import os
import datetime as dt
from time import sleep
import multiprocessing
import threading

import wx
from wx.lib.newevent import NewEvent
import wx.adv

from backup_data import BackupJob, QueueToBackup

# TO DO:
#   - Raise all errors to messageboxes
#   - Make decorator for any button that populates the job to get the current job in readable form and do nothing if no current job


EvtUpdateScheduleText, EVT_SCHEDULE = NewEvent()
EvtUpdateProgress, EVT_PROGRESS = NewEvent()


class FrMainwindow(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="Double Archive")

        self.init_menu()
        self.init_gui()

        # Bind frame to event to change queue schedule text
        self.Bind(EVT_SCHEDULE, self.update_queue_text)
        self.Bind(EVT_PROGRESS, self.update_progress_column)

        # Variables
        self.queue = QueueToBackup()
        self.intCurrentJob = 0
        self.cancelButSchedule = False  # State of schedule button
        self.cancelCountdown = False  # Variable to abort countdown thread
        self.cancelButLaunch = False  # State of launch now button

        # Initalise GUI content
        self.populate_job_summary()
        self.populate_job_queue()

        # Display window
        self.Maximize(True)
        self.Show()

    def init_menu(self):
        menuBar = wx.MenuBar()
        menuFile = wx.Menu()
        pass
        # menuItemAddSource = menuFile.Append(
        #     wx.ID_ANY,
        #     "Add source folder",
        #     "Add a folder to the backup queue"
        # )
        # menuBar.Append(menuFile, '&File')
        #
        # # Bind menu functions
        # self.Bind(
        #     event=wx.EVT_MENU,
        #     handler=self.on_add_source,
        #     source=menuItemAddSource
        # )
        # self.SetMenuBar(menuBar)

    def init_gui(self):
        self.panMaster = wx.Panel(self)
        sizerGrid = wx.GridBagSizer(vgap=1, hgap=1)
        colsInGrid = 4
        rowsInGrid = 2
        # That's right! A 2D array of FlexGrid Sizers!
        # Complicated, yes, but growable, iterable and accessible by co-ordinate.
        lstBoxes = [[wx.FlexGridSizer(1, 1, 1) for i in range(colsInGrid)] for j in range(rowsInGrid)]

        # These cells will be 'spanned' into
        lstBoxes[1][2] = None
        lstBoxes[1][3] = None

        # ==========   Adding box sizers to the gridbag   ==========
        # --- Source ---
        self.txtSrc = wx.StaticText(self.panMaster, label="Source")
        self.filePickSrc = wx.GenericDirCtrl(self.panMaster)
        self.filePickSrc.ShowHidden(False)
        self.filePickSrc.CollapseTree()
        self.filePickSrc.Bind(wx.EVT_CHAR_HOOK, self.on_keySrc)

        boxSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.butSrc = wx.Button(self.panMaster, label="Choose as source")
        self.butSrc.Bind(wx.EVT_BUTTON, self.on_butSrc)
        self.butExclude = wx.Button(self.panMaster, label="Exclude this folder")
        self.butExclude.Bind(wx.EVT_BUTTON, self.on_butExclude)
        boxSizer.Add(self.butSrc, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        boxSizer.Add(self.butExclude, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        lstBoxes[0][0].Add(self.txtSrc, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        lstBoxes[0][0].Add(self.filePickSrc, 1, wx.ALL | wx.EXPAND, 5)
        lstBoxes[0][0].AddGrowableRow(1)
        lstBoxes[0][0].AddGrowableCol(0)
        lstBoxes[0][0].Add(boxSizer, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        # --- Destination 1 ---
        self.txtDest1 = wx.StaticText(self.panMaster, label="Destination")
        self.filePickDest1 = wx.GenericDirCtrl(self.panMaster, style=wx.DIRCTRL_DIR_ONLY)
        self.filePickDest1.ShowHidden(False)
        self.filePickDest1.CollapseTree()
        self.filePickDest1.Bind(wx.EVT_CHAR_HOOK, self.on_keyDest1)

        boxSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.butDest1 = wx.Button(self.panMaster, label="Choose as a destination")
        self.butDest1.Bind(wx.EVT_BUTTON, self.on_butDest1)
        self.butMakeChoose1 = wx.Button(self.panMaster, label="Create/choose folder")
        self.butMakeChoose1.Bind(wx.EVT_BUTTON, self.on_butMakeChoose1)
        boxSizer.Add(self.butDest1, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        boxSizer.Add(self.butMakeChoose1, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        lstBoxes[1][0].Add(self.txtDest1, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        lstBoxes[1][0].Add(self.filePickDest1, 1, wx.ALL | wx.EXPAND, 5)
        lstBoxes[1][0].AddGrowableRow(1)
        lstBoxes[1][0].AddGrowableCol(0)
        lstBoxes[1][0].Add(boxSizer, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        # --- Destination 2 ---
        self.txtDest2 = wx.StaticText(self.panMaster, label="Destination")
        self.filePickDest2 = wx.GenericDirCtrl(self.panMaster, style=wx.DIRCTRL_DIR_ONLY)
        self.filePickDest2.ShowHidden(False)
        self.filePickDest2.CollapseTree()
        self.filePickDest2.Bind(wx.EVT_CHAR_HOOK, self.on_keyDest2)

        boxSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.butDest2 = wx.Button(self.panMaster, label="Choose as a destination")
        self.butDest2.Bind(wx.EVT_BUTTON, self.on_butDest2)
        self.butMakeChoose2 = wx.Button(self.panMaster, label="Create/choose folder")
        self.butMakeChoose2.Bind(wx.EVT_BUTTON, self.on_butMakeChoose2)
        boxSizer.Add(self.butDest2, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        boxSizer.Add(self.butMakeChoose2, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        lstBoxes[1][1].Add(self.txtDest2, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        lstBoxes[1][1].Add(self.filePickDest2, 1, wx.ALL | wx.EXPAND, 5)
        lstBoxes[1][1].AddGrowableRow(1)
        lstBoxes[1][1].AddGrowableCol(0)
        lstBoxes[1][1].Add(boxSizer, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        # --- Options ---
        self.txtOptions = wx.StaticText(self.panMaster, label="Options")
        lstBoxes[0][1].Add(self.txtOptions, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        self.boxOpts = wx.StaticBox(self.panMaster, label="Settings for this job")
        self.boxOptsSizer = wx.StaticBoxSizer(self.boxOpts, wx.VERTICAL)
        dummy = BackupJob()
        self.dicChkBoxes = {x: wx.CheckBox(self.panMaster, label=x) for x in dummy.get_options()}
        for chkBoxOpt in self.dicChkBoxes.values():
            self.boxOptsSizer.Add(chkBoxOpt)
            self.Bind(wx.EVT_CHECKBOX, self.on_chkBox, chkBoxOpt)
        lstBoxes[0][1].Add(self.boxOptsSizer, 1, wx.ALL | wx.EXPAND, 5)

        buttonBox = wx.StaticBox(self.panMaster, label="Exclude file types")
        buttonBoxSizer = wx.StaticBoxSizer(buttonBox, wx.VERTICAL)
        self.entFilter = wx.TextCtrl(self.panMaster, style=wx.TE_PROCESS_ENTER)
        self.butFilter = wx.Button(self.panMaster, label="Exclude")
        self.butFilter.Bind(wx.EVT_BUTTON, self.on_butFilter)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_butFilter, self.entFilter)
        buttonBoxSizer.Add(self.entFilter, 1, wx.ALL | wx.ALIGN_LEFT, 5)
        buttonBoxSizer.Add(self.butFilter, 1, wx.ALL | wx.ALIGN_LEFT, 5)
        lstBoxes[0][1].Add(buttonBoxSizer, 1, wx.ALL | wx.EXPAND, 5)

        lstBoxes[0][1].AddGrowableCol(0)
        lstBoxes[0][1].AddStretchSpacer(1)

        # --- Job Summary ---
        self.txtDetails = wx.StaticText(self.panMaster, label="Job Summary")

        infoBox = wx.StaticBox(self.panMaster, label="Details for this job")
        infoBoxSizer = wx.StaticBoxSizer(infoBox, wx.VERTICAL)
        self.txtSrc = wx.StaticText(self.panMaster, label="Source")
        self.lstBoxSrc = wx.ListBox(self.panMaster, size=(10, 25))  # Should find a clever way to make it one line big
        self.txtDest = wx.StaticText(self.panMaster, label="Destinations")
        self.lstBoxDest = wx.ListBox(self.panMaster, style=wx.LB_MULTIPLE)
        self.lstBoxDest.Bind(wx.EVT_CHAR_HOOK, self.on_keyLstBoxDest)
        self.butNoDest = wx.Button(self.panMaster, label="Remove destination")
        self.butNoDest.Bind(wx.EVT_BUTTON, self.on_butNoDest)
        self.txtExclude = wx.StaticText(self.panMaster, label="Folders to exclude")
        self.lstBoxExclude = wx.ListBox(self.panMaster, style=wx.LB_MULTIPLE)
        self.lstBoxExclude.Bind(wx.EVT_CHAR_HOOK, self.on_keyLstBoxExclude)
        self.butNoExclude = wx.Button(self.panMaster, label="Remove folder")
        self.butNoExclude.Bind(wx.EVT_BUTTON, self.on_butNoExclude)
        self.txtFilters = wx.StaticText(self.panMaster, label="File types to exclude")
        self.lstBoxFilters = wx.ListBox(self.panMaster, style=wx.LB_MULTIPLE)
        self.lstBoxFilters.Bind(wx.EVT_CHAR_HOOK, self.on_keyLstBoxFilt)
        self.butNoFilter = wx.Button(self.panMaster, label="Remove file type")
        self.butNoFilter.Bind(wx.EVT_BUTTON, self.on_butNoFilter)
        self.txtCount = wx.StaticText(self.panMaster, label="Total files")
        self.lstBoxCount = wx.ListBox(self.panMaster, size=(10, 25))  # One line big
        # self.butCalcCount = wx.Button(self.panMaster, label="Calculate file count")
        # self.butCalcCount.Bind(wx.EVT_BUTTON, self.on_butCalcCount)
        self.txtSize = wx.StaticText(self.panMaster, label="Total file size")
        self.lstBoxSize = wx.ListBox(self.panMaster, size=(10, 25))  # One line big
        self.butGetFiles = wx.Button(self.panMaster, label="Analyse files")
        self.butGetFiles.Bind(wx.EVT_BUTTON, self.on_butGetFiles)
        self.butExportList = wx.Button(self.panMaster, label="Export file list")
        self.butExportList.Bind(wx.EVT_BUTTON, self.on_butExportList)
        infoBoxSizer.Add(self.txtSrc, 0, wx.TOP | wx.ALIGN_CENTER, 10)
        infoBoxSizer.Add(self.lstBoxSrc, 0, wx.ALL | wx.EXPAND, 2)
        infoBoxSizer.Add(self.txtDest, 0, wx.TOP | wx.ALIGN_CENTER, 15)
        infoBoxSizer.Add(self.lstBoxDest, 0, wx.ALL | wx.EXPAND, 2)
        infoBoxSizer.Add(self.butNoDest, 0, wx.ALL | wx.ALIGN_CENTER, 2)
        infoBoxSizer.Add(self.txtExclude, 0, wx.TOP | wx.ALIGN_CENTER, 15)
        infoBoxSizer.Add(self.lstBoxExclude, 0, wx.ALL | wx.EXPAND, 2)
        infoBoxSizer.Add(self.butNoExclude, 0, wx.ALL | wx.ALIGN_CENTER, 2)
        infoBoxSizer.Add(self.txtFilters, 0, wx.TOP | wx.ALIGN_CENTER, 15)
        infoBoxSizer.Add(self.lstBoxFilters, 0, wx.ALL | wx.EXPAND, 2)
        infoBoxSizer.Add(self.butNoFilter, 0, wx.ALL | wx.ALIGN_CENTER, 2)
        infoBoxSizer.Add(self.txtCount, 0, wx.TOP | wx.ALIGN_CENTER, 15)
        infoBoxSizer.Add(self.lstBoxCount, 0, wx.ALL | wx.EXPAND, 2)
        # infoBoxSizer.Add(self.butCalcCount, 0, wx.ALL | wx.ALIGN_CENTER, 2)
        infoBoxSizer.Add(self.txtSize, 0, wx.TOP | wx.ALIGN_CENTER, 15)
        infoBoxSizer.Add(self.lstBoxSize, 0, wx.ALL | wx.EXPAND, 2)
        infoBoxSizer.Add(self.butGetFiles, 0, wx.TOP | wx.ALIGN_CENTER, 15)
        infoBoxSizer.Add(self.butExportList, 0, wx.ALL | wx.ALIGN_CENTER, 2)

        lstBoxes[0][2].Add(self.txtDetails, 1, wx.ALL | wx.ALIGN_CENTER, 2)
        lstBoxes[0][2].Add(infoBoxSizer, 1, wx.ALL | wx.EXPAND, 5)
        lstBoxes[0][2].AddGrowableCol(0)
        lstBoxes[0][2].AddStretchSpacer()
        # lstBoxes[0][2].AddGrowableRow(3)

        # --- Queue ---
        latestRow = -1
        lstBoxes[0][3].AddGrowableCol(0)
        self.txtQueue = wx.StaticText(self.panMaster, label="Job Queue")
        self.lstCtlQueue = wx.ListCtrl(self.panMaster, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LB_MULTIPLE)
        self.lstCtlQueue.InsertColumn(0, 'Source', width=200)
        self.lstCtlQueue.InsertColumn(1, 'No. of Files', width=100)
        self.lstCtlQueue.InsertColumn(2, 'Size', width=100)
        self.lstCtlQueue.InsertColumn(3, 'Copied', width=100)
        self.lstCtlQueue.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_lstQueue_select)
        self.lstCtlQueue.Bind(wx.EVT_CHAR_HOOK, self.on_lstQueue_key)
        lstBoxes[0][3].Add(self.txtQueue, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        latestRow += 1
        lstBoxes[0][3].Add(self.lstCtlQueue, 1, wx.ALL | wx.EXPAND, 5)
        latestRow += 1
        lstBoxes[0][3].AddGrowableRow(latestRow)

        self.butNewJob = wx.Button(self.panMaster, label="New job")
        self.butNewJob.Bind(wx.EVT_BUTTON, self.on_butNewJob)
        self.butRemove = wx.Button(self.panMaster, label="Remove jobs")
        self.butRemove.Bind(wx.EVT_BUTTON, self.on_butRemoveJobs)
        self.butImport = wx.Button(self.panMaster, label="Import jobs")
        self.butImport.Bind(wx.EVT_BUTTON, self.on_butImport)
        self.butExport = wx.Button(self.panMaster, label="Export jobs")
        self.butExport.Bind(wx.EVT_BUTTON, self.on_butExport)
        boxSizer = wx.BoxSizer(wx.HORIZONTAL)
        boxSizer.Add(self.butNewJob, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        boxSizer.Add(self.butImport, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        boxSizer.Add(self.butRemove, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        boxSizer.Add(self.butExport, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        lstBoxes[0][3].Add(boxSizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        latestRow += 1
        # lstBoxes[0][3].AddSpacer(1)
        # latestRow += 1
        # lstBoxes[0][3].AddGrowableRow(latestRow)

        self.scheduleBox = wx.StaticBox(self.panMaster, label="Schedule queue")
        self.scheduleBoxSizer = wx.StaticBoxSizer(self.scheduleBox, wx.VERTICAL)
        subSizer = wx.GridSizer(2)
        self.dateQueue = wx.adv.DatePickerCtrl(self.panMaster, dt=dt.datetime.today())
        subSizer.Add(self.dateQueue, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        self.timeQueue = wx.adv.TimePickerCtrl(self.panMaster, dt=dt.datetime.now())
        subSizer.Add(self.timeQueue, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        self.butSchedule = wx.Button(self.panMaster, label="Schedule")
        self.butSchedule.Bind(wx.EVT_BUTTON, self.on_butSchedule)
        subSizer.Add(self.butSchedule, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        self.butGo = wx.Button(self.panMaster, label="Launch now!")
        self.butGo.Bind(wx.EVT_BUTTON, self.on_butGo)
        subSizer.Add(self.butGo, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        self.scheduleBoxSizer.Add(subSizer, 1, wx.ALIGN_CENTER)

        self.txtQueueSched = wx.StaticText(self.panMaster, label="No queue scheduled", style=wx.ALIGN_CENTER_HORIZONTAL)
        self.scheduleBoxSizer.Add(self.txtQueueSched, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        lstBoxes[0][3].Add(self.scheduleBoxSizer, 1, wx.TOP | wx.EXPAND, 25)
        latestRow += 1

        lstBoxes[0][3].AddStretchSpacer(1)
        latestRow += 1
        lstBoxes[0][3].AddGrowableRow(latestRow)

        del latestRow

        # ==========    Add it all up + display    ==========
        for row, lst in enumerate(lstBoxes):
            for col, box in enumerate(lst):
                if box:  # See 'None's in initialisation
                    if (row == 0 and 2 <= col <= 4):  # Selecting the double-cells
                        sizerGrid.Add(box, pos=(row, col), span=(2, 1), flag=wx.ALL | wx.EXPAND, border=5)
                    else:
                        sizerGrid.Add(box, pos=(row, col), flag=wx.ALL | wx.EXPAND, border=5)
                    try:
                        sizerGrid.AddGrowableCol(col)
                    except:
                        # nothing on the col yet
                        pass
            try:
                sizerGrid.AddGrowableRow(row)
            except:
                # nothing on the row yet
                pass

        self.panMaster.SetSizer(sizerGrid)

    def on_keySrc(self, event):
        if event.GetKeyCode() == wx.WXK_NUMPAD_ENTER or event.GetKeyCode() == wx.WXK_RETURN:
            self.on_butSrc()
        elif event.GetKeyCode() == wx.WXK_DELETE or event.GetKeyCode() == wx.WXK_BACK:
            self.on_butExclude()
        else:
            event.Skip()

    def on_keyDest1(self, event):
        if event.GetKeyCode() == wx.WXK_NUMPAD_ENTER or event.GetKeyCode() == wx.WXK_RETURN:
            self.on_butDest1()
        else:
            event.Skip()

    def on_keyDest2(self, event):
        if event.GetKeyCode() == wx.WXK_NUMPAD_ENTER or event.GetKeyCode() == wx.WXK_RETURN:
            self.on_butDest2()
        else:
            event.Skip()

    def on_butSrc(self, event=None):
        self.queue.get_jobs()[self.intCurrentJob].set_source(self.filePickSrc.GetPath())
        self.populate_job_summary()
        self.populate_job_queue()

    def on_butExclude(self, event=None):
        self.queue.get_jobs()[self.intCurrentJob].add_dirs_to_skip([self.filePickSrc.GetPath()])
        self.populate_job_summary()

    def on_butDest1(self, event=None):
        self.queue.get_jobs()[self.intCurrentJob].add_destination(self.filePickDest1.GetPath())
        self.populate_job_summary()

    def on_butMakeChoose1(self, event):
        startPath = self.filePickDest1.GetPath()
        with wx.DirDialog(self.panMaster,
                       message="Choose directory",
                       defaultPath=startPath,
                       style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            fp = fd.GetPath()
        self.filePickDest1.SetPath(fp)
        self.on_butDest1()

    def on_butDest2(self, event=None):
        self.queue.get_jobs()[self.intCurrentJob].add_destination(self.filePickDest2.GetPath())
        self.populate_job_summary()

    def on_butMakeChoose2(self, event):
        startPath = self.filePickDest2.GetPath()
        with wx.DirDialog(self.panMaster,
                       message="Choose directory",
                       defaultPath=startPath,
                       style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            fp = fd.GetPath()
        self.filePickDest2.SetPath(fp)
        self.on_butDest2()

    def on_chkBox(self, event):
        dicOptions = {label: box.GetValue() for label, box in self.dicChkBoxes.items()}
        self.queue.get_jobs()[self.intCurrentJob].set_options(dicOptions)
        self.populate_job_summary()

    def on_butFilter(self, event):
        filt = self.entFilter.GetValue()
        if filt:
            self.queue.get_jobs()[self.intCurrentJob].add_filter(filt)
            self.entFilter.Clear()
            self.populate_job_summary()

    def on_keyLstBoxDest(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE or event.GetKeyCode() == wx.WXK_BACK:
            self.on_butNoDest()
        else:
            event.Skip()

    def on_butNoDest(self, event=None):
        dests = [self.queue.get_jobs()[self.intCurrentJob].get_destinations()[x] for x in self.lstBoxDest.GetSelections()]
        self.queue.get_jobs()[self.intCurrentJob].remove_destinations(dests)
        self.populate_job_summary()

    def on_keyLstBoxExclude(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE or event.GetKeyCode() == wx.WXK_BACK:
            self.on_butNoExclude()
        else:
            event.Skip()

    def on_butNoExclude(self, event=None):
        dirs = [self.queue.get_jobs()[self.intCurrentJob].get_dirs_to_skip()[x] for x in self.lstBoxExclude.GetSelections()]
        self.queue.get_jobs()[self.intCurrentJob].remove_dirs_to_skip(dirs)
        self.populate_job_summary()

    def on_keyLstBoxFilt(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE or event.GetKeyCode() == wx.WXK_BACK:
            self.on_butNoFilter()
        else:
            event.Skip()

    def on_butNoFilter(self, event=None):
        filts = [self.queue.get_jobs()[self.intCurrentJob].get_filters()[x] for x in self.lstBoxFilters.GetSelections()]
        self.queue.get_jobs()[self.intCurrentJob].remove_filters(filts)
        self.populate_job_summary()

    def on_butGetFiles(self, event):
        if not self.queue.get_jobs()[self.intCurrentJob].get_source():
            return
        thAnalyse = threading.Thread(target=self.get_file_list)
        thAnalyse.start()
        dialog = "Getting files and sizes in the background."
        wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))

    def on_butExportList(self, event):
        if not self.queue.get_jobs()[self.intCurrentJob].get_source():
            return
        if self.queue.get_jobs()[self.intCurrentJob].countFiles == 0:
            wx.MessageBox("Please analyse files first.")
            return
        with wx.DirDialog(self.panMaster, "Save file lists") as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            fp = fd.GetPath()
        self.queue.get_jobs()[self.intCurrentJob].save_file_lists(fp)

    def on_lstQueue_select(self, event):
        self.intCurrentJob = self.lstCtlQueue.GetFirstSelected()
        self.populate_job_summary()

    def on_lstQueue_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE or event.GetKeyCode() == wx.WXK_BACK:
            self.on_butRemoveJobs()
        else:
            event.Skip()

    def on_butNewJob(self, event):
        self.queue.add_job()
        self.populate_job_queue()
        self.populate_job_summary()
        self.lstCtlQueue.Select(self.lstCtlQueue.GetItemCount()-1)

    def on_butImport(self, event):
        with wx.FileDialog(self.panMaster,
                           "Import queue file",
                           wildcard="*.yaml",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            fp = fd.GetPath()
        self.queue.import_queue_yaml(fp)
        self.lstCtlQueue.Select(0)
        self.populate_job_queue()

    def on_butRemoveJobs(self, event=None):
        lstJobs = list(self.gen_queue_selection())
        for job in lstJobs[::-1]:
            self.queue.remove_job(job)
        self.populate_job_queue()
        self.populate_job_summary()

    def on_butExport(self, event):
        with wx.FileDialog(self.panMaster,
                           "Save queue file",
                           wildcard="*.yaml",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return
            fp = fd.GetPath()
        self.queue.export_queue_yaml(fp)

    def on_butGo(self, event=None):
        if self.cancelButLaunch:
            # User clicked 'abort'
            self.procRunQueue.terminate()
            self.butGo.SetLabel("Launch now!")
            self.cancelButLaunch = False
            dialog = "No queue scheduled"
            wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
        else:
            # User clicked 'launch now!'
            dialog = self.errors_in_queue()
            if dialog:
                wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
                # TO DO: Reset to 'No queue scheduled' after delay - need another thread...
            else:
                self.thLaunch = threading.Thread(target=self.launch_queue_processes)
                self.thLaunch.start()
                self.butGo.SetLabel("Abort")
                dialog = "Running queue"
                wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
                self.cancelButLaunch = True

    def on_butSchedule(self, event):
        if self.cancelButSchedule:
            # User clicked 'cancel'
            self.cancelCountdown = True
            self.butSchedule.SetLabel("Schedule")
            self.cancelButSchedule = False
            del self.thCountdown
            dialog = "No queue scheduled"
            wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
        else:
            # User clicked 'schedule'
            dialog = self.errors_in_queue()
            if dialog:
                wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
                # TO DO: Reset to 'No queue scheduled' after delay - need another thread...
            else:
                self.cancelCountdown = False
                self.thCountdown = threading.Thread(target=self.countdown_to_launch)
                self.thCountdown.start()
                self.butSchedule.SetLabel("Cancel")
                self.cancelButSchedule = True

    def countdown_to_launch(self):
        """
        To be run as separate thread - checks the scheduled time and waits/counts down before running
        """
        schedTime = self.dateQueue.GetValue().GetDateOnly()
        schedTime.SetHour(self.timeQueue.GetValue().GetHour())
        schedTime.SetMinute(self.timeQueue.GetValue().GetMinute())
        schedTime.SetSecond(self.timeQueue.GetValue().GetSecond())

        if schedTime <= wx.DateTime.Now():
            # Go time is in the past
            dialog = "Scheduled time is in the past!"
            wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
            self.cancelCountdown = False
            self.butSchedule.SetLabel("Schedule")
            self.cancelButSchedule = False
            sleep(2)
            dialog = "No queue scheduled"
            wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
            return

        timeTillLaunch = schedTime - wx.DateTime.Now()
        waitTime = 3  # hours
        while timeTillLaunch >= wx.TimeSpan(waitTime):
            if self.cancelCountdown: return
            # Go time is more than {waitTime} hours
            dialog = "Running queue at\n{}".format(schedTime.Format())
            wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
            sleep(1)
            timeTillLaunch = schedTime - wx.DateTime.Now()

        while wx.TimeSpan(0, sec=1) < timeTillLaunch <= wx.TimeSpan(3):
            if self.cancelCountdown: return
            # Go time is less than {waitTime} hours
            timeTillLaunch = schedTime - wx.DateTime.Now()
            dialog = "Running queue in {}".format(timeTillLaunch.Format())
            wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
            sleep(1)

        dialog = "Running queue."
        wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))
        self.butSchedule.SetLabel("Schedule")
        self.cancelButSchedule = False
        self.on_butGo()

    def update_queue_text(self, event):
        self.txtQueueSched.SetLabel(event.attr1)
        self.panMaster.Layout()

    def get_file_list(self):
        self.queue.get_jobs()[self.intCurrentJob].get_file_list(recalculate=True)
        self.populate_job_summary()
        self.populate_job_queue()
        dialog = "No queue scheduled"
        wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))

    def launch_queue_processes(self):
        # Put the process in a multiprocessing queue to allow it to communicate progress
        progress = multiprocessing.Array('l', [0] * len(self.queue.get_jobs()))
        self.procRunQueue = multiprocessing.Process(target=self.queue.run_queue, args=(progress,))
        self.procRunQueue.start()

        while self.procRunQueue.is_alive():
            wx.PostEvent(frame, EvtUpdateProgress(attr1=progress))
            sleep(1)
        # Get final size

        wx.PostEvent(frame, EvtUpdateProgress(attr1=progress))
        self.butGo.SetLabel("Launch now!")
        self.cancelButLaunch = False
        dialog = "No queue scheduled"
        wx.PostEvent(frame, EvtUpdateScheduleText(attr1=dialog))

    def update_progress_column(self, event):
        for count, job in enumerate(self.queue.get_jobs()):
            self.lstCtlQueue.SetItem(count, 3, BackupJob.human_readable(event.attr1[count]))

    def errors_in_queue(self):
        """
        Checks the queue for errors and returns warning messages or False if fine.
        Usage:
        if errors_in_queue():
            deal with errors
        else:
            continue about your business
        :return: Either a string with warning messages or False if all is okay.
        """
        for index, job in enumerate(self.queue.get_jobs()):
            if not job.get_source():
                return f"Job {index + 1} has no source directory."
            if not job.get_destinations():
                return f"Job {index + 1} has no destination directories."
            if not job.check_folder_permissions():
                return f"Do not have permission to write to destination of job {index + 1}."
            if not job.check_space_on_drive():
                return f"Do not have enough space on the drive for job {index + 1}."
        return False

    def gen_queue_selection(self):
        """
        Generator to get the selected items in the queue list ctrl
        """
        firstSel = self.lstCtlQueue.GetFirstSelected()
        nextSel = self.lstCtlQueue.GetNextSelected(firstSel)
        if firstSel == -1:
            yield
        else:
            yield firstSel
        while nextSel != -1:
            yield nextSel
            nextSel = self.lstCtlQueue.GetNextSelected(nextSel)

    def populate_job_summary(self):
        """
        Fill in the job summary box with the selected job details.
        """
        if not self.queue.get_jobs():
            [x.SetValue(False) for x in self.dicChkBoxes.values()]
            self.lstBoxSrc.Clear()
            self.lstBoxDest.Clear()
            self.lstBoxFilters.Clear()
            self.lstBoxExclude.Clear()
            self.lstBoxCount.Clear()
            self.lstBoxSize.Clear()
            return

        # Options
        for opt, value in self.queue.get_jobs()[self.intCurrentJob].get_options().items():
            self.dicChkBoxes[opt].SetValue(value)

        # Source
        self.lstBoxSrc.Clear()
        if self.queue.get_jobs()[self.intCurrentJob].get_source():
            path = os.path.split(self.queue.get_jobs()[self.intCurrentJob].get_source())[1]
            if path == '':
                path = 'Root (everything)'
            self.lstBoxSrc.Append(path)
            del path

        # Dests
        self.lstBoxDest.Clear()
        lstPaths = [os.path.split(x)[1] for x in self.queue.get_jobs()[self.intCurrentJob].get_destinations()]
        for path in lstPaths:
            if path == '':
                path = 'Root (everything)'
        try:
            del path
        except UnboundLocalError:
            pass
        self.lstBoxDest.Append(lstPaths)

        # Filters
        self.lstBoxFilters.Clear()
        self.lstBoxFilters.Append(self.queue.get_jobs()[self.intCurrentJob].get_filters())

        self.lstBoxExclude.Clear()
        lstPaths = [os.path.split(x)[1] for x in self.queue.get_jobs()[self.intCurrentJob].get_dirs_to_skip()]
        for path in lstPaths:
            if path == '':
                path = 'Root (everything)'
        try:
            del path
        except UnboundLocalError:
            pass
        self.lstBoxExclude.Append(lstPaths)

        # File Count
        cnt = str(self.queue.get_jobs()[self.intCurrentJob].get_files_count())
        self.lstBoxCount.Clear()
        self.lstBoxCount.Append(cnt)

        # File Size
        size = self.queue.get_jobs()[self.intCurrentJob].get_files_size()
        self.lstBoxSize.Clear()
        self.lstBoxSize.Append(size)

    def populate_job_queue(self):
        """
        Populate the job queue panel
        """
        self.lstCtlQueue.DeleteAllItems()
        for job in self.queue.get_jobs():
            source = job.get_source()
            if source:
                source = os.path.split(source)[1]
            else:
                source = ''
            self.lstCtlQueue.Append([
                source,
                job.get_files_count(),
                job.get_files_size()
            ])


if __name__ == '__main__':
    app = wx.App()
    frame = FrMainwindow()
    app.MainLoop()

