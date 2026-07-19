SELECT v.inventory_year, COUNT(*) AS variable_count
FROM [GHG_Inventory].[latest].[ghg_value] AS v
WHERE v.country_code = 'DE'
GROUP BY v.inventory_year
