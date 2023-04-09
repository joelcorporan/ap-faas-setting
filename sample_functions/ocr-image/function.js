/**
 * OCR Image
 * @author Joel Corporan
 **/

// import dependencies from node_modules
const AWS = require('aws-sdk');
const tesseract = require('tesseractocr');
const fs = require('fs').promises;

// instantiate AWS service helpers
const S3 = new AWS.S3();

// environment variables specified in serverless.yml
const BUCKET = process.env.IMAGE_BUCKET;
const BUCKET_PATH = process.env.IMAGE_BUCKET_PATH;

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
async function getImage(imageName) {
  const getParams = {
    Bucket: process.env.IMAGE_BUCKET,
    Key: `${BUCKET_PATH}/${imageName}`,
  };

  return S3.getObject(getParams).promise();
}

/**
 * Extract text from image
 * @param {String} image
 * @return {String}
 */
async function getTextFromImage(image) {
  const { Body } = image;

  await fs.writeFile(`/tmp/${image}`, Body);
  return tesseract.recognize(`/tmp/${image}`);
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

    const imageName = path_list[1];

    if (imageName === 'image-list') {
      const results = await getObjects();

      return {
        statusCode: 200,
        headers: HTTP_HEADERS,
        body: JSON.stringify(results.map((item) => item.Key.split('/')[1])),
      };
    }

    const image = await getImage(imageName);
    const text = await getTextFromImage(image);

    return {
      statusCode: 200,
      headers: Object.assign(
        HTTP_HEADERS,
        {
          'Request-Id': context.awsRequestId,
          'Expiration-Time': process.env.EXPIRATION_TIME,
          'Execution-Time': `${new Date() - start}`, // END COUNTER
        },
      ),
      body: JSON.stringify(
        {
          text,
        },
      ),
    };

  } catch (error) {
    return {
      statusCode: 400,
      headers: HTTP_HEADERS,
      body: error.message,
    };
  }
};
