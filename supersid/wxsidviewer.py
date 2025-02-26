"""
Class wxSidViewer implements a graphical user interface for SID on wxPython.

About Threads and wxPython
http://www.blog.pythonlibrary.org/2010/05/22/wxpython-and-threads/

Each Viewer must implement:
- __init__(): all initializations
- run(): main loop to get user input
- close(): cleaning up
- status_display(): display a message in a status bar or equivalent
"""
from __future__ import print_function
import matplotlib
# matplotlib.use('WXAgg') # select back-end before pylab
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
import wx
from wx.lib.pubsub import Publisher

import supersid_plot as SSP
from config import FILTERED, RAW


class wxSidViewer(wx.Frame):
    """
    Viewer class for wx GUI.

    Frame, Menu, Panel, BoxSizer are wx things
    and FigureCanvas, Figure, Axes are MPL things
    Viewer =>> Panel =>> FigureCanvas =>> Figure => Axes
    frame close events are forwarded to SuperSID class
    """

    def __init__(self, controller):
        """Initialize Viewer using wxPython GUI for standalone and client.

        Creation of the Frame with menu and graph display using matplotlib
        """
        matplotlib.use('WXAgg')  # select back-end before pylab
        # the application MUST created first
        self.app = wx.App(redirect=False)
        #
        self.version = "1.3.1 20150421 (wx)"
        self.controller = controller  # previously referred as 'parent'
        # Frame
        wx.Frame.__init__(self, None, -1,
                          "supersid @ " + self.controller.config['site_name'],
                          pos=(20, 20), size=(1000, 400))
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Icon
        try:
            self.SetIcon(wx.Icon("supersid_icon.png", wx.BITMAP_TYPE_PNG))
        finally:
            pass

        # All Menus creation
        menu_item_file = wx.Menu()
        save_buffers_menu = menu_item_file.Append(wx.NewId(),
                                                  '&Save Raw Buffers\tCtrl+B',
                                                  'Save Raw Buffers')
        save_filtered_menu = menu_item_file.Append(wx.NewId(),
                                                   '&Save Filtered Buffers\tCtrl+F',
                                                   'Save Filtered Buffers')
        exit_menu = menu_item_file.Append(wx.NewId(), '&Quit\tCtrl+Q',
                                          'Quit Super SID')

        menu_item_plot = wx.Menu()
        plot_menu = menu_item_plot.Append(wx.NewId(), '&Plot\tCtrl+P',
                                          'Plot data')

        menu_item_help = wx.Menu()
        about_menu = menu_item_help.Append(wx.NewId(), '&About',
                                           'About Super SID')

        menubar = wx.MenuBar()
        menubar.Append(menu_item_file, '&File')
        menubar.Append(menu_item_plot, '&Plot')
        menubar.Append(menu_item_help, '&Help')

        self.SetMenuBar(menubar)
        self.Bind(wx.EVT_MENU, self.on_save_buffers, save_buffers_menu)
        self.Bind(wx.EVT_MENU, self.on_save_filtered, save_filtered_menu)
        self.Bind(wx.EVT_MENU, self.on_plot, plot_menu)
        self.Bind(wx.EVT_MENU, self.on_about, about_menu)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_menu)

        # Frame
        psd_panel = wx.Panel(self, -1)
        psd_sizer = wx.BoxSizer(wx.VERTICAL)
        psd_panel.SetSizer(psd_sizer)

        # FigureCanvas
        psd_figure = Figure(facecolor='beige')
        self.canvas = FigureCanvas(psd_panel, -1, psd_figure)
        self.canvas.mpl_connect('button_press_event', self.on_click)

        psd_sizer.Add(self.canvas, 1, wx.EXPAND)
        self.axes = psd_figure.add_subplot(111)
        self.axes.hold(False)

        # StatusBar
        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetFieldsCount(2)

        # Default View
        self.SetMinSize((600, 600))
        psd_sizer.SetItemMinSize(psd_panel, 1000, 600)
        self.Center(True)
        self.Show()

        # create a pubsub receiver for refresh after data capture
        # ref. link on threads
        Publisher().subscribe(self.updateDisplay, "update")

    def run(self):
        """Implement main loop for the application."""
        self.app.MainLoop()

    def updateDisplay(self, msg):
        """Receive data from thread and updates the display.

        graph and statusbar
        """
        try:
            self.canvas.draw()
            self.status_display(msg.data)
        except:
            pass

    def get_axes(self):
        return self.axes

    def status_display(self, message, level=0, field=0):
        if level == 1:
            wx.CallAfter(self.status_display, message)
        elif level == 2:
            wx.CallAfter(Publisher().sendMessage, "update", message)
        else:
            self.status_bar.SetStatusText(message, field)

    def on_close(self, event):
        """Request to close by the user."""
        self.controller.on_close()

    def close(self):
        """Request to close by the controller."""
        self.app.Exit()
        self.Destroy()

    def on_exit(self, event):
        self.status_display("This is supersid signing off...")
        dlg = wx.MessageDialog(self,
                               'Are you sure to quit supersid?',
                               'Please Confirm',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.Close(True)

    def on_plot(self, event):
        """Save current buffers (raw) and display the data using supersid_plot.

        Using a separate process to prevent interference with data capture
        """
        filenames = self.controller.save_current_buffers(log_format='supersid_format')
        print("plotting", filenames)
        SSP.do_main(filenames)

    def on_plot_files(self, event):
        """Select multiple files and call supersid_plot module for display."""
        filedialog = wx.FileDialog(self, message='Choose files to plot',
                                   defaultDir=self.controller.config.data_path,
                                   defaultFile='',
                                   wildcard='Supported filetypes (*.csv) | *.csv',
                                   style=wx.OPEN | wx.FD_MULTIPLE)

        if filedialog.ShowModal() == wx.ID_OK:
            filelist = ""
            for u_filename in filedialog.GetFilenames():
                filelist = str(filelist + "../Data/" + str(u_filename) + ",")
            filelist = filelist.rstrip(',')  # remove last comma

            ssp = SSP.SUPERSID_PLOT()
            ssp.plot_filelist(filelist)

    def on_save_buffers(self, event):
        """Call the Controller for writing unfiltered/raw data to file."""
        self.controller.save_current_buffers(log_type=RAW)

    def on_save_filtered(self, event):
        """Call the Controller for writing filtered data to file."""
        self.controller.save_current_buffers('current_filtered.csv', FILTERED)

    def on_about(self, event):
        """Open an About message box."""
        info = wx.AboutDialogInfo()
        info.SetIcon(wx.Icon('supersid_icon.png', wx.BITMAP_TYPE_PNG))
        info.SetName('SuperSID')
        info.SetDescription(self.controller.about_app())
        info.SetCopyright('(c) Stanford Solar Center and Eric Gibert')
        wx.AboutBox(info)

    def on_click(self, event):  # MLP mouse event
        """Following user click on the graph.

        Display associated information in statusbar
        """
        if event.inaxes:
            strength = pow(10, (event.ydata/10.0))
            message = "frequency=%.0f  " % event.xdata + " power=%.3f  " % event.ydata + " strength=%.0f" % strength
            self.status_display(message, field=1)

    def display_message(self, message="message...", sender="SuperSID"):
        """For any need to display a MessageBox.

        - to review for better button/choice management]
        """
        status = wx.MessageBox(message,
                               sender,
                               wx.CANCEL | wx.ICON_QUESTION)
        if status == wx.YES:
            return 1  # RETRY
        elif status == wx.NO:
            return 1  # SKIP
        elif status == wx.CANCEL:
            return 1  # STOP
        else:
            return 0

    def get_psd(self, data, NFFT, FS):
        """By calling 'psd' within axes, calculates and plots the spectrum."""
        try:
            Pxx, freqs = self.axes.psd(data, NFFT=NFFT, Fs=FS)
        except wx.PyDeadObjectError:
            exit(3)
        return Pxx, freqs
