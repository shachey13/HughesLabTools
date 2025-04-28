from __future__ import print_function, division, absolute_import
import os
import re
import csv
from java.lang import System
from ij import IJ, ImagePlus
from ij.gui import GenericDialog
from HughesLabTools.Device import Device
from HughesLabTools.gui import VmoToolsGui, ImageTypeChangerGui
from HughesLabTools.DeviceImage import  DeviceImage
from HughesLabTools.VesselsImage import VesselImage
from HughesLabTools.TumorImage import TumorImage
from HughesLabTools.PerfusionImage import PerfusionImage

class DeviceManager:
    """
    Manages devices and their associated images for various image processing tasks.

    This class handles the configuration, processing, and analysis of multiple devices
    and their corresponding images. It provides methods for GUI configuration, directory
    walking, image processing, and various analysis tasks.
    """

    def __init__(self, rootDir="", numTypes=1, typeNames=None, typeColors=None, verbose=False, options=None):
        """
        Initialize a DeviceManager instance.

        Args:
            rootDir (str): Root directory for image processing.
            numTypes (int): Number of image types.
            typeNames (list): Names of image types.
            typeColors (list): Colors associated with image types.
            verbose (bool): Whether to print verbose logs.
            options (dict): Additional options for image processing.
        """
        # Default settings
        self.devices = []
        self.device_dict = {}
        self.options = options if options else {}

        # Initialize or update with provided parameters
        self.rootDir = os.path.abspath(rootDir) if rootDir else ""
        self.numTypes = numTypes
        self.typeNames = typeNames if typeNames else ["Type 1"]
        self.typeColors = typeColors if typeColors else ["Red"]
        self.verbose = verbose

    def configure_with_gui(self):
        """Method to display the GUI, collect options, and configure the DeviceManager."""
        vmo_gui = VmoToolsGui()
        configured = vmo_gui.show_gui(self)  # Pass the DeviceManager instance to configure it

        if configured is None:
            return None  # Return None if the GUI was canceled

        self._apply_gui_options()
        return self

    def _apply_gui_options(self):
        """Apply options from the GUI to the DeviceManager instance."""
        self.rootDir = self.options.get('rootDir', self.rootDir)
        self.numTypes = self.options.get('numTypes', self.numTypes)
        self.typeNames = self.options.get('typeNames', self.typeNames)
        self.typeColors = self.options.get('typeColors', self.typeColors)
        self.verbose = self.options.get('verbose', self.verbose)

    def log(self, message, level="INFO"):
        if level == "WARNING":
            print("WARNING: {}".format(message))
        elif self.verbose and level == "INFO":
            print("INFO: {}".format(message))

    def add_device(self, device_name, device_dir, verbose=False):
        device = Device(typeNames=self.typeNames, name=device_name, deviceDir=device_dir, verbose=verbose)
        self.devices.append(device)
        self.device_dict[device_name] = device
        self.log("Added device: {}".format(device_name))

    def print_info(self):
        """Dynamically prints all relevant attributes of the DeviceManager and its devices."""

        def format_value(value):
            """Helper function to format the value for printing."""
            if isinstance(value, bool):
                return 'true' if value else 'false'
            return value

        def print_dict(dictionary, indent=4):
            """Helper function to print a dictionary with proper indentation."""
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    print(" " * indent + "{}:".format(key))
                    print_dict(value, indent + 2)
                elif isinstance(value, list):
                    if all(isinstance(item, str) for item in value):
                        print(" " * indent + "{}: [{}]".format(key, ", ".join(value)))
                    else:
                        print(" " * indent + "{}: {}".format(key, value))
                else:
                    print(" " * indent + "{}: {}".format(key, format_value(value)))

        # Print DeviceManager attributes
        print("DeviceManager Information:")
        device_manager_attributes = {
            'rootDir': self.rootDir,
            'numTypes': self.numTypes,
            'typeNames': self.typeNames,
            'typeColors': self.typeColors,
            'verbose': format_value(self.verbose)
        }
        print_dict(device_manager_attributes, indent=2)

        # Print Devices information
        print("Devices Count: {}".format(len(self.devices)))
        if self.devices:
            print("Devices Information:")
            for device in self.devices:
                print("  Device Name: {}".format(device.name))
                device_info = {
                    'deviceDir': device.get_deviceDir(),
                    'typeNames': device.get_typeNames(),
                    'image_paths': device.get_image_paths(),
                    'colored_image_paths': device.get_colored_image_paths()
                }
                print_dict(device_info, indent=4)
        else:
            print("No devices found.")

        # Print Options
        print("Options:")
        print_dict(self.options, indent=2)

    def walk_directory_and_add_images(self, formats=None):
        """
         Walk through the root directory, identify image files, and add them to devices.

         Args:
             formats (list): List of image file formats to consider (default: ['tif', 'tiff']).
         """

        if formats is None:
            formats = ['tif', 'tiff', 'png']

        # Gather all image files
        image_files = []
        for root, dirs, files in os.walk(self.rootDir):
            # Process subdirectories based on the GUI options
            if not self.options.get('process_subdirectories', True):
                dirs[:] = []

            # Skip directories named 'colored' or 'merged'
            skip_dirs = [
                'crop',                   # Output from cropping
                'Vessel_Thresholded'      # Output from vessel thresholding
                'Vessel_Segmented',       # Output from vessel segmentation
                'Vessel_Analysis',        # Output from vessel analysis
                'DXF',                    # Output DXF files
                'Tumor_Segmented',        # Output from tumor segmentation
                'Tumor_Segmented_Weka'    # Output from tumor segmentation with Weka
                'subtracted',             # Background subtracted images
                'measure_gray',           # Tumor gray level measurements
                'circularity',            # Tumor circularity measurements
                'merged',                 # Merged images
                'colored',                # Colored images
                'Summary',                # Summary CSV files
                'perfusion',              # Perfusion analysis outputs
                'permeability',           # Permeability analysis outputs
                ''
            ]

            dirs[:] = [d for d in dirs if d not in skip_dirs]

            if self.options.get('process_subdirectories', True):
                self.log("Walking directory and subdirectories: {}".format(root))
            else:
                self.log("Walking directory: {}".format(root))

            image_files.extend(self._get_sorted_image_files(root, files, formats))

        # Determine the number of devices needed
        num_images = len(image_files)
        perfusion_type_index = self.typeNames.index('Perfusion') if 'Perfusion' in self.typeNames else -1
        print(perfusion_type_index)

        if perfusion_type_index != -1:
            # Perfusion is one of the image types, so we need to determine images_per_perfusion_sequence
            images_per_n = self.options.get('images_per_n')
            images_per_n_perm = self.options.get('images_per_n_perm')

            if images_per_n is not None and images_per_n_perm is not None:
                if images_per_n != images_per_n_perm:
                    self.log("Warning: 'images_per_n' and 'images_per_n_perm' are different. Using 'images_per_n_perm' for perfusion images.")
                images_per_perfusion_sequence = int(images_per_n_perm)
            elif images_per_n is not None:
                images_per_perfusion_sequence = int(images_per_n)
            elif images_per_n_perm is not None:
                images_per_perfusion_sequence = int(images_per_n_perm)
            else:
                self.log("Error: 'images_per_n' or 'images_per_n_perm' must be set when processing perfusion images.")
                images_per_perfusion_sequence = 1
                #return

            print("Number of images per perfusion sequence:", images_per_perfusion_sequence)
        else:
            # No perfusion images, so we don't need images_per_perfusion_sequence
            images_per_perfusion_sequence = None

        # Calculate images per device
        if perfusion_type_index != -1:
            images_per_device = images_per_perfusion_sequence + len(self.typeNames) - 1
        else:
            images_per_device = len(self.typeNames)
        self.images_per_device = images_per_device

        print("Number of images per device:", images_per_device)

        print("number of device types:", self.numTypes)

        # Improved warning message
        if num_images % images_per_device != 0:
            self.log("Warning: The number of images ({}) is not a multiple of images per device ({}).".format(
                num_images, images_per_device))
            self.log("Some images may be left unprocessed.")

        # Check if there are enough images to create at least one device
        num_devices = int(num_images // images_per_device)
        if num_devices == 0:
            self.log("Error: Not enough images to create a single device.")
            return

        # Assign images to devices
        for device_idx in range(num_devices):
            device_name = "Device_{}".format(device_idx + 1)
            start_index = device_idx * images_per_device  # NEW LINE
            # Extract the directory from the first image for this device
            device_dir = os.path.dirname(image_files[start_index])
            self.add_device(device_name, device_dir, self.verbose)
            device = self.device_dict[device_name]

            # Assign the correct images to each type for this device
            current_index = start_index
            for type_idx, type_name in enumerate(self.typeNames):
                if type_idx == perfusion_type_index:
                    end_index = current_index + images_per_perfusion_sequence
                    type_images = image_files[current_index:end_index]
                else:
                    end_index = current_index + 1
                    type_images = [image_files[current_index]]

                device.set_image_paths(image_type=type_name, image_path=type_images)

                current_index = end_index

        self.log("Assigned images to {} devices.".format(num_devices))

        # Log any remaining images
        remaining_images = num_images % images_per_device
        if remaining_images > 0:
            self.log("Warning: {} image(s) left unprocessed.".format(remaining_images))

    def _get_sorted_image_files(self, root, files, formats):
        image_files = [os.path.join(root, file) for file in files if self._is_valid_format(file, formats) and not file.startswith('.')]
        image_files = sorted(image_files, key=self._natural_sort_key)
        return image_files

    @staticmethod
    def _natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', s)]

    @staticmethod
    def _is_valid_format(file_name, formats):
        ext = file_name.split('.')[-1].lower()
        return ext in formats

    def get_output_directory_vessel(self):
        return self._get_output_directory(['crop', 'Vessel_Segmented', 'Vessel_Thresholded'])

    def get_output_directory_tumor(self):
        return self._get_output_directory(['crop', 'Tumor_Segmented_Weka', 'subtracted'])

    def _get_output_directory(self, possible_subdirs):
        current_path = self.rootDir
        subdirs = []

        for subdir in possible_subdirs:
            if self._should_add_subdir(subdir):
                current_path, subdirs = self._check_and_add_subdir(current_path, subdirs, subdir)

        output_dir = os.path.join(current_path, *subdirs)
        return output_dir

    def _should_add_subdir(self, subdir):
        if subdir == 'crop':
            return self.options.get('use_crop')
        elif subdir == 'Vessel_Segmented':
            return self.options.get('use_weka_segmentation_vessel')
        elif subdir == 'Vessel_Thresholded':
            return self.options.get('use_vessel_thresholded')
        elif subdir == 'Tumor_Segmented_Weka':
            return self.options.get('use_weka_segmentation_tumor')
        elif subdir == 'subtracted':
            return self.options.get('subtract_background')
        return False

    def _check_and_add_subdir(self, current_path, subdirs, subdir):
        if subdir not in os.path.normpath(current_path).split(os.sep):
            if os.path.exists(os.path.join(current_path, subdir)):
                current_path = os.path.join(current_path, subdir)
            else:
                subdirs.append(subdir)
        return current_path, subdirs

    def run_selected_processes(self):
        """
         Run all selected image processing tasks based on the current configuration.

         This method orchestrates the execution of various image processing tasks including
         cropping, coloring, merging, vessel analysis, tumor analysis, and perfusion analysis.
         """
        self.walk_directory_and_add_images()  # Always walk the directory
        print("Options:", self.options)

        # Confirm image types first
        if self.options.get('confirm_image_types'):
            for device in self.devices:
                self.log("Confirming image types for device: {}".format(device.name))
                changer = ImageTypeChangerGui(device)
                changer.confirm_and_change_image_type()

        # if cropping is selected, running cropping before anything else
        # it is faster to run cropping all at once than during each step of a loop
        if self.options.get('crop'):
            """
            Crop images based on the specified crop type.
            
            :param crop_type: String, one of 'individual', 'batch', or 'grouped'
            """
            if self.options.get('crop_type') not in ['individual', 'batch', 'grouped']:
                raise ValueError("Invalid crop type. Must be 'individual', 'batch', or 'grouped'")

            if self.options.get('crop_type') == 'batch':
                # For batch cropping, we only need to crop one image and apply to all
                first_device = self.devices[0]
                first_image_path = list(first_device.get_image_paths().values())[0]
                if isinstance(first_image_path, list):
                    first_image_path = first_image_path[0]
                first_image = DeviceImage(image_path=first_image_path, verbose=self.verbose)
                coordinates = first_image.crop_image(crop_type='batch', is_first=True)

                # Apply the same crop to all other images
                for device in self.devices:
                    for image_paths in device.get_image_paths().values():
                        if not isinstance(image_paths, list):
                            image_paths = [image_paths]
                        for image_path in image_paths:
                            if image_path != first_image_path:  # Skip the first image as it's already cropped
                                image = DeviceImage(image_path=image_path, verbose=self.verbose)
                                image.crop_image(crop_type='batch', is_first=False, coordinates=coordinates)

            elif self.options.get('crop_type') == 'grouped':
                # Get all files in the directory
                all_files = []
                for device in self.devices:
                    for image_paths in device.get_image_paths().values():
                        if isinstance(image_paths, list):
                            all_files.extend(image_paths)
                        else:
                            all_files.append(image_paths)

                # Group the files
                grouped_files = [all_files[i:i+self.images_per_device] for i in range(0, len(all_files), self.images_per_device)]

                for group in grouped_files:
                    # Crop the first file in the group and get the coordinates
                    first_image = DeviceImage(image_path=group[0], verbose=self.verbose)
                    coordinates = first_image.crop_image(crop_type='grouped', is_first=True)

                    # Crop the remaining files in the group using the coordinates from the first one
                    for file_path in group[1:]:
                        image = DeviceImage(image_path=file_path, verbose=self.verbose)
                        image.crop_image(crop_type='grouped', is_first=False, coordinates=coordinates)

            else:  # individual cropping
                for device in self.devices:
                    for image_paths in device.get_image_paths().values():
                        if not isinstance(image_paths, list):
                            image_paths = [image_paths]
                        for image_path in image_paths:
                            image = DeviceImage(image_path=image_path, verbose=self.verbose)
                            image.crop_image(crop_type='individual')

        # change directory to use cropped if selected
        if self.options.get('use_crop'):
            # Update the root directory to the 'crop' folder
            self.rootDir = os.path.join(self.rootDir, 'crop')

            # Clear existing devices and their image paths
            self.devices = []
            self.device_dict = {}

            # Re-run walk_directory_and_add_images with the new root directory
            self.walk_directory_and_add_images()

        # check if diameter measurements are to be run and create csv
        if self.options.get('meas_diam'):
            output_dir = self.get_output_directory_vessel()
            if self.options.get('use_vessel_weka_segmentation'):
                output_summary_dir = os.path.join(output_dir, 'Vessel_Segmented', 'Vessel_Analysis', 'Summary')
            elif self.options.get('use_vessel_threshold'):
                output_summary_dir = os.path.join(output_dir, 'Vessel_Thresholded', 'Vessel_Analysis', 'Summary')
            else:
                output_summary_dir = os.path.join(output_dir, 'Vessel_Analysis', 'Summary')
            if not os.path.exists(output_summary_dir):
                os.makedirs(output_summary_dir)
            self.create_new_summary_csv(output_summary_dir)

        # check if circiluarity is selected and create csv
        if self.options.get('meas_circ'):
            output_dir = self.get_output_directory_tumor()
            output_summary_circ_dir = os.path.join(output_dir, 'circularity')
            if not os.path.exists(output_summary_circ_dir):
                os.makedirs(output_summary_circ_dir)
            self.create_new_summary_circ_csv(output_summary_circ_dir)

        # check if tumor gray is selected and create csv
        if self.options.get('meas_grey'):
            output_dir = self.get_output_directory_tumor()
            output_summary_gray_dir = os.path.join(output_dir, 'measure_gray')
            if not os.path.exists(output_summary_gray_dir):
                os.makedirs(output_summary_gray_dir)
            self.create_new_summary_gray_csv(output_summary_gray_dir)

        # Process each device
        for device in self.devices:

            # Apply color to images
            if self.options.get("color"):
                    self.log("Applying color to device: {}".format(device.name))
                    device.apply_color_to_images(self.typeColors, self.options.get("sat", 0.3), self.options.get('show_colored', False))

            # Merge images
            if self.options.get("merge"):
                    self.log("Merging images for device: {}".format(device.name))
                    device.merge_images(self.options.get('show_merged', False))

            # Run Vessel Image processing
            if self.options.get('threshold') or self.options.get('vessel_weka') or  self.options.get('meas_diam') or self.options.get('dxf_out'):
                self.log("Processing vessel images for device: {}".format(device.name))
                vessel_image_paths = device.get_image_paths('Vessels')

                if self.options.get('vessel_weka'):
                    device_image = device._load_image(vessel_image_paths[0])
                    device_image.prepare_for_segmentation()

                if vessel_image_paths:
                    vessel_image_paths = vessel_image_paths if isinstance(vessel_image_paths, list) else [vessel_image_paths]
                    for vessel_image_path in vessel_image_paths:
                        self.log("Processing vessel image: {}".format(vessel_image_path))

                        # Load the image and create a VesselImage instance
                        device_image = device._load_image(vessel_image_path, verbose=self.verbose)
                        vessel = VesselImage.from_image_plus(device_image, verbose=self.verbose)

                        # Threshold Vessel Images
                        if self.options.get('threshold'):
                            self.log("Thresholding vessel image: {}".format(vessel_image_path))
                            thresholded_image = vessel.threshold_and_mask(self)
                            if self.options.get('show_threshold', False):
                                thresholded_image.show()

                        # Use thresholded image if option is selected
                        if self.options.get('use_vessel_threshold'):
                            # Check if Vessel_Thresholded folder is created
                            thresholded_folder = os.path.join(os.path.dirname(vessel_image_path), 'Vessel_Thresholded')
                            if os.path.exists(thresholded_folder):
                                # Find the corresponding thresholded image
                                original_filename = os.path.basename(vessel_image_path)
                                thresholded_filename = os.path.splitext(original_filename)[0] + "_thresholded.tif"
                                thresholded_image_path = os.path.join(thresholded_folder, thresholded_filename)

                                if os.path.exists(thresholded_image_path):
                                    self.log("Using thresholded image: {}".format(thresholded_image_path))
                                    # Create a new instance of device_image and vessel
                                    device_image = device._load_image(thresholded_image_path, verbose=self.verbose)
                                    vessel = VesselImage.from_image_plus(device_image, verbose=self.verbose)
                                else:
                                    self.log("Warning: Thresholded image not found. Using original image: {}".format(vessel_image_path))
                            else:
                                self.log("Warning: Vessel_Thresholded folder not found. Using original image: {}".format(vessel_image_path))

                        # Segment the image
                        if self.options.get('vessel_weka'):
                            self.log("Segmenting vessel image: {}".format(vessel_image_path))
                            device_image.segment_image(self.options.get('vessel_weka_classifier'), 'Vessel_Segmented')

                        if self.options.get('use_weka_segmentation_vessels'):
                            # Check if Vessel_Segmented folder is created
                            segmented_folder = os.path.join(os.path.dirname(vessel_image_path), 'Vessel_Segmented')
                            if os.path.exists(segmented_folder):
                                # Find the corresponding segmented image
                                original_filename = os.path.basename(vessel_image_path)
                                segmented_filename = os.path.splitext(original_filename)[0] + "-Segment.tif"
                                segmented_image_path = os.path.join(segmented_folder, segmented_filename)
                                #print(segmented_image_path)

                                if os.path.exists(segmented_image_path):
                                    self.log("Using Weka segmented image: {}".format(segmented_image_path))
                                    # Create a new instance of device_image and vessel
                                    device_image = device._load_image(segmented_image_path, verbose=self.verbose)
                                    vessel = VesselImage.from_image_plus(device_image, verbose=self.verbose)
                                else:
                                    self.log("Warning: Segmented image not found. Using original image: {}".format(vessel_image_path))
                            else:
                                self.log("Warning: Vessel_Segmented folder not found. Using original image: {}".format(vessel_image_path))

                        # ensure proper file format before running downstream process
                        if not vessel._check_image_thresholded():
                            self.log("Warning: Image {} is not thresholded. Skipping vessel analysis and DXF processing.".format(vessel_image_path))
                            continue

                        # Measure Vessel Diameter
                        if self.options.get('meas_diam'):
                            self.log("Measuring vessel diameter for image: {}".format(vessel_image_path))
                            # Implement measurement logic here (if method is defined)
                            vessel.perform_vessel_analysis(options = self.options, summary_csv_path=self.summary_csv_path)

                        if self.options.get('dxf_out'):
                            self.log("Running dxf for device: {}".format(device.name))
                            vessel.process_dxf(device_manager = self)

            # Run Tumor Image processing
            if self.options.get('segment') or self.options.get('tumor_weka') or self.options.get('meas_grey') or self.options.get('meas_circ') or self.options.get('subtract_background'):
                self.log("Processing tumor images for device: {}".format(device.name))
                tumor_image_paths = device.get_image_paths('Tumor')

                if self.options.get('tumor_weka'):
                    device_image = device._load_image(tumor_image_paths[0])
                    device_image.prepare_for_segmentation()

                if tumor_image_paths:
                    tumor_image_paths = tumor_image_paths if isinstance(tumor_image_paths, list) else [tumor_image_paths]
                    for tumor_image_path in tumor_image_paths:
                        self.log("Processing tumor image: {}".format(tumor_image_path))
                        # Load the tumor image
                        tumor_image = device._load_image(tumor_image_path, verbose=self.verbose)
                        # Create a TumorImage instance
                        tumor = TumorImage.from_image_plus(tumor_image, verbose = self.verbose)

                        # Segment Tumor Images
                        if self.options.get('segment'):
                            self.log("Segmenting tumor image: {}".format(tumor_image_path))
                            segmented_image = tumor.segment_tumor()
                            if self.options.get('show_segmented', False):
                                segmented_image.show()

                        # Segment the image
                        if self.options.get('tumor_weka'):
                            self.log("Segmenting tumor image: {}".format(tumor_image_path))
                            device_image.segment_image(self.options.get('tumor_weka_classifier'), 'Tumor_Segmented_Weka')

                        # change path if using the segmented tumor
                        if self.options.get('use_weka_segmentation_tumor'):
                            # Check if Vessel_Segmented folder is created
                            segmented_folder = os.path.join(os.path.dirname(tumor_image_path), 'Tumor_Segmented_Weka')
                            if os.path.exists(segmented_folder):
                                # Find the corresponding segmented image
                                original_filename = os.path.basename(tumor_image_path)
                                segmented_filename = os.path.splitext(original_filename)[0] + "-Segment.tif"
                                segmented_image_path = os.path.join(segmented_folder, segmented_filename)
                                print(segmented_image_path)

                                if os.path.exists(segmented_image_path):
                                    self.log("Using Weka segmented image: {}".format(segmented_image_path))
                                    # Create a new instance of device_image and vessel
                                    tumor_image = device._load_image(segmented_image_path, verbose=self.verbose)
                                    tumor = TumorImage(title=tumor_image.getTitle(), img=tumor_image.getProcessor())
                                else:
                                    self.log("Warning: Segmented image not found. Using original image: {}".format(tumor_image_path))
                            else:
                                self.log("Warning: Vessel_Segmented folder not found. Using original image: {}".format(tumor_image_path))

                        # subtract background
                        if self.options.get('subtract_background'):
                            self.log("Subtracting tumor background for image: {}".format(tumor_image_path))
                            tumor.subtract_background(radius=self.options.get('rolling_radius'))

                            # use subtracted images downstream
                            subtacted_folder = os.path.join(os.path.dirname(tumor_image_path), 'subtracted')
                            if os.path.exists(subtacted_folder):
                                # Find the corresponding segmented image
                                original_filename = os.path.basename(tumor_image_path)
                                subtacted_filename = os.path.splitext(original_filename)[0] + "_subtracted.tif"
                                subtacted_image_path = os.path.join(subtacted_folder, subtacted_filename)

                                if os.path.exists(subtacted_image_path):
                                    self.log("Using background subtracted image: {}".format(subtacted_image_path))
                                    # Create a new instance of device_image and vessel
                                    tumor_image_path = subtacted_image_path
                                    tumor_image = device._load_image(subtacted_image_path, verbose=self.verbose)
                                    tumor = TumorImage.from_image_plus(tumor_image, verbose = self.verbose)
                                else:
                                    self.log("Warning: Segmented image not found. Using original image: {}".format(tumor_image_path))
                            else:
                                self.log("Warning: Vessel_Segmented folder not found. Using original image: {}".format(tumor_image_path))

                        # Measure Tumor Grey Level
                        if self.options.get('meas_grey'):
                            self.log("Measuring tumor grey level for image: {}".format(tumor_image_path))
                            tumor.measure_tumor_gray(self.summary_csv_gray_path)

                        # Measure Tumor Circularity
                        if self.options.get('meas_circ'):
                            self.log("Measuring tumor circularity for image: {}".format(tumor_image_path))
                            tumor.measure_circularity(bp = self.options.get('circ_bp'), st = self.options.get('circ_st'), lt = self.options.get('circ_lt'), summary_csv_path = self.summary_csv_circ_path)

        if self.options.get('permeability_calc') or self.options.get('perfusion_calc'):
            self.log("Processing perfusion images")
            self.process_perfusion_images()

        self.log("Finished processing all devices.")

        # Create and show the completion dialog
        gd = GenericDialog("Processing Complete")
        gd.addMessage("Finished processing all devices. Good luck with your science!")
        gd.showDialog()

    def create_new_summary_circ_csv(self, output_summary_dir):
        """
        Create a new CSV file.
        """
        #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.summary_csv_circ_path = os.path.join(output_summary_dir, "quantification_summary_circ.csv")

        # Create an empty file with headers
        with open(self.summary_csv_circ_path, 'wb') as f:
            writer = csv.writer(f)
            # You may need to adjust these headers based on your summary table structure
            headers = ["Filename","Particle Count",  "Average Area",  "Average %Area", "Average Perim", "Average Circularity", "Average Solidity"]
            writer.writerow(headers)

        return self.summary_csv_circ_path

    def create_new_summary_gray_csv(self, output_summary_dir):
        """
        Create a new CSV file.
        """
        #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.summary_csv_gray_path = os.path.join(output_summary_dir, "quantification_summary_gray.csv")

        # Create an empty file with headers
        with open(self.summary_csv_gray_path, 'wb') as f:
            writer = csv.writer(f)
            # You may need to adjust these headers based on your summary table structure
            headers = ["Filename", "Mean Gray Value", "Standard Deviation", "Mode", "Min", "Max", "Integrated Density", "Raw Integrated Density", "Min Threshold", "Max Threshold"]
            writer.writerow(headers)

        return self.summary_csv_gray_path

    def create_new_summary_csv(self, output_summary_dir):
        """
        Create a new CSV file.
        """
        #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.summary_csv_path = os.path.join(output_summary_dir, "quantification_summary.csv")

        # Create an empty file with headers
        with open(self.summary_csv_path, 'wb') as f:
            writer = csv.writer(f)
            # You may need to adjust these headers based on your summary table structure
            headers = ["Filename", "No. Branch points", "No. segments", "Mean Radius",
                       "Vessel Area", "Vessel Perimeter", "Perivascular Area",
                       "Perivascular Perimeter", "Average branch radius"]
            writer.writerow(headers)

        return self.summary_csv_path

    def apply_weka_segmentation(self, image_paths, analysis_type):
        """
        Apply Weka segmentation to all images in the group if the option is selected.

        :param image_paths: list of str, paths to the original images
        :param analysis_type: str, either 'permeability' or 'perfusion'
        :return: list of str, paths to segmented images (or original if not segmented)
        """
        segment_option = self.options.get('{}_segment'.format(analysis_type))
        weka_classifier = self.options.get('{}_weka_classifier'.format(analysis_type))

        segmented_image_paths = []

        if segment_option and weka_classifier:
            self.log("Applying Weka segmentation to {} images".format(analysis_type))
            for image_path in image_paths:
                device_image = DeviceImage(image_path=image_path, verbose=self.verbose)
                device_image._lazy_load()
                device_image.segment_image(weka_classifier, '{}_Segmented'.format(analysis_type.capitalize()))

                # Use the segmented image
                segmented_folder = os.path.join(os.path.dirname(image_path), '{}_Segmented'.format(analysis_type.capitalize()))
                original_filename = os.path.basename(image_path)
                segmented_filename = os.path.splitext(original_filename)[0] + "-Segment.tif"
                segmented_image_path = os.path.join(segmented_folder, segmented_filename)

                if os.path.exists(segmented_image_path):
                    self.log("Using Weka segmented image: {}".format(segmented_image_path))
                    segmented_image_paths.append(segmented_image_path)
                else:
                    self.log("Warning: Segmented image not found. Using original image.")
                    segmented_image_paths.append(image_path)
        else:
            segmented_image_paths = image_paths

        return segmented_image_paths

    def process_image_group(self, group, analysis_type):
        """
        Process a group of images for a specific analysis type.

        :param group: list of image paths in the group
        :param analysis_type: str, either 'permeability' or 'perfusion'
        """
        self.log("Processing group for {} analysis".format(analysis_type))

        # Apply Weka segmentation if option is selected
        segmented_image_paths = self.apply_weka_segmentation(group, analysis_type)

        # Use the first segmented image to create the PerfusionImage instance
        first_image = DeviceImage(image_path=segmented_image_paths[0], verbose=self.verbose)
        first_image._lazy_load()
        perfusion_image = PerfusionImage.from_image_plus(first_image, verbose=self.verbose)

        # Perform analysis based on the analysis type
        if analysis_type == 'permeability':
            self.log("Performing permeability analysis")
            perfusion_image.perform_permeability_analysis(self.options, additional_images=segmented_image_paths[1:], oval_radius=self.options.get('oval_rad'))
        elif analysis_type == 'perfusion':
            self.log("Performing regular perfusion analysis")
            print(segmented_image_paths)
            perfusion_image.perform_perfusion_analysis(self.options, additional_images=segmented_image_paths)

    def process_perfusion_images(self):
        """
        Process perfusion images for both permeability and perfusion analyses if selected.
        """
        all_perfusion_images = []
        for device in self.devices:
            perfusion_image_paths = device.get_image_paths('Perfusion')
            if perfusion_image_paths:
                if isinstance(perfusion_image_paths, list):
                    all_perfusion_images.extend(perfusion_image_paths)
                else:
                    all_perfusion_images.append(perfusion_image_paths)

        if not all_perfusion_images:
            self.log("No perfusion images found.")
            return

        # Prepare for segmentation if needed
        if self.options.get('permeability_segment') or self.options.get('perfusion_segment'):
            device_image = DeviceImage(image_path=all_perfusion_images[0], verbose=self.verbose)
            device_image.prepare_for_segmentation()

        # Get the number of images per stack
        #images_per_n = int(self.options.get('images_per_n_perm', 1))
        images_per_n = self.options.get('images_per_n')
        images_per_n_perm = self.options.get('images_per_n_perm')

        if images_per_n is not None and images_per_n_perm is not None:
            if images_per_n != images_per_n_perm:
                self.log("Warning: 'images_per_n' and 'images_per_n_perm' are different. Using 'images_per_n_perm' for perfusion images.")
                images_per_perfusion_sequence = int(images_per_n_perm)
        elif images_per_n is not None:
            images_per_perfusion_sequence = int(images_per_n)
        elif images_per_n_perm is not None:
            images_per_perfusion_sequence = int(images_per_n_perm)
        else:
            self.log("Error: 'images_per_n' or 'images_per_n_perm' must be set when processing perfusion images.")
            return
        # Calculate the number of complete groups
        num_complete_groups = len(all_perfusion_images) // images_per_perfusion_sequence

        self.log("Processing {} groups of {} images each".format(num_complete_groups, images_per_perfusion_sequence))

        for i in range(num_complete_groups):
            start_index = i * images_per_perfusion_sequence
            end_index = start_index + images_per_perfusion_sequence
            group = all_perfusion_images[start_index:end_index]

            self.log("Processing group {} of {}".format(i+1, num_complete_groups))

            if self.options.get('permeability_calc'):
                self.process_image_group(group, 'permeability')

            if self.options.get('perfusion_calc'):
                self.process_image_group(group, 'perfusion')

        # Log if there are any remaining images
        remaining_images = len(all_perfusion_images) % images_per_perfusion_sequence
        if remaining_images > 0:
            self.log("Warning: {} image(s) left unprocessed".format(remaining_images))
