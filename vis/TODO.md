About the interface and data exploration:

[ ] Downloads and likes should either be radio buttons or the query should be adapted to consider the gap between two selections.
[ ] Change the route /query-endpoint to consider recursive querying, i.e. the endpoint has a threshold for 10,000 results, but some queries might have more than 10k matching results. Thus, we should have the option to loop until there is no more matching results.
[ ] Consider a SPARQL query that takes into account 'unknown' values (i.e. unbound values), for instance to retrieve datasets that do not have an associated task. This can be interesting to support inpecting the quality of dataset metadata
[ ] Verify why the filter's query have results for years such as 2008 and 2010, but when used in a filter, it does not return anything. (Hint: it might be related to the way the data is currently being loaded in virtuoso)

About the repository:

[ ] Include the KG generation scripts (a cleaning is necessary)
[ ] Include a script that retrieves data from the HuggingFace API and, then, generate the KG