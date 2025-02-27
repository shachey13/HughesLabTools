from __future__ import print_function, division, absolute_import
from ij import IJ, gui
from ij.gui import GenericDialog
from ij.io import OpenDialog
from java.awt import Panel, GridBagLayout, GridBagConstraints, Insets, Dimension, BorderLayout, GridLayout, Label, Choice, TextField, FlowLayout, Checkbox
from javax.swing import JLabel, JCheckBox, JTextField, JPanel

class VmoToolsGui:
    """
    A GUI class for collecting user input to configure and run VMO tools.

    Attributes:
        options (dict): A dictionary storing various operational options selected by the user.
        num_types (int): The number of image types selected by the user.
    """

    def __init__(self):
        """Initializes an empty options dictionary and sets num_types to None."""
        self.options = {
            'use_weka_segmentation_vessels': False,
            'use_weka_segmentation_tumor': False
        }
        self.num_types = None
        self.type_names = []
        self.type_colors = []

    def show_gui(self, device_manager=None):
        """
        Displays the GUI to collect options and configure the DeviceManager.

        Args:
            device_manager (DeviceManager, optional): An instance of DeviceManager to configure. Defaults to None.

        Returns:
            dict or DeviceManager: Returns the options dictionary if device_manager is not provided;
                                   otherwise, returns the configured DeviceManager instance.
        """
        if not self._collect_function_options():
            return None

        if not self._collect_number_of_image_types():
            return None

        if not self._collect_additional_options():
            return None

        if not self._collect_root_directory():
            return None  # Stop if the user cancels the directory selection

        # Add this new step for Weka file selection after root directory selection
        if self.options.get('tumor_weka', False) and self.options.get('use_weka_segmentation', False):
            od = OpenDialog("Select Weka classifier file for tumor segmentation", None)
            weka_file = od.getPath()
            if weka_file:
                self.options['tumor_weka_classifier'] = weka_file
                IJ.log("Weka classifier file selected: " + weka_file)
            else:
                IJ.log("No Weka classifier file selected. Weka segmentation will be skipped.")
                self.options['use_weka_segmentation'] = False

        # Add this new step for Weka file selection after root directory selection
        if self.options.get('vessel_weka', False) and self.options.get('use_vessel_weka_segmentation', False):
            od = OpenDialog("Select Weka classifier file for Vessel segmentation", None)
            weka_file = od.getPath()
            if weka_file:
                self.options['vessel_weka_classifier'] = weka_file
                IJ.log("Vessel Weka classifier file selected: " + weka_file)
            else:
                IJ.log("No Weka classifier file selected. Weka segmentation will be skipped.")
                self.options['use_vessel_weka_segmentation'] = False

        # run perfusion Weka file selection if needed
        if self.options.get('perfusion_segment', False):
            od = OpenDialog("Select Weka classifier file for perfusion segmentation", None)
            weka_file = od.getPath()
            if weka_file:
                self.options['perfusion_weka_classifier'] = weka_file
                IJ.log("Perfusion Weka classifier file selected: " + weka_file)
            else:
                IJ.log("No Weka classifier file selected. Weka segmentation will be skipped.")
                self.options['perfusion_segment'] = False

        # run permeability Weka file selection if needed
        if self.options.get('permeability_segment', False):
            od = OpenDialog("Select Weka classifier file for perfusion segmentation", None)
            weka_file = od.getPath()
            if weka_file:
                self.options['permeability_weka_classifier'] = weka_file
                IJ.log("Permeability Weka classifier file selected: " + weka_file)
            else:
                IJ.log("No Weka classifier file selected. Weka segmentation will be skipped.")
                self.options['permeability_segment'] = False


        if device_manager:
            # Configure the device manager with numTypes, typeNames, and typeColors as attributes
            self._configure_device_manager(device_manager)
            return device_manager

        # Store numTypes, typeNames, and typeColors in the options dictionary
        self.options['numTypes'] = self.num_types
        self.options['typeNames'] = self.type_names
        self.options['typeColors'] = self.type_colors

        return self.options

    def _collect_function_options(self):
        """
        Collects the main function options from the user through a dialog.

        Returns:
            bool: True if the dialog is not canceled, False otherwise.
        """
        dialog = gui.GenericDialog('Run VMO Tools')
        radio_buttons = ['Color and Merge Images', 'Color Images', 'No Coloring']
        dialog.addRadioButtonGroup('Image Coloring Tools:', radio_buttons, 3, 1, radio_buttons[0])

        # Cropping section
        dialog.setInsets(15, 10, 0)
        dialog.addMessage('Cropping Tools:')
        cropping_checkbox_label = ['Crop Images']
        dialog.addCheckboxGroup(1, 1, cropping_checkbox_label, [False])

        dialog.setInsets(15, 10, 0)
        dialog.addMessage('Tumor Image Tools:')
        tumor_checkbox_labels = ['Segment Tumor Images', 'Segment Tumor Weka', 'Subtract Background', 'Measure Tumor Grey Level', 'Measure Tumor Circularity']
        dialog.addCheckboxGroup(5, 1, tumor_checkbox_labels, [False] * 5)

        dialog.setInsets(15, 10, 0)
        dialog.addMessage('Vessel Image Tools:')
        vessel_checkbox_labels = ['Threshold Vessel Images', 'Segment Vessel Weka', 'Measure Vessel Diameter', 'Trace and export as .DXF']
        dialog.addCheckboxGroup(4, 1, vessel_checkbox_labels, [False] * 4)

        dialog.setInsets(15, 10, 0)
        dialog.addMessage('Perfusion Image Tools:')
        perfusion_checkbox_labels = ['Perfusion Calculation', 'Permeability Calculation']
        dialog.addCheckboxGroup(2, 1, perfusion_checkbox_labels, [False] * 2)

        dialog.setOKLabel('Next ...')
        dialog.showDialog()

        if dialog.wasCanceled():
            return False

        self._parse_function_options(dialog, radio_buttons)
        return True

    def _parse_function_options(self, dialog, radio_buttons):
        """
        Parses the function options selected by the user and stores them in the options dictionary.

        Args:
            dialog (GenericDialog): The dialog instance containing user selections.
            radio_buttons (list): A list of radio button labels for image coloring options.
        """
        selected_option = dialog.getNextRadioButton()
        self.options['color'], self.options['merge'] = self._parse_color_merge_option(selected_option, radio_buttons)
        self.options['crop'] = dialog.getNextBoolean()
        self.options['segment'] = dialog.getNextBoolean()
        self.options['tumor_weka'] = dialog.getNextBoolean()
        self.options['subtract_background'] = dialog.getNextBoolean()
        self.options['meas_grey'] = dialog.getNextBoolean()
        self.options['meas_circ'] = dialog.getNextBoolean()
        self.options['threshold'] = dialog.getNextBoolean()
        self.options['vessel_weka'] = dialog.getNextBoolean()
        self.options['meas_diam'] = dialog.getNextBoolean()
        self.options['dxf_out'] = dialog.getNextBoolean()
        self.options['perfusion_calc'] = dialog.getNextBoolean()
        self.options['permeability_calc'] = dialog.getNextBoolean()

    def _parse_color_merge_option(self, selected_option, radio_buttons):
        """
        Helper function to parse the color and merge options.

        Args:
            selected_option (str): The selected radio button option.
            radio_buttons (list): A list of radio button labels for image coloring options.

        Returns:
            tuple: A tuple containing two booleans, indicating whether to color and merge images.
        """
        if selected_option == radio_buttons[0]:
            return True, True
        elif selected_option == radio_buttons[1]:
            return True, False
        else:
            return False, False

    def _collect_number_of_image_types(self):
        """
        Collects the number of image types the user wants to process.

        Returns:
            bool: True if the dialog is not canceled, False otherwise.
        """
        dialog = gui.GenericDialog('Number of Image Types')
        if self.options['color']:
            dialog.addMessage('How many image types are you processing?')
        else:
            dialog.addMessage('How many image types are in the directories you are processing?')

        dialog.addMessage('Examples:\nVessels and Tumors = 2\nVessels, Tumors, and Fibroblasts = 3')
        dialog.setInsets(5, 60, 5)

        dialog.addChoice('', [str(x + 1) for x in range(6)], '2')

        dialog.setOKLabel('Next ...')
        dialog.showDialog()

        if dialog.wasCanceled():
            return False

        self.num_types = int(dialog.getNextChoice())  # Store numTypes separately
        return True


    def _create_image_type_options_panel(self, possible_colors, default_names):

        panel = Panel()
        panel.setLayout(GridBagLayout())
        c = GridBagConstraints()
        c.fill = GridBagConstraints.HORIZONTAL
        c.insets = Insets(5, 5, 5, 5)
        c.anchor = GridBagConstraints.NORTHWEST

        self.name_fields = []
        self.color_choices = []

        num_columns = 3
        num_rows = (self.num_types + num_columns - 1) // num_columns  # Ceiling division

        for idx in range(self.num_types):
            col = idx % num_columns
            row = idx // num_columns

            c.gridx = col * 3  # Multiply by 3 to account for labels, choices, and fields
            c.gridy = row

            # Add "Image Type N" label
            panel.add(Label('Image Type: {}'.format(idx + 1)), c)

            c.gridx += 1

            if self.options['color']:
                # Add Color choice
                color_choice = Choice()
                for color in possible_colors:
                    color_choice.add(color)
                color_choice.select(possible_colors[idx % len(possible_colors)])
                panel.add(color_choice, c)
                self.color_choices.append(color_choice)
                c.gridx += 1
            else:
                self.color_choices.append(None)

            # Add Name field
            name_field = TextField(default_names[idx % len(default_names)], 10)
            panel.add(name_field, c)
            self.name_fields.append(name_field)

        return panel

    # NEW METHOD
    def _create_tumor_options_panel(self):
        tumor_options_selected = any([
            self.options.get('segment', False),
            self.options.get('tumor_weka', False),
            self.options.get('subtract_background', False),
            self.options.get('meas_circ', False),
            self.options.get('meas_grey', False)
        ])

        if not tumor_options_selected:
            return None  # No options selected, so return None

        wrapper_panel = JPanel(BorderLayout())
        panel = JPanel(GridBagLayout())
        wrapper_panel.add(panel, BorderLayout.NORTH)

        c = GridBagConstraints()
        c.fill = GridBagConstraints.HORIZONTAL
        c.insets = Insets(2, 2, 2, 2)  # top, left, bottom, right padding
        c.anchor = GridBagConstraints.NORTHWEST

        c.gridx = 0
        c.gridy = 0
        c.gridwidth = 2
        if self.options['segment'] or self.options['tumor_weka'] or self.options['subtract_background'] or self.options['meas_circ']:
            panel.add(JLabel("Tumor Options:"), c)

        c.gridwidth = 1
        c.gridy += 1

        if self.options['segment']:
            c.gridx = 0
            panel.add(JLabel("Show segmented images:"), c)
            c.gridx = 1
            self.show_segmented_checkbox = JCheckBox()
            panel.add(self.show_segmented_checkbox, c)
            c.gridy += 1

        if self.options['tumor_weka']:
            c.gridx = 0
            panel.add(JLabel("Select Weka classifier file:"), c)
            c.gridx = 1
            self.use_weka_segmentation_checkbox = JCheckBox()
            panel.add(self.use_weka_segmentation_checkbox, c)
            c.gridy += 1

        if self.options['subtract_background']:
            c.gridx = 0
            panel.add(JLabel("Rolling ball radius:"), c)
            c.gridx = 1
            self.rolling_radius_field = JTextField("50", 3)
            self.rolling_radius_field.setMaximumSize(Dimension(50, 20))
            self.rolling_radius_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.rolling_radius_field, c)
            c.gridy += 1

        if self.options['meas_circ']:
            c.gridx = 0
            panel.add(JLabel("Circularity Black:"), c)
            c.gridx = 1
            self.circ_bp_field = JTextField("0", 3)
            self.circ_bp_field.setMaximumSize(Dimension(50, 20))
            self.circ_bp_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.circ_bp_field, c)
            c.gridy += 1

            c.gridx = 0
            panel.add(JLabel("Circularity Min Size:"), c)
            c.gridx = 1
            self.circ_st_field = JTextField("50", 3)
            self.circ_st_field.setMaximumSize(Dimension(50, 20))
            self.circ_st_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.circ_st_field, c)
            c.gridy += 1

            c.gridx = 0
            panel.add(JLabel("Circularity Max Size:"), c)
            c.gridx = 1
            self.circ_lt_field = JTextField("10000", 5)
            self.circ_lt_field.setMaximumSize(Dimension(50, 20))
            self.circ_lt_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.circ_lt_field, c)
            c.gridy += 1

        if self.options['meas_grey'] or self.options['meas_circ']:
            c.gridx = 0
            panel.add(JLabel("Use Weka Segmentation for Tumor:"), c)
            c.gridx = 1
            self.use_weka_segmentation_tumor_checkbox = JCheckBox()
            panel.add(self.use_weka_segmentation_tumor_checkbox, c)
            c.gridy += 1

        return wrapper_panel

    def _create_vessel_options_panel(self):
        vessel_options_selected = any([
            self.options.get('threshold', False),
            self.options.get('vessel_weka', False),
            self.options.get('meas_diam', False),
            self.options.get('dxf_out', False)
        ])

        if not vessel_options_selected:
            return None  # No options selected, so return None

        wrapper_panel = JPanel(BorderLayout())
        panel = JPanel(GridBagLayout())
        wrapper_panel.add(panel, BorderLayout.NORTH)

        c = GridBagConstraints()
        c.fill = GridBagConstraints.HORIZONTAL
        c.insets = Insets(2, 2, 2, 2)
        c.anchor = GridBagConstraints.NORTHWEST

        c.gridx = 0
        c.gridy = 0
        c.gridwidth = 2
        if self.options['threshold'] or self.options['vessel_weka'] or self.options['meas_diam'] or self.options['dxf_out']:
            panel.add(JLabel("Vessel Options:"), c)

        c.gridwidth = 1
        c.gridy += 1

        if self.options['threshold']:
            c.gridx = 0
            panel.add(JLabel("Show thresholded images:"), c)
            c.gridx = 1
            self.show_threshold_checkbox = JCheckBox()
            panel.add(self.show_threshold_checkbox, c)
            c.gridy += 1

        if self.options['vessel_weka']:
            c.gridx = 0
            panel.add(JLabel("Select Weka Vessel classifier file:"), c)
            c.gridx = 1
            self.use_vessel_weka_checkbox = JCheckBox()
            panel.add(self.use_vessel_weka_checkbox, c)
            c.gridy += 1

        if self.options['meas_diam']:
            c.gridx = 0
            c.gridwidth = 2
            panel.add(JLabel("Vessel Measurement Options:"), c)
            c.gridwidth = 1
            c.gridy += 1

            options = [
                ("Hole Threshold:", "50"),
                ("Area Threshold:", "10"),
                ("Cleaning Threshold:", "3"),
                ("Distance Threshold:", "10"),
                ("Mean Threshold:", "50"),
            ]
            fields = []

            for label_text, default_value in options:
                c.gridx = 0
                panel.add(JLabel(label_text), c)
                c.gridx = 1
                field = JTextField(default_value, 3)
                field.setMaximumSize(Dimension(50, 20))
                field.setMinimumSize(Dimension(30, 20))
                panel.add(field, c)
                fields.append(field)
                c.gridy += 1

            # Store references
            (
                self.hole_threshold_field,
                self.area_threshold_field,
                self.image_cleaning_threshold_field,
                self.distance_threshold_field,
                self.mean_threshold_field,
            ) = fields

            c.gridx = 0
            panel.add(JLabel("Show settings for each image:"), c)
            c.gridx = 1
            self.vessel_settings_checkbox = JCheckBox()
            panel.add(self.vessel_settings_checkbox, c)
            c.gridy += 1

        if self.options['dxf_out']:
            c.gridx = 0
            panel.add(JLabel("Enable Smoothing:"), c)
            c.gridx = 1
            self.smooth_checkbox = JCheckBox()
            panel.add(self.smooth_checkbox, c)
            c.gridy += 1

            c.gridx = 0
            panel.add(JLabel("Smoothing Value:"), c)
            c.gridx = 1
            self.smooth_value_field = JTextField("2", 3)
            self.smooth_value_field.setMaximumSize(Dimension(50, 20))
            self.smooth_value_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.smooth_value_field, c)
            c.gridy += 1

        if self.options['meas_diam'] or self.options['dxf_out']:
            c.gridx = 0
            panel.add(JLabel("Use Weka Segmentation for Vessels:"), c)
            c.gridx = 1
            self.use_weka_segmentation_vessels_checkbox = JCheckBox()
            panel.add(self.use_weka_segmentation_vessels_checkbox, c)
            c.gridy += 1

        return wrapper_panel

    def _create_perfusion_options_panel(self):
        perfusion_options_selected = any([
            self.options.get('perfusion_calc', False),
            self.options.get('permeability_calc', False)
        ])

        if not perfusion_options_selected:
            return None  # No options selected, so return None

        wrapper_panel = JPanel(BorderLayout())
        panel = JPanel(GridBagLayout())
        wrapper_panel.add(panel, BorderLayout.NORTH)

        c = GridBagConstraints()
        c.fill = GridBagConstraints.HORIZONTAL
        c.insets = Insets(2, 2, 2, 2)  # top, left, bottom, right padding
        c.anchor = GridBagConstraints.NORTHWEST

        c.gridx = 0
        c.gridy = 0
        c.gridwidth = 2

        if self.options['perfusion_calc']:
            panel.add(JLabel("Perfusion Options:"), c)
            c.gridwidth = 1
            c.gridy += 1

            # Images per N
            c.gridx = 0
            panel.add(JLabel("Images per N:"), c)
            c.gridx = 1
            self.images_per_n_field = JTextField("1", 3)
            self.images_per_n_field.setMaximumSize(Dimension(50, 20))
            self.images_per_n_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.images_per_n_field, c)
            c.gridy += 1

            # Starting/Reference Image
            c.gridx = 0
            panel.add(JLabel("Starting/Reference Image:"), c)
            c.gridx = 1
            self.starting_image_field = JTextField("1", 3)
            self.starting_image_field.setMaximumSize(Dimension(50, 20))
            self.starting_image_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.starting_image_field, c)
            c.gridy += 1

            # Run Weka Segmentation
            c.gridx = 0
            panel.add(JLabel("Run Weka Segmentation:"), c)
            c.gridx = 1
            self.perfusion_segment_checkbox = JCheckBox()
            panel.add(self.perfusion_segment_checkbox, c)
            c.gridy += 1

        # Add extra spacing
        c.gridx = 0
        c.gridwidth = 2
        panel.add(JLabel(" "), c)
        c.gridy += 1

        if self.options['permeability_calc']:
            c.gridwidth = 2
            panel.add(JLabel("Permeability Options:"), c)
            c.gridwidth = 1
            c.gridy += 1

            # Images per N (Permeability)
            c.gridx = 0
            panel.add(JLabel("Images per N (Permeability):"), c)
            c.gridx = 1
            self.images_per_n_perm_field = JTextField("1", 3)
            self.images_per_n_perm_field.setMaximumSize(Dimension(50, 20))
            self.images_per_n_perm_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.images_per_n_perm_field, c)
            c.gridy += 1

            # Manually Align
            c.gridx = 0
            panel.add(JLabel("Manually Align:"), c)
            c.gridx = 1
            self.manual_align_checkbox = JCheckBox()
            panel.add(self.manual_align_checkbox, c)
            c.gridy += 1

            # Radius for Measurement Area
            c.gridx = 0
            panel.add(JLabel("Radius for Measurement Area:"), c)
            c.gridx = 1
            self.oval_rad_field = JTextField("25", 3)
            self.oval_rad_field.setMaximumSize(Dimension(50, 20))
            self.oval_rad_field.setMinimumSize(Dimension(30, 20))
            panel.add(self.oval_rad_field, c)
            c.gridy += 1

            # Run Weka Segmentation
            c.gridx = 0
            panel.add(JLabel("Run Weka Segmentation:"), c)
            c.gridx = 1
            self.permeability_segment_checkbox = JCheckBox()
            panel.add(self.permeability_segment_checkbox, c)

        return wrapper_panel

    def _collect_additional_options(self):
        """
        Collects additional options such as image type names and colors.

        Returns:
            bool: True if the dialog is not canceled, False otherwise.
        """
        dialog = gui.GenericDialog('Image Type Names and Colors')
        possible_colors = ['Red', 'Green', 'Blue', 'Cyan', 'Magenta', 'Yellow']
        default_names = ['Vessels', 'Tumor', 'Fibroblasts', 'Cell 1', 'Cell 2', 'Cell 3']

        type_names, type_colors = [], []

        # Create the custom panel for image types
        image_type_panel = self._create_image_type_options_panel(possible_colors, default_names)
        dialog.addPanel(image_type_panel)

        # Add color and merge options
        self._add_color_merge_options(dialog)

        # Add crop options if enabled
        if self.options['crop']:
            dialog.addMessage('Cropping Options:')
            cropping_methods = ['Crop using same coordinates', 'Crop each pair', 'Crop each image']
            dialog.addRadioButtonGroup("Select Cropping Method:", cropping_methods, 1, 3, cropping_methods[0])
            dialog.addCheckbox('Use cropped images', True)

        # Collect the panels that need to be displayed
        options_panels = []

        tumor_panel = self._create_tumor_options_panel()
        vessel_panel = self._create_vessel_options_panel()
        perfusion_panel = self._create_perfusion_options_panel()

        if tumor_panel is not None:
            options_panels.append(tumor_panel)
        if vessel_panel is not None:
            options_panels.append(vessel_panel)
        if perfusion_panel is not None:
            options_panels.append(perfusion_panel)

        # Create a Panel with appropriate number of columns
        num_panels = len(options_panels)
        if num_panels > 0:
            panel = Panel()
            panel.setLayout(GridLayout(1, num_panels, 10, 0))  # 1 row, num_panels columns
            for p in options_panels:
                panel.add(p)
            dialog.addPanel(panel)

        self._add_file_options(dialog)

        dialog.setOKLabel('Next ...')
        dialog.showDialog()

        if dialog.wasCanceled():
            return False

        # Retrieve values from custom components
        self.type_names = []
        self.type_colors = []
        for i in range(self.num_types):
            name = self.name_fields[i].getText().strip()
            if not name:
                IJ.error("Please enter a name for all image types")
                return False
            self.type_names.append(name)
            if self.color_choices[i]:
                self.type_colors.append(self.color_choices[i].getSelectedItem())
            else:
                self.type_colors.append(None)

        self._finalize_additional_options(dialog)
        return True


    def _add_color_merge_options(self, dialog):
        """
        Adds color and merge options to the dialog.

        Args:
            dialog (GenericDialog): The dialog instance where the color and merge options will be added.
        """
        # Add the message label on its own line
        if self.options['color'] or self.options['merge']:
            dialog.addMessage('Color and Merge Options:')

            # Create a custom panel with FlowLayout for the options
            panel = Panel()
            panel.setLayout(FlowLayout(FlowLayout.LEFT))

            # Create and add 'Show colored images' checkbox
            self.show_colored_images_checkbox = Checkbox('Show colored images', self.options.get('show_colored', False))
            panel.add(self.show_colored_images_checkbox)

            # Create and add 'Sat level' label and text field
            panel.add(Label('Sat level:'))
            self.sat_level_field = TextField(str(self.options.get('sat', 0.3)), 5)
            panel.add(self.sat_level_field)

            # If 'merge' option is enabled, create and add 'Show merged images' checkbox
            if self.options['merge']:
                self.show_merged_images_checkbox = Checkbox('Show merged images', self.options.get('show_merged', False))
                panel.add(self.show_merged_images_checkbox)

            # Add the custom panel to the dialog (options on the line below the label)
            dialog.addPanel(panel)

    def _parse_crop_type(self, selected_option):
        """
        Helper function to parse the crop type option.

        Args:
            selected_option (str): The selected radio button option.

        Returns:
            str: The crop type based on the selected option.
        """
        crop_types = ['batch', 'grouped', 'individual']
        crop_options = ['Crop using same coordinates', 'Crop each pair', 'Crop each image']
        return crop_types[crop_options.index(selected_option)]

    def _add_file_options(self, dialog):
        """
        Adds file processing options to the dialog.

        Args:
            dialog (GenericDialog): The dialog instance where the file options will be added.
        """
        dialog.addMessage('File Options:')

        # Create a panel with FlowLayout to hold the checkboxes
        panel = Panel()
        panel.setLayout(FlowLayout(FlowLayout.LEFT))

        # Create and add the checkboxes to the panel
        self.process_subdirs_checkbox = Checkbox('Process images in subdirectories', self.options.get('process_subdirectories', True))
        panel.add(self.process_subdirs_checkbox)

        self.confirm_image_types_checkbox = Checkbox('Confirm image types', self.options.get('confirm_image_types', False))
        panel.add(self.confirm_image_types_checkbox)

        self.verbose_logging_checkbox = Checkbox('Verbose Logging', self.options.get('verbose', False))
        panel.add(self.verbose_logging_checkbox)

        # Add the panel to the dialog
        dialog.addPanel(panel)

    def _finalize_additional_options(self, dialog):
        """
        Finalizes the additional options collected from the user.

        Args:
            dialog (GenericDialog): The dialog instance from which final options are retrieved.
        """
        # Retrieve values from the color and merge options panel
        if self.options['color']:
            self.options['show_colored'] = self.show_colored_images_checkbox.getState()
            try:
                self.options['sat'] = float(self.sat_level_field.getText())
            except ValueError:
                IJ.error("Please enter a valid number for 'Sat level'")
                return False  # Or handle the error as appropriate
        else:
            self.options['show_colored'] = False
            self.options['sat'] = 0.3  # Default value

        if self.options['merge']:
            self.options['show_merged'] = self.show_merged_images_checkbox.getState()
        else:
            self.options['show_merged'] = False

        if self.options['crop']:
            selected_crop_option = dialog.getNextRadioButton()
            self.options['crop_type'] = self._parse_crop_type(selected_crop_option)
            self.options['use_crop'] = dialog.getNextBoolean()
            print(self.options['crop_type'])

        # process tumor options
        if self.options['segment']:
            self.options['show_segmented'] = self.show_segmented_checkbox.isSelected()
        if self.options['tumor_weka']:
            self.options['use_weka_segmentation'] = self.use_weka_segmentation_checkbox.isSelected()
        if self.options['subtract_background']:
            self.options['rolling_radius'] = float(self.rolling_radius_field.getText())
        if self.options['meas_circ']:
            self.options['circ_bp'] = float(self.circ_bp_field.getText())
            self.options['circ_st'] = float(self.circ_st_field.getText())
            self.options['circ_lt'] = float(self.circ_lt_field.getText())

        # Process vessel options
        if self.options['threshold']:
            self.options['show_threshold'] = self.show_threshold_checkbox.isSelected()
        if self.options['vessel_weka']:
            self.options['use_vessel_weka_segmentation'] = self.use_vessel_weka_checkbox.isSelected()
        if self.options['meas_diam']:
            self.options['hole_threshold'] = float(self.hole_threshold_field.getText())
            self.options['area_threshold_vessels'] = float(self.area_threshold_field.getText())
            self.options['image_cleaning_threshold'] = float(self.image_cleaning_threshold_field.getText())
            self.options['distance_threshold'] = float(self.distance_threshold_field.getText())
            self.options['mean_threshold'] = float(self.mean_threshold_field.getText())
            self.options['vessel_settings'] = self.vessel_settings_checkbox.isSelected()
        if self.options['dxf_out']:
            self.options['smooth_bool'] = self.smooth_checkbox.isSelected()
            self.options['smooth_value'] = float(self.smooth_value_field.getText())

        # process perfusion options
        if self.options['perfusion_calc']:
            self.options['images_per_n'] = float(self.images_per_n_field.getText())
            self.options['starting_image'] = float(self.starting_image_field.getText())
            self.options['perfusion_segment'] = self.perfusion_segment_checkbox.isSelected()
        if self.options['permeability_calc']:
            self.options['images_per_n_perm'] = float(self.images_per_n_perm_field.getText())
            self.options['manual_align'] = self.manual_align_checkbox.isSelected()
            self.options['oval_rad'] = float(self.oval_rad_field.getText())
            self.options['permeability_segment'] = self.permeability_segment_checkbox.isSelected()

        # handle weka
        if self.options['meas_diam'] or self.options['dxf_out']:
            self.options['use_weka_segmentation_vessels'] = self.use_weka_segmentation_vessels_checkbox.isSelected()
        if self.options['meas_grey'] or self.options['meas_circ']:
            self.options['use_weka_segmentation_tumor'] = self.use_weka_segmentation_tumor_checkbox.isSelected()

        # Retrieve values from the checkboxes in the file options panel
        self.options['process_subdirectories'] = self.process_subdirs_checkbox.getState()
        self.options['confirm_image_types'] = self.confirm_image_types_checkbox.getState()
        self.options['verbose'] = self.verbose_logging_checkbox.getState()

    def _collect_root_directory(self):
        """
        Prompts the user to select the root directory and stores it in options.

        Returns:
            bool: True if a root directory is selected, False otherwise.
        """
        self.options['rootDir'] = IJ.getDirectory("Select Root Directory")
        return self.options['rootDir'] is not None

    def _configure_device_manager(self, device_manager):
        """
        Configures the DeviceManager instance with the selected options.

        Args:
            device_manager (DeviceManager): The DeviceManager instance to configure.
        """
        # Set the device-specific configurations
        device_manager.numTypes = self.num_types
        device_manager.typeNames = self.type_names
        device_manager.typeColors = self.type_colors
        device_manager.rootDir = self.options.get('rootDir')
        device_manager.verbose = self.options.get('verbose')

        # Set the operational options (excluding numTypes, typeNames, typeColors, and rootDir)
        device_manager.options = {
            k: v for k, v in self.options.items() if k not in ['numTypes', 'typeNames', 'typeColors', 'rootDir', 'verbose']
        }

        # Apply the options to the device manager
        device_manager._apply_gui_options()


class ImageTypeChangerGui:
    """
    A GUI class for confirming or changing image types within a device.

    Attributes:
        device (Device): The device containing images to confirm or change types for.
    """

    def __init__(self, device):
        """Initializes the ImageTypeChangerGui with a device."""
        self.device = device

    def confirm_and_change_image_type(self):
        """
        Iterates through all images in the device and allows the user to confirm or change their types.
        """
        for img_type, image_paths in self.device.get_image_paths().items():
            if not image_paths:
                continue

            image_paths = self._ensure_list(image_paths)
            valid_types = self.device.get_typeNames()

            for image_path in image_paths:
                new_type = self._show_image_and_get_new_type(image_path, img_type, valid_types)
                if new_type and new_type != img_type:
                    self._update_image_type(image_path, img_type, new_type)

    def _show_image_and_get_new_type(self, image_path, current_type, valid_types):
        """
        Displays the image and prompts the user to confirm or change its type.

        Args:
            image_path (str): The file path of the image to display.
            current_type (str): The current image type.
            valid_types (list): A list of valid image types to choose from.

        Returns:
            str: The new image type selected by the user, or None if canceled.
        """
        image = IJ.openImage(image_path)
        image.show()

        new_type = self._get_user_input(current_type, valid_types)

        image.close()
        return new_type

    def _get_user_input(self, current_type, valid_types):
        """
        Sets up the GUI dialog to get user input for changing image type.

        Args:
            current_type (str): The current image type.
            valid_types (list): A list of valid image types to choose from.

        Returns:
            str: The new image type selected by the user, or None if canceled.
        """
        dialog = gui.GenericDialog("Confirm or Change Image Type")
        dialog.addMessage("Current Type: {}".format(current_type))
        dialog.addRadioButtonGroup("Select new type:", valid_types, 1, len(valid_types), current_type)
        dialog.setOKLabel("Next...")
        dialog.setCancelLabel("Cancel")
        dialog.showDialog()

        if dialog.wasCanceled():
            return None

        return dialog.getNextRadioButton()

    def _update_image_type(self, image_path, old_type, new_type):
        """
        Updates the image type and logs the change if verbose mode is enabled.

        Args:
            image_path (str): The file path of the image to update.
            old_type (str): The old image type.
            new_type (str): The new image type.
        """
        image = self.device._load_image(image_path)
        self.device.update_image_type(image_path, old_type, new_type, image)

        if self.device.verbose:
            print("Image type changed: {} from {} to {}".format(image_path, old_type, new_type))

    def _ensure_list(self, item):
        """
        Ensures that the provided item is returned as a list.

        Args:
            item: The item to ensure as a list.

        Returns:
            list: The item as a list, or a list containing the item if it was not already a list.
        """
        return item if isinstance(item, list) else [item]
