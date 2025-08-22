const express = require('express');
const path = require('path');
const fs = require('fs');
const http = require('http');
const https = require('https');
const { createProxyMiddleware } = require('http-proxy-middleware');
const app = express();
const port = process.env.PORT || 9092;

// CORS 미들웨어
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');

  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});

// 모든 요청 로깅
app.use((req, res, next) => {
  console.log(`[Request] ${req.method} ${req.url} - ${new Date().toISOString()}`);
  next();
});

// 현재 디렉토리의 dist 폴더를 정적 파일 디렉토리로 설정
const distPath = path.join(__dirname, 'dist');
console.log('Serving static files from:', distPath);

// config.ini에서 IP 설정을 읽어오는 함수

const getApiTarget = () => {
  try {
    // config.ini 파일 경로 - 여러 경로 시도
    let configPath = path.join(__dirname, '..', 'config.ini');

    // 첫 번째 경로가 없으면 다른 경로 시도
    if (!fs.existsSync(configPath)) {
      configPath = path.join(__dirname, '..', '..', 'config.ini');
    }

    // 두 번째 경로도 없으면 현재 디렉토리에서 상위로 검색
    if (!fs.existsSync(configPath)) {
      configPath = path.join(__dirname, '..', '..', '..', 'config.ini');
    }

    console.log(`[Config] Trying config.ini path: ${configPath}`);

    if (fs.existsSync(configPath)) {
      const configContent = fs.readFileSync(configPath, 'utf8');
      console.log(`[Config] Config file content preview:`, configContent.substring(0, 500));

      // [WEB] 섹션에서 IP와 포트 추출 - 정규식 개선
      const webSectionMatch = configContent.match(/\[WEB\]([\s\S]*?)(?=\[|$)/);
      console.log(`[Config] Web section match:`, webSectionMatch ? webSectionMatch[1] : 'not found');

      if (webSectionMatch) {
        const webSection = webSectionMatch[1];

        // 주석 처리된 IP는 무시하고 실제 IP만 추출
        const ipMatch = webSection.match(/^ip\s*=\s*([^\n\r#]+)/m);
        const portMatch = webSection.match(/^port\s*=\s*([^\n\r#]+)/m);

        console.log(`[Config] IP match result:`, ipMatch ? ipMatch[1].trim() : 'not found');
        console.log(`[Config] Port match result:`, portMatch ? portMatch[1].trim() : 'not found');

        if (ipMatch && ipMatch[1]) {
          const webIp = ipMatch[1].trim();
          let webPort = '9091'; // 기본 포트

          // 포트가 설정되어 있으면 사용
          if (portMatch && portMatch[1]) {
            webPort = portMatch[1].trim();
          }

          const target = `http://${webIp}:${webPort}`;
          console.log(`[Config] Using WEB IP:Port from config.ini: ${webIp}:${webPort}`);
          console.log(`[Config] Final target URL: ${target}`);
          return target;
        } else {
          console.log(`[Config] No valid IP found in [WEB] section`);
        }
      } else {
        console.log(`[Config] No [WEB] section found in config.ini`);
      }
    } else {
      console.log(`[Config] Config file not found: ${configPath}`);
    }

    // config.ini가 없거나 [WEB] IP가 없으면 기본값 사용
    console.log('[Config] Using default API target (localhost:9091)');
    return 'http://localhost:9091';
  } catch (error) {
    console.error('[Config] Error reading config.ini:', error.message);
    console.error('[Config] Error stack:', error.stack);
    console.log('[Config] Using default API target (localhost:9091)');
    return 'http://localhost:9091';
  }
};

// 환경 변수로 강제 설정 가능
const FORCE_BACKEND_IP = process.env.FORCE_BACKEND_IP;
const FORCE_BACKEND_PORT = process.env.FORCE_BACKEND_PORT || '9091';

if (FORCE_BACKEND_IP) {
  console.log(`[Config] Using forced backend IP: ${FORCE_BACKEND_IP}:${FORCE_BACKEND_PORT}`);
  return `http://${FORCE_BACKEND_IP}:${FORCE_BACKEND_PORT}`;
}

// 동적 프록시 타겟을 위한 함수
const createProxyMiddlewareWithDynamicTarget = () => {
  return createProxyMiddleware({
    target: getApiTarget(),  // 동적으로 타겟 가져오기
    changeOrigin: true,
    secure: false, // HTTPS 검증 비활성화
    timeout: 30000, // 30초 타임아웃
    proxyTimeout: 30000,
    router: (req) => {
      // 요청 시마다 최신 타겟 가져오기
      const target = getApiTarget();
      console.log(`[Proxy] Dynamic target for ${req.path}: ${target}`);
      return target;
    },
    onProxyReq: (proxyReq, req, res) => {
      const target = getApiTarget();
      console.log(`[Proxy] ${req.method} ${req.url} → ${target}${proxyReq.path}`);
      console.log(`[Proxy] Request headers:`, req.headers);
      console.log(`[Proxy] Proxy headers:`, proxyReq.getHeaders());

      // 헤더 설정
      proxyReq.setHeader('X-Forwarded-For', req.connection.remoteAddress);
      proxyReq.setHeader('X-Forwarded-Proto', req.protocol);
      proxyReq.setHeader('X-Forwarded-Host', req.get('host'));
    },
    onProxyRes: (proxyRes, req, res) => {
      console.log(`[Proxy] Response: ${proxyRes.statusCode} for ${req.method} ${req.url}`);

      // CORS 헤더 설정
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    },
    onError: (err, req, res) => {
      console.error('Proxy Error:', err);
      console.error('Proxy Error Details:', {
        message: err.message,
        code: err.code,
        errno: err.errno,
        syscall: err.syscall,
        address: err.address,
        port: err.port
      });

      // 현재 설정된 타겟 정보 로깅
      const currentTarget = getApiTarget();
      console.error(`[Proxy] Current target: ${currentTarget}`);
      console.error(`[Proxy] Request URL: ${req.url}`);
      console.error(`[Proxy] Request method: ${req.method}`);

      // 클라이언트에게 더 자세한 에러 정보 제공
      if (!res.headersSent) {
        res.status(500).json({
          error: 'Proxy Error',
          message: err.message,
          code: err.code,
          target: currentTarget,
          request: {
            url: req.url,
            method: req.method,
            timestamp: new Date().toISOString()
          }
        });
      }
    }
  });
};

// API 프록시 미들웨어 설정
const proxyMiddleware = createProxyMiddlewareWithDynamicTarget();

// 모든 API 경로를 하나의 프록시로 처리
app.use(['/api', '/auth', '/config', '/cameras', '/recordings', '/events', '/users', '/system', '/backup', '/notifications', '/alerts', '/schedules', '/subscribe', '/statistic'], (req, res, next) => {
  console.log(`[Proxy] Intercepting: ${req.method} ${req.path}`);
  console.log(`[Proxy] Original URL: ${req.url}`);
  console.log(`[Proxy] Original path: ${req.path}`);

  // 경로 리라이팅: /auth/login → /api/auth/login
  let targetPath = req.path;
  if (!req.path.startsWith('/api/')) {
    targetPath = `/api${req.path}`;
  }

  console.log(`[Proxy] Rewriting: ${req.path} → ${targetPath}`);
  console.log(`[Proxy] Target: ${getApiTarget()}${targetPath}`);

  // 프록시 미들웨어로 전달
  req.url = targetPath;
  console.log(`[Proxy] Modified req.url: ${req.url}`);

  return proxyMiddleware(req, res, next);
});

// 추가 API 경로들도 프록시 처리
app.use(['/login', '/logout', '/register', '/password'], (req, res, next) => {
  console.log(`[Proxy] Auth intercepting: ${req.method} ${req.path}`);

  // 인증 관련 경로를 /api/auth로 리다이렉트
  const targetPath = `/api/auth${req.path}`;
  console.log(`[Proxy] Auth rewriting: ${req.path} → ${targetPath}`);

  req.url = targetPath;
  return proxyMiddleware(req, res, next);
});

// Socket.IO 연결을 위한 프록시 설정
app.use('/socket.io', (req, res, next) => {
  console.log(`[Socket.IO Proxy] Intercepting: ${req.method} ${req.path}`);
  console.log(`[Socket.IO Proxy] Target: ${getApiTarget()}`);

  // Socket.IO 요청을 백엔드로 프록시
  const target = getApiTarget();
  const proxy = createProxyMiddleware({
    target: target,
    changeOrigin: true,
    ws: true, // WebSocket 지원
    logLevel: 'debug'
  });

  return proxy(req, res, next);
});

// 모든 API 요청에 대한 통합 프록시 처리
app.use((req, res, next) => {
  // API 경로인지 확인
  if (req.path.startsWith('/api/') || req.path.startsWith('/auth/') ||
    ['/login', '/logout', '/register', '/password'].includes(req.path)) {
    console.log(`[Proxy] Global API intercepting: ${req.method} ${req.path}`);
    return proxyMiddleware(req, res, next);
  }

  // API가 아닌 경우 다음 미들웨어로
  next();
});

// 백엔드 서버 연결 테스트 엔드포인트
app.get('/test-backend', (req, res) => {
  const target = getApiTarget();
  console.log(`[Test] Testing connection to: ${target}`);

  // HTTP 요청을 사용한 간단한 연결 테스트
  const url = new URL(target);
  const options = {
    hostname: url.hostname,
    port: url.port || 80,
    path: '/api/auth/check',
    method: 'GET',
    timeout: 5000 // 5초 타임아웃
  };

  console.log(`[Test] HTTP request options:`, options);

  const httpModule = url.protocol === 'https:' ? https : http;
  const httpReq = httpModule.request(options, (response) => {
    console.log(`[Test] Backend response status: ${response.statusCode}`);

    let data = '';
    response.on('data', (chunk) => {
      data += chunk;
    });

    response.on('end', () => {
      if (response.statusCode === 200) {
        res.json({
          status: 'success',
          message: 'Backend server is reachable',
          target: target,
          response: response.statusCode,
          data: data
        });
      } else if (response.statusCode === 401) {
        res.json({
          status: 'success',
          message: 'Backend server is reachable (401 Unauthorized is expected without auth token)',
          target: target,
          response: response.statusCode,
          note: 'This is normal - the backend is working but requires authentication'
        });
      } else {
        res.json({
          status: 'error',
          message: 'Backend server responded with error',
          target: target,
          response: response.statusCode,
          data: data
        });
      }
    });
  });

  httpReq.on('error', (error) => {
    console.error('[Test] Backend connection failed:', error.message);
    res.status(500).json({
      status: 'error',
      message: 'Backend server is not reachable',
      target: target,
      error: error.message,
      errorCode: error.code
    });
  });

  httpReq.on('timeout', () => {
    console.error('[Test] Backend connection timeout');
    httpReq.destroy();
    res.status(500).json({
      status: 'error',
      message: 'Backend server connection timeout',
      target: target,
      error: 'Connection timeout after 5 seconds'
    });
  });

  httpReq.end();
});

// 간단한 ping 테스트 엔드포인트
app.get('/ping', (req, res) => {
  res.json({
    status: 'ok',
    message: 'UI server is running',
    timestamp: new Date().toISOString(),
    port: port
  });
});

// 프록시 상태 확인 엔드포인트
app.get('/proxy-status', (req, res) => {
  const target = getApiTarget();
  const configPath = path.join(__dirname, '..', 'config.ini');

  let configInfo = {};
  try {
    if (fs.existsSync(configPath)) {
      const configContent = fs.readFileSync(configPath, 'utf8');
      const webMatch = configContent.match(/\[WEB\]\s*\n\s*ip\s*=\s*([^\n]+)/);
      const portMatch = configContent.match(/\[WEB\]\s*\n\s*ip\s*=\s*([^\n]+)\s*\n\s*port\s*=\s*([^\n]+)/);

      configInfo = {
        configFile: configPath,
        exists: true,
        webSection: {
          ip: webMatch ? webMatch[1].trim() : 'not found',
          port: portMatch ? portMatch[2].trim() : 'not found'
        },
        rawContent: configContent.substring(0, 1000)
      };
    } else {
      configInfo = {
        configFile: configPath,
        exists: false
      };
    }
  } catch (error) {
    configInfo = {
      configFile: configPath,
      exists: 'error',
      error: error.message
    };
  }

  res.json({
    status: 'active',
    target: target,
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
    port: port,
    config: configInfo
  });
});

// 정적 파일 제공
app.use(express.static(distPath));

// 모든 요청을 index.html로 리다이렉트 (SPA를 위한 설정)
app.get('*', (req, res) => {
  const indexPath = path.join(distPath, 'index.html');
  console.log('Serving index.html from:', indexPath);

  // 파일 존재 여부 확인
  if (require('fs').existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send('index.html not found. Please run npm run build first.');
  }
});

// 에러 핸들링
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).send('Internal Server Error');
});

app.listen(port, () => {
  console.log('='.repeat(50));
  console.log(`UI server is running on port ${port}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`API target: ${getApiTarget()}`);
  console.log(`Backend URL: ${getApiTarget()}`);
  console.log('='.repeat(50));
  console.log(`Please make sure you have run 'npm run build' first`);
}); 