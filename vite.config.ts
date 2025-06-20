// vite.config.ts
import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
// Importă ambele funcții de generare URL
import { generatePresignedUrl, generatePresignedReadUrl } from './server/generatePresignedUrl';

export default defineConfig(({ mode }) => {
  // Load environment variables based on the current mode
  const env = loadEnv(mode, process.cwd(), ''); // Use process.cwd() for root directory

  // Extract AWS specific environment variables
  const awsConfig = {
    accessKeyId: env.AWS_ACCESS_KEY_ID || '', // Asigură-te că aceste variabile sunt în .env
    secretAccessKey: env.AWS_SECRET_ACCESS_KEY || '',
    region: env.AWS_REGION || 'eu-central-1', // Default region if not specified
    bucketName: env.S3_BUCKET_NAME || '',
  };

  // Basic validation for AWS config (optional, but good practice)
  if (!awsConfig.accessKeyId || !awsConfig.secretAccessKey || !awsConfig.bucketName) {
    console.warn('WARNING: AWS credentials or S3_BUCKET_NAME are not fully configured in .env. API routes might fail.');
  }

  return {
    define: {
      // These are for the frontend client-side code
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.AI3_LOGIN': JSON.stringify(env.AI3_LOGIN),
      'process.env.AI3_PW': JSON.stringify(env.AI3_PW),
      'process.env.S3_BUCKET_NAME': JSON.stringify(env.S3_BUCKET_NAME),
      // Also expose AWS config for frontend if needed (e.g., for direct S3 upload with Cognito Identity Pool)
      'process.env.AWS_ACCESS_KEY_ID': JSON.stringify(awsConfig.accessKeyId),
      'process.env.AWS_SECRET_ACCESS_KEY': JSON.stringify(awsConfig.secretAccessKey),
      'process.env.AWS_REGION': JSON.stringify(awsConfig.region),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    },
    plugins: [vue()],
    server: {
      // Eliminăm blocul `proxy` dacă gestionăm rutele direct în `configureServer`
      // `proxy` este pentru redirecționarea cererilor către un *server extern*.
      // `configureServer` este pentru gestionarea cererilor *în cadrul* serverului Vite.
      proxy: {}, // Lăsăm gol sau îl eliminăm complet dacă nu ai alte proxy-uri

      configureServer(server: any) {
        console.info("Configure started");
        // --- Middleware pentru /api/presigned-url (PUT) ---
        server.middlewares.use(async (req: any, res: any, next: any) => {
          console.log(`Dev URL: ${req.url}`);
          // Verifică dacă URL-ul cererii începe cu ruta API și metoda este GET
          if (req.url?.startsWith('/api/presigned-url') && req.method === 'GET') {
            const url = new URL(req.url, `http://${req.headers.host}`);
            const fileName = url.searchParams.get('fileName');
            const fileType = url.searchParams.get('fileType');

            // Set CORS headers early for preflight and actual requests
            res.setHeader('Access-Control-Allow-Origin', '*'); // Adaptează la originea aplicației tale!
            res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With'); // Include X-Requested-With for some clients

            if (req.method === 'OPTIONS') { // Handle CORS preflight
              res.statusCode = 204;
              res.end();
              return; // Terminate response
            }

            if (!fileName || !fileType) {
              res.statusCode = 400;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: 'Missing fileName or fileType' }));
              return;
            }

            try {
              const presignedUrl = await generatePresignedUrl(fileName, fileType, awsConfig);
              res.statusCode = 200;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ presignedUrl }));
            } catch (error: any) {
              console.error('Error in /api/presigned-url:', error);
              res.statusCode = 500;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: error.message || 'Internal server error' }));
            }
            return; // Important: Terminate the request here to prevent fallthrough
          }

          // --- Middleware pentru /api/presigned-read-url (GET) ---
          if (req.url?.startsWith('/api/presigned-read-url') && req.method === 'GET') {
            const url = new URL(req.url, `http://${req.headers.host}`);
            const s3Key = url.searchParams.get('key');
            const expiresIn = url.searchParams.get('expiresIn');

            // Set CORS headers early
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With');

            if (req.method === 'OPTIONS') { // Handle CORS preflight
              res.statusCode = 204;
              res.end();
              return;
            }

            if (!s3Key) {
              res.statusCode = 400;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: 'Missing S3 object key' }));
              return;
            }

            try {
              const expiresInNum = expiresIn ? parseInt(expiresIn, 10) : undefined;
              const presignedReadUrl = await generatePresignedReadUrl(s3Key, awsConfig, expiresInNum);
              res.statusCode = 200;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ presignedReadUrl }));
            } catch (error: any) {
              console.error('Error in /api/presigned-read-url:', error);
              res.statusCode = 500;
              res.setHeader('Content-Type', 'application/json');
              res.end(JSON.stringify({ error: error.message || 'Internal server error' }));
            }
            return; // Important: Terminate the request here
          }

          // Dacă cererea nu este pentru API-ul nostru, continuă la următoarele middleware-uri Vite
          next();
        });
      },
    },
  };
});