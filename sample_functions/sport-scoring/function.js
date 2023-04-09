/**
 * Sport scoring
 * @author Joel Corporan
 **/

// import dependencies from node_modules
const axios = require('axios');

// pull in environment variables that we specified in lambda settings
const SPORTRADAR_API_URL = process.env.SPORTRADAR_API_URL;
const SPORTRADAR_API_KEY = process.env.SPORTRADAR_API_KEY;

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
 * Get current games
 * @return Promise<Object>
 */
async function getGames() {
  const today = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const parsedURL = `${SPORTRADAR_API_URL}/${today.getFullYear()}/${(today.getMonth() + 1)}/${today.getDate()}/schedule.json`;

  // equivalent to `axios.get('https://example.com/?blah=something')`
  return axios.get(parsedURL, { params: { api_key: SPORTRADAR_API_KEY } });
}

async function getGame(gameID) {
  const parsedURL = `${SPORTRADAR_API_URL}/${gameID}/boxscore.json`;

  // equivalent to `axios.get('https://example.com/?blah=something')`
  return axios.get(parsedURL, { params: { api_key: SPORTRADAR_API_KEY } });
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

    const gameID = path_list[1];

    if (gameID === 'game-list') {
      const { data } = await getGames();

      return {
        statusCode: 200,
        headers: HTTP_HEADERS,
        body: JSON.stringify(data.games.map((item) => (
          {
            id: item.id,
            game: `${item.home.name} vs ${item.away.name}`,
            status: item.status,
            scheduled: new Date(item.scheduled).toLocaleString('en-US', { timeZone: 'America/New_York' }),
          }
        ))),
      };
    }

    const { data } = await getGame(gameID);

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
          gameId: data.id,
          status: data.status,
          home: {
            points: data.home.points,
            scoring: data.home.scoring,
          },
          away: {
            points: data.away.points,
            scoring: data.away.scoring,
          },
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
