# Fictional sample provenance

`fictional_jurisdictions.csv` is a hand-constructed software fixture, not observed or estimated country data. Alpha, Beta, Gamma, and Delta are fictional; their region is fictional. There is no observation date, external data source, or personal information.

All thirteen input proxies in each row equal 10, 40, 65, or 90 respectively. Equal inputs make the expected weighted composite transparent: 10, 40, 65, and 90. Tests also use a nonuniform hand-calculated case to exercise unequal layer weights. These inputs illustrate all four model bands without asserting empirical calibration.

The separate sample runner uses the existing scenario and simulation functions with seed 42, 1,000 draws, and noise standard deviation 7.5 by default. Generated outputs are ignored by Git and labeled synthetic. Do not use this fixture as a substitute for observed jurisdiction evidence.
