#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright Martin Manns
# Distributed under the terms of the GNU General Public License

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread. If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
_chart_dialog
=============

Chart creation dialog with interactive matplotlib chart widget

Provides
--------

* ChartDialog: Chart dialog class

"""


import ast
from copy import copy

import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import wx.lib.colourselect as csel
from wx.lib.intctrl import IntCtrl, EVT_INT
import wx.lib.agw.flatnotebook as fnb
import numpy

from _widgets import PenWidthComboBox, LineStyleComboBox, MarkerStyleComboBox
from _events import post_command_event, ChartDialogEventMixin
import src.lib.i18n as i18n
import src.lib.charts as charts

#use ugettext instead of getttext to avoid unicode errors
_ = i18n.language.ugettext


class LabeledWidgetPanel(wx.Panel, ChartDialogEventMixin):
    """Base class for boxed panels with labeled widgets"""

    def __init__(self, *args, **kwargs):

        self.parent = args[0]
        self.series_data = kwargs.pop("series_data")

        box_label = kwargs.pop("box_label")
        self.widgets = kwargs.pop("widgets")

        wx.Panel.__init__(self, *args, **kwargs)

        self.staticbox = wx.StaticBox(self, -1, box_label)

        for name, label, widget_cls, args, kwargs in self.widgets:
            widget = widget_cls(*args, **kwargs)

            label_name = name + "_label"
            editor_name = name + "_editor"

            setattr(self, label_name, wx.StaticText(self, -1, label))
            setattr(self, editor_name, widget)

        self.__do_layout()

    def __do_layout(self):
        self.staticbox.Lower()
        box_sizer = wx.StaticBoxSizer(self.staticbox, wx.HORIZONTAL)
        box_grid_sizer = wx.FlexGridSizer(3, 2, 0, 0)

        for name, label, widget_cls, args, kwargs in self.widgets:
            label_name = name + "_label"
            editor_name = name + "_editor"

            label = getattr(self, label_name)
            editor = getattr(self, editor_name)

            box_grid_sizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            box_grid_sizer.Add(editor, 0, wx.ALL | wx.EXPAND, 0)

        box_grid_sizer.AddGrowableCol(1)
        box_sizer.Add(box_grid_sizer, 1, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(box_sizer)

        self.Layout()

    def _color_from_string(self, color_string):
        """Returns wx.Colour from given tuple string"""

        color_tuple = self.parent.get_series_tuple(color_string)
        color_tuple_int = map(lambda x: int(x * 255), color_tuple)
        return wx.Colour(*color_tuple_int)


class ChartAxisDataPanel(LabeledWidgetPanel):
    """Panel for data entry for chart axis"""

    def __init__(self, *args, **kwargs):

        # Custom data
        kwargs["box_label"] = _("Data")

        kwargs["widgets"] = [
            ("x", _("X"), wx.TextCtrl,
             (self, -1, kwargs["series_data"]["xdata"]), {}),
            ("y", _("Y"), wx.TextCtrl,
             (self, -1, kwargs["series_data"]["ydata"]), {}),
        ]

        LabeledWidgetPanel.__init__(self, *args, **kwargs)

        self.__set_properties()
        self.__bindings()

    def __set_properties(self):
        self.x_editor.SetToolTipString(
            _("Enter a list of X values (optional)."))
        self.y_editor.SetToolTipString(_("Enter a list of Y values."))

    def __bindings(self):
        """Binds events ton handlers"""

        self.Bind(wx.EVT_TEXT, self.OnXText, self.x_editor)
        self.Bind(wx.EVT_TEXT, self.OnYText, self.y_editor)

    # Handlers
    # --------

    def OnXText(self, event):
        """Event handler for x_text_ctrl"""

        self.series_data["xdata"] = event.GetString()

        post_command_event(self, self.DrawChartMsg)

    def OnYText(self, event):
        """Event handler for y_text_ctrl"""

        self.series_data["ydata"] = event.GetString()

        post_command_event(self, self.DrawChartMsg)


class ChartAxisLinePanel(LabeledWidgetPanel):
    """Panel for line style entry"""

    def __init__(self, *args, **kwargs):

        # Custom data
        _widths = map(unicode, xrange(12))

        kwargs["box_label"] = _("Line")

        pen_style_combo_args = (self, -1), {}
        colorselect_args = (self, -1, unichr(0x2500) * 6), {"size": (80, 25)}
        pen_width_combo_args = (self,), {"choices": _widths,
                                "style": wx.CB_READONLY, "size": (50, -1)}

        kwargs["widgets"] = [
            ("style", _("Style"), LineStyleComboBox) + pen_style_combo_args,
            ("color", _("Color"), csel.ColourSelect) + colorselect_args,
            ("width", _("Width"), PenWidthComboBox) + pen_width_combo_args,
        ]

        LabeledWidgetPanel.__init__(self, *args, **kwargs)

        self.__set_properties()
        self.__bindings()

    def __set_properties(self):
        # Set controls to default values
        self.width_editor.SetSelection(int(self.series_data["linewidth"]))

    def __bindings(self):
        """Binds events to handlers"""

        self.style_editor.Bind(wx.EVT_CHOICE, self.OnStyle)
        self.Bind(wx.EVT_COMBOBOX, self.OnWidth, self.width_editor)
        self.color_editor.Bind(csel.EVT_COLOURSELECT, self.OnColor)

    # Handlers
    # --------

    def OnStyle(self, event):
        """Line style event handler"""

        line_style_code = self.style_editor.get_code(event.GetString())
        self.series_data["linestyle"] = repr(line_style_code)
        post_command_event(self, self.DrawChartMsg)

    def OnWidth(self, event):
        """Line width event handler"""

        self.series_data["linewidth"] = repr(event.GetSelection())
        post_command_event(self, self.DrawChartMsg)

    def OnColor(self, event):
        """Line color event handler"""

        self.series_data["color"] = \
                repr(tuple(i / 255.0 for i in event.GetValue().Get()))
        post_command_event(self, self.DrawChartMsg)


class ChartAxisMarkerPanel(LabeledWidgetPanel):
    """Panel for marker style entry"""

    def __init__(self, parent, *args, **kwargs):

        self.parent = parent
        kwargs["box_label"] = _("Marker")

        marker_style_combo_args = (self, -1), {}
        colorselect_args = (self, -1), {"size": (80, 25)}
        intctrl_args = (self, -1, 0, None), {}

        kwargs["widgets"] = [
            ("style", _("Style"), MarkerStyleComboBox) +
                                  marker_style_combo_args,
            ("size", _("Size"), IntCtrl) + intctrl_args,
            ("face_color", _("Face"), csel.ColourSelect) + colorselect_args,
            ("edge_color", _("Edge"), csel.ColourSelect) + colorselect_args,
        ]

        LabeledWidgetPanel.__init__(self, parent, *args, **kwargs)

        self.__set_properties()
        self.__bindings()

    def __set_properties(self):
        # Set controls to default values

        marker_style_code = self.series_data["marker"][1:-1]
        marker_style_label = self.style_editor.get_label(marker_style_code)
        self.style_editor.SetStringSelection(marker_style_label)

        self.size_editor.SetValue(int(self.series_data["markersize"]))

        face_color_string = self.series_data["markerfacecolor"]
        face_color = self._color_from_string(face_color_string)
        self.face_color_editor.SetColour(face_color)

        edge_color_string = self.series_data["markeredgecolor"]
        edge_color = self._color_from_string(edge_color_string)
        self.edge_color_editor.SetColour(edge_color)

    def __bindings(self):
        """Binds events to handlers"""

        self.style_editor.Bind(wx.EVT_CHOICE, self.OnStyle)
        self.size_editor.Bind(EVT_INT, self.OnSize)
        self.face_color_editor.Bind(csel.EVT_COLOURSELECT, self.OnFaceColor)
        self.edge_color_editor.Bind(csel.EVT_COLOURSELECT, self.OnEdgeColor)

    # Handlers
    # --------

    def OnStyle(self, event):
        """Marker style event handler"""

        marker_style_code = self.style_editor.get_code(event.GetString())
        self.series_data["marker"] = repr(marker_style_code)
        post_command_event(self, self.DrawChartMsg)

    def OnSize(self, event):
        """Marker size event"""

        self.series_data["markersize"] = repr(event.GetValue())
        post_command_event(self, self.DrawChartMsg)

    def OnEdgeColor(self, event):
        """Marker front color event handler"""

        self.series_data["markeredgecolor"] = \
                repr(tuple(i / 255.0 for i in event.GetValue().Get()))
        post_command_event(self, self.DrawChartMsg)

    def OnFaceColor(self, event):
        """Marker back color event handler"""

        self.series_data["markerfacecolor"] = \
                repr(tuple(i / 255.0 for i in event.GetValue().Get()))
        post_command_event(self, self.DrawChartMsg)


class PlotPanel(wx.Panel):
    """Static box panel that holds widgets for one plot series"""

    def __init__(self, parent, __id, series_data=None):

        wx.Panel.__init__(self, parent, __id)

        self.get_series_tuple = parent.get_series_tuple

        # Default data for series plot

        self.series_data = {
            "xdata": u"",
            "ydata": u"",
            "linestyle": u"'-'",
            "linewidth": u"1",
            "color": u"(0, 0, 0)",
            "marker": u"''",
            "markersize": u"5",
            "markerfacecolor": u"(0, 0, 0)",
            "markeredgecolor": u"(0, 0, 0)",
        }

        if series_data is not None:
            self.series_data.update(series_data)

        # Data types for keys

        self.series_keys = ["xdata", "ydata", "color", "markerfacecolor",
                            "markeredgecolor"]
        self.string_keys = ["linestyle", "marker"]
        self.float_keys = ["markersize"]

        # Widgets

        self.data_panel = \
            ChartAxisDataPanel(self, -1, series_data=self.series_data)
        self.line_panel = \
            ChartAxisLinePanel(self, -1, series_data=self.series_data)
        self.marker_panel = \
            ChartAxisMarkerPanel(self, -1, series_data=self.series_data)

        self.__do_layout()

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(1, 1, 0, 0)

        main_sizer.Add(self.data_panel, 1, wx.ALL | wx.EXPAND, 2)
        main_sizer.Add(self.line_panel, 1, wx.ALL | wx.EXPAND, 2)
        main_sizer.Add(self.marker_panel, 1, wx.ALL | wx.EXPAND, 2)
        main_sizer.AddGrowableCol(0)

        self.SetSizer(main_sizer)

        self.Layout()


def parse_dict_strings(code):
    level = 0
    chunk_start = 0
    curr_paren = None
    for i, char in enumerate(code):
        if char in ["(", "[", "{"] and curr_paren is None:
            level += 1
        elif char in [")", "]", "}"] and curr_paren is None:
            level -= 1
        elif char in ['"', "'"]:
            if curr_paren == char:
                curr_paren = None
            elif curr_paren is None:
                curr_paren = char
        if level == 0 and char in [':', ','] and curr_paren is None:
            yield code[chunk_start: i].strip().strip("(").strip(")")
            chunk_start = i + 1
    yield code[chunk_start: i + 1].strip()


class ChartDialog(wx.Dialog, ChartDialogEventMixin):
    """Chart dialog for generating chart generation strings"""

    series = []

    def __init__(self, parent, code, **kwds):
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | \
                        wx.THICK_FRAME
        self.grid = parent

        wx.Dialog.__init__(self, parent, **kwds)

        agwstyle = fnb.FNB_NODRAG | fnb.FNB_DROPDOWN_TABS_LIST | fnb.FNB_BOTTOM
        self.series_notebook = fnb.FlatNotebook(self, -1, agwStyle=agwstyle)

        if code[:7] == "charts.":
            # If chart data is present build the chart
            key = self.grid.actions.cursor
            self.figure = self.grid.code_array._eval_cell(key, code)

            # Get data from figure
            code_param_string = code.split("(", 1)[1][:-1]
            code_param_list = list(parse_dict_strings(code_param_string))
            code_param = []
            for series_param_string in code_param_list:
                series_param_list = \
                    list(parse_dict_strings(series_param_string[1:-1]))
                series_param = dict((ast.literal_eval(k), v) for k, v in
                    zip(series_param_list[::2], series_param_list[1::2]))
                code_param.append(series_param)

            for series_param in code_param:
                plot_panel = PlotPanel(self, -1, series_param)

                self.series_notebook.AddPage(plot_panel, _("Series"))

                for key in series_param:
                    plot_panel.series_data[key] = series_param[key]

        else:
            # Use default values
            plot_panel = PlotPanel(self, -1)
            self.series_notebook.AddPage(plot_panel, _("Series"))
            chart_data = self.eval_chart_data()
            self.figure = charts.ChartFigure(*chart_data)

        self.series_notebook.AddPage(wx.Panel(self, -1), _("+"))

        # end series creation

        self.cancel_button = wx.Button(self, wx.ID_CANCEL)
        self.ok_button = wx.Button(self, wx.ID_OK)

        self.figure_canvas = FigureCanvasWxAgg(self, -1, self.figure)

        self.__set_properties()
        self.__do_layout()
        self.__bindings()

        # Draw figure initially
        post_command_event(self, self.DrawChartMsg)

    def __set_properties(self):
        self.SetTitle(_("Insert chart"))
        self.SetSize((600, 400))
        self.figure_canvas.SetMinSize((400, 300))

    def __do_layout(self):
        main_sizer = wx.FlexGridSizer(2, 2, 0, 0)
        button_sizer = wx.FlexGridSizer(1, 3, 0, 3)

        main_sizer.Add(self.series_notebook, 1, wx.EXPAND, 0)
        main_sizer.Add(self.figure_canvas, 1, wx.EXPAND | wx.FIXED_MINSIZE, 0)
        main_sizer.Add(button_sizer, wx.ALL | wx.EXPAND, 3)
        main_sizer.AddGrowableRow(0)
        main_sizer.AddGrowableCol(0)

        button_sizer.Add(self.ok_button, 0,
            wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 3)
        button_sizer.Add(self.cancel_button, 0,
            wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 3)
        button_sizer.AddGrowableCol(2)

        self.SetSizer(main_sizer)

        self.Layout()

    def __bindings(self):
        """Binds events to handlers"""

        self.Bind(self.EVT_CMD_DRAW_CHART, self.OnDrawChart)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CLOSING, self.OnSeriesDeleted)
        self.Bind(fnb.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.OnSeriesChanged)

    def __disable_controls(self, unneeded_ctrls):
        """Disables the controls that are not needed by chart"""

        for ctrl in unneeded_ctrls:
            ctrl.Disable()

    def get_series_tuple(self, code):
        """Returns series tuples"""

        key = self.grid.actions.cursor

        try:
            result = self.grid.code_array._eval_cell(key, code)
            result_tuple = tuple(numpy.array(result))

        except (TypeError, ValueError):
            result_tuple = tuple(())

        return result_tuple

    def eval_chart_data(self):
        """Returns evaluated content for chart data"""

        chart_data = []
        no_series = self.series_notebook.GetPageCount() - 1

        for panel_number in xrange(no_series):
            series_panel = self.series_notebook.GetPage(panel_number)

            series_data = copy(series_panel.series_data)

            for key in series_panel.series_keys:
                series_data[key] = self.get_series_tuple(series_data[key])

            for key in series_panel.string_keys:
                series_data[key] = series_data[key][1:-1]

            for key in series_panel.float_keys:
                series_data[key] = float(series_data[key])

            chart_data.append(series_data)

        return chart_data

    def get_figure_code(self):
        """Returns code that generates figure"""

        chart_data_code = ""
        no_series = self.series_notebook.GetPageCount() - 1

        for panel_number in xrange(no_series):
            panel = self.series_notebook.GetPage(panel_number)
            series_data = panel.series_data

            # Build series data string
            series_data_code = ""

            for key in series_data:
                value_str = series_data[key]

                if key in panel.series_keys:
                    if not value_str or \
                       (value_str[0] != "(" or value_str[-1] != ")"):
                        value_str = "(" + value_str + ")"

                series_data_code += "'{}': {}, ".format(key, value_str)

            # Merge series data to chart data
            chart_data_code += ", {" + series_data_code + "}"

        chart_data_code = chart_data_code[2:]

        cls_name = charts.ChartFigure.__name__
        return 'charts.{}({})'.format(cls_name, chart_data_code)

    # Handlers
    # --------

    def OnSeriesChanged(self, event):
        """FlatNotebook change event handler"""

        selection = event.GetSelection()

        if selection == self.series_notebook.GetPageCount() - 1:
            # Add new series
            new_panel = PlotPanel(self, -1)
            self.series_notebook.InsertPage(selection, new_panel, _("Series"))

        event.Skip()

    def OnSeriesDeleted(self, event):
        """FlatNotebook closing event handler"""

        # Redraw Chart
        post_command_event(self, self.DrawChartMsg)

        event.Skip()

    def OnDrawChart(self, event):
        """Figure drawing event handler"""

        self.figure.chart_data = self.eval_chart_data()

        try:
            self.figure.draw_chart()
        except ValueError:
            return

        self.figure_canvas.draw()