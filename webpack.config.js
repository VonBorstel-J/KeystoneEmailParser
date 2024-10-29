const path = require('path');

module.exports = {
  entry: './static/js/main.js',
  output: {
    path: path.resolve(__dirname, 'static/dist'),
    filename: 'bundle.js',
    publicPath: '/static/dist/'
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react'],
            plugins: [
              '@babel/plugin-transform-runtime',
              '@babel/plugin-proposal-class-properties'
            ]
          }
        }
      },
      {
        test: /\.css$/,
        use: [
          'style-loader',
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
    extensions: ['.js', '.jsx'],
    alias: {
      '@': path.resolve(__dirname, 'static'),
      'components': path.resolve(__dirname, 'static/components'),
      'actions': path.resolve(__dirname, 'static/js/actions'),
      'reducers': path.resolve(__dirname, 'static/js/reducers'),
      'utils': path.resolve(__dirname, 'static/js/utils'),
      'core': path.resolve(__dirname, 'static/js/core')
    }
  },
  devServer: {
    static: {
      directory: path.join(__dirname, 'static'),
    },
    compress: true,
    port: 3000,
    proxy: {
      '/parse_email': 'http://localhost:5000',
      '/health': 'http://localhost:5000',
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true
      }
    }
  }
};