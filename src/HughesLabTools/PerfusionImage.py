from ij import IJ, ImagePlus, WindowManager, ImageStack, ImageJ
from ij.gui import Roi, OvalRoi, Toolbar, PointRoi, ImageWindow, WaitForUserDialog, Line
from ij.measure import ResultsTable
from ij.plugin.frame import RoiManager
from ij.process import ImageProcessor
from HughesLabTools.DeviceImage import DeviceImage
import os
from os.path import join, splitext
import csv
import array

class PerfusionImage(DeviceImage):
    def __init__(self, title=None, img=None):
        if title is not None and img is not None:
            super(PerfusionImage, self).__init__(title, img)
        elif title is not None:
            super(PerfusionImage, self).__init__(title)
        else:
            super(PerfusionImage, self).__init__()
        #self.oval_radius = self.options['oval_rad']  # Default ROI radius in pixels
        self.roi_manager = RoiManager(False)

    def perform_permeability_analysis(self, options, additional_images=None, output_dir=None, oval_radius=None):
        """
        Perform perfusion analysis on the image stack and save results.
        """
        self.roi_manager.reset()
        # Load additional images if they're provided as paths
        loaded_additional_images = [IJ.openImage(path) for path in additional_images]

        #self.oval_radius = options.get('oval_radius', self.oval_radius)
        manual_align = options.get('manual_align', False)

        # Create output directory
        output_dir = self.output_path("Permeability")

        # Create image stack
        stack = self.create_image_stack(additional_images)
        stack.show()

        # Perform manual alignment if selected
        if manual_align:
            stack = self.manual_align(stack)

        # Set ROIs
        rois = self.set_rois(stack, oval_radius=oval_radius)

        # Measure ROIs across all slices
        results = self.measure_rois(stack, rois)

        # Save results
        self.save_results(results, output_dir, stack)

        # Clean up
        stack.close()
        self.roi_manager.reset()
        self.roi_manager.close()
        imp = None

    def create_image_stack(self, additional_images):
        """Create an image stack from this image and additional images."""
        self._lazy_load()  # Ensure the current image is loaded
        images = [DeviceImage(image_path=img_path) for img_path in (additional_images or [])]

        # Get dimensions from the first image
        width = self.getWidth()
        height = self.getHeight()

        # Create a new stack
        stack = ImageStack(width, height)
        # Add the first image (self) to the stack
        stack.addSlice(self.getTitle(), self.getProcessor())

        for img in images:
            img._lazy_load()  # Ensure each image is loaded
            print("loaded each image successfully")
            ip = img.getProcessor()
            print(ip)

            # Resize the image if necessary
            if ip.getWidth() != width or ip.getHeight() != height:
                ip = ip.resize(width, height)

            print(ip)
            stack.addSlice(img.getTitle(), ip)

        # Create an ImagePlus from the stack
        imp = ImagePlus("Stack", stack)

        return imp

    def manual_align(self, stack):
        """Perform manual alignment of the image stack."""
        aligned_stack = stack.duplicate()
        width = aligned_stack.getWidth()
        height = aligned_stack.getHeight()
        n_slices = aligned_stack.getNSlices()

        line_x = array.array('f', [0.0] * n_slices)
        line_y = array.array('f', [0.0] * n_slices)
        adjust_x = array.array('f', [0.0] * n_slices)
        adjust_y = array.array('f', [0.0] * n_slices)

        mid_x = width / 2
        mid_y = height / 2

        for i in range(n_slices):
            aligned_stack.setSlice(i + 1)

            # Vertical line
            line = Line(mid_x, 0, mid_x, height)
            aligned_stack.setRoi(line)
            WaitForUserDialog("Adjust Vertical Line", "Adjust the line to the center of the communication pore.").show()
            adjusted_line = aligned_stack.getRoi()
            line_x[i] = adjusted_line.getXBase()
            adjust_x[i] = line_x[i] - line_x[0]

            # Horizontal line
            line = Line(0, mid_y, width, mid_y)
            aligned_stack.setRoi(line)
            WaitForUserDialog("Adjust Horizontal Line", "Adjust the line to the center of the tissue chamber.").show()
            adjusted_line = aligned_stack.getRoi()
            line_y[i] = adjusted_line.getYBase()
            adjust_y[i] = line_y[i] - line_y[0]

            print("Timepoint {} Adjustment: {}, {}".format(i+1, adjust_x[i], adjust_y[i]))

        # Apply the adjustments
        for i in range(n_slices):
            aligned_stack.setSlice(i + 1)
            ip = aligned_stack.getProcessor()
            ip.translate(-int(adjust_x[i]), -int(adjust_y[i]))

        aligned_stack.setSlice(1)
        aligned_stack.deleteRoi()

        return aligned_stack

    def set_rois(self, stack, oval_radius):
        """Allow the user to set ROIs on the first slice of the stack."""
        IJ.run(stack, "Select None", "")
        IJ.run("Point Tool...", "type=Hybrid color=Yellow size=Small label")
        dialog = WaitForUserDialog(
            "Add Points",
            "1. Please select the Multi-point Tool. \n" +
            "2. Click to add points for your ROIs.\n" +
            "3. Click 'OK' when you're done adding points."
        )
        dialog.show()

        if stack.getRoi() is None:
            raise ValueError("No ROIs were selected. Please try again.")

        points = stack.getRoi().getContainedPoints()
        rois = []
        self.roi_manager.reset()
        for point in points:
            oval = OvalRoi(point.x - oval_radius, point.y - oval_radius,
                           oval_radius * 2, oval_radius * 2)
            rois.append(oval)
            self.roi_manager.addRoi(oval)

        return rois

    def measure_rois(self, stack, rois):
        """Measure ROIs across all slices of the stack."""
        results = []
        rt = ResultsTable()

        for n in range(1, stack.getNSlices() + 1):
            stack.setSlice(n)
            for i, roi in enumerate(rois):
                stack.setRoi(roi)
                stats = stack.getStatistics()
                results.append({
                    'Timepoint': n,
                    'ROI_Number': i + 1,
                    'Mean_Intensity': stats.mean,
                    'Area': stats.area,
                    'Min_Intensity': stats.min,
                    'Max_Intensity': stats.max
                })

                rt.incrementCounter()
                rt.addValue("Timepoint", n)
                rt.addValue("ROI", i + 1)
                rt.addValue("Mean", stats.mean)
                rt.addValue("Area", stats.area)
                rt.addValue("Min", stats.min)
                rt.addValue("Max", stats.max)

        return results

    def save_results(self, results, output_dir, stack):
        """Save the results to a CSV file."""
        csv_path = join(output_dir, self.getTitle() + "_permeability_results.csv")
        with open(csv_path, 'wb') as f:
            writer = csv.DictWriter(f, fieldnames=['Timepoint', 'ROI_Number', 'Mean_Intensity', 'Area', 'Min_Intensity', 'Max_Intensity'])
            writer.writeheader()
            for row in results:
                writer.writerow(row)

        # Save ROIs
        self.roi_manager.runCommand("Save", join(output_dir, self.getTitle() + "_ROIs.zip"))

        # Log summary
        IJ.log("Number of ROIs Measured: {}".format(len(results) // stack.getNSlices()))
        for i, roi in enumerate(self.roi_manager.getRoisAsArray()):
            IJ.log("ROI Coordinates {}: {}, {}".format(i+1, roi.getXBase(), roi.getYBase()))

    def perform_perfusion_analysis(self, options, additional_images=None):
        """
        Perform perfusion analysis on the image stack and save results.
        """
        self._lazy_load()  # Ensure the current image is loaded
        output_dir = self.output_path("Perfusion")

        # Get the starting image (reference image) from options
        starting_image = int(options.get('starting_image', 1))   # Convert to 0-based index

        if starting_image < 0 or starting_image >= len(additional_images):
            self.log("Error: Invalid starting image index.")
            return

        # The reference image is now selected based on the user input
        reference_index = starting_image - 1
        reference_path = additional_images[reference_index]
        reference_imp = IJ.openImage(reference_path)

        # Create output CSV file
        output_csv = os.path.join(output_dir, self.getTitle() + "_perfusion_results.csv")
        with open(output_csv, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Image", "Unique Area", "Total Area"])

        # Process each image, skipping the reference image
        for i, img_path in enumerate(additional_images):
            self.process_perfusion_image(reference_imp, img_path, output_csv)

        self.log("Perfusion analysis complete. Results saved to %s" % output_csv)

        # Close the reference image
        reference_imp.changes = False
        reference_imp.close()

    def process_perfusion_image(self, reference_imp, data_path, output_csv):
        """
        Process a single image for perfusion analysis.
        """
        data_imp = IJ.openImage(data_path)

        reference_pixels = reference_imp.getProcessor().convertToFloat().getPixels()
        data_pixels = data_imp.getProcessor().convertToFloat().getPixels()

        dif_img = [ref - data for ref, data in zip(reference_pixels, data_pixels)]
        dif_img = [0 if val == 255 else 255 if val == -255 else val for val in dif_img]

        unique_area = sum(dif_img) / 255
        total_area = len(dif_img)

        with open(output_csv, 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([os.path.basename(data_path), unique_area, total_area])

        data_imp.changes = False
        data_imp.close()

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
