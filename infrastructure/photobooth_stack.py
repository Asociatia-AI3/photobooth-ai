# photobooth_ai/cdk_infrastructure/photobooth_s3_stack.py
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct

class PhotoboothS3Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Create the S3 Bucket for storing photos
        # Bucket names must be globally unique. CDK will generate a unique name.
        # For production, consider not setting auto_delete_objects and removal_policy to DESTROY
        photo_bucket = s3.Bucket(
            self, "PhotoboothBucket",
            versioned=False,  # Poți seta True dacă dorești versionare
            encryption=s3.BucketEncryption.S3_MANAGED, # Criptare server-side
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, # Recomandat
            # ATENȚIE: Următoarele două linii sunt pentru dezvoltare/testare facilă.
            # Pentru producție, acestea ar trebui setate la False sau eliminate,
            # și bucket-ul ar trebui reținut sau golit manual înainte de ștergere.
            auto_delete_objects=True, # Șterge obiectele la distrugerea stack-ului (doar dacă bucket-ul e gol fără asta)
            removal_policy=RemovalPolicy.DESTROY, # Șterge bucket-ul la distrugerea stack-ului
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=[
                        "*",
                    ],
                    allowed_headers=["*"], 
                ),
            ]
        )

        # 2. Create an IAM Group for Photobooth users
        photobooth_user_group = iam.Group(self, "PhotoboothUserGroup")

        # 3. Create an IAM Policy Document granting necessary S3 permissions
        s3_access_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "s3:PutObject", # Pentru a încărca poze
                        "s3:GetObject"  # Pentru a genera presigned URLs pentru download
                    ],
                    resources=[
                        photo_bucket.bucket_arn + "/*" # Permisiuni pe obiectele din bucket
                    ],
                    effect=iam.Effect.ALLOW
                ),
                iam.PolicyStatement( # Permite listarea bucket-ului, util pentru unele SDK-uri, dar nu strict necesar pentru Put/Get Object
                    actions=["s3:ListBucket"],
                    resources=[photo_bucket.bucket_arn],
                    effect=iam.Effect.ALLOW
                )
            ]
        )

        # 4. Create an IAM Managed Policy from the document
        photobooth_s3_policy = iam.ManagedPolicy(
            self, "PhotoboothS3AccessPolicy",
            document=s3_access_policy_document,
            description="Policy for Photobooth app to access its S3 bucket"
        )
        
        # 5. Attach the policy to the group
        photobooth_user_group.add_managed_policy(photobooth_s3_policy)

        # 6. Output the S3 bucket name and IAM Group name
        CfnOutput(
            self, "OutputPhotoboothBucketName",
            value=photo_bucket.bucket_name,
            description="Name of the S3 bucket for storing photobooth images."
        )
        CfnOutput(
            self, "OutputPhotoboothUserGroupName",
            value=photobooth_user_group.group_name,
            description="Name of the IAM Group. Add your IAM user (for the Pi) to this group."
        )

        self.bucket_name = photo_bucket.bucket_name # Pentru a putea fi accesat dacă stack-ul e importat
        self.user_group_name = photobooth_user_group.group_name
