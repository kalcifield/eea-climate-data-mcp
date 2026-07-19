SELECT p.Status_of_implementation, COUNT(*) AS n
FROM [GHGPAMS].[latest].[annexIX_flat_view_PaMs_elasticsearch] AS p
WHERE p.Country = 'Hungary'
GROUP BY p.Status_of_implementation
