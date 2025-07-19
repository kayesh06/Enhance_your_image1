# my_new_django_project/myapp/views.py

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image, ImageFilter
import io
import base64
import requests
from django.conf import settings  # Make sure this is imported!
import os

from .forms import UploadImageForm


def image_processing_view(request):
    """
    Handles image upload and processing (rotate, blur, crop, etc.).
    Returns JSON response for AJAX POST requests, and HTML for GET requests.
    """
    processed_image_url = None
    image_original_url = None
    image_caption = None
    detected_objects = None
    form = UploadImageForm()

    if request.method == 'POST':
        form = UploadImageForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_image = form.cleaned_data['image']
            operation = form.cleaned_data.get('operation')

            # Read image content once and store in a BytesIO buffer
            uploaded_image.seek(0)
            image_buffer = io.BytesIO(uploaded_image.read())
            image_buffer.seek(0)  # Reset buffer position to the beginning after reading

            # Save the original image to media for display if needed
            original_filename_base, original_filename_ext = os.path.splitext(uploaded_image.name)
            if 'blob' in original_filename_base.lower() or default_storage.exists(uploaded_image.name):
                unique_suffix = os.urandom(8).hex()
                original_filename = f"original_upload_{original_filename_base}_{unique_suffix}{original_filename_ext}"
            else:
                original_filename = uploaded_image.name

            temp_path = default_storage.save(original_filename, ContentFile(image_buffer.getvalue()))
            image_original_url = default_storage.url(temp_path)

            image_buffer.seek(0)  # Reset buffer position again after saving to storage

            try:
                img = None  # Initialize img to None

                # Operations that require PIL to open the image from the buffer
                if operation not in ['image_captioning', 'background_removal', 'object_detection']:
                    img = Image.open(image_buffer)
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')
                elif operation == 'draw':
                    img = Image.open(image_buffer)
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')

                # --- Apply Operations based on 'operation' field ---
                if operation == 'rotate':
                    angle = form.cleaned_data.get('rotation_angle')
                    if angle is not None:
                        img = img.rotate(angle, expand=True)

                elif operation == 'blur':
                    intensity = form.cleaned_data.get('blur_intensity')
                    if intensity is not None:
                        if intensity % 2 == 0:
                            intensity += 1
                        img = img.filter(ImageFilter.GaussianBlur(intensity))

                elif operation == 'crop':
                    top = form.cleaned_data.get('crop_top')
                    left = form.cleaned_data.get('crop_left')
                    width = form.cleaned_data.get('crop_width')
                    height = form.cleaned_data.get('crop_height')

                    if all(v is not None for v in [top, left, width, height]):
                        if left < 0 or top < 0 or (left + width) > img.width or (top + height) > img.height:
                            form.add_error(None, "Crop coordinates are out of image bounds.")
                        else:
                            img = img.crop((left, top, left + width, top + height))
                    else:
                        form.add_error(None, "Crop operation requires all crop coordinates (top, left, width, height).")

                elif operation == 'grayscale':
                    img = img.convert('L')

                elif operation == 'resize':
                    scale_factor = form.cleaned_data.get('scale_factor')
                    if scale_factor is not None:
                        original_width, original_height = img.size
                        new_width = int(original_width * (int(scale_factor) / 100))
                        new_height = int(original_height * (int(scale_factor) / 100))
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                elif operation == 'image_captioning':
                    base64_image = base64.b64encode(image_buffer.getvalue()).decode('utf-8')

                    # --- CORRECTED: Read from settings and strip whitespace ---
                    api_key = settings.GEMINI_API_KEY.strip()
                    if not api_key or api_key == 'AIzaSyAMZtPSY-hLrQNZ3gRsoYMEVaXtQmFwYwQ': # Check against placeholder too
                        form.add_error(None, "Gemini API key is not configured in settings.py.")
                        raise ValueError("Gemini API key missing or invalid.") # Raise to stop processing

                    gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

                    headers = {
                        'Content-Type': 'application/json'
                    }

                    payload = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {"text": "Describe this image in detail."},
                                    {
                                        "inlineData": {
                                            "mimeType": uploaded_image.content_type,
                                            "data": base64_image
                                        }
                                    }
                                ]
                            }
                        ]
                    }

                    try:
                        gemini_response = requests.post(gemini_api_url, headers=headers, json=payload)
                        gemini_response.raise_for_status()
                        gemini_result = gemini_response.json()

                        if gemini_result and gemini_result.get('candidates'):
                            image_caption = gemini_result['candidates'][0]['content']['parts'][0]['text']
                            processed_image_url = image_original_url  # Keep original image URL for display
                        else:
                            form.add_error(None,
                                           "AI captioning failed: No description generated. Gemini API response might be empty or malformed.")
                            print(f"Gemini API response: {gemini_result}")

                    except requests.exceptions.RequestException as req_err:
                        form.add_error(None, f"AI API request failed: {str(req_err)}. Check network or API key.")
                        print(f"Gemini API Request Error: {req_err}")
                    except Exception as e:
                        form.add_error(None, f"Error processing AI response: {str(e)}. Check API response structure.")
                        print(f"Gemini Response Processing Error: {e}")

                elif operation == 'object_detection':
                    base64_image = base64.b64encode(image_buffer.getvalue()).decode('utf-8')

                    # --- CORRECTED: Read from settings and strip whitespace ---
                    api_key = settings.GEMINI_API_KEY.strip()
                    if not api_key or api_key == 'YOUR_GEMINI_API_KEY_HERE': # Check against placeholder too
                        form.add_error(None, "Gemini API key is not configured in settings.py.")
                        raise ValueError("Gemini API key missing or invalid.") # Raise to stop processing

                    gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

                    headers = {
                        'Content-Type': 'application/json'
                    }

                    payload = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [
                                    {
                                        "text": "List all distinct objects you can identify in this image, separated by commas. For example: 'tree, car, house, person'. If no objects are found, respond with 'No objects detected.'"},
                                    {
                                        "inlineData": {
                                            "mimeType": uploaded_image.content_type,
                                            "data": base64_image
                                        }
                                    }
                                ]
                            }
                        ]
                    }

                    try:
                        gemini_response = requests.post(gemini_api_url, headers=headers, json=payload)
                        gemini_response.raise_for_status()
                        gemini_result = gemini_response.json()

                        if gemini_result and gemini_result.get('candidates'):
                            detected_objects = gemini_result['candidates'][0]['content']['parts'][0]['text']
                            processed_image_url = image_original_url  # Keep original image URL for display
                        else:
                            form.add_error(None,
                                           "AI object detection failed: No objects identified. Gemini API response might be empty or malformed.")
                            print(f"Gemini API response (object detection): {gemini_result}")

                    except requests.exceptions.RequestException as req_err:
                        form.add_error(None, f"AI API request failed: {str(req_err)}. Check network or API key.")
                        print(f"Gemini API Request Error (object detection): {req_err}")
                    except Exception as e:
                        form.add_error(None, f"Error processing AI response: {str(e)}. Check API response structure.")
                        print(f"Gemini Response Processing Error (object detection): {e}")

                elif operation == 'background_removal':
                    remove_bg_api_key = settings.REMOVE_BG_API_KEY.strip() # Also strip this key
                    if not remove_bg_api_key or remove_bg_api_key == 'YOUR_REMOVE_BG_API_KEY_HERE':
                        form.add_error(None, "remove.bg API key is not configured. Please add it to settings.py.")
                        raise ValueError("remove.bg API key missing or invalid.")
                    else:
                        remove_bg_url = "https://api.remove.bg/v1.0/removebg"

                        files = {
                            'image_file': (uploaded_image.name, image_buffer.getvalue(), uploaded_image.content_type)}
                        headers = {'X-Api-Key': remove_bg_api_key} # Use the stripped key here
                        data = {'size': 'auto'}

                        try:
                            remove_bg_response = requests.post(remove_bg_url, files=files, headers=headers, data=data)
                            remove_bg_response.raise_for_status()

                            if 'image' in remove_bg_response.headers.get('Content-Type', ''):
                                processed_filename = f"processed_bg_removed_{original_filename_base}.png"
                                file_path = default_storage.save(processed_filename,
                                                                 ContentFile(remove_bg_response.content))
                                processed_image_url = default_storage.url(file_path)
                            else:
                                error_data = remove_bg_response.json()
                                error_message = error_data.get('errors', [{'title': 'Unknown error'}])[0].get('title',
                                                                                                              'Unknown error from remove.bg')
                                form.add_error(None, f"Background removal failed: {error_message}.")
                                print(f"remove.bg API error response: {error_data}")

                        except requests.exceptions.RequestException as req_err:
                            form.add_error(None,
                                           f"Background removal API request failed: {str(req_err)}. Check network or API key.")
                            print(f"remove.bg API Request Error: {req_err}")
                        except Exception as e:
                            form.add_error(None,
                                           f"Error processing remove.bg response: {str(e)}. Check API response structure.")
                            print(f"remove.bg Response Processing Error: {e}")

                # --- Save the processed image if no form errors occurred during processing ---
                if not form.errors and operation not in ['image_captioning', 'background_removal', 'object_detection']:
                    buffer = io.BytesIO()
                    file_extension = original_filename_ext.lower().replace('.', '')
                    if operation == 'draw' or file_extension == 'png':
                        img.save(buffer, format='PNG')
                    elif file_extension in ['jpg', 'jpeg']:
                        img.save(buffer, format='JPEG')
                    elif file_extension == 'gif':
                        img.save(buffer, format='GIF')
                    else:
                        img.save(buffer, format='PNG')  # Default to PNG if unsure

                    processed_filename = f"processed_{operation}_{original_filename_base}{original_filename_ext}"

                    file_path = default_storage.save(processed_filename, ContentFile(buffer.getvalue()))
                    processed_image_url = default_storage.url(file_path)

            except Exception as e:
                if isinstance(e, ValueError) and ("API key missing" in str(e) or "invalid" in str(e)):
                    pass # Error already added to form, no need to add again
                else:
                    form.add_error(None, f"General image processing failed: {str(e)}.")
                    print(f"General Image processing error: {e}")

        # --- RETURN JSON RESPONSE FOR AJAX POST REQUESTS ---
        response_data = {
            'success': not form.errors,
            'processed_image_url': processed_image_url,
            'image_original_url': image_original_url,
            'image_caption': image_caption,
            'detected_objects': detected_objects,
            'errors': form.errors.as_json() if form.errors else {}
        }
        if form.errors:
            response_data['message'] = 'Form validation failed or processing error occurred.'
            return JsonResponse(response_data, status=400)
        else:
            response_data['message'] = 'Image processed successfully!'
            return JsonResponse(response_data, status=200)

    else:  # Handle GET request (initial page load)
        context = {
            'form': form,
            'processed_image_url': None,
            'image_original_url': None,
            'form_errors': None,
            'image_caption': None,
            'detected_objects': None,
        }
        return render(request, 'myapp/ipp.html', context)
