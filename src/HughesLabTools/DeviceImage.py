from ij import IJ, ImagePlus, Prefs
import os


class DeviceImage(ImagePlus):
    def __init__(self, title=None, img=None, image_path=None, verbose=False):
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
        if not isinstance(image_plus, ImagePlus):
            raise TypeError("Input must be an instance of ImagePlus.")
        return cls(img=image_plus, verbose=verbose)

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
                        from ij.io import FileInfo
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
        self._lazy_load()
        if not self._loaded:
            raise IOError("Image not loaded, cannot apply color")

        IJ.run(self, "Enhance Contrast...", "saturated={} normalize".format(sat))
        IJ.run(self, color.title(), "")
        IJ.run(self, "RGB Color", "")

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
