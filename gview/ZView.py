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

Examples:
    rd 1 /home/eric/testdata/SPCAM/SUPA01118760.fits
    v 1
    cm rainbow3
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

    def log(self, text, w_time=False):
        self.gv.log(text, w_time=w_time)

    def cmd_cd(self, *args):
        """cd [path]

        Change the current working directory to `path`.
        """
        if len(args) == 0:
            path = os.environ['HOME']
        else:
            path = args[0]
        os.chdir(path)
        self.cwd = os.getcwd()
        self.cmd_pwd()

    def cmd_ls(self, *args):
        """ls [options]

        Execute list files command
        """
        cmd_str = ' '.join(['ls'] + list(args))
        self.gv.exec_shell(cmd_str)

    def cmd_pwd(self):
        """pwd

        List the current working directory.
        """
        self.log("%s" % (self.cwd))

    def cmd_rd(self, bufname, path, *args):
        """rd bufname path

        Read file from `path` into buffer `bufname`.  If the buffer does
        not exist it will be created.

        If `path` does not begin with a slash it is assumed to be relative
        to the current working directory.
        """
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

    def cmd_v(self, bufname, *args):
        """v bufname [min max] [colormap]

        Display buffer `bufname` in the current viewer.  If no viewer
        exists one will be created.

        Optional:
        `min` and `max` specify lo/hi cut levels to scale the image
        data for display.

        `colormap` specifies a color map to use for the image.
        """
        if not bufname in self.buffers:
            self.log("!! No such buffer: '%s'" % (bufname))
            return
        image = self.buffers[bufname]

        if self._view is None:
            self.make_viewer("gview_0")
        gw = self._view.gw

        gw.set_image(image)

        locut = None
        if len(args) > 0:
            try:
                locut = float(args[0])
                hicut = float(args[1])
                args = args[2:]
            except ValueError:
                pass

        if locut is not None:
            gw.cut_levels(locut, hicut)

        if len(args) > 0:
            cm_name = args[0]
            if cm_name == 'inv':
                gw.invert_cmap()
            else:
                gw.set_color_map(cm_name)


    def cmd_tv(self, bufname, *args):
        """tv <bufname> [min max] [bw | inv | jt]

        This command provided for ZVIEW compatibility.
        """
        args = list(args)

        if 'bw' in args:
            # replace "bw" with gray colormap
            i = args.index('bw')
            args[i] = 'gray'

        if 'jt' in args:
            # replace "jt" with rainbow3 colormap
            i = args.index('jt')
            args[i] = 'rainbow3'

        self.cmd_v(bufname, *args)

    def cmd_cm(self, *args):
        """cm [<cm_name> | inv]

        Set a color map (`cm_name`) for the current viewer. Special
        value 'inv' means to invert the current colormap.

        If no value is given, reports the current color map.
        """
        if self._view is None:
            self.log("No viewers")
            return
        gw = self._view.gw

        if len(args) == 0:
            rgbmap = gw.get_rgbmap()
            cmap = rgbmap.get_cmap()
            self.log(cmap.name)

        else:
            cm_name = args[0]

            if cm_name == 'inv':
                gw.invert_cmap()
            else:
                gw.set_color_map(cm_name)

    def cmd_dist(self, *args):
        """dist [<dist_name>]

        Set a color distribution (`dist_name`) for the current viewer.
        Possible values are linear, log, power, sqrt, squared, asinh, sinh,
        and histeq.

        If no value is given, reports the current color distribution
        algorithm.
        """
        if self._view is None:
            self.log("No viewers")
            return
        gw = self._view.gw

        if len(args) == 0:
            rgbmap = gw.get_rgbmap()
            dist = rgbmap.get_dist()
            self.log(str(dist))
        else:
            dist_name = args[0]
            gw.set_color_algorithm(dist_name)

    def cmd_help(self, *args):
        """help [cmd]
        Get general help, or help for command `cmd`.
        """
        if len(args) > 0:
            cmdname = args[0].lower()
            try:
                method = getattr(self, "cmd_" + cmdname)
                doc = method.__doc__
                if doc is None:
                    self.log("Sorry, no documentation found for '%s'" % (
                        cmdname))
                else:
                    self.log("%s: %s" % (cmdname, doc))
            except AttributeError:
                self.log("No such command '%s'; type help for general help." % (
                    cmdname))
        else:
            res = []
            for attrname in dir(self):
                if attrname.startswith('cmd_'):
                    method = getattr(self, attrname)
                    doc = method.__doc__
                    cmdname = attrname[4:]
                    if doc is None:
                        doc = "no documentation"
                    res.append("%s: %s" % (cmdname, doc))
            self.log('\n'.join(res))

    def cmd_mkv(self, name, *args):
        """mkv name [width height]

        Make a viewer with name NAME.

        Optional:
        `width` and `height` specify the pixel dimensions of the view pane.
        """
        width = self.default_viewer_width
        height = self.default_viewer_height
        if len(args) > 0:
            width = int(args[0])
            height = int(args[1])

        self._view = self.make_viewer(name, width=width, height=height)
        self.cmd_view()

    def cmd_lsv(self):
        """lsv

        List the viewers, showing the current one.
        """
        names = list(self.viewers.keys())
        names.sort()

        if len(names) == 0:
            self.log("No viewers")
            return

        res = []
        for name in names:
            if self._view == self.viewers[name]:
                res.append(">%s" % (name))
            else:
                res.append(" %s" % (name))

        self.log("\n".join(res))

    def cmd_lscm(self):
        """lscm

        List the possible color maps that can be loaded.
        """
        from ginga import cmap
        self.log("\n".join(cmap.get_names()))

    def cmd_head(self, bufname, *args):
        """head buf [kwd ...]

        List the headers for the image in the named buffer.
        """
        if bufname not in self.buffers:
            self.log("No such buffer: '%s'" % (bufname))
            return

        image = self.buffers[bufname]
        header = image.get_header()
        res = []
        # TODO: include the comments
        if len(args) > 0:
            for kwd in args:
                if not kwd in header:
                    res.append("%-8.8s  -- NOT FOUND IN HEADER --" % (kwd))
                else:
                    res.append("%-8.8s  %s" % (kwd, str(header[kwd])))
        else:
            for kwd in header.keys():
                res.append("%-8.8s  %s" % (kwd, str(header[kwd])))

        self.log('\n'.join(res))

    def cmd_swv(self, name):
        """swv name

        Switch the current viewer to NAME.
        """
        if not name in self.viewers:
            self.log("No such viewer: '%s'" % (name))

        else:
            self._view = self.viewers[name]
            self.cmd_view()

    def cmd_lsb(self):
        """lsb

        List the buffers
        """
        names = list(self.buffers.keys())
        names.sort()

        if len(names) == 0:
            self.log("No buffers")
            return

        res = []
        for name in names:
            d = self.get_buffer_info(name)
            d.size = "%dx%d" % (d.width, d.height)
            res.append("%(name)-10.10s  %(size)13s  %(path)s" % d)
        self.log("\n".join(res))

    def cmd_rmb(self, *args):
        """rmb NAME ...

        Remove buffer NAME
        """
        for name in args:
            if name in self.buffers:
                del self.buffers[name]
            else:
                self.log("No such buffer: '%s'" % (name))
        self.cmd_lsb()

    def cmd_rm(self, *args):
        """command to be deprecated--use 'rmb'
        """
        self.log("warning: this command will be deprecated--use 'rmb'")
        self.cmd_rmb(*args)

    def get_buffer_info(self, name):
        image = self.buffers[name]
        path = image.get('path', "None")
        res = Bunch.Bunch(dict(name=name, path=path, width=image.width,
                               height=image.height))
        return res

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
        self.log("ZVIEW> (contour plot)", w_time=True)
        try:
            results = self.find_objects(viewer, data_x, data_y)
            qs = results[0]
            x, y = qs.objx, qs.objy

        except Exception as e:
            self.log("No objects found")
            # we can still proceed with a contour plot at the point
            # where the key was pressed
            x, y = data_x, data_y

        self.make_contour_plot()

        image = viewer.get_image()
        self._plot.plot_contours(x, y, self.contour_radius, image,
                                 num_contours=12)
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
        self.log("ZVIEW> (gaussians plot)", w_time=True)
        try:
            results = self.find_objects(viewer, data_x, data_y)
            qs = results[0]

        except Exception as e:
            self.log("No objects found")
            return

        self.make_gaussians_plot()

        image = viewer.get_image()
        x, y = qs.objx, qs.objy

        self._plot.plot_fwhm(x, y, self.radius, image)
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
        self.log("ZVIEW> (radial plot)", w_time=True)
        try:
            results = self.find_objects(viewer, data_x, data_y)
            qs = results[0]

        except Exception as e:
            self.log("No objects found")
            return

        self.make_radial_plot()

        image = viewer.get_image()
        x, y = qs.objx, qs.objy

        self._plot.plot_radial(x, y, self.radius, image)

        rpt = self.make_report(image, qs)
        self.log("seeing size %5.2f" % (rpt.starsize))
        # TODO: dump other stats from the report
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

# This is the list of commands generated by the old ZVIEW 'help' menu:
# cd		Change to directory DIR.
# help		Display this text.
# ?		Synonym for `help'.
# ls		List files in DIR.
# pwd		Print the current working directory.
# exit		Synonym for `quit'.
# quit		Quit using zview.
# rd		Read FITS file   rd buf filename [type].
# rdm		Connect to shared memory   rdm buf shmkeyfilename.
# tv		Display buffer   tv buf [min max] [inv, bw or jt].
# buf		Buffer contents    buf.
# rm		Remove Buffer        rm buf.
# key		Wait for Key-input    key.
# ref		Refresh Image Display    ref.
# slop		Slop             slop targetreg bgre.
# stat		Statistics of defined region.
# head		Show FITS header.
# set		Set parameters/flags.
# unset		Unset flags.
# psprint		Create Postscript File.
# region		Define/List region.
# plum		my useful command.
# kerop		CTE analysis.
# ql		Quick Look routine for Suprime-Cam ver1.0    ql buf filename.
# hscql		Quick Look routine for Hyper Suprime-Cam  hscql buf filename.
# create		create blank buffer  create buf protobuf xsize ysize.
# map		Map buffer to another   map buf bufD [shiftx shifty].
# wf		Write FITS file   wf buf filename.
# debias		debias buf bufD targetregid overscanregid.
# copy		Copy buffer     copy  buf bufD regid.
# rdebias		rdebias buf bufD targetregid overscanregid.

#END
