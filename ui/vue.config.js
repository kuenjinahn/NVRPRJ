const path = require('path');
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

let configJson = {};
try {
  configJson = require('./config.json');
} catch (e) {
  console.log('config.json not found, using default config');
}

process.env.VUE_APP_SERVER_PORT = configJson.port || 9091;

// config.ini에서 IP 설정을 읽어오는 함수
const fs = require('fs');

const getApiTarget = () => {
  try {
    // config.ini 파일 경로 (상위 디렉토리의 config.ini)
    const configPath = path.join(__dirname, '..', 'config.ini');

    if (fs.existsSync(configPath)) {
      const configContent = fs.readFileSync(configPath, 'utf8');

      // [WEB] 섹션에서 IP와 포트 추출
      const webMatch = configContent.match(/\[WEB\]\s*\n\s*ip\s*=\s*([^\n]+)/);
      const portMatch = configContent.match(/\[WEB\]\s*\n\s*ip\s*=\s*([^\n]+)\s*\n\s*port\s*=\s*([^\n]+)/);

      if (webMatch && webMatch[1]) {
        const webIp = webMatch[1].trim();
        let webPort = '9091'; // 기본 포트

        // 포트가 설정되어 있으면 사용
        if (portMatch && portMatch[2]) {
          webPort = portMatch[2].trim();
        }

        console.log(`[Config] Using WEB IP:Port from config.ini: ${webIp}:${webPort}`);
        return `http://${webIp}:${webPort}`;
      }
    }

    // config.ini가 없거나 [WEB] IP가 없으면 기본값 사용
    console.log('[Config] Using default API target (localhost:9091)');
    return 'http://localhost:9091';
  } catch (error) {
    console.error('[Config] Error reading config.ini:', error.message);
    console.log('[Config] Using default API target (localhost:9091)');
    return 'http://localhost:9091';
  }
};


module.exports = {
  transpileDependencies: ['vuetify'],
  devServer: {
    port: 9092,
    proxy: {
      '/api': {
        target: getApiTarget(),
        changeOrigin: true,
        pathRewrite: {
          '^/api': '/api'
        }
      }
    }
  },
  outputDir: path.resolve(__dirname, 'dist'),
  assetsDir: 'static',
  indexPath: 'index.html',
  productionSourceMap: false,
  pwa: {
    name: 'NVR',
    themeColor: '#4DBA87',
    msTileColor: '#000000',
    appleMobileWebAppCapable: 'yes',
    appleMobileWebAppStatusBarStyle: 'black',
    assetsVersion: Date.now(),
    manifestPath: 'manifest.json',
    manifestOptions: {
      lang: 'en',
      dir: 'ltr',
      name: 'camera.ui',
      short_name: 'camera.ui',
      description: 'camera.ui is a user interface for RTSP capable cameras.',
      theme_color: '#f1f1f1',
      background_color: '#f1f1f1',
      display: 'standalone',
      orientation: 'any',
      id: '/',
      scope: '/',
      start_url: '/',
      icons: [
        {
          src: '/img/icons/android-chrome-192x192.png',
          sizes: '192x192',
          type: 'image/png',
        },
        {
          src: '/img/icons/android-chrome-512x512.png',
          sizes: '512x512',
          type: 'image/png',
        },
        {
          src: '/img/icons/android-chrome-maskable-192x192.png',
          sizes: '192x192',
          type: 'image/png',
          purpose: 'maskable',
        },
        {
          src: '/img/icons/android-chrome-maskable-512x512.png',
          sizes: '512x512',
          type: 'image/png',
          purpose: 'maskable',
        },
        {
          src: '/img/icons/apple-touch-icon-dark-60x60.png',
          sizes: '60x60',
          type: 'image/png',
        },
        {
          src: '/img/icons/apple-touch-icon-dark-76x76.png',
          sizes: '76x76',
          type: 'image/png',
        },
        {
          src: '/img/icons/apple-touch-icon-dark-120x120.png',
          sizes: '120x120',
          type: 'image/png',
        },
        {
          src: '/img/icons/apple-touch-icon-dark-152x152.png',
          sizes: '152x152',
          type: 'image/png',
        },
        {
          src: '/img/icons/apple-touch-icon-dark-180x180.png',
          sizes: '180x180',
          type: 'image/png',
        },
        {
          src: '/img/icons/apple-touch-icon-dark.png',
          sizes: '180x180',
          type: 'image/png',
        },
        {
          src: '/img/icons/favicon-16x16.png',
          sizes: '16x16',
          type: 'image/png',
        },
        {
          src: '/img/icons/favicon-32x32.png',
          sizes: '32x32',
          type: 'image/png',
        },
        {
          src: '/img/icons/msapplication-icon-144x144.png',
          sizes: '144x144',
          type: 'image/png',
        },
        {
          src: '/img/icons/mstile-150x150.png',
          sizes: '150x150',
          type: 'image/png',
        },
      ],
    },
    iconPaths: {
      favicon32: 'img/icons/favicon-32x32.png',
      favicon16: 'img/icons/favicon-16x16.png',
      appleTouchIcon: 'img/icons/apple-touch-icon-dark-180x180.png',
      maskIcon: 'img/icons/safari-pinned-tab.svg',
      msTileImage: 'img/icons/msapplication-icon-144x144.png',
    },
    workboxPluginMode: 'GenerateSW',
    workboxOptions: {
      skipWaiting: true,
      clientsClaim: true
    }
  },
  chainWebpack: (config) => {
    config.performance.maxEntrypointSize(500000).maxAssetSize(500000);
    config.plugin('html').tap((arguments_) => {
      const payload = arguments_;
      payload[0].title = 'camera.ui';
      return payload;
    });
  },
  configureWebpack: {
    /*performance: {
      hints: process.env.NODE_ENV === 'production' ? false : 'warning',
    },*/
    module: {
      rules: [
        {
          test: /\.js$/,
          include: [
            path.resolve(__dirname, 'node_modules/vue-echarts'),
            path.resolve(__dirname, 'node_modules/resize-detector'),
            path.resolve(__dirname, 'node_modules/@vue/composition-api')
          ],
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                ['@babel/preset-env', {
                  targets: {
                    browsers: ['> 1%', 'last 2 versions', 'not dead']
                  }
                }]
              ],
              plugins: ['@babel/plugin-proposal-optional-chaining']
            }
          }
        }
      ]
    },
    resolve: {
      alias: {
        jquery: path.resolve(__dirname, 'node_modules/gridstack/dist/jq/jquery.js'),
        'jquery-ui': path.resolve(__dirname, 'node_modules/gridstack/dist/jq/jquery-ui.js'),
        'jquery.ui': path.resolve(__dirname, 'node_modules/gridstack/dist/jq/jquery-ui.js'),
        'jquery.ui.touch-punch': path.resolve(__dirname, 'node_modules/gridstack/dist/jq/jquery.ui.touch-punch.js'),
      },
    },
    plugins: [
      new BundleAnalyzerPlugin({
        analyzerMode: process.env.ANALYZE ? 'server' : 'disabled'
      })
    ]
  },
  css: {
    extract:
      process.env.NODE_ENV === 'production'
        ? {
          ignoreOrder: true,
        }
        : false,
  },
};
