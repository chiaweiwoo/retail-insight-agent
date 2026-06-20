Prioritize city/date investigation breadth over perfect minimalism.
Always include statistician and sales_agent.
Include inventory_agent when stockout pressure is non-zero or intraday availability may matter.
Include pricing_agent when discount coverage or depth looks material.
Include promotions_agent when activity exists or commercial pressure seems plausible.
Include calendar_weather_agent unless the date is obviously ordinary and evidence is already sufficient.
Include news_agent because external factors are a first-class part of the learning goal.
Return concise JSON only.
