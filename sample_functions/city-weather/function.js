/**
 * City weather
 * @author Joel Corporan
 **/

// import dependencies from node_modules
const axios = require('axios');

// pull in environment variables that we specified in lambda settings
const OPENWEATHERMAP_API_URL = process.env.OPENWEATHERMAP_API_URL;
const OPENWEATHERMAP_API_KEY = process.env.OPENWEATHERMAP_API_KEY;

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
 * Get weather
 * @param {String} city
 * @param {String} units
 * @returns {Promise<Object>}
 */
async function getWeather(city, units) {
  // equivalent to `axios.get('https://example.com/?blah=something')`
  return axios.get(
    OPENWEATHERMAP_API_URL,
    {
      params: {
        appid: OPENWEATHERMAP_API_KEY,
        q: decodeURI(city),
        units: units || 'imperial',
      },
    },
  );
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

    const city = path_list[1];
    const parameters = event.queryStringParameters || { units: null };
    const { units } = parameters;

    const { data } = await getWeather(city, units);
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
      body: JSON.stringify(data),
    };

  } catch (error) {
    return {
      statusCode: 400,
      headers: HTTP_HEADERS,
      body: error.message,
    };
  }
};
