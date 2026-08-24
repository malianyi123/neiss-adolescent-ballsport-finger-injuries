# Manual NEISS Download Instructions

Automated download was attempted first. If one or more files are missing, use these steps.

1. Open the official CPSC NEISS query/download page:
   https://www.cpsc.gov/cgibin/NEISSQuery/home.aspx
2. Select `Researcher` or the most appropriate user affiliation.
3. Under `Archived Annual NEISS Data`, select each year listed below.
4. Select `Tab Delimited Text` and click `Find Data`.
5. Save raw files unchanged in `data/raw/neiss/` with the exact filenames shown.

- 2015: `neiss2015.tsv`
- 2016: `neiss2016.tsv`
- 2017: `neiss2017.tsv`
- 2018: `neiss2018.tsv`
- 2019: `neiss2019.tsv`
- 2020: `neiss2020.tsv`
- 2021: `neiss2021.tsv`
- 2022: `neiss2022.tsv`
- 2023: `neiss2023.tsv`
- 2024: `neiss2024.tsv`
- 2025: `neiss2025.tsv`

Also download the official NEISS Data Dictionary Excel file from:
https://www.cpsc.gov/s3fs-public/DataDictionary042022.xlsx?VersionId=ZudA.bM6W3epO1LHUp_XwQjL8q7zIgvD

Save it as `data/raw/neiss/DataDictionary042022.xlsx`.

Save the NEISS format file, if needed, from:
https://www.cpsc.gov/cgibin/NEISSQuery/Data/Info%20Docs/neiss_fmt.txt

as `data/raw/neiss/neiss_fmt.txt`.
