//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///// SoCaTel - A multi-stakeholder co-creation platform for better access to Long-Term Care services
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///// LIBRARY IMPORT METHODS
const redis = require("redis");
const nodedatetime = require('node-datetime');
const _ElasticSearch = require('@elastic/elasticsearch');
const _Config = require("./config.json");
const node_processes_running_log = require('why-is-node-running')
const logger = require('node-color-log');
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
///// DB Clients Definition
const _ElasticSearchClient = new _ElasticSearch.Client(_Config.elasticsearch_configuration_connection)
const _RedisClient = redis.createClient(_Config.redis_configuration_connetion);
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//logger.setLevel("error");

/**
 * This function checks that the ES is not empty and that there exist the necessary indices required
 * for reading the services. All indexes of interest that exists in the ES but with no data are removed
 * @param {*} resp 
 */
const _elasticSearchIndexValidation = function(resp) {
  var indexes_of_interest = [];
  var indices = resp.body;
  logger.debug(`ElasticSearch Index Validation`);
  if (indices && indices.length > 1) {
    let elasticsearch_ioi = _Config.elasticsearch_ioi;
    elasticsearch_ioi.forEach(ioi => {
      let ioi_obj = indices.find(el => el.index === ioi);
      if (!ioi_obj) {
        logger.warn(`The index [${ioi}] was not found. The index would not be parsed to fetch Twitter account tweets`);
      }
      else {        
        if (parseInt(ioi_obj["docs.count"]) === 0) {
          logger.warn(`Index of interest [${ioi}] was found but with no data within. Removing it from the list of indexes of interest`);
        }
        else {
          logger.info(`Index of interest [${ioi}] was found`);
          indexes_of_interest.push(ioi);
        }
      }
    });
  }
  else {
    throw "No indices have been returned. The ElasticSearch seems to be empty. Check this with the Administrator"
  }
  return indexes_of_interest;
}

/**
 * This function obtains all indexes from ElasticSearch and for each index in the index of interest(ioi)
 * it calls the ElasticSearch to perform a search request to obtain all data. All the data for all the index of interest
 * are then going to be pushed to the RedisCache (*see next function)
 * @param {*} es_indices 
 */
const _elasticSearchSearchIOI = function(es_indices) {
  logger.debug(`ElasticSearch Index Index of Interest Function`);
  var _elasticsearchSearchPromises = [];    
  es_indices.forEach(ioi => {    
    logger.info(`Searching on index [${ioi}] for available services`);
    var _promise =  _ElasticSearchClient.search({
      index: ioi,   
      size: 1000          
    });
    _elasticsearchSearchPromises.push(_promise);      
  });
 
  return Promise.all(_elasticsearchSearchPromises);
}

/**
 * rpush redis command
 * @param {*} list 
 * @param {*} data 
 */
const _rpushRedis = function (list, data){
  return _RedisClient.rpush(list, JSON.stringify(data));
}

/**
 * 
 * @param {*} obtained_data 
 */
const _elasticSearchObtainedData = function(obtained_data) {
  logger.info("Successfully retrieved search data from all index of interest");
  logger.info("Initiating procedure of pushing data to RedisCache");
  obtained_data.forEach(es_index_data => {
    let total_hits = es_index_data.body.hits.total;
    let index_name = es_index_data.body.hits.hits[0]._index;
    logger.info(`Index [${index_name}] returned back ${total_hits} services... Now pushing them on RedisCache`);
    es_index_data.body.hits.hits.forEach(service => {
      if (service._source.twitter_screen_name !== undefined && service._source.twitter_screen_name !== null){
	      logger.info(`Pushing Organisation Name [${service._source.organisation_name}] with Twitter screen name [${service._source.twitter_screen_name}]`);
	      var _rpushFeed = _rpushRedis(_Config.redis_twitter_services_feed_list, service);
	      var _rpushReplies = _rpushRedis(_Config.redis_twitter_services_replies_list, service);
      }
      else {
      	logger.warn(`Cannot push Organisation Name [${service._source.organisation_name}] since the Twitter screen name is either null or undefined`);
      }
     return Promise.all([_rpushFeed, _rpushReplies]);      
    });    
  });
}

/**
 * Output the error to the console for the time being
 * @param {*} err 
 */
const _errorHandling = function(err) {
  logger.error(err);
}

/**
 * Finally workaround method
 */
const _finally = function() {
  _ElasticSearchClient.close();
  _RedisClient.quit();
  logger.debug("Exiting Twitter Handler"); 
  //node_processes_running_log();
}

const main = function(){
  // List the ElasticSearch Indices

  logger.debug("=================================================================================");
  logger.debug(`HANDLER LOADER STARTED ON ${nodedatetime.create().format('Y-m-d H:M:S')}`);
  logger.debug("=================================================================================");

  _ElasticSearchClient.cat.indices( {
    format: "json"
  })
  //Validate that all required Indices exist within the ES KB
  .then(_elasticSearchIndexValidation)
  .then(_elasticSearchSearchIOI)
  .then(_elasticSearchObtainedData)
  .then(function(resp){
    logger.info(`Services successfully imported in RedisCache`);
  })
  //Error Handling
  .catch(_errorHandling)
  .then(_finally)
}


// Initiator Function :) 
main();
