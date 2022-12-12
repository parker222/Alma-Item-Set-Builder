# Alma Item Set Builder
This python executable allows the user to create Physical Item Sets in Alma by scanning item barcodes.

You will need a profile on the Ex Libris Developer Network and an API-Key with the following permissions: Configuration (Read/Write), Bibs (Read).

Config.ini will need to be edited for your site before deployment.

All sets will create a subdirectory below the directory where the set builder is installed. This subdirectory will contain a list of barcodes added to the list and lists of all barcodes that were not added to lists. The barcodes not added will be in individual files by error type.

In Alma all sets are recorded as public sets created by exl_api and named with the following default convention {set_prefix}_{YYYYMMDD}_{system login name}. It is suggested that if multiple machines are using the same system login name that a further identifier be added to the end of the set name (staff initials, location, etc.).
