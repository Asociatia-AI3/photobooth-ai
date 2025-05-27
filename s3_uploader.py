# photobooth_ai/s3_uploader.py
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import config
import os
import time

class S3Uploader:
    def __init__(self):
        self.bucket_name = config.AWS_S3_BUCKET_NAME
        self.region = config.AWS_S3_REGION
        self.s3_client = boto3.client(
            's3',
            region_name=self.region
            # Credentialele ar trebui configurate în mediul AWS (CLI, rol IAM, variabile de mediu)
            # aws_access_key_id=config.AWS_ACCESS_KEY_ID, # Nu e recomandat direct în cod
            # aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY # Nu e recomandat direct în cod
        )

    def upload_file(self, file_path, object_name=None):
        """
        Încarcă un fișier pe un bucket S3.

        Args:
            file_path (str): Calea către fișierul local.
            object_name (str, optional): Numele obiectului S3. Dacă nu este specificat,
                                         se folosește numele fișierului de bază.

        Returns:
            str: URL-ul presigned pentru descărcare dacă încărcarea a reușit, None altfel.
        """
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return None

        if object_name is None:
            object_name = os.path.basename(file_path)
        
        # Adaugă prefixul din config dacă există
        if config.S3_PHOTO_PREFIX:
            object_name = os.path.join(config.S3_PHOTO_PREFIX, object_name).replace("\\", "/") # Asigură slash-uri corecte

        # Generează un nume unic pentru a evita suprascrierile, de ex. cu timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        name, ext = os.path.splitext(object_name)
        unique_object_name = f"{name}_{timestamp}{ext}"

        print(f"Uploading {file_path} to S3 bucket {self.bucket_name} as {unique_object_name}...")
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, unique_object_name)
            print(f"File {unique_object_name} uploaded successfully to {self.bucket_name}.")
            
            # Generează un URL presigned pentru acces temporar
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': unique_object_name},
                ExpiresIn=config.S3_LINK_EXPIRATION_SECONDS
            )
            print(f"Generated presigned URL (expires in {config.S3_LINK_EXPIRATION_SECONDS}s): {url}")
            return url
            
        except FileNotFoundError:
            print(f"Error: The file {file_path} was not found for upload.")
        except NoCredentialsError:
            print("Error: AWS credentials not found. Configure AWS CLI or environment variables.")
        except PartialCredentialsError:
            print("Error: Incomplete AWS credentials. Configure AWS CLI or environment variables.")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == 'NoSuchBucket':
                print(f"Error: S3 bucket '{self.bucket_name}' does not exist or you don't have access.")
            elif error_code == 'AccessDenied':
                print(f"Error: Access denied to S3 bucket '{self.bucket_name}'. Check permissions.")
            else:
                print(f"ClientError during S3 upload: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during S3 upload: {e}")
            
        return None

if __name__ == '__main__':
    # Test S3 Uploader
    # Asigură-te că AWS_S3_BUCKET_NAME și AWS_S3_REGION sunt setate în config.py
    # și că ai credentiale AWS configurate.

    # Mock config pentru testare
    class MockConfig:
        AWS_S3_BUCKET_NAME = "your-test-bucket-photobooth" # Modifică cu un bucket real pentru test
        AWS_S3_REGION = "eu-central-1" # Modifică cu regiunea bucket-ului tău
        S3_PHOTO_PREFIX = "test_uploads/"
        S3_LINK_EXPIRATION_SECONDS = 600
        TEMP_DIR = "temp"

    # Creează directorul temp și un fișier de test dacă nu există
    if not os.path.exists(MockConfig.TEMP_DIR):
        os.makedirs(MockConfig.TEMP_DIR)
    
    test_file_name = "s3_upload_test.txt"
    test_file_path = os.path.join(MockConfig.TEMP_DIR, test_file_name)
    with open(test_file_path, "w") as f:
        f.write("This is a test file for S3 upload.")
    
    # Folosește config-ul global dacă disponibil, altfel mock-ul
    try:
        import config as app_config # type: ignore
        # Verifică dacă bucket-ul este cel placeholder pentru a nu rula testul accidental
        if app_config.AWS_S3_BUCKET_NAME == "your-s3-bucket-name-for-photos":
             print("S3Uploader test skipped: AWS_S3_BUCKET_NAME is set to placeholder.")
             app_config = None # Previne rularea testului
        elif not app_config.AWS_S3_BUCKET_NAME or not app_config.AWS_S3_REGION:
            print("S3Uploader test skipped: AWS_S3_BUCKET_NAME or AWS_S3_REGION not configured in actual config.")
            app_config = None # Previne rularea testului

    except ImportError:
        app_config = MockConfig() # type: ignore
        print("Using MockConfig for s3_uploader test.")
        # Suprascrie config-ul global pentru a testa comportamentul mock al funcției
        import sys
        # sys.modules['config'] = app_config # Comentat pentru a nu interfera cu boto3 dacă config real nu e setat bine

    if app_config and app_config.AWS_S3_BUCKET_NAME and app_config.AWS_S3_BUCKET_NAME != "your-s3-bucket-name-for-photos":
        print(f"\n--- Testing S3 Upload to bucket: {app_config.AWS_S3_BUCKET_NAME} ---")
        
        # Forțează utilizarea MockConfig pentru test, dacă este necesar, suprascriind din nou
        # Acest lucru e complicat din cauza modului în care rulează codul aici. Ideal ar fi să ai un config de test.
        original_config = config # Păstrează originalul
        globals()['config'] = app_config # Suprascrie temporar config-ul global pentru instanțierea S3Uploader

        uploader = S3Uploader() # Se va folosi config-ul suprascris
        
        globals()['config'] = original_config # Restaurează config-ul original

        download_url = uploader.upload_file(test_file_path) # Va folosi bucket/region din app_config

        if download_url:
            print(f"Test file uploaded successfully. Download URL: {download_url}")
            print("VERIFY: Check your S3 bucket to confirm the upload and try the URL.")
        else:
            print("Test file upload failed. Check AWS configuration and bucket policies.")
            print(f"Ensure bucket '{app_config.AWS_S3_BUCKET_NAME}' exists in region '{app_config.AWS_S3_REGION}' and you have write permissions.")
    else:
        if app_config: # Doar dacă app_config a fost setat inițial (nu placeholder)
             print("\nS3Uploader test skipped due to placeholder or missing S3 config.")

    # Curăță fișierul de test
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
    
    print("\nS3Uploader test finished.")
