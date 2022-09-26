import os

import wx

from .icons import (
    icons8_add_new_25,
    icons8_curly_brackets_50,
    icons8_edit_25,
    icons8_paste_25,
    icons8_remove_25,
)
from .mwindow import MWindow

_ = wx.GetTranslation


class WordlistPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.parent_panel = None
        self.wlist = self.context.elements.mywordlist
        self.current_entry = None
        # For Grid editing
        self.cur_skey = None
        self.cur_index = None
        self.to_save = None

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_grids = wx.BoxSizer(wx.HORIZONTAL)
        sizer_grid_left = wx.BoxSizer(wx.VERTICAL)
        sizer_grid_right = wx.BoxSizer(wx.VERTICAL)
        sizer_grids.Add(sizer_grid_left, 1, wx.EXPAND, 0)
        sizer_grids.Add(sizer_grid_right, 1, wx.EXPAND, 0)

        sizer_index_left = wx.BoxSizer(wx.HORIZONTAL)
        sizer_grid_left.Add(sizer_index_left, 0, wx.EXPAND, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, _("Start Index for CSV-based data:"))
        sizer_index_left.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.cbo_Index = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        sizer_index_left.Add(self.cbo_Index, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.grid_wordlist = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
        )
        sizer_grid_left.Add(self.grid_wordlist, 1, wx.EXPAND, 0)

        self.grid_content = wx.ListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES
            | wx.LC_REPORT
            | wx.LC_VRULES
            | wx.LC_SINGLE_SEL
            | wx.LC_EDIT_LABELS,
        )

        sizer_edit_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_edit_button_add = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(25, 25)
        )
        self.btn_edit_button_del = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(25, 25)
        )
        self.btn_edit_button_edit = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(25, 25)
        )
        self.btn_edit_button_paste = wx.StaticBitmap(
            self, wx.ID_ANY, size=wx.Size(25, 25)
        )
        self.btn_edit_button_add.SetBitmap(icons8_add_new_25.GetBitmap())
        self.btn_edit_button_del.SetBitmap(icons8_remove_25.GetBitmap())
        self.btn_edit_button_edit.SetBitmap(icons8_edit_25.GetBitmap())
        self.btn_edit_button_paste.SetBitmap(icons8_paste_25.GetBitmap())

        self.btn_edit_button_add.SetToolTip(
            _("Add a new entry for the active variable")
        )
        self.btn_edit_button_del.SetToolTip(
            _("Delete the current entry for the active variable")
        )
        self.btn_edit_button_edit.SetToolTip(
            _("Edit the current entry for the active variable")
        )
        self.btn_edit_button_paste.SetToolTip(
            _(
                "Paste the clipboard as new entries for the active variable, any line as new entry"
            )
        )
        minsize = 23
        self.btn_edit_button_add.SetMinSize(wx.Size(minsize, minsize))
        self.btn_edit_button_del.SetMinSize(wx.Size(minsize, minsize))
        self.btn_edit_button_edit.SetMinSize(wx.Size(minsize, minsize))
        self.btn_edit_button_paste.SetMinSize(wx.Size(minsize, minsize))
        sizer_edit_buttons.Add(self.btn_edit_button_add, 0, wx.EXPAND, 0)
        sizer_edit_buttons.Add(self.btn_edit_button_del, 0, wx.EXPAND, 0)
        sizer_edit_buttons.Add(self.btn_edit_button_edit, 0, wx.EXPAND, 0)
        sizer_edit_buttons.Add(self.btn_edit_button_paste, 0, wx.EXPAND, 0)

        sizer_index_right = wx.BoxSizer(wx.HORIZONTAL)
        label_2 = wx.StaticText(self, wx.ID_ANY, _("Start Index for field:"))
        sizer_index_right.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.cbo_index_single = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        sizer_index_right.Add(self.cbo_index_single, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        dummylabel = wx.StaticText(self, wx.ID_ANY, " ")
        sizer_index_right.Add(dummylabel, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_index_right.Add(sizer_edit_buttons, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_grid_right.Add(sizer_index_right, 0, wx.EXPAND, 0)
        sizer_grid_right.Add(self.grid_content, 1, wx.EXPAND, 0)

        self.txt_pattern = wx.TextCtrl(self, wx.ID_ANY, "")

        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons.Add(self.txt_pattern, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_add = wx.Button(self, wx.ID_ANY, _("Add Text"))
        self.btn_add.SetToolTip(_("Add another wordlist entry"))
        sizer_buttons.Add(self.btn_add, 0, 0, 0)

        self.btn_add_counter = wx.Button(self, wx.ID_ANY, _("Add Counter"))
        sizer_buttons.Add(self.btn_add_counter, 0, 0, 0)

        self.btn_delete = wx.Button(self, wx.ID_ANY, _("Delete"))
        self.btn_delete.SetToolTip(_("Delete the current wordlist entry"))
        sizer_buttons.Add(self.btn_delete, 0, 0, 0)

        sizer_exit = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_backup = wx.Button(self, wx.ID_ANY, _("Backup Wordlist"))
        self.btn_backup.SetToolTip(_("Save current wordlist to disk"))
        sizer_exit.Add(self.btn_backup, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_restore = wx.Button(self, wx.ID_ANY, _("Restore Wordlist"))
        self.btn_restore.SetToolTip(_("Load wordlist from disk"))
        sizer_exit.Add(self.btn_restore, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.lbl_message = wx.StaticText(self, wx.ID_ANY, "")
        sizer_exit.Add(self.lbl_message, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_lower = wx.BoxSizer(wx.HORIZONTAL)
        sizer_lower.Add(sizer_buttons, 1, wx.ALL, 0)
        sizer_lower.Add(sizer_exit, 1, wx.ALL, 0)

        sizer_main.Add(sizer_grids, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_lower, 0, wx.ALL, 0)

        self.SetSizer(sizer_main)
        self.Layout()

        self.btn_add.Bind(wx.EVT_BUTTON, self.on_btn_add)
        self.btn_add_counter.Bind(wx.EVT_BUTTON, self.on_add_counter)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_btn_delete)
        self.btn_backup.Bind(wx.EVT_BUTTON, self.on_backup)
        self.btn_restore.Bind(wx.EVT_BUTTON, self.on_restore)
        self.txt_pattern.Bind(wx.EVT_TEXT, self.on_patterntext_change)
        self.cbo_Index.Bind(wx.EVT_COMBOBOX, self.on_cbo_select)
        self.grid_wordlist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_grid_wordlist)
        self.grid_content.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_grid_content)
        self.grid_content.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_begin_edit)
        self.grid_content.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_edit)
        self.btn_edit_button_add.Bind(wx.EVT_LEFT_DOWN, self.on_button_edit_add)
        self.btn_edit_button_del.Bind(wx.EVT_LEFT_DOWN, self.on_button_edit_del)
        self.btn_edit_button_edit.Bind(wx.EVT_LEFT_DOWN, self.on_button_edit_edit)
        self.btn_edit_button_paste.Bind(wx.EVT_LEFT_DOWN, self.on_button_edit_paste)
        self.cbo_index_single.Bind(wx.EVT_COMBOBOX, self.on_single_index)
        self.populate_gui()

    def set_parent(self, par_panel):
        self.parent_panel = par_panel

    def pane_show(self):
        self.populate_gui()
        self.grid_wordlist.SetFocus()

    def pane_hide(self):
        pass

    def on_button_edit_add(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        self.wlist.add_value(self.cur_skey, "---", 0)
        self.refresh_grid_content(skey, 0)

    def on_button_edit_del(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        index = self.grid_content.GetFirstSelected()
        if index >= 0:
            pass
        self.wlist.delete_value(skey, index)
        self.refresh_grid_content(skey, 0)

    def on_button_edit_edit(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        index = self.grid_content.GetFirstSelected()
        if index >= 0:
            self.cur_index = index
            self.grid_content.EditLabel(self.cur_index)

    def on_button_edit_paste(self, event):
        skey = self.cur_skey
        if skey is None:
            return
        text_data = wx.TextDataObject()
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(text_data)
            wx.TheClipboard.Close()
        if success:
            msg = text_data.GetText()
            if msg is not None and len(msg) > 0:
                lines = msg.splitlines()
                for entry in lines:
                    self.wlist.add_value(skey, entry, 0)
                self.refresh_grid_content(skey, 0)

    def refresh_grid_wordlist(self):
        self.current_entry = None
        self.grid_wordlist.ClearAll()
        self.cur_skey = None
        self.grid_wordlist.InsertColumn(0, _("Type"))
        self.grid_wordlist.InsertColumn(1, _("Name"))
        self.grid_wordlist.InsertColumn(2, _("Index"))
        typestr = [_("Text"), _("CSV"), _("Counter")]
        for skey in self.wlist.content:
            index = self.grid_wordlist.InsertItem(
                self.grid_wordlist.GetItemCount(), typestr[self.wlist.content[skey][0]]
            )
            self.grid_wordlist.SetItem(index, 1, skey)
            self.grid_wordlist.SetItem(index, 2, str(self.wlist.content[skey][1] - 2))
        self.grid_wordlist.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.grid_wordlist.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        self.grid_wordlist.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

    def get_column_text(self, grid, index, col):
        item = grid.GetItem(index, col)
        return item.GetText()

    def set_column_text(self, grid, index, col, value):
        # item = grid.GetItem(index)
        grid.SetStringItem(index, col, value)

    def refresh_grid_content(self, skey, current):
        self.cbo_index_single.Clear()
        choices = []
        selidx = 0
        self.grid_content.ClearAll()
        self.cur_skey = skey
        self.cur_index = None
        self.grid_content.InsertColumn(0, _("Content"))

        for idx in range(2, len(self.wlist.content[skey])):
            myidx = idx - 2
            s_entry = str(self.wlist.content[skey][idx])
            choices.append(f"{myidx:3d} - {s_entry[:10]}")
            index = self.grid_content.InsertItem(
                self.grid_content.GetItemCount(), s_entry
            )
            if idx == current + 2:
                selidx = current
                self.grid_content.SetItemTextColour(index, wx.RED)
        wsize = self.grid_content.GetSize()
        self.grid_content.SetColumnWidth(0, wsize[0] - 10)
        self.cbo_index_single.Set(choices)
        if selidx >= 0:
            self.cbo_index_single.SetSelection(selidx)

    def on_single_index(self, event):
        skey = self.cur_skey
        idx = self.cbo_index_single.GetSelection()
        if skey is None:
            return
        self.wlist.set_index(skey, idx)
        self.refresh_grid_content(skey, idx)
        # We need to refresh the main_index_column as well
        self.set_column_text(self.grid_wordlist, self.current_entry, 2, str(idx))

    def on_grid_wordlist(self, event):
        current_item = event.Index
        self.current_entry = current_item
        skey = self.get_column_text(self.grid_wordlist, current_item, 1)
        try:
            current = int(self.get_column_text(self.grid_wordlist, current_item, 2))
        except ValueError:
            current = 0

        self.refresh_grid_content(skey, current)
        self.txt_pattern.SetValue(skey)
        event.Skip()

    def on_grid_content(self, event):
        # Single Click
        event.Skip()

    def on_begin_edit(self, event):
        index = self.grid_content.GetFirstSelected()
        if index >= 0:
            self.cur_index = index
        self.to_save = (self.cur_skey, self.cur_index)
        event.Allow()

    def on_end_edit(self, event):
        if self.to_save is None:
            self.edit_message(_("Update failed"))
        else:
            skey = self.to_save[0]
            index = self.to_save[1]
            value = event.GetText()
            self.wlist.set_value(skey, value, index)
        self.to_save = None
        event.Allow()

    def populate_gui(self):
        self.cbo_Index.Clear()
        self.cbo_Index.Enable(False)
        maxidx = -1
        self.grid_content.ClearAll()
        self.refresh_grid_wordlist()
        for skey in self.wlist.content:
            if self.wlist.content[skey][0] == 1:  # CSV
                i = len(self.wlist.content[skey]) - 2
                if i > maxidx:
                    maxidx = i
        if maxidx >= 0:
            for i in range(maxidx):
                self.cbo_Index.Append(str(i))
            self.cbo_Index.SetValue("0")
        self.cbo_Index.Enable(True)
        # Lets refresh the scene to acknowledge new changes
        self.context.signal("refresh_scene")

    def edit_message(self, text):
        self.lbl_message.Label = text
        self.lbl_message.Refresh()

    def on_cbo_select(self, event):
        try:
            idx = int(self.cbo_Index.GetValue())
        except ValueError:
            idx = 0
        self.wlist.set_index(skey="@all", idx=idx)
        selidx = self.grid_wordlist.GetFirstSelected()
        if selidx < 0:
            selidx = 0
        self.refresh_grid_wordlist()
        self.grid_wordlist.Select(selidx, True)

    def on_btn_add(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey) > 0:
            if skey in self.wlist.content:
                self.wlist.delete(skey)
            self.wlist.add_value(skey, "---", 0)
            self.populate_gui()
        event.Skip()

    def on_patterntext_change(self, event):
        enab = len(self.txt_pattern.GetValue()) > 0
        self.btn_add.Enable(enab)
        self.btn_add_counter.Enable(enab)
        self.btn_delete.Enable(enab)

    def on_add_counter(self, event):  # wxGlade: editWordlist.<event_handler>
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey) > 0:
            if skey in self.wlist.content:
                self.wlist.delete(skey)
            self.wlist.add_value(skey, 1, 2)
            self.populate_gui()
        event.Skip()

    def on_btn_delete(self, event):
        skey = self.txt_pattern.GetValue()
        if skey is not None and len(skey) > 0:
            self.wlist.delete(skey)
            self.populate_gui()
        event.Skip()

    def on_backup(self, event):
        if self.wlist.default_filename is not None:
            self.wlist.save_data(self.wlist.default_filename)
            msg = _("Saved to ") + self.wlist.default_filename
            self.edit_message(msg)
        event.Skip()

    def on_restore(self, event):
        if self.wlist.default_filename is not None:
            self.wlist.load_data(self.wlist.default_filename)
            msg = _("Loaded from ") + self.wlist.default_filename
            self.edit_message(msg)
            self.populate_gui()
        event.Skip()


class ImportPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.parent_panel = None
        self.context = context
        self.wlist = self.context.elements.mywordlist
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        info_box = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("Import CSV")),
            wx.HORIZONTAL,
        )
        sizer_csv = wx.BoxSizer(wx.HORIZONTAL)
        info_box.Add(sizer_csv, 1, wx.EXPAND, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, _("Import CSV-File"))
        sizer_csv.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.txt_filename = wx.TextCtrl(self, wx.ID_ANY, "")
        sizer_csv.Add(self.txt_filename, 1, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_fileDialog = wx.Button(self, wx.ID_ANY, "...")
        self.btn_fileDialog.SetMinSize((23, 23))
        sizer_csv.Add(self.btn_fileDialog, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        self.btn_import = wx.Button(self, wx.ID_ANY, _("Import CSV"))
        sizer_csv.Add(self.btn_import, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        main_sizer.Add(info_box, 0, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()
        self.btn_fileDialog.Bind(wx.EVT_BUTTON, self.on_btn_file)
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_btn_import)
        self.txt_filename.Bind(wx.EVT_TEXT, self.on_filetext_change)
        self.btn_import.Enable(False)

    def set_parent(self, par_panel):
        self.parent_panel = par_panel

    def on_btn_file(self, event):
        myfile = ""
        mydlg = wx.FileDialog(
            self,
            message=_("Choose a csv-file"),
            wildcard="CSV-Files (*.csv)|*.csv|Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW,
        )
        if mydlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            myfile = mydlg.GetPath()
        mydlg.Destroy()
        if myfile != "":
            self.txt_filename.SetValue(myfile)
            self.on_btn_import(None)

    def on_btn_import(self, event):
        myfile = self.txt_filename.GetValue()
        if os.path.exists(myfile):
            ct, colcount, headers = self.wlist.load_csv_file(myfile)
            msg = _("Imported file, {col} fields, {row} rows").format(
                col=colcount, row=ct
            )
            if self.parent_panel is not None:
                self.parent_panel.edit_message(msg)
                self.parent_panel.populate_gui()

    def on_filetext_change(self, event):
        myfile = self.txt_filename.GetValue()
        enab = False
        if os.path.exists(myfile):
            enab = True
        self.btn_import.Enable(enab)


class AboutPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        info_box = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, _("How to use...")),
            wx.VERTICAL,
        )
        self.parent_panel = None

        s = _(
            "The objective of this functionality is to create burning templates, that can be reused"
        )
        s += " " + ("for different data with minimal adjustment effort.")
        s += "\n" + _(
            "Let's clarify the term variable first: a variable is a placeholder for some text"
        )
        s += " " + _(
            "that can be used as part of the text-definition of a Text-Object."
        )
        s += "\n" + _(
            "It's reference (i.e. variable name) is used within curly brackets to indicate"
        )
        s += " " + _("that it will eventually be replaced by 'real' content.")

        s += "\n" + _(
            "Let's come back to our use-case, imagine you want to create a name-tag pattern that"
        )
        s += " " + _(
            "can be reused. Lets create a text-object inside a frame and set its text to"
        )
        s += " " + _(
            r"'This item belongs to {NAME}'. If you define a variable named 'NAME' and"
        )
        s += " " + _(
            "assign a value like 'John' to it, then the burned text will finally state:"
        )
        s += "\n" + _("'This item belongs to John'")

        s += "\n" + _(
            "You can define a set of variables (called wordlist) that could be populated"
        )
        s += " " + _(
            "by a standard comma-separated CSV file. The you could have not just one"
        )
        s += " " + _(
            "entry defined for 'NAME' but dozens of them. Which of the multiple entries"
        )
        s += " " + _("is currently active is decided by its index value.")
        s += "\n" + _(
            "You are not restricted to a single use of a variable (useful e.g."
        )
        s += " " + _(
            r"if you want to batch-burn a couple of name-tags). The standard use {NAME} indicates"
        )
        s += " " + _(
            r"the value at position #index of the loaded list, {NAME#+1} (note the plus sign)"
        )
        s += " " + _(
            r"uses the next entry, {NAME#+2} the second entry after the current."
        )
        s += "\n" + _(
            r"Note: This usage does not change the index position, you need to manually advance it."
        )
        s += "\n" + _(
            r"If you want to autoadvance the index after every use, then you can use {NAME++}."
        )
        s += "\n\n" + _(
            "There are couple of predefined variables, that refer to the current burn operation"
        )
        s += " " + _(
            r"(like {op_power}, {op_speed} or others) or contain date/time-information ({date}, {time})."
        )
        s += "\n" + _(
            "Please note that date and time may be provided in a format that allows to define their"
        )
        s += " " + _(
            r"appearance according to local preferences: e.g. {date@%d.%m.%Y} will provide a date"
        )
        s += " " + _(r"like 31.12.2022 and {time@%H:%M} a time like 23:59.")
        s += "\n" + _("For a complete set of format-directives see:")
        s += (
            "\n"
            + r"https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior"
        )
        info_label = wx.TextCtrl(
            self, wx.ID_ANY, value=s, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        info_label.SetBackgroundColour(self.GetBackgroundColour())
        info_box.Add(info_label, 1, wx.EXPAND, 0)
        main_sizer.Add(info_box, 1, wx.EXPAND, 0)
        self.SetSizer(main_sizer)
        self.Layout()

    def set_parent(self, par_panel):
        self.parent_panel = par_panel


class WordlistEditor(MWindow):
    def __init__(self, *args, **kwds):
        super().__init__(500, 530, *args, **kwds)

        self.panel_editor = WordlistPanel(self, wx.ID_ANY, context=self.context)
        self.panel_import = ImportPanel(self, wx.ID_ANY, context=self.context)
        self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)

        self.panel_editor.set_parent(self)
        self.panel_import.set_parent(self)
        self.panel_about.set_parent(self)

        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icons8_curly_brackets_50.GetBitmap())
        self.SetIcon(_icon)
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.notebook_main.AddPage(self.panel_editor, _("Editing"))
        self.notebook_main.AddPage(self.panel_import, _("Import/Export"))
        self.notebook_main.AddPage(self.panel_about, _("How to use"))
        # begin wxGlade: Keymap.__set_properties
        self.SetTitle(_("Wordlist Editor"))

    def delegates(self):
        yield self.panel_editor
        yield self.panel_import
        yield self.panel_about

    @staticmethod
    def sub_register(kernel):
        kernel.register(
            "button/config/Wordlist",
            {
                "label": _("Wordlist"),
                "icon": icons8_curly_brackets_50,
                "tip": _("Manages Wordlist-Entries"),
                "action": lambda v: kernel.console("window toggle Wordlist\n"),
            },
        )

    def window_open(self):
        pass

    def window_close(self):
        pass

    def edit_message(self, msg):
        self.panel_editor.edit_message(msg)

    def populate_gui(self):
        self.panel_editor.populate_gui()

    @staticmethod
    def submenu():
        return ("Editing", "Variables + Wordlists")
