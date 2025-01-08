from ij import IJ, Prefs
import os
from os.path import join, splitext
from java.lang import Double
from ij.plugin.frame import RoiManager
from ij.plugin import CanvasResizer
from ij.plugin.filter import ParticleAnalyzer
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

        # Save the thresholded image
        output_dir = join(self.getOriginalFileInfo().directory, 'thresholded')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_path = join(output_dir, splitext(self.getTitle())[0] + '_thresholded.jpg')
        self.save(output_path)

        # Verbose logging
        if device_manager.verbose:
            device_manager.log("Thresholded image saved at: {}".format(output_path))

        # Optionally show the thresholded image
        if device_manager.options.get('show_threshold', False):
            imp2.show()

        return imp2

    def process_dxf(self,  device_manager):
        """
        Create an AutoCAD DXF file that contains a trace of the image
        :param smooth_images: logical to indicate if trace should be smoothed to decrease the number of vertices
        :param smooth_value: Relative proportion for Shape Smoothing Plugin
        Saves each image as a .dxf file
        """
        # convert ip to imp

        if self.imp.getType() != IJ.GRAY8:
            IJ.run(self.imp, "8-bit", "")

        if device_manager.options.get('smooth_bool'):
            self.smooth_image_function(device_manager.options.get('smooth_value'))

        ip = self.imp.getProcessor()
        width = ip.getWidth() + 10
        height = ip.getHeight() + 10
        expanded_ip = CanvasResizer().expandImage(ip, width, height, 5, 5)
        expanded_imp = self.imp.createImagePlus()
        expanded_imp.setProcessor(expanded_ip)
        IJ.run(expanded_imp, "Make Binary", "")
        IJ.run(expanded_imp, "Outline", "")

        options = ParticleAnalyzer.SHOW_OUTLINES | ParticleAnalyzer.ADD_TO_MANAGER
        pa = ParticleAnalyzer(options, 0, None, 0, Double.POSITIVE_INFINITY)
        pa.analyze(expanded_imp)

        rm = RoiManager.getInstance()
        if rm is None:
            rm = RoiManager()

        num_rois = rm.getCount()
        output_dxf_path = join(self.getOriginalFileInfo().directory, splitext(self.getTitle())[0] + '.dxf')
        print(output_dxf_path)
        fid = self.dxf_open(output_dxf_path)

        for i in range(num_rois):
            roi = rm.getRoi(i)
            x_points = roi.getPolygon().xpoints
            y_points = roi.getPolygon().ypoints
            z_points = [0] * len(x_points)
            self.dxf_polyline(fid, x_points, y_points, z_points)

        self.dxf_close(fid)
        expanded_imp.changes = False
        expanded_imp.close()
        rm.reset()

    def smooth_image_function(self, relative_proportion, absolute_number=2):
        IJ.run(self.imp, "Shape Smoothing",
               "relative_proportion_fds=%s absolute_number_fds=%s keep=[Relative_proportion of FDs]" % (relative_proportion, absolute_number))

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