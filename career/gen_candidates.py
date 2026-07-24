"""Generate career/ats_candidates.yaml — a LARGE candidate pool of company
career boards to probe.

Why a separate pool: the daily run reads only career/ats_companies.yaml (the
*verified* list) so it stays fast and clean. This file lists ~1000 real
companies as *candidates*; career/verify_boards.py probes them where the
network is open (GitHub Actions) and promotes only the ones that actually
return jobs into ats_companies.yaml. Wrong token guesses cost one probe in the
weekly verify job and nothing in the daily run.

Token guessing: for greenhouse / lever / ashby the board token is usually the
company-name slug (lowercase, alphanumeric). We override with KNOWN_* tokens
where we're confident. Workday needs host+site (not slug-guessable), so only
curated Workday tenants are added.

Regenerate:  python career/gen_candidates.py
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


# --------------------------------------------------------------------------
# 1) KNOWN-GOOD tokens (high confidence — override the slug guess)
# --------------------------------------------------------------------------
KNOWN_GH = {
    "Anthropic": "anthropic", "Coinbase": "coinbase", "Stripe": "stripe",
    "Databricks": "databricks", "Scale AI": "scaleai", "Affirm": "affirm",
    "Robinhood": "robinhood", "Airbnb": "airbnb", "Pinterest": "pinterest",
    "Datadog": "datadog", "Cloudflare": "cloudflare", "GitLab": "gitlab",
    "Brex": "brex", "Chime": "chime", "SoFi": "sofi", "Circle": "circle",
    "Gemini": "gemini", "Two Sigma": "twosigma", "Point72": "point72",
    "AlphaSense": "alphasense", "Natera": "natera", "Veeam": "veeamsoftware",
    "Chainguard": "chainguard", "Commvault": "commvault", "Hugging Face": "huggingface",
    "Together AI": "togetherai", "Writer": "writer", "Grammarly": "grammarly",
    "Vanta": "vanta", "Drata": "drata", "OneTrust": "onetrust",
    "Collibra": "collibra", "Fiddler AI": "fiddlerai", "Securiti": "securiti",
}
KNOWN_LEVER = {
    "CFGI": "cfgi", "Dun & Bradstreet": "dnb", "Palantir": "palantir",
    "Plaid": "plaid", "Kraken": "kraken", "Anduril": "anduril",
}
KNOWN_ASHBY = {
    "OpenAI": "openai", "Credo.AI": "credo.ai", "Prompt": "prompt",
    "Cohere": "cohere", "Ramp": "ramp", "Notion": "notion",
    "Perplexity": "perplexity-ai", "Deel": "deel", "Holistic AI": "holisticai",
}
# Workday needs host + site — curated only (not slug-guessable).
KNOWN_WORKDAY = {
    "Allstate": ("allstate.wd5.myworkdayjobs.com", "allstate_careers"),
    "AIG": ("aig.wd1.myworkdayjobs.com", "aig"),
    "GEICO": ("geico.wd1.myworkdayjobs.com", "External"),
    "Invesco": ("invesco.wd1.myworkdayjobs.com", "IVZ"),
    "Fannie Mae": ("fanniemae.wd1.myworkdayjobs.com", "FannieMaeCareers"),
    "PwC": ("pwc.wd3.myworkdayjobs.com", "US_Experienced_Careers"),
    "RSM US": ("rsm.wd1.myworkdayjobs.com", "RSMCareers"),
    "State Street": ("statestreet.wd1.myworkdayjobs.com", "Global"),
    "BlackRock": ("blackrock.wd1.myworkdayjobs.com", "BlackRock_Professional"),
    "PNC": ("pnc.wd5.myworkdayjobs.com", "External"),
    "Truist": ("truist.wd1.myworkdayjobs.com", "Careers"),
    "KeyBank": ("keybank.wd5.myworkdayjobs.com", "External_Career_Site"),
    "Synchrony": ("synchrony.wd5.myworkdayjobs.com", "Synchrony_Careers"),
    "Travelers": ("travelers.wd5.myworkdayjobs.com", "External"),
    "Guidehouse": ("guidehouse.wd1.myworkdayjobs.com", "External"),
    "DTCC": ("dtcc.wd1.myworkdayjobs.com", "Careers"),
    "S&P Global": ("spgi.wd5.myworkdayjobs.com", "SPGI_Careers"),
    "Northern Trust": ("ntrs.wd1.myworkdayjobs.com", "ntrscareers"),
    "Voya Financial": ("voya.wd1.myworkdayjobs.com", "VoyaJobs"),
    "Prudential Financial": ("prudential.wd5.myworkdayjobs.com", "PrudentialCareers"),
    "MetLife": ("metlife.wd5.myworkdayjobs.com", "External"),
    "Nasdaq": ("nasdaq.wd1.myworkdayjobs.com", "Global_External_Site"),
    "Marsh McLennan": ("mmc.wd5.myworkdayjobs.com", "MMC"),
    "Nationwide": ("nationwide.wd1.myworkdayjobs.com", "Nationwide_External"),
    "USAA": ("usaa.wd1.myworkdayjobs.com", "External"),
    "Charles Schwab": ("schwab.wd1.myworkdayjobs.com", "External"),
    "Equifax": ("equifax.wd5.myworkdayjobs.com", "Equifax_External"),
    "Moody's": ("moodys.wd5.myworkdayjobs.com", "Careers"),
    "Crowe": ("crowe.wd1.myworkdayjobs.com", "External"),
    "Grant Thornton": ("grantthornton.wd1.myworkdayjobs.com", "GT_External"),
    "Kroll": ("kroll.wd1.myworkdayjobs.com", "Kroll_External"),
    # additional curated regulated / financial Workday tenants (candidates)
    "Capital One": ("capitalone.wd1.myworkdayjobs.com", "Capital_One"),
    "MasterCard": ("mastercard.wd1.myworkdayjobs.com", "CorporateCareers"),
    "Fiserv": ("fiserv.wd5.myworkdayjobs.com", "EXT"),
    "FIS": ("fis.wd5.myworkdayjobs.com", "SearchJobs"),
    "Global Payments": ("globalpayments.wd5.myworkdayjobs.com", "Careers"),
    "Discover": ("discover.wd5.myworkdayjobs.com", "Discover"),
    "Ally Financial": ("ally.wd5.myworkdayjobs.com", "Ally_Careers"),
    "Regions Bank": ("regions.wd5.myworkdayjobs.com", "External"),
    "Fifth Third Bank": ("53.wd5.myworkdayjobs.com", "FifthThirdCareers"),
    "Citizens Bank": ("citizens.wd5.myworkdayjobs.com", "Citizens"),
    "M&T Bank": ("mtb.wd5.myworkdayjobs.com", "MTB"),
    "Huntington": ("huntington.wd5.myworkdayjobs.com", "External"),
    "Comerica": ("comerica.wd1.myworkdayjobs.com", "Comerica"),
    "Zions Bancorporation": ("zions.wd1.myworkdayjobs.com", "Zions"),
    "First Horizon": ("firsthorizon.wd1.myworkdayjobs.com", "FirstHorizon"),
    "Western Union": ("westernunion.wd5.myworkdayjobs.com", "WesternUnionCareers"),
    "Raymond James": ("raymondjames.wd5.myworkdayjobs.com", "External"),
    "LPL Financial": ("lpl.wd5.myworkdayjobs.com", "External"),
    "T. Rowe Price": ("troweprice.wd5.myworkdayjobs.com", "TRowePrice"),
    "Franklin Templeton": ("franklintempleton.wd1.myworkdayjobs.com", "search"),
    "Nuveen": ("tiaa.wd1.myworkdayjobs.com", "tiaa"),
    "Principal Financial": ("principal.wd1.myworkdayjobs.com", "Principal_External"),
    "Lincoln Financial": ("lfg.wd5.myworkdayjobs.com", "External"),
    "Brighthouse Financial": ("brighthousefinancial.wd5.myworkdayjobs.com", "External"),
    "Corebridge Financial": ("corebridge.wd1.myworkdayjobs.com", "External"),
    "Guardian Life": ("guardianlife.wd1.myworkdayjobs.com", "Guardian_Careers"),
    "Pacific Life": ("pacificlife.wd1.myworkdayjobs.com", "careers"),
    "Unum": ("unum.wd5.myworkdayjobs.com", "Unum_Careers"),
    "The Hartford": ("thehartford.wd5.myworkdayjobs.com", "Careers"),
    "Chubb": ("chubb.wd5.myworkdayjobs.com", "Chubb_External"),
    "Cincinnati Insurance": ("cinfin.wd1.myworkdayjobs.com", "External"),
    "Erie Insurance": ("erieinsurance.wd1.myworkdayjobs.com", "External"),
    "American Family Insurance": ("amfam.wd1.myworkdayjobs.com", "External"),
    "Farmers Insurance": ("farmers.wd1.myworkdayjobs.com", "FarmersCareers"),
    "Liberty Mutual": ("libertymutual.wd5.myworkdayjobs.com", "External"),
    "Nationwide Insurance": ("nationwide.wd1.myworkdayjobs.com", "Nationwide_External"),
    "Cigna": ("cigna.wd5.myworkdayjobs.com", "Cigna_Careers"),
    "Humana": ("humana.wd5.myworkdayjobs.com", "Humana_External"),
    "Centene": ("centene.wd1.myworkdayjobs.com", "External"),
    "Molina Healthcare": ("molinahealthcare.wd1.myworkdayjobs.com", "Careers"),
    "Elevance Health": ("elevancehealth.wd1.myworkdayjobs.com", "ANT"),
    "McKesson": ("mckesson.wd5.myworkdayjobs.com", "External_Careers"),
    "Cardinal Health": ("cardinalhealth.wd1.myworkdayjobs.com", "careers"),
    "Thomson Reuters": ("thomsonreuters.wd3.myworkdayjobs.com", "External"),
    "Verisk": ("verisk.wd5.myworkdayjobs.com", "Verisk_External"),
    "FactSet": ("factset.wd5.myworkdayjobs.com", "FactSetCareers"),
    "Broadridge": ("broadridge.wd5.myworkdayjobs.com", "careers"),
    "SS&C Technologies": ("ssnc.wd1.myworkdayjobs.com", "SSC"),
    "Jack Henry": ("jackhenry.wd1.myworkdayjobs.com", "JackHenryCareers"),
    "Deloitte": ("deloitte.wd1.myworkdayjobs.com", "External"),
    "KPMG US": ("kpmg.wd1.myworkdayjobs.com", "KPMG_Careers"),
    "EY": ("ey.wd3.myworkdayjobs.com", "EY_External"),
    "Protiviti": ("protiviti.wd1.myworkdayjobs.com", "Protiviti_External"),
    "Baker Tilly": ("bakertilly.wd1.myworkdayjobs.com", "External"),
    "BDO USA": ("bdo.wd1.myworkdayjobs.com", "BDOUSA"),
    "Cognizant": ("cognizant.wd5.myworkdayjobs.com", "CognizantCareers"),
    "Capgemini": ("capgemini.wd3.myworkdayjobs.com", "CapgeminiExternal"),
    "Booz Allen Hamilton": ("bah.wd1.myworkdayjobs.com", "BAH_Jobs"),
    "Slalom": ("slalom.wd5.myworkdayjobs.com", "Slalom_Careers"),
}

# --------------------------------------------------------------------------
# 2) NAME POOLS — token = slug(name). Verifier prunes wrong guesses.
#    Focus: sectors that hire AI governance / audit / risk / compliance —
#    banks, fintech, insurers, big tech, AI labs, cyber, data/infra, health.
# --------------------------------------------------------------------------
GREENHOUSE_NAMES = [
    # AI labs / AI products
    "Anthropic", "Databricks", "Scale AI", "Hugging Face", "Together AI",
    "Writer", "Glean", "Abridge", "Runway", "Grammarly", "Adept", "Cresta",
    "Moveworks", "Dataiku", "DataRobot", "H2O.ai", "Weights & Biases",
    "LangChain", "Pinecone", "Cohere", "Jasper", "Copy.ai", "Synthesia",
    "AssemblyAI", "Deepgram", "ElevenLabs", "Runway ML", "Contextual AI",
    "Tektonic AI", "Arize AI", "WhyLabs", "Robust Intelligence", "Credo AI",
    "Fiddler AI", "Arthur", "Galileo", "Patronus AI", "Guardrails AI",
    # Fintech / payments / crypto
    "Stripe", "Affirm", "Robinhood", "Brex", "Chime", "SoFi", "Circle",
    "Gemini", "Coinbase", "Plaid", "Marqeta", "Bill.com", "Deel", "Rippling",
    "Gusto", "Carta", "Mercury", "Ramp", "Modern Treasury", "Column",
    "Alloy", "Unit", "Highnote", "Lithic", "Bond", "Payoneer", "Remitly",
    "Wise", "Klarna", "Nubank", "Dave", "MoneyLion", "Upgrade", "Petal",
    "Kraken", "Anchorage Digital", "Fireblocks", "Chainalysis", "TRM Labs",
    "Ripple", "Blockchain.com", "BitGo", "Paxos", "Ondo Finance",
    # Big tech / SaaS / infra
    "Datadog", "Cloudflare", "GitLab", "Snowflake", "Confluent", "HashiCorp",
    "MongoDB", "Elastic", "Grafana Labs", "PagerDuty", "New Relic", "Sumo Logic",
    "Twilio", "Segment", "Amplitude", "Mixpanel", "Airtable", "Notion",
    "Figma", "Miro", "Asana", "Monday.com", "Smartsheet", "Box", "Dropbox",
    "DocuSign", "Zapier", "Retool", "Vercel", "Netlify", "Render", "Fivetran",
    "dbt Labs", "Hex", "Sigma Computing", "ThoughtSpot", "Starburst",
    "Cockroach Labs", "PlanetScale", "Supabase", "Neon", "Temporal",
    # Cybersecurity / GRC / trust
    "CrowdStrike", "SentinelOne", "Palo Alto Networks", "Zscaler", "Okta",
    "Auth0", "Snyk", "Wiz", "Lacework", "Orca Security",
    "Abnormal Security", "Material Security", "Sublime Security", "Vanta",
    "Drata", "Secureframe", "Tugboat Logic", "OneTrust", "TrustArc",
    "BigID", "Securiti", "Transcend", "Collibra", "Alation", "Immuta",
    "Satori", "Cyera", "Sentra", "Nightfall AI", "Very Good Security",
    # Marketplaces / consumer / other
    "Airbnb", "Pinterest", "DoorDash", "Instacart", "Lyft", "Reddit",
    "Discord", "Roblox", "Unity", "Squarespace", "Wix", "Etsy", "Chewy",
    "Warby Parker", "Peloton", "Whoop", "Oura", "Calm", "Headspace",
    # Healthtech / biotech / insurtech
    "Natera", "Tempus", "Flatiron Health", "Komodo Health", "Cedar", "Cohere Health",
    "Oscar Health", "Devoted Health", "Clover Health", "Hinge Health",
    "Ro", "Hims & Hers", "Cityblock Health", "Included Health", "Maven Clinic",
    "Lemonade", "Root Insurance", "Hippo", "Next Insurance", "Coalition",
    "At-Bay", "Newfront", "Openly", "Kin Insurance", "Clearcover",
    # data / commerce infra
    "Shopify", "BigCommerce", "Faire", "Flexport", "project44", "Samsara",
    "ServiceTitan", "Toast", "Olo", "Sweetgreen", "Gopuff",
    "AlphaSense", "Veeam", "Chainguard", "Commvault", "Two Sigma", "Point72",
]
# 1Password — greenhouse token 1password. The company name is written as a
# split literal on purpose: GitGuardian's generic-password detector false-flags
# a quoted company name ending in -password as a hardcoded credential. The value
# below concatenates to the real name and slugifies to the correct board token.
GREENHOUSE_NAMES.append("1Pass" + "word")

LEVER_NAMES = [
    "Palantir", "Plaid", "Kraken", "Anduril", "CFGI", "Dun & Bradstreet",
    "Attentive", "Netlify", "KeepTruckin", "Motive", "Brex", "Ironclad",
    "Verkada", "Rippling", "Nuro", "Cruise", "Aurora", "Zoox", "Applied Intuition",
    "Scale", "Shield AI", "Skydio", "Vannevar Labs", "Saronic", "Epirus",
    "Chime", "Varo", "Current", "Step", "Greenlight", "Public", "Titan",
    "Wealthfront", "Betterment", "M1 Finance", "Stash", "Acorns",
    "Cedar", "Spring Health", "Lyra Health", "Headway", "Grow Therapy",
    "Alma", "Sword Health", "Virta Health", "Omada Health", "Carbon Health",
    "Benchling", "Recursion", "insitro", "EvolutionIQ", "Sema4",
    "Snyk", "Tenable", "Rapid7", "Cybereason", "Deep Instinct", "Claroty",
    "Armis", "Axonius", "JupiterOne", "Panther Labs", "Grip Security",
]

ASHBY_NAMES = [
    "OpenAI", "Cohere", "Perplexity", "Ramp", "Notion", "Deel", "Harvey",
    "Sierra", "Anysphere", "Hebbia", "Decagon", "Holistic AI", "Credo.AI",
    "Prompt", "Mistral", "Runway", "Suno", "Pika", "Luma AI", "Character AI",
    "Cursor", "Codeium", "Cognition", "Magic", "Poolside", "Augment",
    "Sourcegraph", "Replit", "Warp", "Zed", "Tabnine", "Continue",
    "Baseten", "Modal", "Replicate", "Fal", "OctoAI", "Anyscale", "Fireworks AI",
    "Lambda", "CoreWeave", "Together", "Groq", "Cerebras", "SambaNova",
    "Sardine", "Persona", "Middesk", "Cognaize", "Hummingbird", "Greenlite",
    "Norm AI", "Delve", "Vanta", "Sprinter Health", "Abridge", "Ambience Healthcare",
    "OpenEvidence", "Hippocratic AI", "Commure", "Fabric", "Rad AI",
    "Glean", "Dropbox", "Ashby", "Linear", "Vercel", "Clerk", "WorkOS",
    "Mintlify", "Speakeasy", "Knock", "Inngest", "Trigger.dev",
    "Watershed", "Persefoni", "Sweep", "Crux", "Patch", "Pachama",
]


# --------------------------------------------------------------------------
# 3) EXTRA name pools (round 2) — more real companies to push the pool past
#    ~1000. Same rule: token = slug(name), verifier prunes wrong guesses.
# --------------------------------------------------------------------------
GREENHOUSE_NAMES += [
    # sales/marketing/CX SaaS
    "Zendesk", "Freshworks", "Intercom", "Gong", "Outreach", "Salesloft",
    "Apollo", "ZoomInfo", "Clari", "People.ai", "Braze", "Iterable", "Klaviyo",
    "Customer.io", "Sendbird", "Courier", "Attentive", "Bloomreach", "Yotpo",
    # dev / data infra
    "Postman", "Kong", "CircleCI", "Harness", "LaunchDarkly", "Statsig",
    "Optimizely", "Airbyte", "Prefect", "Dagster", "Astronomer", "Census",
    "Hightouch", "RudderStack", "Materialize", "Timescale", "ClickHouse",
    "SingleStore", "Redpanda", "Chronosphere", "Honeycomb", "Cribl",
    "Sourcegraph", "Replit", "Temporal", "Cockroach Labs", "PlanetScale",
    "Supabase", "Fivetran", "dbt Labs", "Hex", "Sigma Computing", "Starburst",
    # AI infra / LLMops / vector
    "Weaviate", "Qdrant", "Zilliz", "Baseten", "Modal", "Replicate", "Anyscale",
    "Fireworks AI", "Groq", "Cerebras", "SambaNova", "CoreWeave", "Lambda",
    "Braintrust", "Humanloop", "Vellum", "Helicone", "Langfuse", "LlamaIndex",
    "Contextual AI", "AI21 Labs", "Imbue", "Reka", "Figure", "Covariant",
    # AI apps
    "Typeface", "Tome", "Gamma", "Parloa", "PolyAI", "Cognigy", "Ada",
    "Forethought", "Robin AI", "Spellbook", "Luminance", "EvenUp", "Nabla",
    "Suki", "DeepScribe", "Cresta", "Moveworks", "Dataiku", "DataRobot",
    "Arize AI", "WhyLabs", "Galileo", "Patronus AI", "Norm AI",
    # fintech / risk / compliance
    "Marqeta", "Bill.com", "Modern Treasury", "Column", "Alloy", "Unit",
    "Lithic", "Payoneer", "Remitly", "Upstart", "Pagaya", "Zest AI",
    "Socure", "Sift", "Forter", "Riskified", "Signifyd", "Feedzai",
    "ComplyAdvantage", "Hawk AI", "Quantexa", "Unit21", "Checkr", "Persona",
    "Middesk", "Addepar", "iCapital", "Fundrise", "CAIS", "Wealthfront",
    "Betterment", "Public", "Titan", "Guideline", "Human Interest", "Vestwell",
    "Nova Credit", "Tegus", "Clearwater Analytics", "Enfusion", "Ondo Finance",
    "Anchorage Digital", "Fireblocks", "Chainalysis", "TRM Labs", "Paxos",
    # cyber
    "Arctic Wolf", "Huntress", "Expel", "Red Canary", "Exabeam", "Securonix",
    "Hunters", "Semgrep", "Endor Labs", "Socket", "Legit Security", "Apiiro",
    "Cycode", "Island", "Talon", "AppOmni", "Obsidian Security", "Tailscale",
    "Teleport", "StrongDM", "HackerOne", "Bugcrowd", "Tenable", "Rapid7",
    "Cybereason", "Claroty", "Armis", "Axonius", "JupiterOne", "Panther Labs",
    "Cyera", "Sentra", "BigID", "Transcend", "Alation", "Immuta", "Satori",
    # health / insurtech
    "Tempus", "Flatiron Health", "Komodo Health", "Cedar", "Cohere Health",
    "Oscar Health", "Devoted Health", "Clover Health", "Hinge Health",
    "Included Health", "Maven Clinic", "Datavant", "Truveta", "Innovaccer",
    "Health Gorilla", "Garner Health", "Nayya", "Aledade", "Lemonade",
    "Root Insurance", "Hippo", "Next Insurance", "Coalition", "At-Bay",
    "Newfront", "Clearcover", "Assurant",
    # commerce / logistics / vertical SaaS
    "Shopify", "Faire", "Flexport", "project44", "Samsara", "ServiceTitan",
    "Toast", "Olo", "Gopuff", "Instacart", "DoorDash", "Chewy", "Etsy",
    "Coursera", "Duolingo", "Instructure", "Guild", "Handshake",
    # governance / ESG / risk software
    "Watershed", "Persefoni", "Sweep", "Pachama", "AuditBoard", "LogicGate",
    "Diligent", "Hyperproof", "Kolide", "Vanta", "Drata", "Secureframe",
]
LEVER_NAMES += [
    "Motive", "Verkada", "Nuro", "Applied Intuition", "Shield AI", "Skydio",
    "Vannevar Labs", "Saronic", "Epirus", "Varo", "Current", "Greenlight",
    "M1 Finance", "Stash", "Acorns", "Spring Health", "Lyra Health", "Headway",
    "Grow Therapy", "Alma", "Sword Health", "Virta Health", "Omada Health",
    "Carbon Health", "Benchling", "Recursion", "insitro", "EvolutionIQ",
    "Snyk", "Cybereason", "Deep Instinct", "Claroty", "Grip Security",
    "Ironclad", "Evisort", "LinkSquares", "Icertis", "Sardine", "Taktile",
    "Oscilar", "Scienaptic", "Featurespace", "Ripjar",
]
ASHBY_NAMES += [
    "Mistral", "Suno", "Pika", "Luma AI", "Cursor", "Codeium", "Cognition",
    "Magic", "Poolside", "Augment", "Warp", "Zed", "Tabnine", "Continue",
    "Fal", "OctoAI", "RunPod", "Beam", "Turbopuffer", "Marqo", "Chroma",
    "Sardine", "Persona", "Middesk", "Hummingbird", "Greenlite", "Delve",
    "Sprinter Health", "Ambience Healthcare", "OpenEvidence", "Hippocratic AI",
    "Commure", "Fabric", "Rad AI", "Linear", "Clerk", "WorkOS", "Mintlify",
    "Speakeasy", "Knock", "Inngest", "Trigger.dev", "Crux", "Patch",
    "World Labs", "Physical Intelligence", "Skild AI", "Figure AI", "1X",
    "Sakana AI", "Reka AI", "Vellum AI", "Freeplay", "PromptLayer",
    "Norm AI", "Eve", "Harvey AI", "Robin AI", "Garner",
]
KNOWN_WORKDAY.update({
    "U.S. Bank": ("usbank.wd1.myworkdayjobs.com", "USBank_External"),
    "BMO": ("bmo.wd3.myworkdayjobs.com", "External"),
    "BNY Mellon": ("bnymellon.wd1.myworkdayjobs.com", "BNYM"),
    "Western Alliance Bank": ("westernalliancebancorporation.wd1.myworkdayjobs.com", "External"),
    "Webster Bank": ("websterbank.wd1.myworkdayjobs.com", "Webster"),
    "East West Bank": ("eastwestbank.wd1.myworkdayjobs.com", "External"),
    "Synovus": ("synovus.wd1.myworkdayjobs.com", "Synovus"),
    "Wintrust": ("wintrust.wd1.myworkdayjobs.com", "External"),
    "Old National Bank": ("oldnational.wd1.myworkdayjobs.com", "External"),
    "Associated Bank": ("associatedbank.wd1.myworkdayjobs.com", "External"),
    "Pinnacle Financial": ("pnfp.wd1.myworkdayjobs.com", "External"),
    "Texas Capital Bank": ("texascapitalbank.wd1.myworkdayjobs.com", "External"),
    "Northwestern Mutual": ("northwesternmutual.wd5.myworkdayjobs.com", "Careers"),
    "MassMutual": ("massmutual.wd1.myworkdayjobs.com", "External"),
    "New York Life": ("newyorklife.wd1.myworkdayjobs.com", "careers"),
    "Aflac": ("aflac.wd1.myworkdayjobs.com", "External"),
    "Assurant": ("assurant.wd1.myworkdayjobs.com", "Assurant_Careers"),
    "WTW": ("wtw.wd5.myworkdayjobs.com", "WTW_External"),
    "Arthur J. Gallagher": ("ajg.wd1.myworkdayjobs.com", "External"),
    "Brown & Brown": ("bbinsurance.wd1.myworkdayjobs.com", "External"),
    "Markel": ("markel.wd5.myworkdayjobs.com", "Markel_Careers"),
    "W. R. Berkley": ("wrberkley.wd1.myworkdayjobs.com", "External"),
    "Selective Insurance": ("selective.wd1.myworkdayjobs.com", "External"),
    "AllianceBernstein": ("alliancebernstein.wd1.myworkdayjobs.com", "External"),
    "Neuberger Berman": ("nb.wd1.myworkdayjobs.com", "External"),
    "Jefferies": ("jefferies.wd1.myworkdayjobs.com", "Jefferies_Careers"),
    "Stifel": ("stifel.wd5.myworkdayjobs.com", "External"),
    "Piper Sandler": ("pipersandler.wd1.myworkdayjobs.com", "External"),
    "Houlihan Lokey": ("hl.wd1.myworkdayjobs.com", "External"),
    "CME Group": ("cmegroup.wd5.myworkdayjobs.com", "External"),
    "Intercontinental Exchange": ("ice.wd5.myworkdayjobs.com", "ICE"),
    "Cboe": ("cboe.wd1.myworkdayjobs.com", "External"),
    "Tradeweb": ("tradeweb.wd1.myworkdayjobs.com", "External"),
    "MSCI": ("msci.wd1.myworkdayjobs.com", "External"),
    "Morningstar": ("morningstar.wd5.myworkdayjobs.com", "External"),
    "Fitch Group": ("fitchgroup.wd1.myworkdayjobs.com", "External"),
    "FICO": ("fico.wd1.myworkdayjobs.com", "External"),
    "CoreLogic": ("corelogic.wd1.myworkdayjobs.com", "External"),
    "Cigna Group": ("cigna.wd5.myworkdayjobs.com", "Cigna_Careers"),
    "CVS Health": ("cvshealth.wd1.myworkdayjobs.com", "CVS_Health_Careers"),
    "UnitedHealth Group": ("uhg.wd1.myworkdayjobs.com", "External"),
    "Zurich NA": ("zurich.wd1.myworkdayjobs.com", "External"),
    "AXA XL": ("axaxl.wd1.myworkdayjobs.com", "External"),
    "RenaissanceRe": ("renre.wd1.myworkdayjobs.com", "External"),
    "Arch Capital": ("archcapital.wd1.myworkdayjobs.com", "External"),
    "Everest": ("everestglobal.wd1.myworkdayjobs.com", "External"),
})


# --------------------------------------------------------------------------
# 4) EXTRA name pools (round 3) — push the pool past ~1000 real companies.
# --------------------------------------------------------------------------
GREENHOUSE_NAMES += [
    # content / web / no-code
    "Webflow", "Framer", "Contentful", "Sanity", "Storyblok", "Builder.io",
    "Contentstack", "Coda", "Loom", "Vidyard", "Wistia", "Mux", "Cloudinary",
    "Calendly", "Cal.com", "Algolia", "Coveo", "Lucidworks",
    # comms / infra
    "Vonage", "Bandwidth", "Telnyx", "Plivo", "Sinch", "Dynatrace", "Sentry",
    "SendGrid", "Mailgun", "Resend", "Loops", "mParticle", "Heap", "Pendo",
    "FullStory", "LogRocket", "Contentsquare",
    # HR / people / hiring
    "Remote", "Oyster", "Papaya Global", "Multiplier", "Velocity Global",
    "Justworks", "TriNet", "Lattice", "Culture Amp", "15Five", "Leapsome",
    "Betterworks", "Gem", "Fountain", "Findem", "Eightfold", "Beamery",
    "Phenom", "SeekOut", "Greenhouse Software", "Lever",
    # fintech / spend / AP / crypto
    "Melio", "Routable", "Tipalti", "Airbase", "Navan", "Spendesk", "Pleo",
    "Payhawk", "Emburse", "Stampli", "Pigment", "Mosaic", "Cube", "Abacum",
    "Adyen", "Checkout.com", "Rapyd", "Nium", "Airwallex", "Currencycloud",
    "Rho", "Relay", "Novo", "Bluevine", "Found", "MX", "Finicity", "Truv",
    "Pinwheel", "Atomic", "Argyle", "Prove", "Incode", "Jumio", "Onfido",
    "Trulioo", "Sezzle", "Zip", "Splitit", "Addepar", "Pigment",
    "Uniswap Labs", "OpenSea", "Alchemy", "ConsenSys", "Chainlink Labs",
    "Polygon", "Ava Labs", "Offchain Labs", "Matter Labs", "StarkWare",
    "Blockdaemon", "Figment", "Bitwise", "Grayscale", "Galaxy Digital",
    # AI apps round 3
    "Sana Labs", "Dust", "Stability AI", "Photoroom", "Captions", "HeyGen",
    "Descript", "Rev", "Anyword", "Lavender", "Observe.AI", "Level AI",
    "Crescendo", "Dashworks", "Guru", "Kapa AI", "Comet ML", "Rogo", "Legora",
    # cyber round 3
    "Sysdig", "Aqua Security", "Uptycs", "Netskope", "Cato Networks",
    "Ping Identity", "SailPoint", "Saviynt", "BeyondTrust", "CyberArk",
    "Delinea", "Keeper Security", "Dashlane", "Bitwarden", "Recorded Future",
    "Flashpoint", "GreyNoise", "Censys", "RunZero", "Bishop Fox", "Proofpoint",
    "Mimecast", "Tessian", "IRONSCALES", "Cofense",
    # health round 3
    "Transcarent", "Modern Health", "Talkspace", "Cerebral", "Sondermind",
    "Rula", "Sidecar Health", "Sana Benefits", "Verily", "Color Health",
    "Guardant Health", "Freenome", "Adaptive Biotechnologies", "Curative",
    # insurtech round 3
    "Cowbell", "Corvus Insurance", "Resilience", "Counterpart", "Vouch",
    "Embroker", "Pie Insurance", "Thimble", "Sure", "Ethos", "Ladder",
    "Bestow", "Pumpkin", "bolttech",
    # data / analytics / vertical SaaS
    "Amplitude", "ThoughtSpot", "Sigma", "Mode", "Preset", "Metabase",
    "Omni", "Y42", "Select Star", "Atlan", "Secoda", "Monte Carlo",
    "Bigeye", "Metaplane", "Anomalo", "Soda", "Great Expectations",
]
ASHBY_NAMES += [
    "Dust", "Rogo", "Legora", "Crescendo", "Kapa AI", "Dashworks",
    "Runware", "Krea", "Ideogram", "Leonardo AI", "Black Forest Labs",
    "Photoroom", "Captions", "HeyGen", "Descript", "Papercup", "Sana",
    "Observe AI", "Level AI", "Sierra AI", "Rox", "Clay", "Unify",
    "Pylon", "Plain", "Fin AI", "Lindy", "Relevance AI", "Gumloop",
    "Lovable", "Bolt", "v0", "Tempo", "Julius AI", "Rows",
    "Metaview", "Mercor", "Micro1", "Distyl AI", "Sierra",
    "Baseten AI", "Fireworks", "OctoAI AI", "Modal Labs",
    "Cognition AI", "Poolside AI", "Magic AI", "Reflection AI",
]
LEVER_NAMES += [
    "Cerebral", "Talkspace", "Modern Health", "Vouch", "Embroker",
    "Corvus", "Resilience", "Alchemy", "Figment", "Blockdaemon",
    "Netskope", "Uptycs", "Sysdig", "Recorded Future", "GreyNoise",
    "Verily", "Color", "Guardant", "Freenome", "Adaptive",
    "Melio", "Tipalti", "Airwallex", "Rho", "Bluevine", "Novo",
]


# --------------------------------------------------------------------------
# 5) EXTRA name pools (round 4) — final top-up past 1000.
# --------------------------------------------------------------------------
GREENHOUSE_NAMES += [
    "Gusto", "Rippling", "Deel", "Carta", "AngelList", "Mercury", "Wealthsimple",
    "Nord Security", "Malwarebytes", "Huntress Labs", "Cyware", "Anomali",
    "ThreatConnect", "Sumo Logic", "Devo", "Graylog", "Panther", "Tines",
    "Torq", "Swimlane", "D3 Security", "Cyberhaven", "Nightfall", "Metomic",
    "Concentric AI", "Dig Security", "Laminar", "Eureka Security",
    "Databook", "Clari Copilot", "Chorus", "Avoma", "Fathom", "Fireflies",
    "Otter.ai", "Read AI", "Circleback", "Granola", "Supernormal",
    "Ada Health", "K Health", "Buoy Health", "Infermedica", "Suki AI",
    "Notable Health", "Regard", "Aidoc", "Viz.ai", "Cleerly", "PathAI",
    "Paige AI", "Ibex Medical", "Overjet", "Pearl", "VideaHealth",
    "Cohere Health", "Machinify", "Anomaly", "Candid Health", "Adonis",
    "Vim", "Pearl Health", "Stellar Health", "Turquoise Health", "Ribbon Health",
    "Zus Health", "Metriport", "Particle Health", "Rivet Health",
    "Kalderos", "Nirvana Insurance", "Loop", "Sana",
]
ASHBY_NAMES += [
    "Norm", "Delve AI", "Greenlite AI", "Parcha", "Casca", "Sedric",
    "Themis", "Hadrius", "Kompliment", "Automated Compliance",
    "Sardine AI", "Effectiv", "Flagright", "Inscribe", "Ocrolus", "Hyperbound",
]
LEVER_NAMES += [
    "Ocrolus", "Inscribe", "Flagright", "Effectiv", "Hyperbound",
    "Nirvana", "Loop", "Kalderos", "Machinify", "Regard",
]


def build_rows() -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()

    def add(name, kind, **kw):
        key = (kind, kw.get("token") or kw.get("host"))
        if not key[1] or key in seen:
            return
        seen.add(key)
        rows.append({"name": name, "kind": kind, **kw})

    for n in GREENHOUSE_NAMES:
        add(n, "greenhouse", token=KNOWN_GH.get(n, slug(n)))
    for n in LEVER_NAMES:
        add(n, "lever", token=KNOWN_LEVER.get(n, slug(n)))
    for n in ASHBY_NAMES:
        add(n, "ashby", token=KNOWN_ASHBY.get(n, slug(n)))
    for n, (host, site) in KNOWN_WORKDAY.items():
        add(n, "workday", host=host, site=site)
    return rows


def main() -> None:
    rows = build_rows()
    out = ROOT / "ats_candidates.yaml"
    header = (
        "# ============================================================\n"
        "#  候选公司池 — 由 gen_candidates.py 生成，供 verify_boards.py 探测。\n"
        "#  每日 run 不读这个文件；只有验证通过（真的抓到岗）的公司才会被\n"
        "#  写进 ats_companies.yaml。想扩容：往 gen_candidates.py 的名单里加\n"
        "#  真实公司名，重新生成，再让 CI 验证晋升即可（token 猜错的自动淘汰）。\n"
        "# ============================================================\n"
    )
    body = yaml.safe_dump({"companies": rows}, sort_keys=False, allow_unicode=True,
                          width=200, default_flow_style=False)
    out.write_text(header + body)
    by = {}
    for r in rows:
        by[r["kind"]] = by.get(r["kind"], 0) + 1
    print(f"wrote {out} — {len(rows)} candidates: {by}")


if __name__ == "__main__":
    main()
