from __future__ import print_function, division, absolute_import
import os
import re
import csv
from java.lang import System
from ij import IJ, ImagePlus
from HughesLabTools.Device import Device
from HughesLabTools.gui import VmoToolsGui, ImageTypeChangerGui
from HughesLabTools.DeviceImage import  DeviceImage
from HughesLabTools.VesselsImage import VesselImage
from HughesLabTools.TumorImage import TumorImage
from HughesLabTools.PerfusionImage import PerfusionImage

class DeviceManager:
    def __init__(self, rootDir="", numTypes=1, typeNames=None, typeColors=None, verbose=False, options=None):
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
        if formats is None:
            formats = ['tif', 'tiff']

        # Gather all image files
        image_files = []
        for root, dirs, files in os.walk(self.rootDir):
            # Process subdirectories based on the GUI options
            if not self.options.get('process_subdirectories', True):
                dirs[:] = []

            # Skip directories named 'colored' or 'merged'
            dirs[:] = [d for d in dirs if d not in ['colored', 'merged']]

            if self.options.get('process_subdirectories', True):
                self.log("Walking directory and subdirectories: {}".format(root))
            else:
                self.log("Walking directory: {}".format(root))

            image_files.extend(self._get_sorted_image_files(root, files, formats))

        # Determine the number of devices needed
        num_images = len(image_files)
        if num_images % self.numTypes != 0:
            self.log("Warning: The number of images is not a multiple of the number of types.")
            return

        num_devices = num_images // self.numTypes

        # Assign images to devices
        for device_idx in range(num_devices):
            device_name = "Device_{}".format(device_idx + 1)
            # Extract the directory from the first image for this device
            device_dir = os.path.dirname(image_files[device_idx * self.numTypes])
            self.add_device(device_name, device_dir, self.verbose)
            device = self.device_dict[device_name]

            # Assign the correct image to each type for this device
            for type_idx, img_type in enumerate(self.typeNames):
                img_index = device_idx * self.numTypes + type_idx
                if img_index < num_images:
                    img_file = image_files[img_index]
                    device.set_image_paths(image_type=img_type, image_path=img_file)

        self.log("Assigned images to {} devices.".format(num_devices))

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

    def run_selected_processes(self):
        """Run all selected processes based on the options configuration."""
        self.walk_directory_and_add_images()  # Always walk the directory

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
                grouped_files = [all_files[i:i+self.numTypes] for i in range(0, len(all_files), self.numTypes)]

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
            output_summary_dir = os.path.join(self.rootDir, 'Vessel_Analysis', 'Summary')
            if not os.path.exists(output_summary_dir):
                os.makedirs(output_summary_dir)
            self.create_new_summary_csv(output_summary_dir)


        # Process each device
        for device in self.devices:
            # Confirm image types
            if self.options.get('confirm_image_types'):
                    self.log("Confirming image types for device: {}".format(device.name))
                    changer = ImageTypeChangerGui(device)
                    changer.confirm_and_change_image_type()

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
                                print(segmented_image_path)

                                if os.path.exists(segmented_image_path):
                                    self.log("Using Weka segmented image: {}".format(segmented_image_path))
                                    # Create a new instance of device_image and vessel
                                    device_image = device._load_image(segmented_image_path, verbose=self.verbose)
                                    vessel = VesselImage.from_image_plus(device_image, verbose=self.verbose)
                                else:
                                    self.log("Warning: Segmented image not found. Using original image: {}".format(vessel_image_path))
                            else:
                                self.log("Warning: Vessel_Segmented folder not found. Using original image: {}".format(vessel_image_path))

                        # Measure Vessel Diameter
                        if self.options.get('meas_diam'):
                            self.log("Measuring vessel diameter for image: {}".format(vessel_image_path))
                            # Implement measurement logic here (if method is defined)
                            vessel.perform_vessel_analysis(options = self.options, summary_csv_path=self.summary_csv_path)
                            # vessel.measure_diameter()

                        if self.options.get('dxf_out'):
                            self.log("Running dxf for device: {}".format(device.name))
                            vessel.process_dxf(device_manager = self)

            # Run Tumor Image processing
            if self.options.get('segment') or self.options.get('tumor_weka') or self.options.get('meas_grey') or self.options.get('meas_circ'):
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
                        tumor = TumorImage(title=tumor_image.getTitle(), img=tumor_image.getProcessor())

                        # Segment Tumor Images
                        if self.options.get('segment'):
                            self.log("Segmenting tumor image: {}".format(tumor_image_path))
                            segmented_image = tumor.segment_tumor()
                            if self.options.get('show_segmented', False):
                                segmented_image.show()

                        # Segment the image
                        if self.options.get('tumor_weka'):
                            self.log("Segmenting tumor image: {}".format(tumor_image_path))
                            device_image.segment_image(self.options.get('tumor_weka_classifier'), 'Tumor_Segmented')

                        # change path if using the segmented tumor
                        if self.options.get('use_weka_segmentation_tumor'):
                            # Check if Vessel_Segmented folder is created
                            segmented_folder = os.path.join(os.path.dirname(tumor_image_path), 'Tumor_Segmented')
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

                        # Measure Tumor Grey Level
                        if self.options.get('meas_grey'):
                            self.log("Measuring tumor grey level for image: {}".format(tumor_image_path))
                            tumor.measure_tumor_gray()

                        # Measure Tumor Circularity
                        if self.options.get('meas_circ'):
                            self.log("Measuring tumor circularity for image: {}".format(tumor_image_path))
                            # Implement measurement logic here (if method is defined)
                            # tumor.measure_circularity()

        if self.options.get('permeability_calc'):
            self.log("Processing permeability images")
            self.process_permeability_images()

            # Garbage collection
            System.gc()

        self.log("Finished processing all devices.")

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

    def process_permeability_images(self):
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

        # Get the number of images per stack
        images_per_n = int(self.options.get('images_per_n_perm', 1))

        # Calculate the number of complete groups
        num_complete_groups = len(all_perfusion_images) // images_per_n

        self.log("Processing {} groups of {} images each".format(num_complete_groups, images_per_n))

        # Process only complete groups
        for i in range(num_complete_groups):
            start_index = i * images_per_n
            end_index = start_index + images_per_n
            group = all_perfusion_images[start_index:end_index]

            self.log("Processing group {} of {}".format(i+1, num_complete_groups))

            # Load the first image and create a PerfusionImage instance
            first_image_path = group[0]
            device_image = DeviceImage(image_path = first_image_path, verbose = self.verbose)
            device_image._lazy_load()
            perfusion_image = PerfusionImage.from_image_plus(device_image, verbose=self.verbose)

            # Perform perfusion analysis
            additional_image_paths = group[1:]
            perfusion_image.perform_permeability_analysis(self.options, additional_images=additional_image_paths, oval_radius=self.options['oval_rad'])

        # Log if there are any remaining images
        remaining_images = len(all_perfusion_images) % images_per_n
        if remaining_images > 0:
            self.log("Warning: {} image(s) left unprocessed".format(remaining_images))
