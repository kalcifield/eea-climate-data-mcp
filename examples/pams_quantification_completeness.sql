SELECT p.Country, COUNT(*) AS n,
  COUNT(p.Total_GHG_emissions_reductions_in_2025__kt_CO2eq_y_GHG) AS ea25,
  COUNT(p.Total_GHG_emissions_reductions_in_2030__kt_CO2eq_y_GHG) AS ea30,
  COUNT(p.Total_GHG_emissions_reductions_in_2035__kt_CO2eq_y_GHG) AS ea35,
  COUNT(p.GHG_emissions_reductions_ESR_in_2030__kt_CO2eq_y_GHG) AS esr30,
  COUNT(p.Average_expost_emission_reduction__kt_CO2eq_y_GHG) AS expost
FROM [GHGPAMS].[latest].[annexIX_flat_view_PaMs_elasticsearch] AS p
GROUP BY p.Country
