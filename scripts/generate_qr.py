import qrcode
import sys
import os
from urllib.parse import urlparse

def generate_qr_code(url):
    """
    Generate a QR code from a URL and save it as a PNG file.
    The filename is derived from the URL.
    """
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add data to QR code
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create an image from the QR code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Generate filename from URL
    parsed_url = urlparse(url)
    # Use the full URL path or domain as filename base
    filename_base = parsed_url.netloc + parsed_url.path
    # Replace invalid filename characters
    filename_base = filename_base.replace('/', '_').replace(':', '_').replace('?', '_').replace('&', '_')
    # Remove trailing underscores
    filename_base = filename_base.strip('_')
    
    # If filename is empty, use 'qr_code' as default
    if not filename_base:
        filename_base = 'qr_code'
    
    filename = f"{filename_base}.png"
    
    # Save the image
    img.save(filename)
    print(f"QR code generated and saved as: {filename}")
    return filename

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_qr.py <url>")
        print("Example: python generate_qr.py https://example.com")
        sys.exit(1)
    
    url = sys.argv[1]
    generate_qr_code(url)
