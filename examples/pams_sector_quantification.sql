SELECT p.Sector_s__affected, COUNT(*) AS n,
  COUNT(p.Total_GHG_emissions_reductions_in_2030__kt_CO2eq_y_GHG) AS q30
FROM [GHGPAMS].[latest].[annexIX_flat_view_PaMs_elasticsearch] AS p
GROUP BY p.Sector_s__affected
