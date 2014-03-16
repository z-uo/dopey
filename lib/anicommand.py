# This file is part of MyPaint.
# Copyright (C) 2007-2008 by Martin Renold <martinxyz@gmx.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from command import Action, SelectLayer
import layer
from gettext import gettext as _

def layername_from_description(description):
    layername = "CEL"
    if description != '':
        layername += " " + description
    return layername


class SelectFrame(Action):
    display_name = _("Select frame")
    def __init__(self, doc, idx):
        self.doc = doc
        self.frames = doc.ani.frames
        self.idx = idx
        self.prev_layer_idx = None

    def redo(self):
        cel = self.frames.cel_at(self.idx)
        if cel is not None:
            # Select the corresponding layer:
            layer_idx = self.doc.layers.index(cel)
            self.prev_layer_idx = self.doc.layer_idx
            self.doc.layer_idx = layer_idx
        
        self.prev_frame_idx = self.frames.idx
        self.frames.select(self.idx)
        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        if self.prev_layer_idx is not None:
            self.doc.layer_idx = self.prev_layer_idx
        
        self.frames.select(self.prev_frame_idx)
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class ToggleKey(Action):
    display_name = _("Toggle key")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame
    
    def redo(self):
        self.prev_value = self.frame.is_key
        self.frame.toggle_key()
        self.doc.ani.update_opacities()
        self._notify_document_observers()

    def undo(self):
        self.frame.is_key = self.prev_value
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class ToggleSkipVisible(Action):
    display_name = _("Toggle skip visible")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame

    def redo(self):
        self.prev_value = self.frame.skip_visible
        self.frame.toggle_skip_visible()
        self.doc.ani.update_opacities()
        self._notify_document_observers()

    def undo(self):
        self.frame.skip_visible = self.prev_value
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class ChangeDescription(Action):
    display_name = _("Change description")
    def __init__(self, doc, frame, new_description):
        self.doc = doc
        self.frame = frame
        self.new_description = new_description
        if self.frame.cel != None:
            self.old_layername = self.frame.cel.name

    def redo(self):
        self.prev_value = self.frame.description
        self.frame.description = self.new_description
        self._notify_document_observers()
        if self.frame.cel != None:
            layername = layername_from_description(self.frame.description)
            self.frame.cel.name = layername

    def undo(self):
        self.frame.description = self.prev_value
        self._notify_document_observers()
        if self.frame.cel != None:
            self.frame.cel.name = self.old_layername


class AddCel(Action):
    display_name = _("Add cel")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame

        # Create new layer:
        layername = layername_from_description(self.frame.description)
        self.layer = layer.Layer(name=layername)
        self.layer._surface.observers.append(self.doc.layer_modified_cb)
    
    def redo(self):
        self.doc.layers.append(self.layer)
        self.prev_idx = self.doc.layer_idx
        self.doc.layer_idx = len(self.doc.layers) - 1
        
        self.frame.add_cel(self.layer)
        self._notify_canvas_observers([self.layer])
        self.doc.ani.update_opacities()
        self._notify_document_observers()
    
    def undo(self):
        self.doc.layers.remove(self.layer)
        self.doc.layer_idx = self.prev_idx
        self.frame.remove_cel()
        self._notify_canvas_observers([self.layer])
        self.doc.ani.update_opacities()
        self._notify_document_observers()


class InsertFrames(Action):
    display_name = _("Insert Frame")
    def __init__(self, doc, length):
        self.doc = doc
        self.frames = doc.ani.frames
        self.idx = doc.ani.frames.idx
        self.length = length

    def redo(self):
        self.frames.insert_empty_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.frames.remove_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()


class RemoveFrameCel(Action):
    display_name = _("Remove frame / cel")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frames = doc.ani.frames
        self.frame = frame
        self.prev_idx = None
        self.removed_frame = True
        self.layer = None
        
    def redo(self):
        if self.frame.cel:
            layer = self.frame.cel
            self.doc.layers.remove(layer)
            self.prev_idx = self.doc.layer_idx
            self.doc.layer_idx = len(self.doc.layers) - 1
            self._notify_canvas_observers([layer])
            
        if len(self.frames) == 1:
            self.removed_frame = False
            self.layer = self.frame.cel
            self.frame.remove_cel()
        else:
            self.frames.remove_frames(1)
        
        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()
            
    def undo(self):
        if not self.removed_frame:
            self.frame.add_cel(self.layer)
        else:
            self.frames.insert_frames([self.frame])
        if self.frame.cel:
            self.doc.layers.append(self.frame.cel)
            self.doc.layer_idx = self.prev_idx
            self._notify_canvas_observers([self.frame.cel])
        self.doc.ani.update_opacities()
        self.doc.ani.cleared = True
        self._notify_document_observers()


class AppendFrames(Action):
    display_name = _("Append frame")
    def __init__(self, doc, length):
        self.doc = doc
        self.frames = doc.ani.frames
        self.length = length

    def redo(self):
        self.frames.append_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()

    def undo(self):
        self.frames.remove_frames(self.length)
        self.doc.ani.cleared = True
        self._notify_document_observers()


class PasteCel(Action):
    display_name = _("Paste cel")
    def __init__(self, doc, frame):
        self.doc = doc
        self.frame = frame

    def redo(self):
        self.prev_edit_operation = self.doc.ani.edit_operation
        self.prev_edit_frame = self.doc.ani.edit_frame
        self.prev_cel = self.frame.cel

        if self.doc.ani.edit_operation == 'copy':
            # TODO duplicate layer?
            self.frame.add_cel(self.doc.ani.edit_frame.cel)
        elif self.doc.ani.edit_operation == 'cut':
            self.frame.add_cel(self.doc.ani.edit_frame.cel)
            self.doc.ani.edit_frame.remove_cel()
        else:
            raise Exception 

        self.doc.ani.edit_operation = None
        self.doc.ani.edit_frame = None

        self.doc.ani.update_opacities()
        self._notify_document_observers()

    def undo(self):
        self.doc.ani.edit_operation = self.prev_edit_operation
        self.doc.ani.edit_frame = self.prev_edit_frame
        self.frame.add_cel(self.prev_cel)
        self.doc.ani.update_opacities()
        self._notify_document_observers()
