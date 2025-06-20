// server/generatePresignedUrl.ts
import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

// Definim o interfață pentru a tipa variabilele de mediu
interface AwsConfig {
    accessKeyId: string;
    secretAccessKey: string;
    region: string;
    bucketName: string;
}

// Modificăm funcția pentru a primi configurația AWS
export async function generatePresignedUrl(
    fileName: string,
    fileType: string,
    awsConfig: AwsConfig
): Promise<string> {
    const { accessKeyId, secretAccessKey, region, bucketName } = awsConfig;

    const s3Client = new S3Client({
        region: region,
        credentials: {
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey,
        },
    });

    const key = `uploads/${fileName}`; // Definește calea în S3
    const command = new PutObjectCommand({
        Bucket: bucketName,
        Key: key,
        ContentType: fileType,
    });

    try {
        const presignedUrl = await getSignedUrl(s3Client, command, {
            expiresIn: 600, // URL-ul va fi valid timp de 600 de secunde (10 minute)
        });
        console.log(`URL pre-signed generat pentru ${key}: ${presignedUrl}`);
        return presignedUrl;
    } catch (error) {
        console.error('Eroare la generarea URL-ului pre-signed:', error);
        throw new Error(`Could not generate pre-signed URL: ${error instanceof Error ? error.message : String(error)}`);
    }
}

// Noua funcție pentru URL pre-signed de citire (GET)
export async function generatePresignedReadUrl(
    key: string,
    awsConfig: AwsConfig,
    expiresIn: number = 3600 // Durata de valabilitate în secunde (implicit 1 oră)
): Promise<string> {
    const { accessKeyId, secretAccessKey, region, bucketName } = awsConfig;

    const s3Client = new S3Client({
        region: region,
        credentials: {
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey,
        },
    });

    const command = new GetObjectCommand({
        Bucket: bucketName,
        Key: key,
    });

    try {
        const presignedUrl = await getSignedUrl(s3Client, command, { expiresIn });
        console.log(`URL pre-signed de citire generat pentru ${key}: ${presignedUrl}`);
        return presignedUrl;
    } catch (error) {
        console.error('Eroare la generarea URL-ului pre-signed de citire:', error);
        throw new Error(`Could not generate pre-signed read URL: ${error instanceof Error ? error.message : String(error)}`);
    }
}