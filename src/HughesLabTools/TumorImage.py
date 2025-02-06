from __future__ import print_function
from ij import IJ
from ij.measure import ResultsTable
from ij.plugin import ImageCalculator
from DeviceImage import DeviceImage
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

    def analyze_particles(self):
        IJ.run('Clear Results', '')
        IJ.run(self, 'Analyze Particles...', 'size=0-Infinity show=Outlines display in_situ clear')
        return ResultsTable.getResultsTable()

    def save_results(self, img, results_table):
        base_dir = self.getOriginalFileInfo().directory
        segmented_dir = join(base_dir, 'segmented')
        if not os.path.exists(segmented_dir):
            os.makedirs(segmented_dir)
        segmented_path = join(segmented_dir, splitext(self.getTitle())[0] + '_segmented.jpg')
        results_path = join(segmented_dir, splitext(self.getTitle())[0] + '_results.csv')
        self.save(segmented_path)
        results_table.saveAs(results_path)

    def create_segmented_image(self, original_image):
        ic = ImageCalculator()
        img2 = ic.run('Add create', original_image, original_image.duplicate())
        img2.setTitle(splitext(original_image.getTitle())[0] + '_segmented')
        return img2

    def segment_tumor(self):
        self.apply_threshold_and_mask()
        self.set_measurements()
        results_table = self.analyze_particles()
        segmented_image = self.create_segmented_image(self)
        self.save_results(segmented_image, results_table)
        return segmented_image

    def measure_tumor_gray(self):
        IJ.run('Clear Results', '')
        measurements = 'mean standard modal min integrated limit display'
        IJ.run('Set Measurements...', measurements)
        an = filter.Analyzer(self)
        an.measure()
        rt = ResultsTable.getResultsTable()
        results_dir = join(self.getOriginalFileInfo().directory, 'measured_gray')
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        results_path = join(results_dir, splitext(self.getOriginalFileInfo().fileName)[0] + '_tumor_gray_results.csv')
        rt.saveAs(results_path)
