// webpack.config.js

const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin'); // To generate HTML files

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    mode: isProduction ? 'production' : 'development',
    entry: {
      main: './static/js/main.js', // Define entry points as an object
    },
    output: {
      path: path.resolve(__dirname, 'static/dist'),
      filename: isProduction ? '[name].[contenthash].js' : '[name].js', // Use [name].js to differentiate chunks
      chunkFilename: isProduction ? '[name].[contenthash].js' : '[name].js', // Similarly for non-entry chunks
      publicPath: '/static/dist/',
      clean: true, // Automatically clean the output directory before emit
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
      historyApiFallback: {
        // Prevent historyApiFallback from intercepting asset paths
        rewrites: [
          { from: /^\/static\/dist\/[a-z0-9]+\.[a-z0-9]+\.[a-z0-9]+\.(js|css)$/, to: (context) => context.parsedUrl.pathname },
        ],
      },
      proxy: {
        '/api': 'http://localhost:5000',
        '/socket.io': {
          target: 'http://localhost:5000',
          ws: true,
          changeOrigin: true,
        },
      },
    },
    module: {
      rules: [
        {
          test: /\.(js|jsx)$/, // Handle JS and JSX files
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
          },
        },
        {
          test: /\.css$/, // Handle CSS files
          use: [
            isProduction ? MiniCssExtractPlugin.loader : 'style-loader', // Extract CSS in production
            {
              loader: 'css-loader',
              options: {
                importLoaders: 1, // Number of loaders applied before CSS loader
              },
            },
            'postcss-loader', // Apply PostCSS transformations
          ],
        },
        {
          test: /\.(png|jpe?g|gif|svg)$/i, // Handle image assets
          type: 'asset/resource',
          generator: {
            filename: 'images/[hash][ext][query]', // Output images to images/ directory
          },
        },
      ],
    },
    resolve: {
      extensions: ['.js', '.jsx', '.css'], // Resolve these extensions
      alias: {
        '@': path.resolve(__dirname, 'static'),
        '@components': path.resolve(__dirname, 'static/components'),
        '@actions': path.resolve(__dirname, 'static/js/actions'),
        '@reducers': path.resolve(__dirname, 'static/js/reducers'),
        '@core': path.resolve(__dirname, 'static/js/core'),
        '@utils': path.resolve(__dirname, 'static/js/utils'),
        '@css': path.resolve(__dirname, 'static/css'),
      },
    },
    plugins: [
      new MiniCssExtractPlugin({
        filename: isProduction ? '[name].[contenthash].css' : '[name].css', // Unique CSS filenames
      }),
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, 'templates', 'index.html'),
        filename: 'index.html',
        inject: 'body', // Inject scripts at the end of the body
        minify: isProduction
          ? {
              removeComments: true,
              collapseWhitespace: true,
              removeRedundantAttributes: true,
            }
          : false,
      }),
    ],
    optimization: {
      splitChunks: {
        chunks: 'all', // Split vendor and commons
      },
      runtimeChunk: 'single', // Create a single runtime bundle
    },
    performance: {
      hints: isProduction ? 'warning' : false, // Show performance hints only in production
    },
  };
};
