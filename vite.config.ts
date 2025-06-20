import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import { generatePresignedUrl, generatePresignedReadUrl } from './server/generatePresignedUrl';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  const awsConfig = {
    accessKeyId: env.AWS_ACCESS_KEY_ID || '',
    secretAccessKey: env.AWS_SECRET_ACCESS_KEY || '',
    region: env.AWS_REGION || 'eu-central-1',
    bucketName: env.S3_BUCKET_NAME || '',
  };

  console.log('[Vite Config] Loaded S3_BUCKET_NAME:', awsConfig.bucketName);
  console.log('[Vite Config] Loaded AWS_REGION:', awsConfig.region);
  if (!awsConfig.accessKeyId || !awsConfig.secretAccessKey || !awsConfig.bucketName) {
    console.warn('⚠️ WARNING: AWS credentials or S3_BUCKET_NAME are not fully configured in your .env file. API routes might fail.');
  }

  return {
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.AI3_LOGIN': JSON.stringify(env.AI3_LOGIN),
      'process.env.AI3_PW': JSON.stringify(env.AI3_PW),
      'process.env.S3_BUCKET_NAME': JSON.stringify(env.S3_BUCKET_NAME),
      'process.env.AWS_REGION': JSON.stringify(awsConfig.region),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    },
    plugins: [vue()],
    server: {
      proxy: {
        '/api/presigned-url': {
          target: "http://does-not.exist",
          changeOrigin: true,
          secure: false,
          configure: (proxy, options) => {
            proxy.on('proxyReq', async (proxyReq, req, res) => {
              console.log(`[Vite Proxy] Intercepted request to: ${req.url} for method: ${req.method}`);

              const url = new URL(req.url!, `http://${req.headers.host}`);
              const fileName = url.searchParams.get('fileName');
              const fileType = url.searchParams.get('fileType');

              // AICI ESTE CRUCIAL: Setăm anteturile CORS și Content-Type O SINGURĂ DATĂ
              // indiferent de rezultat, ÎNAINTE de orice `res.end()` sau `res.write()`.
              res.setHeader('Access-Control-Allow-Origin', '*');
              res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT');
              res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
              res.setHeader('Content-Type', 'application/json'); // Asigură-te că tipul de conținut este JSON

              if (req.method === 'OPTIONS') {
                console.log('[Vite Proxy] OPTIONS request received for /api/presigned-url, sending 204.');
                res.statusCode = 204;
                res.end();
                // Important: Oprește cererea către backend-ul fictiv al proxy-ului
                proxyReq.destroy(); 
                return;
              }

              if (!fileName || !fileType) {
                console.warn('[Vite Proxy] Missing fileName or fileType for /api/presigned-url.');
                res.statusCode = 400; // Bad Request
                res.end(JSON.stringify({ error: 'Missing fileName or fileType' }));
                proxyReq.destroy(); // Oprește cererea
                return;
              }

              try {
                const presignedUrl = await generatePresignedUrl(fileName, fileType, awsConfig);
                console.log('[Vite Proxy] Successfully generated presigned URL for upload.');
                res.statusCode = 200; // OK
                res.end(JSON.stringify({ presignedUrl }));
                proxyReq.destroy(); // Oprește cererea după răspuns
              } catch (error: any) {
                console.error('[Vite Proxy] Error handling /api/presigned-url:', error.message);
                res.statusCode = 500; // Internal Server Error
                res.end(JSON.stringify({ error: error.message || 'Internal server error' }));
                proxyReq.destroy(); // Oprește cererea chiar și la eroare
              }
            });
          },
        },

        '/api/presigned-read-url': {
          target: 'http://localhost',
          changeOrigin: true,
          secure: false,
          configure: (proxy, options) => {
            proxy.on('proxyReq', async (proxyReq, req, res) => {
              console.log(`[Vite Proxy] Intercepted read request to: ${req.url} for method: ${req.method}`);

              const url = new URL(req.url!, `http://${req.headers.host}`);
              const s3Key = url.searchParams.get('key');
              const expiresIn = url.searchParams.get('expiresIn');

              // AICI ESTE CRUCIAL: Setăm anteturile CORS și Content-Type O SINGURĂ DATĂ
              res.setHeader('Access-Control-Allow-Origin', '*');
              res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
              res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
              res.setHeader('Content-Type', 'application/json');

              if (req.method === 'OPTIONS') {
                console.log('[Vite Proxy] OPTIONS request received for /api/presigned-read-url, sending 204.');
                res.statusCode = 204;
                res.end();
                proxyReq.destroy(); // Oprește cererea
                return;
              }

              if (!s3Key) {
                console.warn('[Vite Proxy] Missing S3 object key for /api/presigned-read-url.');
                res.statusCode = 400; // Bad Request
                res.end(JSON.stringify({ error: 'Missing S3 object key' }));
                proxyReq.destroy(); // Oprește cererea
                return;
              }

              try {
                const expiresInNum = expiresIn ? parseInt(expiresIn, 10) : undefined;
                const presignedReadUrl = await generatePresignedReadUrl(s3Key, awsConfig, expiresInNum);
                console.log('[Vite Proxy] Successfully generated presigned read URL.');
                res.statusCode = 200; // OK
                res.end(JSON.stringify({ presignedReadUrl }));
                proxyReq.destroy(); // Oprește cererea după răspuns
              } catch (error: any) {
                console.error('[Vite Proxy] Error handling /api/presigned-read-url:', error.message);
                res.statusCode = 500; // Internal Server Error
                res.end(JSON.stringify({ error: error.message || 'Internal server error' }));
                proxyReq.destroy(); // Oprește cererea chiar și la eroare
              }
            });
          },
        },
      },
    },
  };
});