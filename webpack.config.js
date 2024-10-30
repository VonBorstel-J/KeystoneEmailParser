const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

module.exports = {
  mode: 'development',
  entry: './static/js/main.js',
  output: {
    path: path.resolve(__dirname, 'static/dist'),
    filename: 'bundle.js',
    publicPath: '/static/dist/',
  },
  devServer: {
    static: [
      {
        directory: path.join(__dirname, 'static'),
        publicPath: '/static'
      },
      {
        directory: path.join(__dirname, 'templates'),
        publicPath: '/'
      }
    ],
    compress: true,
    port: 8080,
    hot: true,
    historyApiFallback: true,
    proxy: {
      '/api': 'http://localhost:5000',
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true
      }
    }
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader'
        }
      },
      {
        test: /\.css$/,
        use: [
          MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader',
            options: {
              importLoaders: 1
            }
          },
          'postcss-loader'
        ]
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx', '.css'],
    alias: {
      '@': path.resolve(__dirname, 'static'),
      '@components': path.resolve(__dirname, 'static/components'),
      '@actions': path.resolve(__dirname, 'static/js/actions'),
      '@reducers': path.resolve(__dirname, 'static/js/reducers'),
      '@core': path.resolve(__dirname, 'static/js/core'),
      '@utils': path.resolve(__dirname, 'static/js/utils'),
      '@ui': path.resolve(__dirname, 'static/js/ui'),
      '@css': path.resolve(__dirname, 'static/css')
    },
    fallback: {
      "path": false,
      "fs": false
    }
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: 'styles.css'
    })
  ],
  externals: {
    'socket.io-client': 'io',
    'lucide': 'lucide',
    'jspdf': {
      commonjs: 'jspdf',
      commonjs2: 'jspdf',
      amd: 'jspdf',
      root: 'jsPDF'
    },
    'lottie-web': 'bodymovin'
  }
};