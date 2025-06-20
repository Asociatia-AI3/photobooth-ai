import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue'; // Sau react(), etc.
import { generatePresignedUrl } from './server/generatePresignedUrl';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.AI3_LOGIN': JSON.stringify(env.AI3_LOGIN),
      'process.env.AI3_PW': JSON.stringify(env.AI3_PW),
      'process.env.S3_BUCKET_NAME': JSON.stringify(env.S3_BUCKET_NAME)
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    },
    plugins: [vue()], // Asigură-te că ai plugin-ul corect pentru framework-ul tău
    server: {
      proxy: {
        // Aceasta este o abordare comună pentru a redirecționa cererile API către un backend.
        // Pentru serverul de dezvoltare Vite, vom intercepta direct.
        // Puteți folosi și 'proxy' pentru a face request-uri către un server de backend separat.
      },
      // Aceasta este partea cheie pentru a crea o "rută" în serverul de dezvoltare Vite
      configureServer(server: any) {
        server.middlewares.use('/api/presigned-url', async (req, res, next) => {
          if (req.method === 'GET') { // Sau POST, în funcție de preferințe
            const url = new URL(req.url!, `http://${req.headers.host}`);
            const fileName = url.searchParams.get('fileName');
            const fileType = url.searchParams.get('fileType');

            if (!fileName || !fileType) {
              res.statusCode = 400;
              res.end(JSON.stringify({ error: 'Missing fileName or fileType' }));
              return;
            }

            try {
              const presignedUrl = await generatePresignedUrl(fileName, fileType);
              res.statusCode = 200;
              res.setHeader('Content-Type', 'application/json');
              // Permite CORS pentru această rută API
              res.setHeader('Access-Control-Allow-Origin', '*'); // Adaptează la originea aplicației tale!
              res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
              res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
              res.end(JSON.stringify({ presignedUrl }));
            } catch (error: any) {
              res.statusCode = 500;
              res.end(JSON.stringify({ error: error.message }));
            }
          } else if (req.method === 'OPTIONS') { // Răspunde la preflight requests
            res.statusCode = 204;
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
            res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
            res.end();
          } else {
            next(); // Permite altor middleware-uri să proceseze cererea
          }
        });
      },
    },
  };
});
