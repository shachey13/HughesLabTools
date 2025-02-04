from ij import IJ, Prefs, ImagePlus, Menus
import os
from os.path import join, splitext
from java.lang import Double
from ij.plugin.frame import RoiManager
from ij.plugin import CanvasResizer
from ij.plugin.filter import ParticleAnalyzer
from ij.measure import ResultsTable
from ij.gui import Roi
from HughesLabTools.DeviceImage import DeviceImage

class VesselImage(DeviceImage):
    def __init__(self, title=None, img=None):
        if title is not None and img is not None:
            super(VesselImage, self).__init__(title, img)
        elif title is not None:
            super(VesselImage, self).__init__(title)
        else:
            super(VesselImage, self).__init__()

    def threshold_and_mask(self, device_manager):
        """
        Apply thresholding and convert the image to a mask. Save the result and optionally show it.

        Args:
            device_manager (DeviceManager): The DeviceManager instance containing options like 'show_threshold'.
        """
        # Duplicate the image
        imp2 = self.duplicate()

        # Set the title of the duplicated image
        imp2.setTitle(splitext(self.getTitle())[0] + '_threshold')

        # Apply threshold and convert to mask
        IJ.setAutoThreshold(imp2, 'Li dark b&w')
        Prefs.blackBackground = True
        IJ.run(imp2, 'Convert to Mask', '')

        # create output dir
        output_dir = self.output_path('thresholded')

        # save file
        output_path = join(output_dir, splitext(self.getTitle())[0] + '_thresholded.jpg')
        IJ.save(imp2, output_path)
        #self.save(output_path)

        # Verbose logging
        if device_manager.verbose:
            device_manager.log("Thresholded image saved at: {}".format(output_path))

        # Optionally show the thresholded image
        if device_manager.options.get('show_threshold', False):
            imp2.show()

        return imp2

    def output_path(self, newDir):
        """
        Check to see if the ImagePlus has a file path. Additionally creates a new directory for saving
        files to that path
        :return: file_path used for saving image
        """
        file_info = self.getFileInfo()
        if file_info is not None and file_info.directory:
            output_dir = join(file_info.directory, newDir)
        elif self.image_path is not None:
            output_dir = join(os.path.dirname(self.image_path), newDir)
        else:
            self.log("WARNING: Could not determine output directory; using current working directory.")
            output_dir = os.getcwd()

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        return output_dir # return output directory


    # Set functionality for generating DXF images
    def process_dxf(self,  device_manager):
        """
        Create an AutoCAD DXF file that contains a trace of the image
        :param smooth_images: logical to indicate if trace should be smoothed to decrease the number of vertices
        :param smooth_value: Relative proportion for Shape Smoothing Plugin
        Saves each image as a .dxf file
        """
        imp2 = self._prepare_image(device_manager)
        expanded_imp = self._expand_image(imp2)
        rm = self._analyze_particles(expanded_imp)
        self._write_dxf_file(rm, device_manager)
        self._cleanup(expanded_imp, rm)

    def _prepare_image(self, device_manager):
        imp2 = self.duplicate()
        imp2.setTitle(splitext(self.getTitle())[0] + '_dxf')
        if imp2.getType() != ImagePlus.GRAY8:
            IJ.run(imp2, "8-bit", "")
        if device_manager.options.get('smooth_bool'):
            imp2 = self.smooth_image_function(imp2, device_manager.options.get('smooth_value'))
        return imp2

    def _expand_image(self, device_manager):
        ip = self.getProcessor()
        width, height = ip.getWidth() + 10, ip.getHeight() + 10
        expanded_ip = CanvasResizer().expandImage(ip, width, height, 5, 5)
        expanded_imp = self.createImagePlus()
        expanded_imp.setProcessor(expanded_ip)
        IJ.run(expanded_imp, "Make Binary", "")
        IJ.run(expanded_imp, "Outline", "")
        return expanded_imp

    def _analyze_particles(self, imp):
        rm = RoiManager(False)
        options = ParticleAnalyzer.SHOW_NONE
        measurements = 0
        rt = ResultsTable()
        minSize, maxSize = 0, Double.POSITIVE_INFINITY
        pa = ParticleAnalyzer(options, measurements, rt, minSize, maxSize)
        pa.setRoiManager(rm)
        pa.analyze(imp)
        return rm

    def _write_dxf_file(self, rm, device_manager):
        if device_manager.options.get('smooth_bool'):
            output_dir = self.output_path('dxf_smoothed')
        else:
            output_dir = self.output_path('dxf')

        output_dxf_path = join(output_dir, splitext(self.getTitle())[0] + '.dxf')
        print(output_dxf_path)
        fid = self.dxf_open(output_dxf_path)
        for i in range(rm.getCount()):
            roi = rm.getRoi(i)
            x_points = roi.getPolygon().xpoints
            y_points = roi.getPolygon().ypoints
            z_points = [0] * len(x_points)
            self.dxf_polyline(fid, x_points, y_points, z_points)
        self.dxf_close(fid)

    def _cleanup(self, expanded_imp, rm):
        expanded_imp.changes = False
        expanded_imp.close()
        rm.reset()
        rm.close()

    def smooth_image_function(self, imp, relative_proportion, absolute_number=2):
        """
        Applies shape smoothing to the given image if the Shape Smoothing plugin is available and the image is binary.

        Args:
            imp (ImagePlus): The image to be smoothed.
            relative_proportion (float): The relative proportion parameter for the plugin.
            absolute_number (int, optional): The absolute number parameter for the plugin. Defaults to 2.

        Returns:
            ImagePlus: The smoothed image (modified imp).
        """
        # Check if the image is binary using imp.getProcessor().isBinary()
        if not imp.getProcessor().isBinary():
            IJ.log("WARNING: Image is not binary. Skipping shape smoothing.")
            return imp  # Return the original image without modification

        # Check if the "Shape Smoothing" plugin is available
        commands = Menus.getCommands()
        plugin_name = "Shape Smoothing"
        if plugin_name in commands:
            # Plugin is available; construct the options string and run the plugin
            options = "relative_proportion_fds={} absolute_number_fds={} keep=[Relative_proportion of FDs]".format(relative_proportion, absolute_number)
            IJ.run(imp, plugin_name, options)
            return imp  # Return the modified image
        else:
            # Plugin is not available; output a warning and skip running the code
            IJ.log("WARNING: Shape Smoothing plugin not found. Skipping smoothing step.")
            return imp  # Return the original image without modification


    def dxf_open(self, fname):
        try:
            fid = open(fname, 'w')
            FID = {
                'filename': fname,
                'fid': fid,
                'show': False,
                'dump': True,
                'layer': 0,
                'color': 255
            }
            fid.write('0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1006\n9\n$INSUNITS\n70\n6\n0\nENDSEC\n')
            fid.write('0\nSECTION\n2\nENTITIES\n')
            return FID
        except Exception as e:
            if fid:
                fid.close()
            raise e

    def dxf_close(self, FID):
        try:
            FID['fid'].write('0\nENDSEC\n0\nEOF\n')
            FID['fid'].close()
        except Exception as e:
            if FID['fid']:
                FID['fid'].close()
            raise e

    def dxf_polyline(self, FID, X, Y, Z):
        try:
            if FID['dump']:
                FID['fid'].write('0\nPOLYLINE\n')
                self.dxf_print_layer(FID)
                FID['fid'].write('66\n1\n')
                self.dxf_print_point(FID, 0, 0.0, 0.0, 0.0)
                FID['fid'].write('70\n8\n')
                self.dxf_print_vertex(FID, X, Y, Z)
                self.dxf_print_seqend(FID)
        except Exception as e:
            raise e

    def dxf_print_layer(self, FID):
        fid = FID['fid']
        fid.write("8\n{}\n62\n{}\n".format(FID['layer'], FID['color']))

    def dxf_print_point(self, FID, pointno, x, y, z):
        fid = FID['fid']
        y = y * -1  # Flip Y-coordinate
        fid.write("1%s\n%.8g\n2%s\n%.8g\n3%s\n%.8g\n" % (pointno, x, pointno, y, pointno, z))

    def dxf_print_vertex(self, FID, x_list, y_list, z_list):
        fid = FID['fid']
        for x, y, z in zip(x_list, y_list, z_list):
            fid.write("0\nVERTEX\n")
            self.dxf_print_layer(FID)
            self.dxf_print_point(FID, 0, x, y, z)
        # Close the polyline by connecting the last point to the first
        fid.write("0\nVERTEX\n")
        self.dxf_print_layer(FID)
        self.dxf_print_point(FID, 0, x_list[0], y_list[0], z_list[0])

    def dxf_print_seqend(self, FID):
        fid = FID['fid']
        fid.write("0\nSEQEND\n8\n{layer}\n".format(layer=FID['layer']))