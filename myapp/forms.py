# my_new_django_project/myapp/forms.py

from django import forms

OPERATION_CHOICES = [
    ('blur', 'Blur'),
    ('rotate', 'Rotate'),
    ('resize', 'Resize'),
    ('crop', 'Crop'),
    ('grayscale', 'Grayscale'),
    ('to_pdf', 'Convert to PDF'),
    ('super_resolution', 'Super Resolution'),
    ('draw', 'Drawing Tool'),
    ('image_captioning', 'Image Captioning (AI)'),
    ('background_removal', 'Background Removal (AI)'),
    ('object_detection', 'Object Detection (AI)'),
]

SCALE_CHOICES = [
    (50, '50%'),
    (100, '100%'),
    (150, '150%'),
    (200, '200%'),
    (300, '300%'),
]


class UploadImageForm(forms.Form):
    image = forms.ImageField(
        required=True,
        label="Upload Image",
        help_text="Upload an image to apply operations."
    )

    operation = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        label="Choose Operation",
        help_text="Select an image processing operation."
    )

    blur_intensity = forms.IntegerField(
        required=False,
        label='Blur Intensity',
        min_value=1,
        max_value=55,
        initial=15,
        widget=forms.NumberInput(attrs={'type': 'range', 'step': 2}),
        help_text="Adjust the intensity of the blur effect (1-55, odd numbers recommended)."
    )

    rotation_angle = forms.IntegerField(
        required=False,
        label='Rotation Angle',
        min_value=0,
        max_value=360,
        initial=0,
        widget=forms.HiddenInput(),
        help_text="The final rotation angle (0-360 degrees) controlled by mouse."
    )

    scale_factor = forms.ChoiceField(
        choices=SCALE_CHOICES,
        required=False,
        label='Resize Scale',
        help_text="Choose a percentage to resize the image."
    )

    crop_top = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        min_value=0,
        label='Crop Top (px)'
    )
    crop_left = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        min_value=0,
        label='Crop Left (px)'
    )
    crop_width = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        min_value=1,
        label='Crop Width (px)'
    )
    crop_height = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
        min_value=1,
        label='Crop Height (px)'
    )

    def clean(self):
        cleaned_data = super().clean()
        operation = cleaned_data.get('operation')

        if operation == 'crop':
            crop_fields = ['crop_top', 'crop_left', 'crop_width', 'crop_height']
            for field_name in crop_fields:
                if cleaned_data.get(field_name) is None:
                    self.add_error(field_name, "This field is required for cropping.")

            crop_width = cleaned_data.get('crop_width')
            crop_height = cleaned_data.get('crop_height')
            if crop_width is not None and crop_width <= 0:
                self.add_error('crop_width', "Crop width must be greater than 0.")
            if crop_height is not None and crop_height <= 0:
                self.add_error('crop_height', "Crop height must be greater than 0.")

        if operation == 'rotate':
            rotation_angle = cleaned_data.get('rotation_angle')
            if rotation_angle is None:
                self.add_error('rotation_angle', "Rotation angle is required for rotation operation.")
            elif not (0 <= rotation_angle <= 360):
                self.add_error('rotation_angle', "Rotation angle must be between 0 and 360 degrees.")

        return cleaned_data
