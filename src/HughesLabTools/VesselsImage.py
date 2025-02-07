from ij import IJ, Prefs, ImagePlus, Menus
import os
from os.path import join, splitext
from java.lang import Double
from ij.plugin.frame import RoiManager
from ij.plugin import CanvasResizer
from ij.plugin.filter import ParticleAnalyzer, Analyzer, ThresholdToSelection
from ij.measure import ResultsTable, Measurements
from ij.gui import Roi
from ij.process import ImageProcessor, FloatProcessor, ImageConverter
from ij.io import FileSaver
import math
import csv
from HughesLabTools.DeviceImage import DeviceImage

# Ensure that the AnalyzeSkeleton_ plugin is available
from sc.fiji.analyzeSkeleton import AnalyzeSkeleton_

class Point:
    def __init__(self, x, y, z=0):
        self.x = x
        self.y = y
        self.z = z

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


    ## Set functionality for generating DXF images
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
        """Prepare the image for DXF processing."""
        imp2 = self.duplicate()
        imp2.setTitle(splitext(self.getTitle())[0] + '_dxf')
        if imp2.getType() != ImagePlus.GRAY8:
            IJ.run(imp2, "8-bit", "")
        if device_manager.options.get('smooth_bool'):
            imp2 = self.smooth_image_function(imp2, device_manager.options.get('smooth_value'))
        return imp2

    def _expand_image(self, device_manager):
        """Expand the image and apply binary and outline processing."""
        ip = self.getProcessor()
        width, height = ip.getWidth() + 10, ip.getHeight() + 10
        expanded_ip = CanvasResizer().expandImage(ip, width, height, 5, 5)
        expanded_imp = self.createImagePlus()
        expanded_imp.setProcessor(expanded_ip)
        IJ.run(expanded_imp, "Make Binary", "")
        IJ.run(expanded_imp, "Outline", "")
        return expanded_imp

    def _analyze_particles(self, imp):
        """Analyze particles in the image and return ROI manager."""
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
        """Write DXF file based on ROI Manager data."""
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
        """Clean up resources after DXF processing."""
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
        """Open a DXF file for writing."""
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
        """Close the DXF file."""
        try:
            FID['fid'].write('0\nENDSEC\n0\nEOF\n')
            FID['fid'].close()
        except Exception as e:
            if FID['fid']:
                FID['fid'].close()
            raise e

    def dxf_polyline(self, FID, X, Y, Z):
        """Write a polyline to the DXF file."""
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


    ## Vessel Quantification Methods
    def perform_vessel_analysis(self, options, summary_csv_path):
        """
        Perform vessel analysis on the image and save results.
        """
        # set output folders, get parametes, and set file names
        output_folder = self.output_path('Vessel_Analysis')
        cleaned_folder, output_skeleton_dir, output_summary_dir = self._make_vessel_folders(output_folder)
        parameters = self._get_analysis_parameters(options)
        filename, base_filename = self._prepare_filenames()

        # duplicate and process the image
        expanded_imp, og_imp = self._expand_and_fill(parameters)
        test_imp = expanded_imp.duplicate()
        expanded_imp = self._clean_image(expanded_imp, parameters['image_cleaning_threshold'])

        # skeletonize and find branches
        IJ.run(expanded_imp, "Skeletonize", "")
        rt_all, rt_unique, branchNumber = self._process_junction_points(expanded_imp, distance_threshold=parameters['distance_threshold'])
        expanded_imp = self._break_branches_and_prune(expanded_imp, rt_all, parameters['mean_threshold'])
        cleaned_save_path = join(cleaned_folder, splitext(self.getTitle())[0] + '_cleaned2.tif')
        FileSaver(expanded_imp).saveAsTiff(cleaned_save_path)
        rt_all, rt_unique, branchNumber = self._process_junction_points(expanded_imp, distance_threshold=parameters['distance_threshold'])

        # measure diameters
        IJ.run(test_imp, "Distance Map", "")
        output_imp, skeleton_values = self._skeleton_map(expanded_imp, test_imp)
        _ , average_values = self._break_branches_and_analyze(output_imp, rt_all)

        # compute area
        #og_imp = self.duplicate()
        og_imp = self._custom_binarize(og_imp, 200)
        resultsArea = self._area_and_perimeter(og_imp)

        # save results
        summary_table = self._create_summary_table(filename, branchNumber, average_values, skeleton_values, resultsArea)
        skeleton_save_path = join(output_skeleton_dir,splitext(self.getTitle())[0] + '_skeleton.tif')
        FileSaver(expanded_imp).saveAsTiff(skeleton_save_path)
        skeleton_values_save_path = join(output_summary_dir, splitext(self.getTitle())[0] + '_skeleton_values.csv')
        self._save_array_to_csv(skeleton_values, skeleton_values_save_path)
        summary_table_path = join(output_summary_dir, "quantification_summary.csv")
        self._append_to_summary_csv(summary_table, summary_csv_path)

        # Close ROI Manager
        roi_manager = RoiManager(False)
        if roi_manager:
            roi_manager.reset()
            roi_manager.close()

        print("Done with vessel quantification")

    def _make_vessel_folders(self, base_folder):
        cleaned_folder = os.path.join(base_folder, 'Cleaned_Images')
        skeleton_folder = os.path.join(base_folder, 'Skeleton')
        summary_folder = os.path.join(base_folder, 'Summary')

        for folder in [cleaned_folder, skeleton_folder, summary_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        return cleaned_folder, skeleton_folder, summary_folder

    def _get_analysis_parameters(self, options):
        return {
            'hole_threshold': options.get('hole_threshold', 50),
            'area_threshold_vessels': options.get('area_threshold_vessels', 100),
            'image_cleaning_threshold': options.get('image_cleaning_threshold', 1),
            'distance_threshold': options.get('distance_threshold', 5),
            'mean_threshold': options.get('mean_threshold', 10)
        }

    def _prepare_filenames(self):
        image_path = self.image_path if self.image_path else "unknown_image"
        filename = os.path.basename(image_path)
        base_filename = os.path.splitext(filename)[0]
        return filename, base_filename

    def _expand_and_fill(self, parameters):
        expanded_imp = self.duplicate()
        if expanded_imp.getType() == ImagePlus.COLOR_RGB:
            IJ.log("Warning: RGB image detected. Converting to grayscale: {}".format(self.getTitle()))
            IJ.run(expanded_imp, "8-bit", "")
        og_imp = expanded_imp
        expanded_imp, _ = self._fill_holes_and_remove_small_regions(expanded_imp,
            parameters['hole_threshold'],
            parameters['area_threshold_vessels']
        )
        expanded_imp = self._custom_binarize(expanded_imp, 200)
        expanded_imp = self._invert_and_fill_holes(expanded_imp)
        expanded_imp = self._custom_binarize(expanded_imp, 200)
        return expanded_imp, og_imp


    def _custom_binarize(self, imp, threshold):
        """
        Apply custom binarization to the image using the provided threshold.
        """
        ip = imp.getProcessor()
        width = ip.getWidth()
        height = ip.getHeight()

        for y in range(height):
            for x in range(width):
                pixel_value = ip.getPixel(x, y)
                if pixel_value < threshold:
                    ip.putPixel(x, y, 0)
                else:
                    ip.putPixel(x, y, 255)

        imp.updateAndDraw()
        return imp

    def _clean_image(self, imp, threshold):
        """
        Clean the image using distance map and threshold.
        """
        IJ.run(imp, "Distance Map", "")
        IJ.setAutoThreshold(imp, "Default dark")
        ip = imp.getProcessor()
        ip.setThreshold(threshold, 255, ImageProcessor.NO_LUT_UPDATE)
        imp.setProcessor(ip)
        IJ.run(imp, "Options...", "black")
        IJ.run(imp, "Convert to Mask", "")
        return imp

    def _fill_holes_and_remove_small_regions(self, imp, hole_threshold, area_threshold_vessel):
        """
        Fill holes in the image and remove small regions below the given thresholds.
        """
        rt = ResultsTable()
        roi_manager = RoiManager(False)
        roi_manager.reset()

        IJ.run(imp, "Invert", "")

        options = ParticleAnalyzer.SHOW_NONE + ParticleAnalyzer.EXCLUDE_EDGE_PARTICLES
        measurements = Measurements.AREA

        pa = ParticleAnalyzer(options, measurements, rt, 0, hole_threshold)
        pa.setRoiManager(roi_manager)
        pa.setHideOutputImage(True)
        pa.analyze(imp)

        hole_rois = roi_manager.getRoisAsArray()
        ip = imp.getProcessor()

        for i, roi in enumerate(hole_rois):
            area = rt.getValue("Area", i)
            if area <= hole_threshold:
                ip.setRoi(roi)
                ip.setValue(0)
                ip.fill(roi)

        IJ.run(imp, "Invert", "")
        imp.updateAndDraw()

        roi_manager.reset()
        rt.reset()

        ip = imp.getProcessor()

        pa = ParticleAnalyzer( ParticleAnalyzer.EXCLUDE_EDGE_PARTICLES,
                              Measurements.AREA, rt, 0, area_threshold_vessel)
        pa.setHideOutputImage(True)
        pa.setRoiManager(roi_manager)
        pa.analyze(imp)

        rois = roi_manager.getRoisAsArray()

        for i, roi in enumerate(rois):
            area = rt.getValue("Area", i)
            if area < area_threshold_vessel:
                ip.setRoi(roi)
                ip.setValue(0)
                ip.fill(roi)

        imp.updateAndDraw()
        imp.setOverlay(None)

        return imp, hole_rois

    def _invert_and_fill_holes(self, imp):
        """
        Invert the image and fill holes.
        """
        if imp is None:
            print("The ImagePlus object is None")
            return None

        IJ.run(imp, "Invert", "")
        IJ.run(imp, "Fill Holes", "")
        IJ.run(imp, "Invert", "")

        return imp

    def _process_junction_points(self, imp, distance_threshold):
        """
        Process junction points in the skeleton image.
        """
        analyzeSkeleton = AnalyzeSkeleton_()
        analyzeSkeleton.setup("", imp)
        results = analyzeSkeleton.run(AnalyzeSkeleton_.NONE, False, False, None, True, False)

        branchNumber = results.getBranches()
        juncList = results.getListOfJunctionVoxels()

        all_junction_points = []
        for i in range(juncList.size()):
            voxel_list = juncList.get(i)
            all_junction_points.append(voxel_list)

        clusters = self._cluster_points(all_junction_points, threshold=distance_threshold)
        unique_junction_points = [cluster[0] for cluster in clusters]

        rt_all = ResultsTable()
        rt_unique = ResultsTable()

        for voxel in all_junction_points:
            x = voxel.x
            y = voxel.y
            z = voxel.z
            rt_all.incrementCounter()
            rt_all.addValue("X", x)
            rt_all.addValue("Y", y)
            rt_all.addValue("Z", z)

        for voxel in unique_junction_points:
            x = voxel.x
            y = voxel.y
            z = voxel.z
            rt_unique.incrementCounter()
            rt_unique.addValue("X", x)
            rt_unique.addValue("Y", y)
            rt_unique.addValue("Z", z)

        print("Number of unique junction points:", len(unique_junction_points))

        return rt_all, rt_unique, len(unique_junction_points)

    def _distance(self, p1, p2):
        """
        Calculate Euclidean distance between two points.
        """
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)

    def _cluster_points(self, points, threshold):
        """
        Cluster points that are within the given distance threshold.
        """
        clusters = []
        used = set()

        for i, p1 in enumerate(points):
            if i in used:
                continue
            cluster = [p1]
            used.add(i)
            for j, p2 in enumerate(points):
                if j in used:
                    continue
                if self._distance(p1, p2) <= threshold:
                    cluster.append(p2)
                    used.add(j)
            clusters.append(cluster)
        return clusters

    def _break_branches_and_prune(self, imp, rt_all, mean_threshold):
        """
        Break branches in the skeleton and remove small segments based on mean threshold.
        """
        output_ip = imp.getProcessor()
        modified_ip = output_ip.duplicate()
        modified_imp = ImagePlus("Modified Skeleton", modified_ip)

        branch_points_set = set()
        for i in range(rt_all.size()):
            x = int(rt_all.getValue("X", i))
            y = int(rt_all.getValue("Y", i))
            branch_points_set.add((x, y))

        for (x, y) in branch_points_set:
            modified_ip.putPixelValue(x, y, 0)

        modified_ip.setThreshold(1, Double.MAX_VALUE, ImageProcessor.NO_LUT_UPDATE)

        roi_manager = RoiManager(False)

        rt_segments = ResultsTable()
        pa = ParticleAnalyzer(ParticleAnalyzer.SHOW_NONE | ParticleAnalyzer.RECORD_STARTS,
                              Measurements.AREA | Measurements.CENTROID, rt_segments, 0, Double.POSITIVE_INFINITY)
        pa.setHideOutputImage(True)
        pa.setRoiManager(roi_manager)
        pa.analyze(modified_imp)
        hole_rois = roi_manager.getRoisAsArray()

        #self.show()

        for i in range(rt_segments.size()):
            mean_val = rt_segments.getValue("Area", i)

            if mean_val < mean_threshold:
                roi = hole_rois[i]
                modified_imp.setRoi(roi)
                modified_imp.updateAndDraw()
                x = int(rt_segments.getValue("XStart", i))
                y = int(rt_segments.getValue("YStart", i))
                start_point = Point(int(x), int(y))

                IJ.doWand(modified_imp, x, y, 0, "8-connected")
                roiWand = modified_imp.getRoi()

                modified_imp.setRoi(roiWand)
                segmentPts = roiWand.getContainedPoints()
                endX = segmentPts[-1].x
                endY = segmentPts[-1].y
                end_point = Point(int(endX), int(endY))

                neighboursStart = self._get_neighbours(start_point, output_ip)
                neighboursEnd = self._get_neighbours(end_point, output_ip)
                if (len(neighboursStart) == 1 or len(neighboursEnd) == 1):
                    for p in segmentPts:
                        modified_ip.putPixelValue(p.x, p.y, 0)

        for (x, y) in branch_points_set:
            modified_ip.putPixelValue(x, y, 255)

        modified_imp.updateAndDraw()

        self.changes = False
        self.close()
        roi_manager.close()

        return modified_imp

    def _get_neighbours(self, point, ip):
        """
        Get neighbouring pixels of a point in the image.
        """
        x, y = point.x, point.y
        width, height = ip.getWidth(), ip.getHeight()
        neighbours = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height and ip.getPixel(nx, ny) == 255:
                        neighbours.append(Point(nx, ny))
        return neighbours

    def _skeleton_map(self, expanded_imp, cleaned_imp):
        """
        Map the skeleton onto the image and extract skeleton values.
        """
        if cleaned_imp.getWidth() != self.getWidth() or cleaned_imp.getHeight() != self.getHeight():
            raise ValueError("Both images must have the same dimensions.")

        width = cleaned_imp.getWidth()
        height = cleaned_imp.getHeight()

        cleaned_ip = cleaned_imp.getProcessor()
        expanded_ip = expanded_imp.getProcessor()

        output_ip = FloatProcessor(width, height)

        skeleton_values = []

        for y in range(height):
            for x in range(width):
                if expanded_ip.getPixel(x, y) != 0:
                    value = cleaned_ip.getPixelValue(x, y)
                    output_ip.putPixelValue(x, y, value)
                    skeleton_values.append(value)

        output_imp = ImagePlus("Skeleton with Values", output_ip)
        return output_imp, skeleton_values

    def _break_branches_and_analyze(self, output_imp, rt_all):
        """
        Break branches and analyze average values.
        """
        modified_ip = output_imp.getProcessor().duplicate()
        modified_imp = ImagePlus("Modified Skeleton", modified_ip)

        for i in range(rt_all.size()):
            x = int(rt_all.getValue("X", i))
            y = int(rt_all.getValue("Y", i))
            modified_ip.putPixelValue(x, y, 0)

        modified_ip.setThreshold(1, Double.MAX_VALUE, ImageProcessor.NO_LUT_UPDATE)

        rt_segments = ResultsTable()
        pa = ParticleAnalyzer(ParticleAnalyzer.SHOW_NONE, Measurements.MEAN, rt_segments, 0, Double.POSITIVE_INFINITY)

        pa.setHideOutputImage(True)
        pa.analyze(modified_imp)

        mean_column = rt_segments.getColumnAsDoubles(rt_segments.getColumnIndex("Mean"))

        if mean_column is not None:
            average_values = list(mean_column)
        else:
            average_values = []

        return modified_imp, average_values

    def _area_and_perimeter(self, imp):
        """
        Calculate area and perimeter of the vessel and perivascular regions.
        """
        roi_manager = RoiManager(False)
        roi_manager.reset()

        unique_results_table = ResultsTable()

        if imp is None:
            print("The ImagePlus object is None")
            return None

        # Set measurements to include Area and Perimeter
        IJ.run("Set Measurements...", "area perimeter")
        IJ.run(imp, "Create Selection", "")
        roi_manager.addRoi(imp.getRoi())

        analyzer = Analyzer(imp, unique_results_table)
        analyzer.measure()

        original_area = unique_results_table.getValue("Area", unique_results_table.size() - 1)
        original_perimeter = unique_results_table.getValue("Perim.", unique_results_table.size() - 1)

        IJ.run(imp, "Invert", "")
        IJ.run(imp, "Make Inverse", "")

        roi_manager.addRoi(imp.getRoi())
        analyzer.measure()

        inverted_area = unique_results_table.getValue("Area", unique_results_table.size() - 1)
        inverted_perimeter = unique_results_table.getValue("Perim.", unique_results_table.size() - 1)

        roi_manager.reset()
        unique_results_table.reset()

        return {
            "original_area": original_area,
            "original_perimeter": original_perimeter,
            "inverted_area": inverted_area,
            "inverted_perimeter": inverted_perimeter
        }

    def _create_summary_table(self, filename, branchNumber, average_values, skeleton_values, resultsArea):
        """
        Create a summary table with the vessel analysis results.
        """
        branch_number = branchNumber
        unique_length = len(average_values)
        skeleton_mean = sum(skeleton_values) / len(skeleton_values) if skeleton_values else 0
        branch_mean = sum(average_values) / len(average_values) if average_values else 0

        if not hasattr(self, "summary_table"):
            self.summary_table = ResultsTable()

        self.summary_table.incrementCounter()
        self.summary_table.addValue("Filename", filename)
        self.summary_table.addValue("No. Branch points", branch_number)
        self.summary_table.addValue("No. segments", unique_length)
        self.summary_table.addValue("Mean Radius", skeleton_mean)
        self.summary_table.addValue("Vessel Area", resultsArea["original_area"])
        self.summary_table.addValue("Vessel Perimeter", resultsArea["original_perimeter"])
        self.summary_table.addValue("Perivascular Area", resultsArea["inverted_area"])
        self.summary_table.addValue("Perivascular Perimeter", resultsArea["inverted_perimeter"])
        self.summary_table.addValue("Average branch radius", branch_mean)

        return self.summary_table

    def _save_array_to_csv(self, array, file_path):
        """
        Save an array to a CSV file.
        """
        with open(file_path, 'w') as f:
            for value in array:
                f.write(str(value) + "\n")

    def _append_to_summary_csv(self, summary_table, file_path):
        """
        Append the summary table to the CSV file created for this run.
        """
        row_data = [summary_table.getStringValue(i, 0) for i in range(summary_table.getLastColumn() + 1)]

        with open(file_path, 'ab') as f:
            writer = csv.writer(f)
            writer.writerow(row_data)
