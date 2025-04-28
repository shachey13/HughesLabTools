from ij import IJ, ImagePlus, Prefs, WindowManager
from ij.plugin.filter import Binary
from ij.process import FloatProcessor, ImageProcessor
from ij.gui import Roi, WaitForUserDialog, GenericDialog
from ij.io import FileSaver, FileInfo
import os
from os.path import join, splitext
from javax.swing import JDialog, JLabel, JButton, Timer
from java.awt import FlowLayout, Rectangle
from java.awt.event import ActionListener
import time


class DeviceImage(ImagePlus):
    _trainable_segmentation_available = None

    def __init__(self, title=None, img=None, image_path=None, verbose=False):
        """
        Initialize a DeviceImage instance.

        Args:
            title (str, optional): The title of the image.
            img (ImageProcessor, optional): The image processor.
            image_path (str, optional): The path to the image file.
            verbose (bool, optional): Whether to print verbose logs. Defaults to False.
        """
        self.verbose = verbose
        self.image_path = image_path
        self._loaded = False
        if title is not None and img is not None:
            ImagePlus.__init__(self, title, img)
        elif title is not None:
            ImagePlus.__init__(self, title)
        else:
            ImagePlus.__init__(self)

    @classmethod
    def from_image_plus(cls, image_plus, verbose=False):
        """
        Create a DeviceImage instance from an ImagePlus object.

        Args:
            image_plus (ImagePlus): The ImagePlus object to convert.
            verbose (bool, optional): Whether to print verbose logs. Defaults to False.

        Returns:
            DeviceImage: A new DeviceImage instance.

        Raises:
            TypeError: If the input is not an instance of ImagePlus.
        """
        if not isinstance(image_plus, ImagePlus):
            raise TypeError("Input must be an instance of ImagePlus.")

        instance = cls(title=image_plus.getTitle(), img=image_plus.getProcessor())
        instance.verbose = verbose
        instance.setCalibration(image_plus.getCalibration())

        # set image_path if available
        if hasattr(image_plus, 'image_path') and image_plus.image_path:
            instance.image_path = image_plus.image_path
        else:
            instance.image_path = None

        # Copy FileInfo if available
        if image_plus.getOriginalFileInfo() is not None:
            instance.setFileInfo(image_plus.getOriginalFileInfo())

        instance._loaded = True

        return instance

    def log(self, message, level="INFO"):
        if level == "WARNING":
            print("WARNING: {}".format(message))
        elif self.verbose and level == "INFO":
            print("INFO: {}".format(message))

    def show(self):
        if not self._loaded:
            self._lazy_load()

        try:
            temp_image = ImagePlus(self.getTitle(), self.getProcessor())
            temp_image.show()
        except Exception as e:
            print("Caught Exception:", e)

    def _lazy_load(self):
        if not self._loaded and self.image_path:
            self.log("INFO: Attempting to load image from path: {}".format(self.image_path))
            if not os.path.exists(self.image_path):
                raise IOError("File not found at path: {}".format(self.image_path))
            if not os.access(self.image_path, os.R_OK):
                raise IOError("File not accessible (read permission denied) at path: {}".format(self.image_path))
            try:
                img = IJ.openImage(self.image_path)
                if img:
                    self.setProcessor(img.getProcessor())
                    self.setTitle(img.getTitle())

                    # Set FileInfo using setFileInfo()
                    if img.getFileInfo() is not None:
                        self.setFileInfo(img.getFileInfo())
                    else:
                        fi = FileInfo()
                        fi.fileName = os.path.basename(self.image_path)
                        fi.directory = os.path.dirname(self.image_path) + os.sep  # Ensure directory ends with separator
                        self.setFileInfo(fi)

                    self._loaded = True
                    self.log("INFO: Loaded image successfully from path: {}".format(self.image_path))
                else:
                    raise IOError("Failed to load image from path: {}".format(self.image_path))
            except Exception as e:
                raise IOError("INFO: Error loading image from path: {}. Exception: {}".format(self.image_path, str(e)))

    def apply_color(self, color, sat=0.3):
        """
        Apply a color to the image.

        Args:
            color (str): The color to apply.
            sat (float, optional): The saturation level. Defaults to 0.3.

        Raises:
            IOError: If the image is not loaded.
        """
        self._lazy_load()
        if not self._loaded:
            raise IOError("Image not loaded, cannot apply color")

        IJ.run(self, "Enhance Contrast...", "saturated={} normalize".format(sat))
        IJ.run(self, color.title(), "")
        IJ.run(self, "RGB Color", "")

    def crop_image(self, crop_type='individual', num_types=1, is_first=False, coordinates=None):
        """
        Crop the image based on the specified parameters.

        Args:
            crop_type (str, optional): The type of cropping to perform. Must be 'individual', 'batch', or 'grouped'. Defaults to 'individual'.
            num_types (int, optional): The number of image types. Defaults to 1.
            is_first (bool, optional): Whether this is the first image in a batch or group. Defaults to False.
            coordinates (tuple, optional): The coordinates for cropping (x, y, width, height). Required for batch and grouped cropping when not the first image.

        Returns:
            tuple: The coordinates of the crop if it's the first image in a batch or group crop.

        Raises:
            IOError: If the image is not loaded.
            ValueError: If an invalid crop type is specified.
        """
        self._lazy_load()
        if not self._loaded:
            raise IOError("Image not loaded, cannot crop")

        if crop_type not in ['individual', 'batch', 'grouped']:
            raise ValueError("Invalid crop type. Must be 'individual', 'batch', or 'grouped'")

        crop_folder = self._output_path("crop")

        if crop_type == 'individual' or (crop_type in ['grouped', 'batch'] and is_first):
            self.open_image_and_set_roi()
            bounds = self.create_instruction_dialog(crop_type == 'batch')
            if bounds is None:
                self.close()
                return
        elif crop_type in ['batch', 'grouped'] and not is_first:
            bounds = Rectangle(*coordinates)
        else:
            bounds = Rectangle(*coordinates)

        self._crop_and_save(bounds, crop_folder)
        self.close()

        # cleanup
        WindowManager.closeAllWindows()

        if crop_type == 'grouped' and is_first or (crop_type == 'batch' and is_first):
            return (bounds.x, bounds.y, bounds.width, bounds.height)

    def open_image_and_set_roi(self):
        self.show()
        WindowManager.setCurrentWindow(self.getWindow())

        default_crop_width, default_crop_height = 200, 200
        width, height = self.getWidth(), self.getHeight()
        midX = int(width / 2 - default_crop_width / 2)
        midY = int(height / 2 - default_crop_height / 2)

        roi = Roi(midX, midY, default_crop_width, default_crop_height)
        self.setRoi(roi)
        self.updateAndDraw()
        #self.show()

    def create_instruction_dialog(self, is_batch):
        dialog = JDialog(None, "Adjust ROI", False)
        dialog.setSize(300, 100)
        dialog.setLayout(FlowLayout())
        dialog.setLocationRelativeTo(None)
        dialog.setAlwaysOnTop(True)

        label = JLabel("Draw an ROI using the Rectangle Tool and click OK to continue.")
        dialog.add(label)

        ok_button = JButton("OK")
        cancel_button = JButton("Skip")

        bounds = [None]

        class OKListener(ActionListener):
            def actionPerformed(self, event):
                bounds[0] = DeviceImage.set_roi(dialog, is_batch)
                dialog.dispose()

        class CancelListener(ActionListener):
            def actionPerformed(self, event):
                dialog.dispose()

        ok_button.addActionListener(OKListener())
        cancel_button.addActionListener(CancelListener())

        dialog.add(ok_button)
        dialog.add(cancel_button)
        dialog.setVisible(True)

        while dialog.isVisible():
            time.sleep(0.1)

        return bounds[0]

    @staticmethod
    def set_roi(dialog, is_batch):
        imp = WindowManager.getCurrentImage()
        roi = imp.getRoi()
        if roi is None:
            IJ.log("No ROI selected. Exiting cropping.")
            imp.changes = False
            imp.close()
            return None

        bounds = roi.getBounds()
        IJ.log("Start X: " + str(bounds.x))
        IJ.log("Start Y: " + str(bounds.y))
        IJ.log("ROI Width: " + str(bounds.width))
        IJ.log("ROI Height: " + str(bounds.height))

        imp.changes = False
        imp.close()

        return bounds

    def _crop_and_save(self, bounds, crop_folder):
        roi = Roi(bounds.x, bounds.y, bounds.width, bounds.height)
        self.setRoi(roi)
        cropped_imp = self.crop()
        save_path = os.path.join(crop_folder, self.getTitle())
        FileSaver(cropped_imp).saveAsTiff(save_path)
        IJ.log("Cropped and saved: " + save_path)
        cropped_imp.close()

    def duplicate_and_rename(self, suffix):
        """
        Duplicates the current image and gives it a new title with the specified suffix.

        :param suffix: The suffix to add to the duplicated image title
        :return: The duplicated ImagePlus object with the new title
        """
        self._lazy_load()
        duplicated_image = self.duplicate()
        new_title = os.path.splitext(self.getTitle())[0] + suffix
        duplicated_image.setTitle(new_title)
        return duplicated_image

    def apply_threshold_and_mask(self, method='Li dark b&w', black_background=True):
        """
        Applies thresholding and converts the duplicated image to a mask.
        """
        thresholded_image = self.duplicate_and_rename('_threshold')
        IJ.setAutoThreshold(thresholded_image, method)
        Prefs.blackBackground = black_background
        IJ.run(thresholded_image, 'Convert to Mask', '')
        return thresholded_image

    def segment_image(self, selected_file, output_folder):
        """
        Segment the image using a Weka classifier and save the result.

        Args:
            selected_file (str): The path to the Weka classifier file.
            output_folder (str): The name of the folder to save the segmented image.

        Raises:
            IOError: If the image is not loaded or if there's an error in saving the segmented image.
        """
        segment_folder = self._output_path(output_folder)

        IJ.log("Starting segmentation of image: {}".format(self.getTitle()))

        # convert image to grayscale if necessary and run classifier
        grayscale_image = self._convert_to_grayscale()

        # Load the classifier
        segmenter = WekaSegmentation(grayscale_image)
        segmenter.loadClassifier(selected_file)
        result = segmenter.applyClassifier(grayscale_image)

        # generate image from result
        result_ip = result.getProcessor() if isinstance(result, ImagePlus) else FloatProcessor(result)
        result_imp = ImagePlus("Result", result_ip)

        # binarize result
        result_ip.setThreshold(1, 255, ImageProcessor.NO_LUT_UPDATE)
        binary = Binary()
        binary.setup("make binary", result_imp)
        binary.run(result_ip)

        # invert result and save
        result_imp = self._convert_and_invert_binary_255(result_ip)
        segmented_image_path = os.path.join(segment_folder, "{}-Segment.tif".format(os.path.splitext(self.getTitle())[0]))
        IJ.saveAs(result_imp, "Tiff", segmented_image_path)

        # clean up
        IJ.run("Close All")

        IJ.log("Segmentation completed for image: {}".format(self.getTitle()))


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

    def _convert_and_invert_binary_255(self, result_ip):
        result_imp = ImagePlus("Result", result_ip.duplicate())
        result_processor = result_imp.getProcessor()
        for y in range(result_processor.getHeight()):
            for x in range(result_processor.getWidth()):
                if result_processor.getPixel(x, y) > 0:
                    result_processor.set(x, y, 0)
                else:
                    result_processor.set(x, y, 255)
        result_imp.setProcessor(result_processor)
        return result_imp

    def _get_image_type(self):
        processor = self.getProcessor()
        if processor.getBitDepth() == 24:
            return "color"
        else:
            return "grayscale"

    def _convert_to_grayscale(self):
        if self._get_image_type() == "color":
            IJ.run(self, "8-bit", "")
            return DeviceImage.from_image_plus(self)
        return self

    @classmethod
    def prepare_for_segmentation(cls):
        """
        Check for trainableSegmentation availability and import it if available.
        This method can be called once before running multiple segmentations.
        """
        if cls._trainable_segmentation_available is None:
            try:
                global WekaSegmentation
                from trainableSegmentation import WekaSegmentation
                cls._trainable_segmentation_available = True
                IJ.log("trainableSegmentation module is available and imported successfully.")
            except ImportError:
                IJ.log("Error: trainableSegmentation module is not installed.")
                IJ.log("Please install it via the Fiji updater or manually add it to the plugins folder.")
                cls._trainable_segmentation_available = False

        return cls._trainable_segmentation_available

    def save(self, file_path):
        self._lazy_load()
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        try:
            IJ.save(self, file_path)
            self.log("INFO: Image saved successfully at {}".format(file_path))
            return True
        except Exception as e:
            self.log("WARNING: Failed to save the image: {}".format(e), level="WARNING")
            return False
