# photobooth_ai/cdk_infrastructure/app.py
import aws_cdk as cdk
from photobooth_stack import PhotoboothS3Stack
import os

app = cdk.App()

# Preia regiunea și contul din variabilele de mediu implicite ale AWS CLI/CDK
# Sau le poți hardcoda dacă este necesar (nu e recomandat pentru portabilitate)
aws_env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
)

PhotoboothS3Stack(
    app, "PhotoboothS3Stack-Prod", # Numele stack-ului în CloudFormation
    env=aws_env,
    description="S3 Bucket and IAM Group for the AI Photobooth application"
)

app.synth()
