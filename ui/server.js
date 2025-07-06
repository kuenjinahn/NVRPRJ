const express = require('express');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');
const app = express();
const port = process.env.PORT || 9092;

// 현재 디렉토리의 dist 폴더를 정적 파일 디렉토리로 설정
const distPath = path.join(__dirname, 'dist');
console.log('Serving static files from:', distPath);

// API 프록시 설정
app.use('/api', createProxyMiddleware({
  target: 'http://20.41.121.184:9091',  // 프로덕션 API 서버 주소로 변경
  changeOrigin: true,
  pathRewrite: {
    '^/api': '/api'
  },
  onError: (err, req, res) => {
    console.error('Proxy Error:', err);
    res.status(500).send('Proxy Error');
  }
}));

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
  console.log(`UI server is running on port ${port}`);
  console.log(`Please make sure you have run 'npm run build' first`);
}); 