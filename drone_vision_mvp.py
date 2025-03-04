from PIL import Image
import pdb 
def process_image_to_cmyk(image_path):
    # Open the image file
    with Image.open(image_path) as img:
        # Convert the image to CMYK
        cmyk_img = img.convert('CMYK')
        # Get pixel values
        pixel_values = list(cmyk_img.getdata())
    for i in range(len(pixel_values)):
            if pixel_values[i][3] > 150:
                pixel_values[i][1] = 0
                pixel_values[i + 1][2] = 0
                pixel_values[i + 2][3] = 0
                pixel_values[i + 3][4] = 0
                i += 4 
     # Save the processed image
    cmyk_img.putdata(pixel_values)
    new_image_path = 'processed_' + image_path
    cmyk_img.save(new_image_path)
    print(f"Processed image saved as {new_image_path}")
            # else:
            #     og_img_pixels = list(img.getdata())
            #     og_img_pixels[i] = 0
            #     og_img_pixels[i + 1] = 256
            #     og_img_pixels[i + 2] = 0


# Example usage
if __name__ == "__main__":
    image_path = 'nitrogen_deficiency.jpg'
    pixels = process_image_to_cmyk(image_path)
   