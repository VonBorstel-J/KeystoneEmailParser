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
            presets: ['@babel/preset-env', '@babel/preset-react']
          }
        }
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx'],
    alias: {
      '@static': path.resolve(__dirname, 'static/'),
      '@js': path.resolve(__dirname, 'static/js/'),
      '@components': path.resolve(__dirname, 'static/components/'),
      '@core': path.resolve(__dirname, 'static/js/core/'),
      '@actions': path.resolve(__dirname, 'static/js/actions/'),
      '@reducers': path.resolve(__dirname, 'static/js/reducers/'),
      '@utils': path.resolve(__dirname, 'static/js/utils/'),
      '@ui': path.resolve(__dirname, 'static/js/ui/')
    }
  }
};