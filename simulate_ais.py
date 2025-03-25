#!/usr/bin/env python
import wx
import socket
import time
import ais_simulation
import threading

simulation = ais_simulation.Simulation()

DEFAULT_FILENAME = "ais_simulation.gpx"

class SimulatorFrame(wx.Frame):

    def __init__(self, parent, title):
        super(SimulatorFrame, self).__init__(parent, title = title, size=(600,800))  # Increased window size
        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer = wx.GridBagSizer(0,0)

        ## Set up Statictext
        text1 = wx.StaticText(panel, label = "filename")
        top_sizer.Add(text1, pos = (0, 0), flag = wx.ALL, border = 3)
        text2 = wx.StaticText(panel, label = "true wind")
        top_sizer.Add(text2, pos = (3, 0), flag = wx.ALL, border = 3)
        text3 = wx.StaticText(panel, label = "current")
        top_sizer.Add(text3, pos = (4, 0), flag = wx.ALL, border = 3)
        text4 = wx.StaticText(panel, label = "speedup")
        top_sizer.Add(text4, pos = (0, 3), flag = wx.ALL, border = 3)
        
        # Add NMEA Messages label
        text6 = wx.StaticText(panel, label = "NMEA Messages")
        top_sizer.Add(text6, pos = (5, 0), flag = wx.ALL, border = 3)

        ## Setup up controls
        filename = wx.TextCtrl(panel, value=DEFAULT_FILENAME)
        top_sizer.Add(filename, pos = (0,1), flag = wx.EXPAND|wx.ALL, span=(1,2))
        def OnChange_filename(event):
             buttonStart.filename = filename.GetValue()
        self.Bind(wx.EVT_TEXT, OnChange_filename, filename)

        # Set up buttons
        buttonStart = wx.Button(panel, label = "Start" )
        top_sizer.Add(buttonStart, pos = (1, 0), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)
        buttonStart.filename = filename.GetValue()

        buttonPause = wx.Button(panel, label = "Pause" )
        top_sizer.Add(buttonPause, pos = (1, 2), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)

        buttonResume = wx.Button(panel, label = "Resume" )
        top_sizer.Add(buttonResume, pos = (1, 3), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)

        buttonStop = wx.Button(panel, label = "Stop" )
        top_sizer.Add(buttonStop, pos = (1, 4), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)

        buttonMinus10 = wx.Button(panel, label = "-10" )
        top_sizer.Add(buttonMinus10, pos = (2, 0), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)
        buttonMinus10.steerValue=-10

        buttonMinus1 = wx.Button(panel, label = "-1" )
        top_sizer.Add(buttonMinus1, pos = (2, 1), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)
        buttonMinus1.steerValue=-1

        buttonPlus1 = wx.Button(panel, label = "+1" )
        top_sizer.Add(buttonPlus1, pos = (2, 3), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)
        buttonPlus1.steerValue=1

        buttonPlus10 = wx.Button(panel, label = "+10" )
        top_sizer.Add(buttonPlus10, pos = (2, 4), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)
        buttonPlus10.steerValue=10

        buttonSetWind = wx.Button(panel, label = "Set wind")
        top_sizer.Add(buttonSetWind, pos = (3, 4), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)

        buttonSetCurrent = wx.Button(panel, label = "Set current")
        top_sizer.Add(buttonSetCurrent, pos = (4, 4), flag = wx.ALIGN_CENTER|wx.ALL, border = 3)
        
        textSpeedup = wx.TextCtrl(panel, value="60", size=(70,10))
        top_sizer.Add(textSpeedup, pos = (0, 4), flag = wx.EXPAND|wx.ALL, border = 3)
        def OnChange_speedup(event):
            simulation.setSpeedup(float(textSpeedup.GetValue()))
        textSpeedup.Bind(wx.EVT_TEXT, OnChange_speedup, textSpeedup)
        
        textTwd = wx.TextCtrl(panel, value="225", size=(70,10))
        top_sizer.Add(textTwd, pos = (3, 1), flag = wx.EXPAND|wx.ALL, border = 3)
        textTws = wx.TextCtrl(panel, value="15", size=(70,20))
        top_sizer.Add(textTws, pos = (3, 2), flag = wx.EXPAND|wx.ALL, border = 3)
        textTwv = wx.TextCtrl(panel, value="10", size=(70,20))
        top_sizer.Add(textTwv, pos = (3, 3), flag = wx.EXPAND|wx.ALL, border = 3)

        textCurD = wx.TextCtrl(panel, value="270", size=(70,10))
        top_sizer.Add(textCurD, pos = (4, 1), flag = wx.EXPAND|wx.ALL, border = 3)
        textCurS = wx.TextCtrl(panel, value="2.0", size=(70,20))
        top_sizer.Add(textCurS, pos = (4, 2), flag = wx.EXPAND|wx.ALL, border = 3)
        textCurV = wx.TextCtrl(panel, value="0", size=(70,20))
        top_sizer.Add(textCurV, pos = (4, 3), flag = wx.EXPAND|wx.ALL, border = 3)

        # Add NMEA message display with proper sizing
        self.nmea_display = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        
        # Add the top sizer to the main sizer
        main_sizer.Add(top_sizer, 0, wx.EXPAND|wx.ALL, 5)
        
        # Add the NMEA display to the main sizer with proportion=1 to make it expand
        main_sizer.Add(self.nmea_display, 1, wx.EXPAND|wx.ALL, 5)

        buttonStart.Bind(wx.EVT_BUTTON, simulation.startBoats)
        buttonPause.Bind(wx.EVT_BUTTON, simulation.pauseBoats)
        buttonResume.Bind(wx.EVT_BUTTON, simulation.resumeBoats)
        buttonStop.Bind(wx.EVT_BUTTON, simulation.stopBoats)

        buttonMinus10.Bind(wx.EVT_BUTTON, simulation.steerBoat)
        buttonMinus1.Bind(wx.EVT_BUTTON, simulation.steerBoat)
        buttonPlus1.Bind(wx.EVT_BUTTON, simulation.steerBoat)
        buttonPlus10.Bind(wx.EVT_BUTTON, simulation.steerBoat)
        
        def OnChange_wind(event):
             buttonSetWind.twd = textTwd.GetValue()
             buttonSetWind.tws = textTws.GetValue()
             buttonSetWind.twv = textTwv.GetValue()
        self.Bind(wx.EVT_TEXT, OnChange_wind, textTwd)
        self.Bind(wx.EVT_TEXT, OnChange_wind, textTws)
        self.Bind(wx.EVT_TEXT, OnChange_wind, textTwv)
        buttonSetWind.Bind(wx.EVT_BUTTON, simulation.setTrueWind)
        OnChange_wind(None)

        def OnChange_current(event):
             buttonSetCurrent.curd = textCurD.GetValue()
             buttonSetCurrent.curs = textCurS.GetValue()
             buttonSetCurrent.curv = textCurV.GetValue()
             simulation.setTrueCurrent
        self.Bind(wx.EVT_TEXT, OnChange_current, textCurD)
        self.Bind(wx.EVT_TEXT, OnChange_current, textCurS)
        self.Bind(wx.EVT_TEXT, OnChange_current, textCurV)
        buttonSetCurrent.Bind(wx.EVT_BUTTON, simulation.setTrueCurrent)
        OnChange_current(None)

        text5 = wx.StaticText(panel)
        top_sizer.Add(text5, pos = (2, 2), flag = wx.ALL, border = 3)
        
        def updateHeading(self):
            heading = simulation.getHeading()
            text5.SetLabel(heading)
        
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, updateHeading, self.timer)
        self.timer.Start(1000)

        # Set the main sizer for the panel
        panel.SetSizer(main_sizer)
        
        # Bind the window resize event
        self.Bind(wx.EVT_SIZE, self.OnSize)
        
        self.Bind(wx.EVT_CLOSE, self.OnExitApp)

    def OnSize(self, event):
        """Handle the window resize event"""
        if self.GetAutoLayout():
            self.Layout()
        event.Skip()

    def update_nmea(self, message):
        """Update the NMEA message display"""
        wx.CallAfter(self.nmea_display.AppendText, message + "\n")
        if self.nmea_display.GetNumberOfLines() > 100:  # Keep only last 100 lines
            wx.CallAfter(self.nmea_display.Remove, 0, self.nmea_display.GetLineLength(0) + 1)
        
    def OnExitApp(self, event):
        print ('--- Window closed')
        simulation.stopBoats(event)
        simulation.wrapup()
        self.Destroy()

simulation.loadBoats(DEFAULT_FILENAME)
print("--- Initial positioning of boats")
simulation.showBoats()

app = wx.App()
myFrame = SimulatorFrame(None, title = 'AIS Simulator')
simulation.frame = myFrame  # Store reference to frame for NMEA updates
app.MainLoop()

