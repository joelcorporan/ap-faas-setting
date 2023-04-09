/**
 * Image Resizer
 * @author Joel Corporan
 **/

// import dependencies from node_modules
const AWS = require('aws-sdk');
const SHARP = require('sharp');

// instantiate S3 helper
const S3 = new AWS.S3();

// pull in environment variables that we specified in lambda settings
const BUCKET = process.env.IMAGE_BUCKET;
const BUCKET_PATH = process.env.IMAGE_BUCKET_PATH;
const IMAGE_DOMAIN = `https://${process.env.IMAGE_BUCKET}.s3.amazonaws.com`;

const HTTP_HEADERS = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Request-Headers': [
    'Origin',
    'X-Requested-With',
    'Content-Type',
    'Accept',
    'Authorization',
    'Cache-Control',
    'Pragma',
  ].join(','),
};

/**
 * Get List Images
 * @param {Array} objects
 * @returns {Promise<Object>}
 */
async function getObjects(objects = []) {
  const params = {
    Bucket: BUCKET,
    Prefix: BUCKET_PATH,
  };

  const response = await S3.listObjectsV2(params).promise();

  response.Contents.forEach((obj) => objects.push(obj));

  if (response.NextContinuationToken) {
    params.ContinuationToken = response.NextContinuationToken;
    await getObjects(params, objects);
  }

  return objects;
}

/**
 * Get Image from bucket
 * @param {String} image
 * @returns {Promise<Object>}
 */
async function getImage(image) {
  const getParams = {
    Bucket: process.env.IMAGE_BUCKET,
    Key: `${BUCKET_PATH}/${image}`,
  };

  // fetch the original image from S3
  return S3.getObject(getParams).promise();
}

async function resizeImage(image, width, height) {
  const imageType = image.split('.')[1];

  // fetch the original image from S3
  const { Body } = await getImage(image);

  // use Sharp (https://www.npmjs.com/package/sharp)
  // a node.js image conversion library, to resize the image.
  const resizeConfig = {};
  let keyName = '';

  if (width) {
    resizeConfig.width = parseInt(width, 10);
    keyName = keyName !== '' ? `${width}` : width;
  }

  if (height) {
    resizeConfig.height = parseInt(height, 10);
    keyName = keyName !== '' ? `${keyName}x${height}` : `wx${height}`;

  } else {
    keyName = `${keyName}xh`;
  }

  const buffer = await SHARP(Body)
    .resize(resizeConfig)
    .toFormat(imageType, { quality: 100 })
    .toBuffer();

  const putParams = {
    Body: buffer,
    Bucket: BUCKET,
    Key: `resized/${keyName}/${image}`,
    ContentType: `image/${imageType === 'jpg' ? 'jpeg' : imageType}`,
    ContentDisposition: 'inline', // ensure that the browser will display S3 images inline
  };

  await S3.putObject(putParams).promise();

  return `${IMAGE_DOMAIN}/resized/${keyName}/${image}`;
}

/**
 * Handler
 * @param {Object} event
 * @param {Object} context
 */
exports.handler = async (event, context) => {
  const start = new Date(); // START COUNTER

  try {

    // Parse path parameter
    const paths = event.rawPath || event.path;
    const path_list = paths.slice(1).split('/');

    if (path_list.length > 2) {
      return {
        statusCode: 400,
        headers: HTTP_HEADERS,
        body: 'Inconsistent parameters',
      };
    }

    const image = path_list[1];

    if (image === 'image-list') {
      const results = await getObjects();

      return {
        statusCode: 200,
        headers: HTTP_HEADERS,
        body: JSON.stringify(results.map((item) => item.Key.split('/')[1])),
      };
    }

    const parameters = event.queryStringParameters || { w: null, h: null };
    const width = parameters.w || null;
    const height = parameters.h || null;

    if (!width && !height) {
      return {
        statusCode: 301,
        headers: Object.assign(
          HTTP_HEADERS,
          {
            'Request-Id': context.awsRequestId,
            'Expiration-Time': process.env.EXPIRATION_TIME,
            'Execution-Time': `${new Date() - start}`, // END COUNTER
            Location: `${IMAGE_DOMAIN}/${BUCKET_PATH}/${image}`,
          },
        ),
        body: `Redirecting to ${IMAGE_DOMAIN}/${BUCKET_PATH}/${image}`,
      };

    }

    const imageURL = await resizeImage(image, width, height);

    return {
      statusCode: 301,
      headers: Object.assign(
        HTTP_HEADERS,
        {
          'Request-Id': context.awsRequestId,
          'Expiration-Time': process.env.EXPIRATION_TIME,
          'Execution-Time': `${new Date() - start}`, // END COUNTER
          Location: `${imageURL}`,
        },
      ),
      body: `Redirecting to ${imageURL}`,
    };

  } catch (error) {
    return {
      statusCode: 400,
      headers: HTTP_HEADERS,
      body: error.message,
    };
  }
};
