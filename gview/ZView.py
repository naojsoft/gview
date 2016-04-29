#! /usr/bin/env python
#
# ZView.py -- compatibility library for ZView using Ginga
#
# Eric Jeschke (eric@naoj.org)
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This is the list of commands generated by the 'help' menu:
cd		Change to directory DIR.
help		Display this text.
?		Synonym for `help'.
ls		List files in DIR.
pwd		Print the current working directory.
exit		Synonym for `quit'.
quit		Quit using zview.
rd		Read FITS file   rd buf filename [type].
rdm		Connect to shared memory   rdm buf shmkeyfilename.
tv		Display buffer   tv buf [min max] [inv, bw or jt].
buf		Buffer contents    buf.
rm		Remove Buffer        rm buf.
key		Wait for Key-input    key.
ref		Refresh Image Display    ref.
slop		Slop             slop targetreg bgre.
stat		Statistics of defined region.
head		Show FITS header.
set		Set parameters/flags.
unset		Unset flags.
psprint		Create Postscript File.
region		Define/List region.
plum		my useful command.
kerop		CTE analysis.
ql		Quick Look routine for Suprime-Cam ver1.0    ql buf filename.
hscql		Quick Look routine for Hyper Suprime-Cam  hscql buf filename.
create		create blank buffer  create buf protobuf xsize ysize.
map		Map buffer to another   map buf bufD [shiftx shifty].
wf		Write FITS file   wf buf filename.
debias		debias buf bufD targetregid overscanregid.
copy		Copy buffer     copy  buf bufD regid.
rdebias		rdebias buf bufD targetregid overscanregid.

Examples:
    rd 1 /home/eric/testdata/SPCAM/SUPA01118760.fits
    tv 1 0 2000 rainbow3
    view
    mkview 1
    mkview 2
    swview 1
    view
"""
import time
import os

from ginga.misc import Bunch
from ginga import AstroImage, colors
from ginga.util import plots, iqcalc, wcs


class ZView(object):

    def __init__(self, logger, gv):
        self.logger = logger
        self.gv = gv

        self.viewers = Bunch.Bunch()
        # the current viewer
        self._view = None

        self.default_viewer_width = 900
        self.default_viewer_height = 1000

        self.buffers = Bunch.Bunch()

        self.iqcalc = iqcalc.IQCalc(self.logger)
        self._plot = None

        # Peak finding parameters and selection criteria
        self.radius = 10
        self.settings = {}
        self.max_side = self.settings.get('max_side', 1024)
        self.radius = self.settings.get('radius', 10)
        self.threshold = self.settings.get('threshold', None)
        self.min_fwhm = self.settings.get('min_fwhm', 2.0)
        self.max_fwhm = self.settings.get('max_fwhm', 50.0)
        self.min_ellipse = self.settings.get('min_ellipse', 0.5)
        self.edgew = self.settings.get('edge_width', 0.01)
        self.show_candidates = self.settings.get('show_candidates', False)
        # Report in 0- or 1-based coordinates
        self.pixel_coords_offset = self.settings.get('pixel_coords_offset',
                                                     0.0)

        self.contour_radius = 10

        self.cwd = os.getcwd()

    def log(self, text):
        self.gv.log(text)

    def cmd_head(self, bufname):
        self.log("Command not implemented")

    def cmd_cd(self, path):
        os.chdir(path)
        self.cwd = os.getcwd()
        self.cmd_pwd()

    def cmd_pwd(self):
        self.log("Current directory is %s" % (self.cwd))

    def cmd_ls(self, *args):
        self.log("Current directory is %s" % (self.cwd))

    def cmd_rd(self, bufname, path, *args):
        if not path.startswith('/'):
            path = os.path.join(self.cwd, path)
        if bufname in self.buffers:
            self.log("Buffer %s is in use. Will discard the previous data" % (
                bufname))
            image = self.buffers[bufname]
        else:
            # new buffer
            image = AstroImage.AstroImage(logger=self.logger)
            self.buffers[bufname] = image

        self.log("Reading file...(%s)" % (path))
        image.load_file(path)
        # TODO: how to know if there is an error
        self.log("File read")

    def cmd_tv(self, bufname, *args):
        if not bufname in self.buffers:
            self.log("!! No such buffer: '%s'" % (bufname))
            return
        image = self.buffers[bufname]

        if self._view is None:
            self.make_viewer("gview_0")
        gw = self._view.gw

        gw.set_image(image)

        if len(args) > 0:
            locut = float(args[0])
            hicut = float(args[1])
            gw.cut_levels(locut, hicut)

        args = args[2:]
        if len(args) > 0:
            cm_name = args[0]
            gw.set_color_map(cm_name)

    def cmd_help(self, *args):
        self.log(help_text)

    def cmd_mkview(self, name, *args):
        width = self.default_viewer_width
        height = self.default_viewer_height
        if len(args) > 0:
            width = int(args[0])
            height = int(args[1])

        self._view = self.make_viewer(name, width=width, height=height)
        self.cmd_view()

    def cmd_view(self):
        if self._view is None:
            self.log("No viewers")
        else:
            self.log("Current viewer is %s" % (self._view.name))

    def make_viewer(self, name, width=None, height=None):
        if width is None:
            width = self.default_viewer_width
        if height is None:
            height = self.default_viewer_height

        viewer = self.gv.make_viewer(name, width=width, height=height)
        viewer.gw.name = name
        self.viewers[name] = viewer
        if self._view is None:
            self._view = viewer
        return viewer

    def delete_viewer(self, name):
        viewer = self.viewers[name]
        del self.viewers[name]
        self.gv.delete_viewer(viewer)

    def initialize_plot(self):
        self._plot = plots.Plot(logger=self.logger,
                                width=600, height=600)
        self.gv.initialize_plot_gui(self._plot, width=600, height=600)

    def make_contour_plot(self):
        if self._plot is None:
            self.initialize_plot()

        fig = self._plot.get_figure()
        fig.clf()

        # Replace plot with Contour plot
        self._plot = plots.ContourPlot(logger=self.logger,
                                       figure=fig,
                                       width=600, height=600)
        self._plot.add_axis(axisbg='black')

    def do_contour_plot(self, viewer, event, data_x, data_y):
        results = self.find_objects(viewer, data_x, data_y)
        qs = results[0]

        self.make_contour_plot()

        image = viewer.get_image()
        x, y = qs.objx, qs.objy
        self._plot.plot_contours(x, y, self.contour_radius, image,
                                 num_contours=12)
        #self._plot_w.set_title("Contours")
        return True


    def make_gaussians_plot(self):
        if self._plot is None:
            self.initialize_plot()

        fig = self._plot.get_figure()
        fig.clf()

        # Replace plot with FWHM gaussians plot
        self._plot = plots.FWHMPlot(logger=self.logger,
                                    figure=fig,
                                    width=600, height=600)
        self._plot.add_axis(axisbg='white')

    def do_gaussians_plot(self, viewer, event, data_x, data_y):
        results = self.find_objects(viewer, data_x, data_y)
        qs = results[0]

        self.make_gaussians_plot()

        image = viewer.get_image()
        x, y = qs.objx, qs.objy

        self._plot.plot_fwhm(x, y, self.radius, image)
        #self._plot_w.set_title("FWHM")
        return True

    def make_radial_plot(self):
        if self._plot is None:
            self.initialize_plot()

        fig = self._plot.get_figure()
        fig.clf()

        # Replace plot with Radial profile plot
        self._plot = plots.RadialPlot(logger=self.logger,
                                       figure=fig,
                                       width=700, height=600)
        self._plot.add_axis(axisbg='white')

    def do_radial_plot(self, viewer, event, data_x, data_y):
        results = self.find_objects(viewer, data_x, data_y)
        qs = results[0]

        self.make_radial_plot()

        image = viewer.get_image()
        x, y = qs.objx, qs.objy

        self._plot.plot_radial(x, y, self.radius, image)
        #self._plot_w.set_title("Radial Profile")

        rpt = self.make_report(image, qs)
        self.log("seeing size %5.2f" % (rpt.starsize))
        return True

    def find_objects(self, viewer, x, y):
        #x, y = viewer.get_last_data_xy()
        image = viewer.get_image()

        msg, results, qs = None, [], None
        try:
            data, x1, y1, x2, y2 = image.cutout_radius(x, y, self.radius)

            # Find bright peaks in the cutout
            self.logger.debug("Finding bright peaks in cutout")
            peaks = self.iqcalc.find_bright_peaks(data,
                                                  threshold=self.threshold,
                                                  radius=self.radius)
            num_peaks = len(peaks)
            if num_peaks == 0:
                raise Exception("Cannot find bright peaks")

            # Evaluate those peaks
            self.logger.debug("Evaluating %d bright peaks..." % (num_peaks))
            objlist = self.iqcalc.evaluate_peaks(peaks, data,
                                                 fwhm_radius=self.radius)

            num_candidates = len(objlist)
            if num_candidates == 0:
                raise Exception("Error evaluating bright peaks: no candidates found")

            self.logger.debug("Selecting from %d candidates..." % (num_candidates))
            height, width = data.shape
            results = self.iqcalc.objlist_select(objlist, width, height,
                                                 minfwhm=self.min_fwhm,
                                                 maxfwhm=self.max_fwhm,
                                                 minelipse=self.min_ellipse,
                                                 edgew=self.edgew)
            if len(results) == 0:
                raise Exception("No object matches selection criteria")

            # add back in offsets from cutout to result positions
            for qs in results:
                qs.x += x1
                qs.y += y1
                qs.objx += x1
                qs.objy += y1

        except Exception as e:
            msg = str(e)
            self.logger.error("Error finding object: %s" % (msg))
            raise e

        return results

    def make_report(self, image, qs):
        d = Bunch.Bunch()
        try:
            x, y = qs.objx, qs.objy
            equinox = float(image.get_keyword('EQUINOX', 2000.0))

            try:
                ra_deg, dec_deg = image.pixtoradec(x, y, coords='data')
                ra_txt, dec_txt = wcs.deg2fmt(ra_deg, dec_deg, 'str')

            except Exception as e:
                self.logger.warning("Couldn't calculate sky coordinates: %s" % (str(e)))
                ra_deg, dec_deg = 0.0, 0.0
                ra_txt = dec_txt = 'BAD WCS'

            # Calculate star size from pixel pitch
            try:
                header = image.get_header()
                ((xrot, yrot),
                 (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(header)

                starsize = self.iqcalc.starsize(qs.fwhm_x, cdelt1,
                                                qs.fwhm_y, cdelt2)
            except Exception as e:
                self.logger.warning("Couldn't calculate star size: %s" % (str(e)))
                starsize = 0.0

            rpt_x = x + self.pixel_coords_offset
            rpt_y = y + self.pixel_coords_offset

            # make a report in the form of a dictionary
            d.setvals(x = rpt_x, y = rpt_y,
                      ra_deg = ra_deg, dec_deg = dec_deg,
                      ra_txt = ra_txt, dec_txt = dec_txt,
                      equinox = equinox,
                      fwhm = qs.fwhm,
                      fwhm_x = qs.fwhm_x, fwhm_y = qs.fwhm_y,
                      ellipse = qs.elipse, background = qs.background,
                      skylevel = qs.skylevel, brightness = qs.brightness,
                      starsize = starsize,
                      time_local = time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.localtime()),
                      time_ut = time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.gmtime()),
                      )
        except Exception as e:
            self.logger.error("Error making report: %s" % (str(e)))

        return d

#END