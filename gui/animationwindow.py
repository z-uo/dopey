# This file is part of MyPaint.
# Copyright (C) 2009 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import gtk
import pango

from gettext import gettext as _
import gobject

import dialogs
import anidialogs
from layerswindow import stock_button

from lib.framelist import DEFAULT_ACTIVE_CELS

COLUMNS_NAME = ('frame_index', 'frame_data')
COLUMNS_ID = dict((name, i) for i, name in enumerate(COLUMNS_NAME))

class AnimationTool (gtk.VBox):

    stock_id = 'mypaint-tool-animation'
    
    tool_widget_title = _("Animation")

    tool_widget_icon_name = "mypaint-tool-animation"
    tool_widget_title = _("Animation")
    tool_widget_description = _("Create cel-based animation")

    __gtype_name__ = 'MyPaintAnimationTool'
    
    def __init__(self):
        gtk.VBox.__init__(self)
        from application import get_app
        app = get_app()
        self.app = app
        self.ani = app.doc.ani.model
        self.is_playing = False

        self.set_size_request(200, 150)
        self.app.doc.model.doc_observers.append(self.doc_structure_modified_cb)
        
        # create list:
        self.listmodel = self.create_list()
        
        # create tree view:
        self.treeview = gtk.TreeView(self.listmodel)
        self.treeview.set_rules_hint(True)
        self.treeview.set_headers_visible(False)
        treesel = self.treeview.get_selection()
        treesel.set_mode(gtk.SELECTION_SINGLE)
        self.changed_handler = treesel.connect('changed', self.on_row_changed)
        self.treeview.connect('row-activated', self.on_row_activated)
        
        self.add_columns()
        
        layers_scroll = gtk.ScrolledWindow()
        layers_scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        layers_scroll.set_placement(gtk.CORNER_TOP_RIGHT)
        layers_scroll.add(self.treeview)

        # xsheet controls:
        
        def pixbuf_button(pixbuf):
            b = gtk.Button()
            img = gtk.Image()
            img.set_from_pixbuf(pixbuf)
            b.add(img)
            return b

        pixbuf_key = self.app.pixmaps.keyframe_add
        self.key_button = pixbuf_button(pixbuf_key)
        self.key_button.connect('clicked', self.on_toggle_key)
        self.key_button.set_tooltip_text(_('Toggle Keyframe'))
        
        pixbuf_skip = self.app.pixmaps.cel_skip
        self.skip_button = pixbuf_button(pixbuf_skip)
        self.skip_button.connect('clicked', self.on_toggle_skip)
        self.skip_button.set_tooltip_text(_('Set/Unset onion skin'))
        
        pixbuf_add = self.app.pixmaps.cel_add
        self.add_cel_button = pixbuf_button(pixbuf_add)
        self.add_cel_button.connect('clicked', self.on_add_cel)
        self.add_cel_button.set_tooltip_text(_('Add cel to this frame'))
        
        insert_frame_button = stock_button(gtk.STOCK_ADD)
        insert_frame_button.connect('clicked', self.on_insert_frame)
        insert_frame_button.set_tooltip_text(_('Insert frame'))
        self.insert_frame_button = insert_frame_button

        remove_frame_button = stock_button(gtk.STOCK_REMOVE)
        remove_frame_button.connect('clicked', self.on_remove_frame)
        remove_frame_button.set_tooltip_text(_('Remove frame / cel'))
        self.remove_frame_button = remove_frame_button
        
        buttons_hbox = gtk.HBox()
        buttons_hbox.pack_start(self.key_button)
        buttons_hbox.pack_start(self.skip_button)
        buttons_hbox.pack_start(self.add_cel_button)
        buttons_hbox.pack_start(insert_frame_button)
        buttons_hbox.pack_start(remove_frame_button)

        # player controls:
        
        self.previous_button = stock_button(gtk.STOCK_GO_UP)
        self.previous_button.connect('clicked', self.on_previous_frame)
        self.previous_button.set_tooltip_text(_('Previous Frame'))
        
        self.next_button = stock_button(gtk.STOCK_GO_DOWN)
        self.next_button.connect('clicked', self.on_next_frame)
        self.next_button.set_tooltip_text(_('Next Frame'))
        
        self.play_button = stock_button(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect('clicked', self.on_animation_play)
        self.play_button.set_tooltip_text(_('Play animation'))
        
        self.pause_button = stock_button(gtk.STOCK_MEDIA_PAUSE)
        self.pause_button.connect('clicked', self.on_animation_pause)
        self.pause_button.set_tooltip_text(_('Pause animation'))

        self.stop_button = stock_button(gtk.STOCK_MEDIA_STOP)
        self.stop_button.connect('clicked', self.on_animation_stop)
        self.stop_button.set_tooltip_text(_('Stop animation'))

        anibuttons_hbox = gtk.HBox()
        anibuttons_hbox.pack_start(self.previous_button)
        anibuttons_hbox.pack_start(self.next_button)
        anibuttons_hbox.pack_start(self.play_button)
        anibuttons_hbox.pack_start(self.pause_button)
        anibuttons_hbox.pack_start(self.stop_button)

        # frames edit controls:
        cut_button = stock_button(gtk.STOCK_CUT)
        cut_button.connect('clicked', self.on_cut)
        cut_button.set_tooltip_text(_('Cut cel'))
        self.cut_button = cut_button

        copy_button = stock_button(gtk.STOCK_COPY)
        copy_button.connect('clicked', self.on_copy)
        copy_button.set_tooltip_text(_('Copy cel'))
        self.copy_button = copy_button

        paste_button = stock_button(gtk.STOCK_PASTE)
        paste_button.connect('clicked', self.on_paste)
        paste_button.set_tooltip_text(_('Paste cel'))
        self.paste_button = paste_button

        editbuttons_hbox = gtk.HBox()
        editbuttons_hbox.pack_start(cut_button)
        editbuttons_hbox.pack_start(copy_button)
        editbuttons_hbox.pack_start(paste_button)

        # lightbox controls:

        adj = gtk.Adjustment(lower=0, upper=100, step_incr=1, page_incr=10)
        self.opacity_scale = gtk.HScale(adj)
        opa = self.app.preferences.get('lightbox.factor', 100)
        self.opacity_scale.set_value(opa)
        self.opacity_scale.set_value_pos(gtk.POS_LEFT)
        opacity_lbl = gtk.Label(_('Opacity:'))
        opacity_hbox = gtk.HBox()
        opacity_hbox.pack_start(opacity_lbl, expand=False)
        opacity_hbox.pack_start(self.opacity_scale, expand=True)
        self.opacity_scale.connect('value-changed',
                                   self.on_opacityfactor_changed)

        self.expander_prefs_loaded = False
        self.connect("show", self.show_cb)

        def opacity_checkbox(attr, label, tooltip=None):
            cb = gtk.CheckButton(label)
            pref = "lightbox.%s" % (attr,)
            default = DEFAULT_ACTIVE_CELS[attr]
            cb.set_active(self.app.preferences.get(pref, default))
            cb.connect('toggled', self.on_opacity_toggled, attr)
            if tooltip is not None:
                cb.set_tooltip_text(tooltip)
            opacityopts_vbox.pack_start(cb, expand=False)

        opacityopts_vbox = gtk.VBox()
        opacity_checkbox('cel', _('Inmediate'), _("Show the inmediate next and previous cels."))
        opacity_checkbox('key', _('Inmediate keys'), _("Show the cel keys that are after and before the current cel."))
        opacity_checkbox('inbetweens', _('Inbetweens'), _("Show the cels that are between the inmediate key cels."))
        opacity_checkbox('other keys', _('Other keys'), _("Show the other keys cels."))
        opacity_checkbox('other', _('Other'), _("Show the rest of the cels."))

        self.framerate_adjustment = gtk.Adjustment(value=self.ani.framerate, lower=1, upper=120, step_incr=1)
        self.framerate_adjustment.connect("value-changed", self.on_framerate_changed)
        self.framerate_entry = gtk.SpinButton(adjustment=self.framerate_adjustment, digits=0, climb_rate=1.5)
        framerate_lbl = gtk.Label(_('Frame rate:'))
        framerate_hbox = gtk.HBox()
        framerate_hbox.pack_start(framerate_lbl, False, False)
        framerate_hbox.pack_start(self.framerate_entry, False, False)

        icons_cb = gtk.CheckButton(_("Small icons"))
        icons_cb.set_active(self.app.preferences.get("xsheet.small_icons", False))
        icons_cb.connect('toggled', self.on_smallicons_toggled)
        icons_cb.set_tooltip_text(_("Use smaller icons, better to see more rows."))

        play_lightbox_cb = gtk.CheckButton(_("Play with lightbox on"))
        play_lightbox_cb.set_active(self.app.preferences.get("xsheet.play_lightbox", False))
        play_lightbox_cb.connect('toggled', self.on_playlightbox_toggled)
        play_lightbox_cb.set_tooltip_text(_("Show other frames while playing, this is slower."))

        showprev_cb = gtk.CheckButton(_("Lightbox show previous"))
        showprev_cb.set_active(self.app.preferences.get("xsheet.lightbox_show_previous", True))
        showprev_cb.connect('toggled', self.on_shownextprev_toggled, 'previous')
        showprev_cb.set_tooltip_text(_("Show previous cels in the lightbox."))

        shownext_cb = gtk.CheckButton(_("Lightbox show next"))
        shownext_cb.set_active(self.app.preferences.get("xsheet.lightbox_show_next", False))
        shownext_cb.connect('toggled', self.on_shownextprev_toggled, 'next')
        shownext_cb.set_tooltip_text(_("Show next cels in the lightbox."))

        controls_vbox = gtk.VBox()
        controls_vbox.pack_start(buttons_hbox, expand=False)
        controls_vbox.pack_start(anibuttons_hbox, expand=False)
        controls_vbox.pack_start(editbuttons_hbox, expand=False)

        preferences_vbox = gtk.VBox()
        preferences_vbox.pack_start(framerate_hbox, expand=False)
        preferences_vbox.pack_start(icons_cb, expand=False)
        preferences_vbox.pack_start(play_lightbox_cb, expand=False)
        preferences_vbox.pack_start(showprev_cb, expand=False)
        preferences_vbox.pack_start(shownext_cb, expand=False)
        preferences_vbox.pack_start(opacity_hbox, expand=False)
        preferences_vbox.pack_start(opacityopts_vbox, expand=False)

        self.controls_expander = gtk.Expander(label=_('Controls'))
        self.controls_expander.add(controls_vbox)
        self.controls_expander.connect("notify::expanded",
            self.expanded_cb, 'controls')

        self.prefs_expander = gtk.Expander(label=_('Preferences'))
        self.prefs_expander.add(preferences_vbox)
        self.prefs_expander.connect("notify::expanded",
            self.expanded_cb, 'preferences')

        self.pack_start(layers_scroll)
        self.pack_start(self.controls_expander, expand=False)
        self.pack_start(self.prefs_expander, expand=False)

        self.show_all()
        self._change_player_buttons()
        self.app.doc.model.doc_observers.append(self.update)

    def _get_path_from_frame(self, frame):
        return (self.ani.frames.idx, )

    def setup_lightbox(self):
        active_cels = {}
        for attr, default in DEFAULT_ACTIVE_CELS.items():
            pref = "lightbox.%s" % (attr,)
            default = DEFAULT_ACTIVE_CELS[attr]
            active_cels[attr] = self.app.preferences.get(pref, default)
        self.ani.frames.setup_active_cels(active_cels)

    def setup(self):
        treesel = self.treeview.get_selection()
        treesel.handler_block(self.changed_handler)

        # disconnect treeview so it doesn't update for each row added:
        self.treeview.set_model(None)

        self.listmodel.clear()
        xsheet_list = list(enumerate(self.ani.frames))
        for i, frame in xsheet_list:
            self.listmodel.append((i, frame))

        column = self.treeview.get_column(0)
        cell = column.get_cells()[0]
        column.set_cell_data_func(cell, self.set_number)
        column = self.treeview.get_column(1)
        cell = column.get_cells()[0]
        column.set_cell_data_func(cell, self.set_icon)
        column = self.treeview.get_column(2)
        cell = column.get_cells()[0]
        column.set_cell_data_func(cell, self.set_description)

        # reconnect treeview:
        self.treeview.set_model(self.listmodel)

        treesel.handler_unblock(self.changed_handler)

        self.on_opacityfactor_changed()
        self.setup_lightbox()

    def _update(self):
        if self.ani.cleared:
            self.setup()
            self.ani.cleared = False

        frame = self.ani.frames.get_selected()
        path = self._get_path_from_frame(frame)
        self.treeview.get_selection().select_path(path)
        self.treeview.scroll_to_cell(path)
        self.queue_draw()
        self._update_buttons_sensitive()

        if not self.is_playing and self.ani.player_state == "play":
            use_lightbox = self.app.preferences.get("xsheet.play_lightbox",
                                                    False)
            self._play_animation(use_lightbox=use_lightbox)

    def update(self, doc):
        return self._update()

    def create_list(self):
        xsheet_list = list(enumerate(self.ani.frames))
        listmodel = gtk.ListStore(int, object)
        for i, frame in xsheet_list:
            listmodel.append((i, frame))
        return listmodel
    
    def add_columns(self):
        listmodel = self.treeview.get_model()
        font = pango.FontDescription('normal 8')

        # frame number column

        frameno_cell = gtk.CellRendererText()
        frameno_cell.set_property('font-desc', font)
        framenumber_col = gtk.TreeViewColumn(_("Frame"))
        framenumber_col.pack_start(frameno_cell, True)
        framenumber_col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        framenumber_col.set_fixed_width(50)
        framenumber_col.set_cell_data_func(frameno_cell, self.set_number)

        # icon column

        icon_cell = gtk.CellRendererPixbuf()
        icon_col = gtk.TreeViewColumn(_("Status"))
        icon_col.pack_start(icon_cell, expand=False)
        icon_col.add_attribute(icon_cell, 'pixbuf', 0)
        icon_col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        icon_col.set_fixed_width(50)
        icon_col.set_cell_data_func(icon_cell, self.set_icon)

        # description column

        desc_cell = gtk.CellRendererText()
        desc_cell.set_property('font-desc', font)
        description_col = gtk.TreeViewColumn(_("Description"))
        description_col.pack_start(desc_cell, True)
        description_col.set_cell_data_func(desc_cell, self.set_description)

        self.treeview.append_column(framenumber_col)
        self.treeview.append_column(icon_col)
        self.treeview.append_column(description_col)
        
    def _change_player_buttons(self):
        if self.is_playing:
            self.play_button.hide()
            self.pause_button.show()
        else:
            self.play_button.show()
            self.pause_button.hide()
        self.stop_button.set_sensitive(self.is_playing)

    def _update_buttons_sensitive(self):
        self.previous_button.set_sensitive(self.ani.frames.has_previous())
        self.next_button.set_sensitive(self.ani.frames.has_next())
        self.cut_button.set_sensitive(self.ani.can_cutcopy())
        self.copy_button.set_sensitive(self.ani.can_cutcopy())
        self.paste_button.set_sensitive(self.ani.can_paste())

    def doc_structure_modified_cb(self, *args):
        self.framerate_adjustment.set_value(self.ani.framerate)
    
    def on_row_changed(self, treesel):
        model, it = treesel.get_selected()
        path = model.get_path(it)
        frame_idx = path[COLUMNS_ID['frame_index']]
        self.ani.select_frame(frame_idx)
        self._update_buttons_sensitive()
    
    def on_row_activated(self, a, r, g):
        treesel = self.treeview.get_selection()
        model, it = treesel.get_selected()
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        description = anidialogs.ask_for(self, _("Change description"),
            _("Description"), frame.description)
        if description:
            self.ani.change_description(description)
            
    def on_toggle_key(self, button):
        self.ani.toggle_key()

    def on_toggle_skip(self, button):
        self.ani.toggle_skip_visible()
    
    def on_previous_frame(self, button):
        self.ani.previous_frame()
    
    def on_next_frame(self, button):
        self.ani.next_frame()
    
    def on_add_cel(self, button):
        self.ani.add_cel()
        
    def on_insert_frame(self, button):
        self.ani.insert_frames(1)

    def on_remove_frame(self, button):
        self.ani.remove_frame()
    
    def _get_row_class(self, model, it):
        """Return 0 if even row, 1 if odd row."""
        path = model.get_path(it)[0]
        return path % 2

    def set_number(self, column, cell, model, it, data):
        idx = model.get_value(it, COLUMNS_ID['frame_index'])
        cell.set_property('text', str(idx+1))
        
    def set_description(self, column, cell, model, it, data):
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        cell.set_property('text', frame.description)
        
    def set_icon(self, column, cell, model, it, data):
        frame = model.get_value(it, COLUMNS_ID['frame_data'])
        pixname = 'frame'
        if frame.cel is not None:
            pixname += '_cel'
            if not frame.skip_visible:
                pixname += '_onion'
        if frame.is_key:
            pixname = 'key' + pixname
        small_icons = self.app.preferences.get("xsheet.small_icons", False)
        if small_icons:
            pixname += '_small'
        pixbuf = getattr(self.app.pixmaps, pixname)
        cell.set_property('pixbuf', pixbuf)

    def _call_player(self, use_lightbox=False):
        self.ani.player_next(use_lightbox)
        keep_playing = True
        if self.ani.player_state == "stop":
            self.ani.select_without_undo(self.beforeplay_frame)
            keep_playing = False
            self.is_playing = False
            self._change_player_buttons()
            self.ani.player_state = None
            self._update()
        elif self.ani.player_state == "pause":
            keep_playing = False
            self.is_playing = False
            self._change_player_buttons()
            self.ani.player_state = None
            self._update()
        return keep_playing

    def _play_animation(self, from_first_frame=True, use_lightbox=False):
        self.is_playing = True
        self.beforeplay_frame = self.ani.frames.idx
        if from_first_frame:
            self.ani.frames.select(0)
        self._change_player_buttons()
        self.ani.hide_all_frames()
        # animation timer
        ms_per_frame = int(round(1000.0/self.framerate_entry.get_value()))

        # show first frame immediately, otherwise there's a single frame delay
        # @TODO: it seems to wait one frame before stopping too
        self._call_player(use_lightbox)

        gobject.timeout_add(ms_per_frame, self._call_player, use_lightbox)

    def on_animation_play(self, button):
        self.ani.play_animation()

    def on_animation_pause(self, button):
        self.ani.pause_animation()

    def on_animation_stop(self, button):
        self.ani.stop_animation()

    def on_opacityfactor_changed(self, *ignore):
        opa = self.opacity_scale.get_value()
        self.app.preferences["lightbox.factor"] = opa
        self.ani.change_opacityfactor(opa/100.0)
        self.queue_draw()

    def on_opacity_toggled(self, checkbox, attr):
        pref = "lightbox.%s" % (attr,)
        self.app.preferences[pref] = checkbox.get_active()
        self.ani.toggle_opacity(attr, checkbox.get_active())
        self.queue_draw()

    def on_framerate_changed(self, adj):
        self.ani.framerate = adj.get_value()

    def on_smallicons_toggled(self, checkbox):
        self.app.preferences["xsheet.small_icons"] = checkbox.get_active()
        # TODO, this is a quick fix, better is to update only the rows
        # height
        self.setup()
        
    def on_playlightbox_toggled(self, checkbox):
        self.app.preferences["xsheet.play_lightbox"] = checkbox.get_active()

    def on_shownextprev_toggled(self, checkbox, nextprev):
        self.app.preferences["xsheet.lightbox_show_" + nextprev] = checkbox.get_active()
        self.ani.toggle_nextprev(nextprev, checkbox.get_active())

    def on_cut(self, button):
        self.ani.cutcopy_cel('cut')

    def on_copy(self, button):
        self.ani.cutcopy_cel('copy')

    def on_paste(self, button):
        self.ani.paste_cel()

    def show_cb(self, widget):
        if self.app.preferences.get("xsheet.expander-controls", False):
            self.controls_expander.set_expanded(True)
        if self.app.preferences.get("xsheet.expander-preferences", False):
            self.prefs_expander.set_expanded(True)
        self.expander_prefs_loaded = True

    def expanded_cb(self, expander, junk, cfg_stem):
        # Save the expander state
        if not self.expander_prefs_loaded:
            return
        expanded = bool(expander.get_expanded())
        self.app.preferences['xsheet.expander-%s' % cfg_stem] = expanded
