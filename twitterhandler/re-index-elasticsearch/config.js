const Config = {
    elastic_search_host_config : {
        host: '<elastic_username>:<elastic_password>@<elastic_host>:9200',
        log: 'trace',
        apiVersion: '7.2',
        log : [
            {
                type: 'stdio',
                levels: ['error', 'warning'] // change these options
            }
        ]
    },  
    semantic_pipeline_path : "http://<insert_linked_pipes_host>:32800/resources/executions",
    semantic_pipeline : "http://<insert_linked_pipes_host>:32800/resources/pipelines/1552388831995"
};

module.exports = Config;