from __future__ import print_function
from ij import IJ, Prefs
from ij.io import FileSaver
from ij.measure import ResultsTable, Measurements
from ij.plugin import ImageCalculator
from ij.plugin.filter import Analyzer, ParticleAnalyzer
from DeviceImage import DeviceImage
import csv
import os
from os.path import splitext, join


class TumorImage(DeviceImage):
    def __init__(self, title=None, img=None):
        if title is not None and img is not None:
            super(TumorImage, self).__init__(title, img)
        elif title is not None:
            super(TumorImage, self).__init__(title)
        else:
            super(TumorImage, self).__init__()

    @staticmethod
    def set_measurements():
        IJ.run('Set Measurements...', 'area mean integrated limit display decimal=3')

    def analyze_particles(self, imp):
        IJ.run('Clear Results', '')
        IJ.run(imp, 'Analyze Particles...', 'size=0-Infinity show=Outlines in_situ clear')
        return ResultsTable.getResultsTable()

    def create_segmented_image(self, original_image):
        ic = ImageCalculator()
        img2 = ic.run('Add create', original_image, original_image.duplicate())
        img2.setTitle(splitext(original_image.getTitle())[0] + '_segmented')
        return img2

    def segment_tumor(self):
        thresholded = self.apply_threshold_and_mask()
        self.set_measurements()
        results_table = self.analyze_particles(thresholded)
        segmented_image = self.create_segmented_image(thresholded)
        output_dir = self._output_path('segmented')
        output_path = join(output_dir, splitext(self.getTitle())[0] + '_segmented.jpg')
        output_path_table = join(output_dir, splitext(self.getTitle())[0] + '_results.csv')
        IJ.save(segmented_image, output_path)
        results_table.saveAs(output_path_table)

        return segmented_image

    def subtract_background(self, radius):
        imp = self.duplicate()
        IJ.run('Clear Results', '')
        rolling_radius = radius
        IJ.run(imp, "Subtract Background...", "rolling=%d" % rolling_radius)
        output_dir = self._output_path('subtracted')
        output_path = join(output_dir, splitext(self.getTitle())[0] + '_subtracted.tif')
        FileSaver(imp).saveAsTiff(output_path)

    def measure_tumor_gray(self, summary_csv_path):
        IJ.run('Clear Results', '')
        measurements = 'mean standard modal min integrated limit display'
        IJ.run('Set Measurements...', measurements)
        an = Analyzer(self)
        an.measure()
        rt = ResultsTable.getResultsTable()
        results_dir = self._output_path('measure_gray')
        results_path = join(results_dir, splitext(self.getTitle())[0] + '_tumor_gray_results.csv')
        rt.saveAs(results_path)

        # create adn save summary table
        summary_table = self._create_tumor_gray_summary_table(rt)
        self._append_to_summary_csv(summary_table, summary_csv_path)

    def _create_tumor_gray_summary_table(self, results_table):
        """
        Create a summary table with tumor gray measurement results.
        """
        summary_table = ResultsTable()

        # Extract measurements
        mean = results_table.getValue("Mean", 0)
        std_dev = results_table.getValue("StdDev", 0)
        mode = results_table.getValue("Mode", 0)
        min_val = results_table.getValue("Min", 0)
        max_val = results_table.getValue("Max", 0)
        integrated_density = results_table.getValue("IntDen", 0)
        rawIntDen = results_table.getValue("RawIntDen", 0)
        minThresh = results_table.getValue("MinThr", 0)
        maxThresh = results_table.getValue("MaxThr", 0)

        summary_table.incrementCounter()
        summary_table.addValue("Filename", self.getTitle())
        summary_table.addValue("Mean Gray Value", mean)
        summary_table.addValue("Standard Deviation", std_dev)
        summary_table.addValue("Mode", mode)
        summary_table.addValue("Min", min_val)
        summary_table.addValue("Max", max_val)
        summary_table.addValue("Integrated Density", integrated_density)
        summary_table.addValue("Raw Integrated Density", rawIntDen)
        summary_table.addValue("Min Threshold", minThresh)
        summary_table.addValue("Max Threshold", maxThresh)

        return summary_table

    def measure_circularity(self, bp, st, lt, summary_csv_path):
        imp = self.duplicate()
        IJ.run('Clear Results', '')
        measurements = 'area perimeter fit shape limit add redirect=None decimal=3'
        IJ.run('Set Measurements...', measurements)

        # adjust black point
        #imp.setDisplayRange(bp, 255)
        #IJ.run(imp, "Apply LUT", "")

        # Threshold and convert to mask
        IJ.setAutoThreshold(imp, 'Li dark b&w')
        Prefs.blackBackground = True
        IJ.run(imp, "Convert to Mask", "")

        # get results table
        st = str(int(st))
        lt = str(int(lt))
        rt = ResultsTable()
        pa = ParticleAnalyzer(ParticleAnalyzer.CLEAR_WORKSHEET |
                              ParticleAnalyzer.IN_SITU_SHOW,
                              Analyzer.getMeasurements(),
                              rt, float(st), float(lt))
        pa.analyze(imp)

        #save results table
        results_dir = self._output_path('circularity')
        results_path = join(results_dir, splitext(self.getTitle())[0] + '_circularity_results.csv')
        rt.saveAs(results_path)

        # save summary table
        summary_table = self._create_circularity_summary_table(rt)
        self._append_to_summary_csv(summary_table, summary_csv_path)

        # save image
        output_path = join(results_dir, splitext(self.getTitle())[0] + '_circularity.tif')
        FileSaver(imp).saveAsTiff(output_path)

    def _create_circularity_summary_table(self, results_table):
        """
        Create a summary table with circularity analysis results.
        """
        summary_table = ResultsTable()

        # Calculate summary statistics
        areas = results_table.getColumn("Area")
        circularities = results_table.getColumn("Circ.")
        perim = results_table.getColumn("Perim.")
        solidity = results_table.getColumn("Solidity")

        if areas and circularities and perim and solidity:
            avg_area = sum(areas) / len(areas)
            avg_circularity = sum(circularities) / len(circularities)
            avg_precentArea = 100 * (sum(areas) / (self.getWidth() * self.getHeight()))
            avg_perim = sum(perim) / len(perim)
            avg_solidity = sum(solidity) / len(solidity)

            summary_table.incrementCounter()
            summary_table.addValue("Filename", self.getTitle())
            summary_table.addValue("Particle Count", len(areas))
            summary_table.addValue("Average Area", avg_area)
            summary_table.addValue("Average %Area", avg_precentArea)
            summary_table.addValue("Average Perim", avg_perim)
            summary_table.addValue("Average Circularity", avg_circularity)
            summary_table.addValue("Average Solidity", avg_solidity)

        return summary_table

    def _append_to_summary_csv(self, summary_table, file_path):
        """
        Append the summary table to the CSV file created for this run.
        """
        headers = [summary_table.getColumnHeading(i) for i in range(summary_table.getLastColumn() + 1)]
        row_data = [summary_table.getStringValue(i, 0) for i in range(summary_table.getLastColumn() + 1)]

        file_exists = os.path.isfile(file_path)

        with open(file_path, 'ab') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row_data)

    def _output_path(self, newDir):
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
