import os
from ij import IJ
from ij import ImageStack, ImagePlus
from ij.plugin import ZProjector
from java.lang import System
from HughesLabTools.DeviceImage import DeviceImage

class Device:
    def __init__(self, typeNames, name=None, deviceDir=None, verbose=False):
        self.name = name
        self.typeNames = typeNames
        self.deviceDir = deviceDir
        self.verbose = verbose
        self.image_paths = {image_type: None for image_type in typeNames}
        self.colored_image_paths = {image_type: None for image_type in typeNames}

    def log(self, message, level="INFO"):
        if level == "ERROR":
            IJ.handleException(Exception(message))
        elif level == "WARNING":
            IJ.log("WARNING: [Device - {}] {}".format(self.name, message))
        elif level == "INFO" and self.verbose:
            IJ.log("INFO: [Device - {}] {}".format(self.name, message))

    def get_deviceDir(self):
        return self.deviceDir

    def get_typeNames(self):
        return self.typeNames

    def set_image_paths(self, image_type=None, image_path=None, image_paths=None):
        if image_paths and isinstance(image_paths, dict):
            self._set_image_paths_from_dict(image_paths)
        elif image_type and image_paths and isinstance(image_paths, list):
            self._set_image_paths_from_list(image_type, image_paths)
        elif image_type and image_path:
            if isinstance(image_path, list):
                self._set_image_paths_from_list(image_type, image_path)
            else:
                self._set_image_path(image_type, image_path)
        self.log("Set image path for {}: {}".format(image_type, self.image_paths[image_type]))

    def _set_image_paths_from_dict(self, image_paths):
        for img_type, img_path in image_paths.items():
            if img_type in self.image_paths:
                self.image_paths[img_type] = os.path.abspath(img_path)

    def _set_image_paths_from_list(self, image_type, image_paths):
        self.image_paths[image_type] = [os.path.abspath(path) for path in image_paths]

    def _set_image_path(self, image_type, image_path):
        if image_type in self.image_paths:
            if self.image_paths[image_type] is None:
                self.image_paths[image_type] = []
            self.image_paths[image_type].append(os.path.abspath(image_path))

    def get_image_paths(self, image_type=None):
        if image_type:
            return self.image_paths.get(image_type, [])
        return self.image_paths

    def set_colored_image_path(self, image_type, image_path):
        if image_type in self.colored_image_paths:
            self.colored_image_paths[image_type] = os.path.abspath(image_path)
            self.log("Set colored image path for {}: {}".format(image_type, self.colored_image_paths[image_type]))

    def get_colored_image_paths(self, image_type=None):
        if image_type:
            return self.colored_image_paths.get(image_type)
        return self.colored_image_paths

    def update_image_type(self, image_path, old_type, new_type, image):
        """
        Updates the image type for a given image.

        Args:
            image_path (str): The file path of the image to update.
            old_type (str): The current image type of the image.
            new_type (str): The new image type to assign.
            image (DeviceImage): The loaded image object.
        """
        # Ensure the old type exists in the image_paths dictionary
        if old_type in self.image_paths:
            if image_path in self.image_paths[old_type]:
                # Remove the image from the old type
                self.image_paths[old_type].remove(image_path)
                if not self.image_paths[old_type]:  # Clean up empty lists
                    self.image_paths[old_type] = None

            # Add the image to the new type
            if new_type not in self.image_paths or self.image_paths[new_type] is None:
                self.image_paths[new_type] = []
            self.image_paths[new_type].append(image_path)

            # Log the change if verbose mode is enabled
            self.log("Updated image type for {} from {} to {}.".format(image_path, old_type, new_type))

        else:
            self.log("Error: Old type {} not found for image {}.".format(old_type, image_path))

    def apply_color_to_images(self, typeColors, sat=0.3, show_colored=False):
        """Applies color to all images of this device."""
        for img_type, color in zip(self.typeNames, typeColors):
            image_paths = self.get_image_paths(img_type)
            if not image_paths:
                self.log("No image paths found for device: {}, type: {}".format(self.name, img_type))
                continue

            if not isinstance(image_paths, list):
                image_paths = [image_paths]

            for image_path in image_paths:
                self._apply_color_to_single_image(img_type, color, image_path, sat, show_colored)

    def _load_image(self, image_path, verbose=False):
        """Loads an image from the given path using DeviceImage with lazy loading."""
        try:
            # Create a DeviceImage instance
            image = DeviceImage(image_path=image_path, verbose=verbose)

            # Perform lazy loading of the image
            image._lazy_load()

            return image
        except Exception as e:
            self.log("Error loading image from path {}: {}".format(image_path, str(e)))
            raise

    def _apply_color_to_single_image(self, img_type, color, image_path, sat, show_colored):
        try:
            # Load the image
            image = self._load_image(image_path, verbose=self.verbose)

            # Apply color to the image
            image.apply_color(color, sat)

            # Save the colored image
            output_directory = os.path.join(self.get_deviceDir(), 'colored')
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)

            base, ext = os.path.splitext(image_path)
            new_filename = "{}_colored{}".format(os.path.basename(base), ext)
            output_path = os.path.join(output_directory, new_filename)

            image.save(output_path)

            # Show the colored image if requested
            if show_colored:
                image.show()

            self.log("Saved colored image at: {}".format(output_path))

            self.set_colored_image_path(img_type, output_path)

        except Exception as e:
            self.log("Error applying color to image: {}. Exception: {}".format(image_path, str(e)), level="WARNING")

    def merge_images(self, show_merged=False):
        """Merge colored images for this device."""
        try:
            all_colored_image_paths = []
            for img_type in self.typeNames:
                colored_image_paths = self.get_colored_image_paths(img_type)
                if not isinstance(colored_image_paths, list):
                    colored_image_paths = [colored_image_paths]
                all_colored_image_paths.extend([path for path in colored_image_paths if path])

            if all_colored_image_paths:
                # Log the colored image paths to confirm they exist
                self.log("Colored image paths to merge: {}".format(all_colored_image_paths))

                # Create DeviceImage objects for all colored image paths
                images = [self._load_image(path) for path in all_colored_image_paths]

                # Log the loaded images to confirm they are correctly loaded
                self.log("Loaded {} images for merging.".format(len(images)))

                # Merge all images into a single image
                merged_image = self._merge_images(images)

                # Save the merged image
                output_directory = os.path.join(self.get_deviceDir(), 'merged')
                if not os.path.exists(output_directory):
                    os.makedirs(output_directory)

                new_filename = "{}_merged.tif".format(self.name)
                output_path = os.path.join(output_directory, new_filename)

                merged_image.save(output_path)
                self.log("Merged image saved for device: {}".format(self.name))

                if show_merged:
                    merged_image.show()
            else:
                self.log("No colored images found to merge for device: {}".format(self.name))

        except Exception as e:
            self.log("Error merging images for device: {}. Exception: {}".format(self.name, str(e)), level="WARNING")

    def _crop_to_smallest_dimensions(self, images):
        """Crops all images to the dimensions of the smallest image in the list."""
        if not images:
            raise ValueError("No images provided for cropping.")

        # Find the minimum width and height among all images
        min_width = min(img.getWidth() for img in images)
        min_height = min(img.getHeight() for img in images)

        self.log("Cropping all images to the minimum dimension of images in the device: {}x{}".format(min_width, min_height))

        # Crop each image to the minimum dimensions
        cropped_images = []
        for img in images:
            try:
                img._lazy_load()
                processor = img.getProcessor()
                # Set the region of interest (ROI) and crop
                processor.setRoi(0, 0, min_width, min_height)
                cropped_processor = processor.crop()

                # Create a new DeviceImage with the cropped processor
                cropped_image = DeviceImage(title=img.getTitle(), img=cropped_processor)
                cropped_images.append(cropped_image)
            finally:
                img.close()
                System.gc()

        return cropped_images

    def _merge_images(self, images):
        """Helper function to merge a list of DeviceImage instances, optionally cropping them if needed."""
        if not images:
            raise ValueError("No images provided for merging.")

        # Get the dimensions of the first image
        first_width = images[0].getWidth()
        first_height = images[0].getHeight()

        # Check if all images have the same dimensions
        if all(img.getWidth() == first_width and img.getHeight() == first_height for img in images):
            self.log(
                "All images have the same dimensions: {}x{}. No cropping needed.".format(first_width, first_height))
        else:
            # Crop images to the smallest dimensions if they don't match
            images = self._crop_to_smallest_dimensions(images)

        # Merge the images
        min_width = images[0].getWidth()
        min_height = images[0].getHeight()
        stack = ImageStack(min_width, min_height)

        for img in images:
            ip = img.getProcessor()
            stack.addSlice(ip)

        imp = ImagePlus('', stack)
        merged_imp = ZProjector.run(imp, 'sum')
        titles = [img.getTitle() for img in images]
        merged_imp.setTitle('_'.join(titles) + '_merged')

        # Convert ImagePlus to DeviceImage
        return DeviceImage(title=merged_imp.getTitle(), img=merged_imp.getProcessor())

