# photobooth_ai/qr_generator.py
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
import config
import os

def generate_qr_code_image(data, filename=config.DOWNLOAD_QR_FILENAME, add_logo=False, logo_path=None):
    """
    Generează o imagine de cod QR și o salvează într-un fișier.

    Args:
        data (str): Datele care trebuie encodate în codul QR.
        filename (str): Calea fișierului unde va fi salvată imaginea QR.
        add_logo (bool): Dacă se adaugă un logo în centrul QR-ului.
        logo_path (str, optional): Calea către fișierul logo. Necesar dacă add_logo este True.

    Returns:
        str: Calea către fișierul imagine QR generat dacă a reușit, None altfel.
    """
    try:
        qr = qrcode.QRCode(
            version=1, # Nivelul de complexitate; None pentru auto
            error_correction=qrcode.constants.ERROR_CORRECT_H, # Toleranță la erori mai mare pentru logo
            box_size=10, # Dimensiunea fiecărui "box" din QR
            border=4,    # Grosimea chenarului (minimum 4 conform standardului)
        )
        qr.add_data(data)
        qr.make(fit=True)

        if add_logo and logo_path and os.path.exists(logo_path):
            # Creează o imagine stilizată pentru a adăuga un logo
            # Acest lucru necesită qrcode[pil] instalat și Pillow.
            # Logo-ul va reduce cantitatea de date care poate fi stocată sau necesită un QR mai dens.
            # ERROR_CORRECT_H este recomandat.
            img = qr.make_image(
                image_factory=StyledPilImage, 
                module_drawer=RoundedModuleDrawer(), # Stilul punctelor QR
                # color_mask=SolidFillColorMask(front_color=(0,0,0), back_color=(255,255,255)), # Culori custom
                embeded_image_path=logo_path
            )
        else:
            img = qr.make_image(fill_color="black", back_color="white")
        
        # Asigură-te că directorul țintă există
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        img.save(filename)
        print(f"QR code generated and saved to {filename} for data: '{data[:30]}...'")
        return filename
    except ImportError:
        print("Error: 'qrcode' or 'Pillow' library not installed. Please install with 'pip install qrcode[pil]'.")
        return None
    except FileNotFoundError as e:
        print(f"Error: Logo file not found at {logo_path} if specified. {e}")
        return None
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

if __name__ == '__main__':
    # Test QR Generator

    # Mock config pentru testare
    class MockConfig:
        TEMP_DIR = "temp"
        DOWNLOAD_QR_FILENAME = os.path.join(TEMP_DIR, "test_qr_output.png")
        LOGO_PATH = "assets/logo.png" # Asigură-te că ai un logo.png în assets

    # Creează directorul temp și assets dacă nu există
    if not os.path.exists(MockConfig.TEMP_DIR):
        os.makedirs(MockConfig.TEMP_DIR)
    if not os.path.exists("assets"): # Pentru logo-ul de test
        os.makedirs("assets")
        print("Created 'assets' directory for logo test. Please place a 'logo.png' there.")

    # Folosește config-ul global dacă disponibil, altfel mock-ul
    try:
        import config as app_config # type: ignore
        # Actualizează calea fișierului de output în mock dacă config-ul real e folosit
        MockConfig.DOWNLOAD_QR_FILENAME = app_config.DOWNLOAD_QR_FILENAME 
        MockConfig.LOGO_PATH = app_config.LOGO_PATH
    except ImportError:
        app_config = MockConfig() # type: ignore
        print("Using MockConfig for qr_generator test.")
        # Suprascrie config-ul global pentru a testa comportamentul mock al funcției
        import sys
        sys.modules['config'] = app_config


    test_data = "https://www.example.com/photo/unique_id_12345"
    
    print("\n--- Testing QR generation (no logo) ---")
    output_path_no_logo = generate_qr_code_image(test_data, filename=MockConfig.DOWNLOAD_QR_FILENAME)
    if output_path_no_logo:
        print(f"QR code (no logo) saved to: {output_path_no_logo}")
    else:
        print("QR code generation (no logo) failed.")

    # Test cu logo - asigură-te că ai un fișier logo.png în assets
    # și că qrcode[pil] este instalat
    print("\n--- Testing QR generation (with logo) ---")
    logo_qr_filename = os.path.join(MockConfig.TEMP_DIR, "test_qr_with_logo_output.png")
    
    # Creează un fișier logo dummy dacă nu există pentru a permite rularea testului
    # Într-un scenariu real, ai avea logo-ul tău.
    if not os.path.exists(MockConfig.LOGO_PATH):
        try:
            from PIL import Image, ImageDraw
            dummy_logo = Image.new('RGB', (50, 50), color = 'red')
            draw = ImageDraw.Draw(dummy_logo)
            draw.text((10,10), "LOGO", fill='white')
            dummy_logo.save(MockConfig.LOGO_PATH)
            print(f"Created a dummy logo at {MockConfig.LOGO_PATH} for testing.")
        except ImportError:
            print("Pillow not installed. Cannot create dummy logo. Skipping logo QR test or it might fail.")
        except Exception as e:
            print(f"Error creating dummy logo: {e}")


    if os.path.exists(MockConfig.LOGO_PATH):
        output_path_with_logo = generate_qr_code_image(test_data, 
                                                       filename=logo_qr_filename, 
                                                       add_logo=True, 
                                                       logo_path=MockConfig.LOGO_PATH)
        if output_path_with_logo:
            print(f"QR code (with logo) saved to: {output_path_with_logo}")
        else:
            print("QR code generation (with logo) failed. Ensure 'qrcode[pil]' is installed and logo exists.")
    else:
        print(f"Skipping QR with logo test: Logo file not found at '{MockConfig.LOGO_PATH}'.")

    print("\nQRGenerator test finished.")
