// server/generatePresignedUrl.ts
import { S3Client } from '@aws-sdk/client-s3';
import { PutObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const AWS_REGION = process.env.AWS_REGION || 'eu-central-1';
const AWS_ACCESS_KEY_ID = process.env.AWS_ACCESS_KEY_ID;
const AWS_SECRET_ACCESS_KEY = process.env.AWS_SECRET_ACCESS_KEY;
const S3_BUCKET_NAME = process.env.S3_BUCKET_NAME || 'photobooths3stack-prod-photoboothbucket0359994f-5sgv4fdcjvfk';

const s3Client = new S3Client({
    region: AWS_REGION,
    credentials: {
        accessKeyId: AWS_ACCESS_KEY_ID!,
        secretAccessKey: AWS_SECRET_ACCESS_KEY!,
    },
});

export async function generatePresignedUrl(fileName: string, fileType: string): Promise<string> {
    const key = `uploads/${fileName}`;
    const command = new PutObjectCommand({
        Bucket: S3_BUCKET_NAME,
        Key: key,
        ContentType: fileType,
        ACL: 'public-read',
    });

    try {
        const presignedUrl = await getSignedUrl(s3Client, command, {
            expiresIn: 600,
        });
        console.log(`URL pre-signed generat pentru ${key}: ${presignedUrl}`);
        return presignedUrl;
    } catch (error) {
        console.error('Eroare la generarea URL-ului pre-signed:', error);
        throw new Error('Could not generate pre-signed URL.');
    }
}