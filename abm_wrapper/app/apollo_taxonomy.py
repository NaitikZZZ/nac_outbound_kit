"""Static reference data for the People Discovery filters.

Two of these four are genuine, documented Apollo enums -- hardcoded here
from Apollo's current docs, NOT fetched live, because there is no API
endpoint that returns them:

- SENIORITIES: Apollo's `person_seniorities[]` values, confirmed against
  their docs. A real, closed enum -- safe as a dropdown.
- EMPLOYEE_SIZE_BUCKETS: `organization_num_employees_ranges[]` has a fixed
  string FORMAT ("min,max"), but Apollo exposes no endpoint listing bucket
  boundaries -- these are the conventional buckets their own UI offers.

The other two requested dropdowns are NOT possible as closed lists: Apollo
confirmed `person_locations[]` and `person_titles[]` are free-text fields
matched against millions of values, with no "all valid values" endpoint at
all. DEFAULT_REGIONS below is a curated starting point for an editable text
field, not an enum -- see skills_bridge.default_people_discovery_titles()
for the equivalent seed list for titles.
"""

SENIORITIES = [
    "owner", "founder", "c_suite", "partner", "vp",
    "head", "director", "manager", "senior", "entry", "intern",
]

EMPLOYEE_SIZE_BUCKETS = [
    ("1,10", "1-10"),
    ("11,20", "11-20"),
    ("21,50", "21-50"),
    ("51,100", "51-100"),
    ("101,200", "101-200"),
    ("201,500", "201-500"),
    ("501,1000", "501-1,000"),
    ("1001,2000", "1,001-2,000"),
    ("2001,5000", "2,001-5,000"),
    ("5001,10000", "5,001-10,000"),
    ("10001,", "10,001+"),
]

DEFAULT_REGIONS = [
    "United States", "United Kingdom", "Canada", "India", "Australia",
    "Germany", "France", "Netherlands", "Singapore", "United Arab Emirates",
    "Saudi Arabia", "Brazil", "Mexico", "Japan", "Ireland",
]
