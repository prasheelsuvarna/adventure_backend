from PIL import Image
import os

def crop_collage():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, "pictures", "WhatsApp Image 2026-06-11 at 11.27.19.jpeg")
    
    if not os.path.exists(img_path):
        print(f"Error: {img_path} does not exist.")
        return
        
    img = Image.open(img_path)
    w, h = img.size
    
    # 1220 x 2712 suggests a vertical collage of 4 photos stacked vertically.
    # Let's crop into 4 vertical slices.
    h_slice = h // 4
    for i in range(4):
        crop_img = img.crop((0, i * h_slice, w, (i + 1) * h_slice))
        out_path = os.path.join(base_dir, "pictures", f"WhatsApp_Image_crop_{i+1}.jpeg")
        crop_img.save(out_path, "JPEG")
        print(f"Saved: {out_path}")

if __name__ == "__main__":
    crop_collage()
