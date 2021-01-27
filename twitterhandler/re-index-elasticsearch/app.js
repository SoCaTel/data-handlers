const elasticsearch = require('elasticsearch');
const _Config = require('./config.js');
const request = require('request');
const queryString = require('query-string');

const es_client = new elasticsearch.Client(_Config.elastic_search_host_config);

async function fetchFromElastic(){

  const allDocs = [];
  const responseQueue = [];
  
  // start things off by searching, setting a scroll timeout, and pushing
  // our first response into the queue to be processed
  responseQueue.push(await es_client.search({
    index: 'kb_twitter_raw',
    size: 1000,
    scroll: '1m', // keep the search results "scrollable" for 1 minute      
  }));
  
  while (responseQueue.length) {
    const response = responseQueue.shift();
  
    // collect the titles from this response
    response.hits.hits.forEach(function (hit) {
      allDocs.push(hit);
    });
  
    // check to see if we have collected all of the titles
    if (response.hits.total.value === allDocs.length) {
      console.log('All documents are collected');
      //break;
    }
    break;
    // get the next response if there are more titles to fetch
    responseQueue.push(
      await es_client.scroll({
        scrollId: response._scroll_id,
        scroll: '1m'
      })
    );
  }

  allDocs.forEach(e=> {
    const url = `${_Config.semantic_pipeline_path}?pipeline=${_Config.semantic_pipeline}`;
    request.post({
        url: url ,
        headers:
        { 
          "Content-Type": "multipart/form-data"
        },
        formData: {
          input: {
              value: JSON.stringify([e]),
              options: {
                filetype: 'json',
                filename: 'input.json',    
                contentType: 'application/json'    
              }   
          }     
        },
    }, function(error, response, body) {
        console.log(body);
    });
  });  
}





fetchFromElastic();


