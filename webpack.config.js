// webpack.config.js
const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const webpack = require('webpack');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    mode: isProduction ? 'production' : 'development',
    entry: {
      main: './frontend/index.js',
    },
    output: {
      path: path.resolve(__dirname, 'static/dist'),
      filename: isProduction ? '[name].[contenthash].js' : '[name].js',
      chunkFilename: isProduction ? '[name].[contenthash].js' : '[name].js',
      publicPath: '/',
      clean: true,
    },
    devtool: isProduction ? 'source-map' : 'inline-source-map',
    devServer: {
      static: [
        {
          directory: path.join(__dirname, 'static'),
          publicPath: '/static',
        },
        {
          directory: path.join(__dirname, 'templates'),
          publicPath: '/',
        },
      ],
      compress: true,
      port: 8080,
      hot: true,
      liveReload: true,
      historyApiFallback: true,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:5000',
          changeOrigin: true,
          secure: false,
          pathRewrite: {'^/api': '/api'},
          logLevel: 'debug'
        },
        '/socket.io': {
          target: 'http://127.0.0.1:5000',
          ws: true,
          changeOrigin: true,
          timeout: 60000,
          proxyTimeout: 60000,
          logLevel: 'debug',
        },
      },
    },
    module: {
      rules: [
        {
          test: /\.(js|jsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              cacheDirectory: true, // Speeds up Babel compilation by caching
            },
          },
        },
        {
          test: /\.css$/,
          use: [
            isProduction ? MiniCssExtractPlugin.loader : 'style-loader',
            {
              loader: 'css-loader',
              options: {
                importLoaders: 1,
                sourceMap: !isProduction,
              },
            },
            'postcss-loader',
          ],
        },
        {
          test: /\.(png|jpe?g|gif|svg)$/i,
          type: 'asset/resource',
          generator: {
            filename: 'images/[hash][ext][query]',
          },
        },
        {
          test: /\.(woff(2)?|eot|ttf|otf|svg)$/, // Handle fonts and additional SVGs
          type: 'asset/resource',
          generator: {
            filename: 'fonts/[name][ext][query]',
          },
        },
      ],
    },
    resolve: {
      extensions: ['.js', '.jsx', '.css'],
      alias: {
        '@': path.resolve(__dirname, 'frontend'),
        '@components': path.resolve(__dirname, 'frontend/components'),
        '@actions': path.resolve(__dirname, 'frontend/actions'),
        '@reducers': path.resolve(__dirname, 'frontend/reducers'),
        '@core': path.resolve(__dirname, 'frontend/core'),
        '@utils': path.resolve(__dirname, 'frontend/utils'),
        '@css': path.resolve(__dirname, 'frontend/static/css'),
      },
    },
    plugins: [
      new MiniCssExtractPlugin({
        filename: isProduction ? '[name].[contenthash].css' : '[name].css',
      }),
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, 'templates', 'index.html'),
        filename: 'index.html',
        inject: 'body',
        minify: isProduction
          ? {
              removeComments: true,
              collapseWhitespace: true,
              removeRedundantAttributes: true,
              useShortDoctype: true,
            }
          : false,
      }),
      new CleanWebpackPlugin(), // Ensures clean build folders
      new webpack.DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify(isProduction ? 'production' : 'development'),
      }),
    ],
    optimization: {
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
          },
        },
      },
      runtimeChunk: 'single',
    },
    performance: {
      hints: isProduction ? 'warning' : false,
    },
  };
};
