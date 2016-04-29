#
# GView.py -- Simple, configurable FITS viewer based on ZVIEW
#
# Eric Jeschke (eric@naoj.org)
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys

from ginga import AstroImage
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.util.toolbox import ModeIndicator
from ginga.util import plots

import ZView


class FitsViewer(object):

    def __init__(self, name, logger, gv, zv):
        self.logger = logger
        self.gv = gv
        self.zv = zv
        self.name = name
        self.app = gv.app
        ## self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()

        from ginga.gw import Widgets, Viewers, GwHelp

        self.top = self.app.make_window(name)
        self.top.add_callback('close', self.closed)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        fi = Viewers.CanvasView(logger=logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.4)
        fi.show_pan_mark(True)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.gw = fi

        bd = fi.get_bindings()
        bd.enable_all(True)
        bd.get_settings().set(scroll_zoom_direct_scale=True)

        # add a color bar
        fi.private_canvas.add(self.dc.ColorBar(side='bottom', offset=10))

        # add little mode indicator that shows modal states in
        # lower left hand corner
        fi.private_canvas.add(self.dc.ModeIndicator(corner='ur', fontsize=10))
        # little hack necessary to get correct operation of the mode indicator
        # in all circumstances
        bm = fi.get_bindmap()
        bm.add_callback('mode-set', lambda *args: fi.redraw(whence=3))

        # add a new "zview" mode
        bm.add_mode('z', 'zview', mode_type='locked', msg=None)

        # zview had this kind of zooming function
        bm.map_event('zview', (), 'right', 'zoom_in')
        bm.map_event('zview', (), 'left', 'zoom_out')

        bm.map_event('zview', (), 'p', 'radial-plot')
        fi.set_callback('keydown-radial-plot', self.zv.do_radial_plot)
        bm.map_event('zview', (), 'e', 'contour-plot')
        fi.set_callback('keydown-contour-plot', self.zv.do_contour_plot)
        bm.map_event('zview', (), 'g', 'gaussians-plot')
        fi.set_callback('keydown-gaussians-plot', self.zv.do_gaussians_plot)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        ## canvas.enable_draw(True)
        ## canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.setSurface(fi)
        self.canvas = canvas
        # add canvas to view
        fi.get_canvas().add(canvas)
        canvas.ui_setActive(True)

        fi.set_desired_size(512, 512)
        iw = Viewers.GingaViewerWidget(viewer=fi)
        vbox.add_widget(iw, stretch=1)

        self.readout = Widgets.Label("")
        self.readout.set_color(bg='black', fg='lightgreen')
        vbox.add_widget(self.readout, stretch=0)

        self.top.set_widget(vbox)

    def load_file(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.gw.set_image(image)
        self.top.set_title(filepath)

    def drop_file(self, gw, paths):
        fileName = paths[0]
        self.load_file(fileName)

    def motion(self, viewer, button, data_x, data_y):

        # Get the value under the data coordinates
        try:
            #value = viewer.get_data(data_x, data_y)
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x+0.5), int(data_y+0.5))

        except Exception:
            value = None

        fits_x, fits_y = data_x + 1, data_y + 1

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = viewer.get_image()
            if image is None:
                # No image loaded
                return
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception as e:
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def set_mode_cb(self, mode, tf):
        canvas = self.gw.get_canvas()
        self.logger.info("canvas mode changed (%s) %s" % (mode, tf))
        if not (tf is False):
            canvas.set_draw_mode(mode)
        return True

    ## def use_trackpad_cb(self, state):
    ##     settings = self.gw.get_bindings().get_settings()
    ##     val = 1.0
    ##     if state:
    ##         val = 0.1
    ##     settings.set(scroll_zoom_acceleration=val)

    def closed(self, w):
        self.logger.info("viewer '%s' closed." % (self.name))
        self.zv.close_viewer(self.name)


class GView(object):

    def __init__(self, logger, app):
        self.logger = logger
        self.app = app

        self.histlimit = 5000
        self._plot_w = None

        self.zv = ZView.ZView(logger, self)

        from ginga.gw import Widgets

        self.top = self.app.make_window('GView')
        #self.top.add_callback('close', self.quit)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        self.cmd_w = Widgets.TextEntry()
        vbox.add_widget(self.cmd_w, stretch=0)
        self.cmd_w.add_callback('activated', self.exec_cmd_cb)

        self.hist_w = Widgets.TextArea(wrap=True, editable=True)
        self.hist_w.set_limit(self.histlimit)
        vbox.add_widget(self.hist_w, stretch=1)

        self.top.set_widget(vbox)
        self.top.resize(800, 600)
        self.top.show()

    def make_viewer(self, name, width=900, height=1000):
        viewer = FitsViewer(name, self.logger, self, self.zv)

        viewer.top.resize(width, height)

        viewer.top.show()
        viewer.top.raise_()
        return viewer

    def initialize_plot_gui(self, plot, width=800, height=600):
        from ginga.gw import Plot
        pw = Plot.PlotWidget(plot)
        pw.resize(width, height)

        self._plot_w = self.app.make_window("Plots")
        self._plot_w.set_widget(pw)
        self._plot_w.show()

    def delete_viewer(self, viewer):
        viewer.top.delete()

    def exec_cmd(self, text):
        text = text.strip()
        self.log("ZVIEW> " + text)

        args = text.split()
        cmd, args = args[0], args[1:]

        try:
            method = getattr(self.zv, "cmd_" + cmd.lower())

        except AttributeError:
            self.log("!! No such command: '%s'" % (cmd))
            return

        try:
            res = method(*args)
            if res is not None:
                self.log("%s" % str(res))

        except Exception as e:
            self.log("!! Error executing '%s': %s" % (text, str(e)))
            # TODO: add traceback

    def exec_cmd_cb(self, w):
        text = w.get_text()
        self.exec_cmd(text)
        w.set_text("")

    def log(self, text):
        if self.hist_w is not None:
            self.hist_w.append_text(text + '\n',
                                    autoscroll=True)

# END
