#
# GView.py -- Simple, configurable FITS viewer based on ZVIEW
#
# Eric Jeschke (eric@naoj.org)
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

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

        from ginga.gw import Widgets, Viewers

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
        self.viewer_w = iw
        vbox.add_widget(iw, stretch=1)

        bm.map_event('zview', (), 'p', 'radial-plot')
        fi.set_callback('keydown-radial-plot',
                        self.gv.plot_cmd_cb, self.zv.do_radial_plot,
                        "Radial Profile", self.viewer_w)
        bm.map_event('zview', (), 'e', 'contour-plot')
        fi.set_callback('keydown-contour-plot',
                        self.gv.plot_cmd_cb, self.zv.do_contour_plot,
                        "Contours", self.viewer_w)
        bm.map_event('zview', (), 'g', 'gaussians-plot')
        fi.set_callback('keydown-gaussians-plot',
                        self.gv.plot_cmd_cb, self.zv.do_gaussians_plot,
                        "FWHM", self.viewer_w)

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
        self.zv.delete_viewer(self.name)


class GView(object):

    def __init__(self, logger, app, ev_quit):
        self.logger = logger
        self.app = app
        self.ev_quit = ev_quit

        self.histlimit = 5000
        self._plot_w = None

        self.zv = ZView.ZView(logger, self)

        from ginga.gw import Widgets, GwHelp

        self.top = self.app.make_window('GView')
        self.top.add_callback('close', lambda w: self.quit())

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)
        self.top.set_widget(vbox)
        self.top.resize(800, 600)

        mbar = Widgets.Menubar()
        vbox.add_widget(mbar, stretch=0)

        filemenu = mbar.add_name("File")
        filemenu.add_separator()

        item = filemenu.add_name("Quit")
        item.add_callback('activated', lambda *args: self.quit())

        nb = Widgets.TabWidget()
        vbox.add_widget(nb, stretch=1)

        sbar = Widgets.StatusBar()
        vbox.add_widget(sbar, stretch=0)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        vbox.add_widget(Widgets.Label("Type command here:"))
        self.cmd_w = Widgets.TextEntry()
        # TODO: this is not fetching a fixed font
        font = GwHelp.get_font("fixed", 12)
        self.cmd_w.set_font(font)
        vbox.add_widget(self.cmd_w, stretch=0)
        self.cmd_w.add_callback('activated', self.exec_cmd_cb)

        vbox.add_widget(Widgets.Label("Output:"))
        self.hist_w = Widgets.TextArea(wrap=True, editable=True)
        self.hist_w.set_font(font)
        self.hist_w.set_limit(self.histlimit)
        vbox.add_widget(self.hist_w, stretch=1)

        nb.add_widget(vbox, "Command")

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
        self.log("gview> " + text, w_time=True)

        if text.startswith('/'):
            # escape to shell for this command
            self.exec_shell(text[1:])
            return

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
                self.log(str(res))

            # this brings the focus back to the command bar if the command
            # causes a new window to be opened
            self.cmd_w.focus()

        except Exception as e:
            self.log("!! Error executing '%s': %s" % (text, str(e)))
            # TODO: add traceback


    def exec_cmd_cb(self, w):
        text = w.get_text()
        self.exec_cmd(text)
        w.set_text("")

    def plot_cmd_cb(self, viewer, event, data_x, data_y, fn, title, viewer_w):
        try:
            fn(viewer, event, data_x, data_y)

            self._plot_w.set_title(title)
        finally:
            # this keeps the focus on the viewer widget, in case a new
            # window was popped up
            viewer_w.focus()

    def exec_shell(self, cmd_str):
        res, out, err = get_exitcode_stdout_stderr(cmd_str)
        if len(out) > 0:
            self.log(out)
        if len(err) > 0:
            self.log(err)
        if res != 0:
            self.log("command terminated with error code %d" % res)

    def log(self, text, w_time=False):
        if self.hist_w is not None:
            pfx = ''
            if w_time:
                pfx = time.strftime("%H:%M:%S", time.localtime()) + ": "
            self.hist_w.append_text(pfx + text + '\n',
                                    autoscroll=True)

    def quit(self):
        self.ev_quit.set()
        self.top.delete()


def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    from subprocess import Popen, PIPE
    import shlex
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode

    return exitcode, out, err


# END
