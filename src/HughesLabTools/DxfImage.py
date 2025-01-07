from ij import IJ, Prefs
import os
from os.path import join, splitext
from threading import Thread
from java.lang import Double
from ij.plugin.frame import RoiManager
from ij.plugin import CanvasResizer
from ij.plugin.filter import ParticleAnalyzer
from ij.gui import Roi
from DeviceImage import DeviceImage

class DxfImage(DeviceImage):
    def __init__(self, title=None, img=None):
        if title is not None and img is not None:
            super(DxfImage, self).__init__(title, img)
        elif title is not None:
            super(DxfImage, self).__init__(title)
        else:
            super(DxfImage, self).__init__()

    def processDxf(self, dxf_folder, smooth_images, smooth_value):
        """
        Create an AutoCAD DXF file that contains a trace of the image

        """
        if self.imp.getType() != IJ.GRAY8:
            IJ.run(self.imp, "8-bit", "")

        if smooth_images:
            self.smooth_image_function(smooth_value)

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
        output_dxf_path = join(dxf_folder, splitext(self.title)[0] + '.dxf')
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
               f"relative_proportion_fds={relative_proportion} absolute_number_fds={absolute_number} keep=[Relative_proportion of FDs]")

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
        fid.write(f"8\n{FID['layer']}\n62\n{FID['color']}\n")

    def dxf_print_point(self, FID, pointno, x, y, z):
        fid = FID['fid']
        y = y * -1  # Flip Y-coordinate
        fid.write(f"1{pointno}\n{format(x, '.8g')}\n2{pointno}\n{format(y, '.8g')}\n3{pointno}\n{format(z, '.8g')}\n")

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
        fid.write(f"0\nSEQEND\n8\n{FID['layer']}\n")
